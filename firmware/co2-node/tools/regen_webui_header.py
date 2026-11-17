#!/usr/bin/env python3
"""Regenerate components/web_server/server_index_v3.h with patched INDEX_GZ.

Patches applied to the stock ESPHome v3 web app bundle:
- Replace the header ESPHome logo with the project wordmark from fonts/logo_green.png.
- Force the page/header title to "Configuration" for every build.
- Remove the dark/light mode switch and force light scheme.
- Style all-button sorting groups (e.g. the "Actions" group) as full-width buttons.

Stock bundle source: webui/stock_v3.html.gz
Boot script source:  webui/boot.js (placeholder __LOGO_B64__ is substituted at runtime).
"""

import argparse
import base64
import gzip
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STOCK_GZ = ROOT / "webui" / "stock_v3.html.gz"
BOOT_JS = ROOT / "webui" / "boot.js"
LOGO_PNG = ROOT / "fonts" / "logo_green.png"
HEADER = ROOT / "components" / "web_server" / "server_index_v3.h"
ARRAY_COMMENT = "// Patched (logo + title + light-mode + all-button group styling). Regenerate with tools/regen_webui_header.py; do not hand-edit.\n"


def format_bytes(data: bytes) -> str:
    lines = []
    for i in range(0, len(data), 10):
        row = data[i : i + 10]
        lines.append("    " + ", ".join(f"0x{b:02x}" for b in row) + ",")
    # Trim trailing comma on the final line to keep the block syntactically valid.
    if lines:
        lines[-1] = lines[-1].rstrip(",")
    return "\n".join(lines) + "\n"


def patch_html(html: bytes, logo_b64: str, boot_js: str) -> bytes:
    script = f'<script>\n{boot_js}</script>'
    marker = b'<meta charset=UTF-8>'
    pos = html.find(marker)
    if pos == -1:
        raise RuntimeError("Could not find <meta charset=UTF-8> insertion point")
    patched = html[: pos + len(marker)] + script.encode("utf-8") + html[pos + len(marker) :]

    # Force the page/header title to "Configuration" regardless of device name.
    patched = patched.replace(
        b"setConfig(e){`log`in e||(e.log=this.config.log),this.config=e,document.title=e.title,e.lang&&(document.documentElement.lang=e.lang)}",
        b"setConfig(e){`log`in e||(e.log=this.config.log),e.title=\"Configuration\",document.title=e.title,this.config=e,e.lang&&(document.documentElement.lang=e.lang)}",
    )
    patched = patched.replace(
        b'renderTitle(){return D`<h1>${this.config.title||D`\xc2\xa0`}</h1><div>${[this.config.comment,`started ${this.uptime()}`].filter(e=>e).join(` \xc2\xb7 `)}</div>`}',
        b'renderTitle(){return D`<h1>Configuration</h1><div>${[this.config.comment,`started ${this.uptime()}`].filter(e=>e).join(` \xc2\xb7 `)}</div>`}',
    )
    if b'<h1>Configuration</h1>' not in patched:
        raise RuntimeError("renderTitle patch did not apply")

    # Remove the dark/light mode switch and force light scheme.
    patched = patched.replace(
        b'<a href="#" id="scheme" @click="${()=>{this.scheme=this.scheme===`dark`?`light`:`dark`}}"><iconify-icon icon="mdi:theme-light-dark" class="top-icon"></iconify-icon></a>',
        b'',
    )
    patched = patched.replace(
        b'schemeDefault(){return this.darkQuery.matches?`dark`:`light`}',
        b'schemeDefault(){return `light`}',
    )
    patched = patched.replace(
        b'updated(e){super.updated(e),e.has(`scheme`)&&document.documentElement.style.setProperty(`color-scheme`,this.scheme),e.has(`ping`)&&this.ping&&this.beat.animate(this.frames,1e3)}',
        b'updated(e){super.updated(e),e.has(`ping`)&&this.ping&&this.beat.animate(this.frames,1e3)}',
    )
    patched = patched.replace(
        b',this.darkQuery=window.matchMedia(`(prefers-color-scheme: dark)`)',
        b'',
    )
    if b'mdi:theme-light-dark' in patched or b'this.darkQuery=' in patched:
        raise RuntimeError("scheme switch or darkQuery was not removed")
    return patched


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-html", metavar="PATH", help="Write the patched, decompressed HTML to PATH for browser preview")
    args = parser.parse_args()

    stock_gz = STOCK_GZ.read_bytes()
    html = gzip.decompress(stock_gz)
    logo_b64 = base64.b64encode(LOGO_PNG.read_bytes()).decode("ascii")
    boot_js = BOOT_JS.read_text("utf-8").replace("__LOGO_B64__", logo_b64)

    patched_html = patch_html(html, logo_b64, boot_js)
    patched_gz = gzip.compress(patched_html, compresslevel=9)

    if args.emit_html:
        Path(args.emit_html).write_bytes(patched_html)
        print(f"Wrote patched HTML to {args.emit_html}")

    header_text = HEADER.read_text("utf-8")
    pattern = re.compile(
        r"(constexpr uint8_t INDEX_GZ\[\] PROGMEM = \{).*?(\};)",
        re.DOTALL,
    )

    def repl(match: re.Match) -> str:
        return match.group(1) + "\n" + format_bytes(patched_gz) + match.group(2)

    new_header, count = pattern.subn(repl, header_text)
    if count != 1:
        raise RuntimeError(f"Expected exactly one INDEX_GZ array; matched {count}")

    # Replace the stock generated-source comment with the regeneration instructions.
    new_header = new_header.replace(
        "// Generated from https://github.com/esphome/esphome-webserver",
        ARRAY_COMMENT.strip(),
        1,
    )

    HEADER.write_text(new_header, "utf-8")
    print(f"Regenerated {HEADER}")
    print(f"  INDEX_GZ size: {len(patched_gz)} bytes (was {len(stock_gz)} bytes)")


if __name__ == "__main__":
    main()
