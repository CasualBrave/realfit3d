#!/usr/bin/env python3
"""Install explicitly reviewed masks into renderer view folders with backup."""

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("render_root", type=Path)
    parser.add_argument("decision_json", type=Path,
                        help='JSON mapping view to mask path or null for empty')
    parser.add_argument("backup_dir", type=Path)
    parser.add_argument("--mask-npy-name", default="left_mask.npy")
    parser.add_argument("--mask-png-name", default="left_mask.png")
    args = parser.parse_args()
    if args.backup_dir.exists():
        raise FileExistsError(args.backup_dir)
    decisions = json.loads(args.decision_json.read_text(encoding="utf-8"))
    args.backup_dir.mkdir(parents=True)
    installed = []
    for view, source in decisions.items():
        view_dir = args.render_root / f"{int(view):03d}"
        image = Image.open(view_dir / "left.png")
        height, width = image.height, image.width
        if source is None:
            mask = np.zeros((height, width), dtype=bool)
        else:
            source_path = Path(source)
            mask = (np.load(source_path) if source_path.suffix == ".npy"
                    else np.asarray(Image.open(source_path)))
            if mask.ndim == 3:
                mask = mask[..., 0]
            mask = mask > 0
            if mask.shape != (height, width):
                raise ValueError(f"{view}: mask {mask.shape} != image {(height, width)}")
        for filename in (args.mask_npy_name, args.mask_png_name):
            destination = view_dir / filename
            if destination.exists():
                target = args.backup_dir / f"{int(view):03d}_{filename}"
                shutil.copy2(destination, target)
        np.save(view_dir / args.mask_npy_name, mask)
        Image.fromarray(mask.astype(np.uint8) * 255).save(
            view_dir / args.mask_png_name
        )
        installed.append({"view": f"{int(view):03d}", "source": source,
                          "area": float(mask.mean())})
    (args.backup_dir / "install_manifest.json").write_text(
        json.dumps(installed, indent=2), encoding="utf-8"
    )
    print(f"installed {len(installed)} reviewed masks; backup={args.backup_dir}")


if __name__ == "__main__":
    main()
