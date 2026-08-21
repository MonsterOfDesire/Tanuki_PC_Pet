from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


ICON_OUTPUTS = (
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
)


def build_iconset(source_path, output_directory):
    source_path = Path(source_path)
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as source:
        source = source.convert("RGBA")
        for file_name, size in ICON_OUTPUTS:
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            resized = source.copy()
            resized.thumbnail(
                (size, size),
                Image.Resampling.LANCZOS,
            )
            canvas.alpha_composite(
                resized,
                (
                    (size - resized.width) // 2,
                    (size - resized.height) // 2,
                ),
            )
            canvas.save(output_directory / file_name, format="PNG")
    return tuple(output_directory / name for name, _size in ICON_OUTPUTS)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Create an Apple .iconset directory from TanukiPet's icon.",
    )
    parser.add_argument("source")
    parser.add_argument("output_directory")
    args = parser.parse_args(argv)
    outputs = build_iconset(args.source, args.output_directory)
    print(f"Generated {len(outputs)} icon files in {args.output_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
