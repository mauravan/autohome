#!/usr/bin/env python3
"""Regenerate components/captive_portal/config_index.h from webui/portal.html.

The captive portal serves this page at GET / (and as the OS captive-probe
catch-all) with Content-Encoding: gzip. Source of truth: webui/portal.html.
"""

import argparse
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "webui" / "portal.html"
HEADER = ROOT / "components" / "captive_portal" / "config_index.h"
ARRAY_COMMENT = (
    "// Generated from webui/portal.html by tools/regen_portal_header.py; do not hand-edit.\n"
)


def format_bytes(data: bytes) -> str:
    lines = []
    for i in range(0, len(data), 10):
        row = data[i : i + 10]
        lines.append("    " + ", ".join(f"0x{b:02x}" for b in row) + ",")
    # Trim trailing comma on the final line to keep the block syntactically valid.
    if lines:
        lines[-1] = lines[-1].rstrip(",")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emit-html", metavar="PATH", help="Write the decompressed HTML to PATH for browser preview"
    )
    args = parser.parse_args()

    html = SOURCE.read_bytes()
    gz = gzip.compress(html, compresslevel=9)

    if args.emit_html:
        Path(args.emit_html).write_bytes(html)
        print(f"Wrote HTML to {args.emit_html}")

    header_text = f"""#pragma once
#include <cstddef>
{ARRAY_COMMENT}
namespace esphome::captive_portal {{

constexpr uint8_t CONFIG_GZ[] PROGMEM = {{
{format_bytes(gz)}}};

constexpr size_t CONFIG_GZ_SIZE = sizeof(CONFIG_GZ);

}}  // namespace esphome::captive_portal
"""
    HEADER.write_text(header_text, "utf-8")
    print(f"Regenerated {HEADER}")
    print(f"  portal.html: {len(html)} bytes raw, {len(gz)} bytes gzipped")


if __name__ == "__main__":
    main()
