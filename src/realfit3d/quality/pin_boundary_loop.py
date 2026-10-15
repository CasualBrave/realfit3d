#!/usr/bin/env python3
"""Copy a garment dictionary and pin evenly spaced vertices on its highest loop."""

import argparse
import pickle
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_garment", type=Path)
    parser.add_argument("output_garment", type=Path)
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument("--vertical-axis", type=int, choices=(0, 1, 2), default=1)
    args = parser.parse_args()
    if args.output_garment.exists():
        raise FileExistsError(args.output_garment)
    with args.input_garment.open("rb") as handle:
        garment = pickle.load(handle)
    rest = np.asarray(garment["rest_pos"])
    faces = np.asarray(garment["faces"], dtype=np.int64)
    edges = np.sort(np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]],
                                    faces[:, [2, 0]])), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = unique[counts == 1]
    adjacency = {}
    for a, b in boundary:
        adjacency.setdefault(int(a), []).append(int(b))
        adjacency.setdefault(int(b), []).append(int(a))
    remaining, components = set(adjacency), []
    while remaining:
        seed = remaining.pop()
        stack, component = [seed], {seed}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor not in component:
                    component.add(neighbor)
                    remaining.discard(neighbor)
                    stack.append(neighbor)
        components.append(component)
    waist = max(components, key=lambda ids: rest[list(ids), args.vertical_axis].mean())
    if any(len([n for n in adjacency[v] if n in waist]) != 2 for v in waist):
        raise RuntimeError("selected boundary is not a simple loop")
    start = min(waist)
    ordered, previous, current = [start], None, start
    while True:
        nxt = [n for n in adjacency[current] if n in waist and n != previous][0]
        if nxt == start:
            break
        if nxt in ordered:
            raise RuntimeError("loop repeated before closing")
        ordered.append(nxt)
        previous, current = current, nxt
    if len(ordered) < args.count:
        raise RuntimeError(f"loop has {len(ordered)} vertices, fewer than {args.count}")
    positions = np.floor(np.arange(args.count) * len(ordered) / args.count).astype(int)
    pin_ids = np.asarray([ordered[index] for index in positions], dtype=np.int64)
    node_type = np.zeros((len(rest), 1), dtype=np.int64)
    node_type[pin_ids] = 3
    garment["node_type"] = node_type
    metadata = garment.setdefault("pinning_metadata", {})
    metadata.update({"method": "highest_boundary_loop_even_spacing",
                     "count": args.count, "indices": pin_ids.tolist(),
                     "vertical_axis": args.vertical_axis})
    args.output_garment.parent.mkdir(parents=True, exist_ok=True)
    with args.output_garment.open("wb") as handle:
        pickle.dump(garment, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"pinned {args.count} of {len(ordered)} loop vertices; output={args.output_garment}")


if __name__ == "__main__":
    main()
