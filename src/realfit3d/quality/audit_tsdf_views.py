#!/usr/bin/env python3
"""Audit mapped masks and emit an explicit TSDF view whitelist."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping_tsv", type=Path)
    parser.add_argument("mask_dir", type=Path)
    parser.add_argument("cameras_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--mask-pattern", default="{view:03d}_mask.npy")
    parser.add_argument("--max-area", type=float, default=0.20)
    parser.add_argument("--border", type=int, default=3)
    parser.add_argument("--max-focal", type=float)
    args = parser.parse_args()

    cameras = json.loads(args.cameras_json.read_text(encoding="utf-8"))
    camera_by_name = {record["img_name"]: record for record in cameras}
    rows, accepted = [], []
    with args.mapping_tsv.open(encoding="utf-8") as handle:
        mapping = list(csv.DictReader(handle, delimiter="\t"))
    for record in mapping:
        view = int(record["view"])
        camera = record["camera"]
        mask = np.load(args.mask_dir / args.mask_pattern.format(view=view)).astype(bool)
        border = args.border
        touches = bool(
            mask[:border].any() or mask[-border:].any()
            or mask[:, :border].any() or mask[:, -border:].any()
        )
        area = float(mask.mean())
        focal = float(camera_by_name[camera]["fx"])
        reasons = []
        if area <= 0:
            reasons.append("empty")
        if area > args.max_area:
            reasons.append("area")
        if touches:
            reasons.append("border")
        if args.max_focal is not None and focal > args.max_focal:
            reasons.append("focal")
        keep = not reasons
        if keep:
            accepted.append(view)
        rows.append({"view": view, "camera": camera, "area": area,
                     "touches_border": touches, "focal": focal,
                     "accepted": keep, "reasons": reasons})
    output = {"accepted_views": accepted, "criteria": {
        "max_area": args.max_area, "border": args.border,
        "max_focal": args.max_focal,
    }, "views": rows}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("TSDF_valid =", accepted)
    print(f"accepted {len(accepted)}/{len(rows)}; wrote {args.output_json}")


if __name__ == "__main__":
    main()
