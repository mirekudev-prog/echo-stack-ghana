#!/usr/bin/env python3
"""Generate PWA icon PNGs from a simple base64-encoded 512x512 template."""

import base64
import os

# Simple solid color PNG with EchoStack gold (#C8962E) and Ghana colors as gradient
# This creates a basic placeholder — replace with proper designed icons later


def create_simple_png(size, bg_color="#C8962E", accent_color="#0D1B2A"):
    """Create a minimal PNG with solid color (no external dependencies)."""
    import struct
    import zlib

    def png_chunk(chunk_type, data):
        chunk_len = len(data)
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", chunk_len) + chunk_type + data + struct.pack(">I", crc)

    # PNG signature
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk
    width, height = size, size
    bit_depth, color_type, compression, filter_method, interlace = 8, 2, 0, 0, 0
    ihdr_data = struct.pack(
        ">IIBBBBB",
        width,
        height,
        bit_depth,
        color_type,
        compression,
        filter_method,
        interlace,
    )
    ihdr = png_chunk(b"IHDR", ihdr_data)

    # IDAT chunk (image data)
    raw_data = b""
    for y in range(height):
        raw_data += b"\x00"  # filter type: none
        for x in range(width):
            # Simple gradient: gold at top, transitioning to dark blue at bottom
            ratio = y / height
            r = int(
                int(bg_color[1:3], 16) * (1 - ratio)
                + int(accent_color[1:3], 16) * ratio
            )
            g = int(
                int(bg_color[3:5], 16) * (1 - ratio)
                + int(accent_color[3:5], 16) * ratio
            )
            b = int(
                int(bg_color[5:7], 16) * (1 - ratio)
                + int(accent_color[5:7], 16) * ratio
            )
            raw_data += bytes([r, g, b])

    compressed = zlib.compress(raw_data, 9)
    idat = png_chunk(b"IDAT", compressed)

    # IEND chunk
    iend = png_chunk(b"IEND", b"")

    return signature + ihdr + idat + iend


if __name__ == "__main__":
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    os.makedirs(icons_dir, exist_ok=True)

    sizes = [192, 512]
    for s in sizes:
        png = create_simple_png(s)
        path = os.path.join(icons_dir, f"icon-{s}.png")
        with open(path, "wb") as f:
            f.write(png)
        print(f"OK: Created {path} ({len(png)} bytes)")

    print(f"\nIcons saved to {icons_dir}/")
