#!/usr/bin/env python3
"""Build one product unit: identity -> compile -> flash -> label -> CSV row.

Usage: python3 build_unit.py --serial AH-CO2-0001 --port /dev/ttyACM0 [--mac XX:..]
Reads MAC via esptool if not given. Renders product-<last4>.yaml from
product.yaml, compiles a SIGNED image, flashes over USB, writes label.svg
(Wi-Fi join QR + setup URL QR) and appends production/units.csv.

Requires: esphome, esptool, segno (pip install segno) [QR optional fallback].
"""
import argparse
import csv
import re
import secrets
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FW = HERE.parent / "firmware" / "co2-node"


def run(*a):
    print("+", " ".join(a))
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        sys.exit(r.returncode)
    return r.stdout


def read_mac(port):
    out = run("esptool.py", "--chip", "esp32c3", "-p", port, "read_mac")
    m = re.search(r"MAC: ([0-9a-f:]{17})", out)
    if not m:
        sys.exit("could not read MAC")
    return m.group(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", required=True)
    ap.add_argument("--port", required=False, default="")
    ap.add_argument("--mac", default="")
    ap.add_argument("--render-only", action="store_true",
                    help="only render product-<last4>.yaml, no flash")
    ap.add_argument("--out-dir", default="",
                    help="write product yaml here (default firmware/co2-node/)")
    a = ap.parse_args()
    if a.render_only and not a.mac:
        sys.exit("build_unit.py: --render-only needs --mac (no hardware touched)")
    mac = a.mac or read_mac(a.port)
    last4 = mac.replace(":", "")[-4:].lower()
    ap_pass = secrets.token_urlsafe(9)[:12]
    dev = f"co2-sensor-{last4}"
    tpl = (FW / "product.yaml").read_text()
    unit = (tpl.replace('device_name: "co2-sensor-XXXX"', f'device_name: "{dev}"')
               .replace('friendly_name: "CO2 Sensor XXXX"',
                        f'friendly_name: "CO2 Sensor {last4}"')
               .replace('ap_ssid: "co2-setup-XXXX"', f'ap_ssid: "co2-setup-{last4}"')
               .replace('ap_password_sub: "REPLACE-12CHAR"',
                        f'ap_password_sub: "{ap_pass}"'))
    outdir = Path(a.out_dir) if a.out_dir else FW
    outdir.mkdir(parents=True, exist_ok=True)
    yf = outdir / f"product-{last4}.yaml"
    yf.write_text(unit)
    if a.render_only:
        print(f"rendered {yf} (no flash, no units.csv)")
        return
    run("esphome", "compile", str(yf))
    run("esphome", "upload", str(yf), "--device", a.port)
    # label
    try:
        import segno
        join = f"WIFI:T:WPA;S:co2-setup-{last4};P:{ap_pass};;"
        segno.make(join).save(HERE / f"wifi-{last4}.png", scale=6)
        segno.make("http://192.168.4.1").save(HERE / f"setup-{last4}.png", scale=6)
        qr = "png"
    except ImportError:
        qr = "segno-missing"
    svg = ((HERE / "label.svg").read_text()
           if (HERE / "label.svg").exists() else "<svg/>\n")
    (HERE / f"label-{last4}.svg").write_text(
        svg.replace("SSID", f"co2-setup-{last4}").replace("PASS", ap_pass))
    csvp = HERE / "units.csv"
    new = not csvp.exists()
    with open(csvp, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["serial", "mac", "device", "ap_ssid", "ap_pass",
                        "qr", "firmware"])
        w.writerow([a.serial, mac, dev, f"co2-setup-{last4}", ap_pass,
                    qr, "1.0.0"])
    print(f"unit {a.serial} {dev} done (label-{last4}.svg, units.csv)")


if __name__ == "__main__":
    main()
