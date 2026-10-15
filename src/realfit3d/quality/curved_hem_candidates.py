#!/usr/bin/env python3
"""Generate topology-changing curved hem clip candidates for visual review."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import pyvista as pv
import trimesh


def parse_candidate(value):
    try:
        base, amplitude = (float(item) for item in value.split(",", 1))
    except Exception as exc:
        raise argparse.ArgumentTypeError("candidate must be BASE,AMPLITUDE") from exc
    return base, amplitude


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_obj", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--candidate", action="append", type=parse_candidate, required=True)
    parser.add_argument("--horizontal-axis", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--vertical-axis", type=int, choices=(0, 1, 2), default=1)
    parser.add_argument("--center", type=float)
    parser.add_argument("--radius", type=float)
    parser.add_argument("--width-quantiles", default="0.01,0.99")
    args = parser.parse_args()
    if args.horizontal_axis == args.vertical_axis:
        raise ValueError("horizontal and vertical axes must differ")

    mesh = trimesh.load(args.input_obj, force="mesh", process=False)
    mesh = max(mesh.split(only_watertight=False), key=lambda part: len(part.faces))
    mesh.remove_unreferenced_vertices()
    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    q0, q1 = (float(x) for x in args.width_quantiles.split(","))
    lo, hi = np.quantile(vertices[:, args.horizontal_axis], [q0, q1])
    center = float((lo + hi) / 2) if args.center is None else args.center
    radius = float((hi - lo) / 2) if args.radius is None else args.radius
    if radius <= 0:
        raise ValueError("radius must be positive")

    def curve(points, base, amplitude):
        u = np.clip(
            np.abs(points[:, args.horizontal_axis] - center) / radius, 0, 1
        )
        return base + amplitude * u * u

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    records = []
    for base, amplitude in args.candidate:
        warped = vertices.copy()
        warped[:, args.vertical_axis] -= curve(vertices, base, amplitude)
        cells = np.hstack([np.full((len(faces), 1), 3), faces])
        poly = pv.PolyData(warped, cells)
        normal = np.zeros(3)
        normal[args.vertical_axis] = 1
        options = []
        for invert in (False, True):
            clipped = (
                poly.clip(normal=normal, origin=(0, 0, 0), invert=invert)
                .extract_surface().triangulate().clean()
            )
            if not clipped.n_points or not clipped.n_cells:
                continue
            out_faces = clipped.faces.reshape(-1, 4)[:, 1:]
            out_vertices = np.asarray(clipped.points).copy()
            out_vertices[:, args.vertical_axis] += curve(
                out_vertices, base, amplitude
            )
            candidate = trimesh.Trimesh(
                vertices=out_vertices, faces=out_faces, process=False
            )
            options.append(candidate)
        if not options:
            raise RuntimeError(f"clip produced no mesh for {base},{amplitude}")
        kept = max(
            options,
            key=lambda item: np.median(
                np.asarray(item.vertices)[:, args.vertical_axis]
            ),
        )
        kept = max(kept.split(only_watertight=False), key=lambda part: len(part.faces))
        kept.remove_unreferenced_vertices()
        name = f"base{base:.5f}_amp{amplitude:.5f}".replace(".", "p")
        kept.export(args.output_dir / f"template_{name}.obj")
        results.append((name, kept))
        records.append({
            "name": name,
            "base": base,
            "amplitude": amplitude,
            "vertices": len(kept.vertices),
            "faces": len(kept.faces),
            "components": len(kept.split(only_watertight=False)),
            "bounds": np.asarray(kept.bounds).tolist(),
        })

    plot_vertices = vertices[:, [0, 2, 1]]
    center3 = (plot_vertices.min(0) + plot_vertices.max(0)) / 2
    extent = np.ptp(plot_vertices, axis=0).max() / 2 * 1.07
    rows = [("original", mesh)] + results
    fig = plt.figure(figsize=(15, 4.4 * len(rows)), dpi=150, facecolor="white")
    for row, (name, candidate) in enumerate(rows):
        vv = np.asarray(candidate.vertices)[:, [0, 2, 1]]
        ff = np.asarray(candidate.faces)
        for col, (label, azimuth) in enumerate(
            (("front", -90), ("back", 90), ("side", 0))
        ):
            ax = fig.add_subplot(len(rows), 3, row * 3 + col + 1,
                                 projection="3d", proj_type="ortho")
            ax.add_collection3d(Poly3DCollection(vv[ff], facecolor="#c7a979",
                                                 edgecolor="none"))
            ax.set_xlim(center3[0] - extent, center3[0] + extent)
            ax.set_ylim(center3[1] - extent, center3[1] + extent)
            ax.set_zlim(center3[2] - extent, center3[2] + extent)
            ax.view_init(elev=0, azim=azimuth)
            ax.set_axis_off()
            ax.set_title(f"{name} — {label}")
    fig.tight_layout()
    fig.savefig(args.output_dir / "curved_hem_candidates.png",
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    manifest = {"source": str(args.input_obj.resolve()), "center": center,
                "radius": radius, "candidates": records}
    (args.output_dir / "candidate_stats.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
