#!/usr/bin/env python3
"""Map renderer view indices to source image names using camera positions."""

import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("splatting_cameras", type=Path,
                        help="Gaussian-splatting cameras.json")
    parser.add_argument("render_camera_data", type=Path,
                        help="gs2mesh camera_data.json")
    parser.add_argument("output_tsv", type=Path)
    parser.add_argument("--max-error", type=float, default=1e-6)
    args = parser.parse_args()

    splatting = json.loads(args.splatting_cameras.read_text(encoding="utf-8"))
    rendered = json.loads(args.render_camera_data.read_text(encoding="utf-8"))
    unused = set(range(len(splatting)))
    rows = []
    for view_index, camera in enumerate(rendered):
        position = np.asarray(camera["left"]["pos"], dtype=float)
        source_index = min(
            unused,
            key=lambda index: np.linalg.norm(
                position - np.asarray(splatting[index]["position"], dtype=float)
            ),
        )
        error = float(np.linalg.norm(
            position - np.asarray(splatting[source_index]["position"], dtype=float)
        ))
        if error > args.max_error:
            raise RuntimeError(
                f"view {view_index}: nearest camera error {error} exceeds {args.max_error}"
            )
        rows.append((view_index, splatting[source_index]["img_name"], error))
        unused.remove(source_index)
    if len({row[1] for row in rows}) != len(rows):
        raise RuntimeError("mapping is not one-to-one")
    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_tsv.open("w", encoding="utf-8", newline="") as handle:
        handle.write("view\tcamera\tposition_error\n")
        for view, camera, error in rows:
            handle.write(f"{view:03d}\t{camera}\t{error:.12g}\n")
    print(f"wrote {len(rows)} one-to-one mappings to {args.output_tsv}")


if __name__ == "__main__":
    main()
