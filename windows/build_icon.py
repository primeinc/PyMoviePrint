"""Build and validate a multi-resolution Windows ICO from PyMoviePrint artwork."""
from __future__ import annotations
import argparse
import hashlib
import struct
from pathlib import Path
from PIL import Image

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def build(source: Path, output: Path) -> tuple[int, ...]:
    with Image.open(source) as image:
        image.load()
        if image.width != image.height or image.width < 256:
            raise ValueError("Icon artwork must be square and at least 256x256")
        rgba = image.convert("RGBA")
        output.parent.mkdir(parents=True, exist_ok=True)
        rgba.save(output, format="ICO", sizes=[(size, size) for size in SIZES])
    data = output.read_bytes()
    reserved, image_type, count = struct.unpack_from("<HHH", data)
    if (reserved, image_type, count) != (0, 1, len(SIZES)):
        raise ValueError("Invalid or incomplete Windows ICO header")
    found = set()
    for index in range(count):
        width, height, colors, reserved, planes, bits, length, offset = struct.unpack_from(
            "<BBBBHHII", data, 6 + 16 * index
        )
        size = width or 256
        if size != (height or 256) or size in found or length == 0 or offset + length > len(data):
            raise ValueError(f"Invalid ICO image table entry {index}")
        found.add(size)
    if found != set(SIZES):
        raise ValueError(f"ICO sizes mismatch: {sorted(found)}")
    return tuple(sorted(found))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build PyMoviePrint Windows icon")
    parser.add_argument("--source", type=Path, default=Path(__file__).with_name("PyMoviePrint-icon.png"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("PyMoviePrint.ico"))
    args = parser.parse_args()
    sizes = build(args.source, args.output)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"Built {args.output} ({args.output.stat().st_size} bytes; SHA256 {digest}) sizes={sizes}")


if __name__ == "__main__":
    main()
