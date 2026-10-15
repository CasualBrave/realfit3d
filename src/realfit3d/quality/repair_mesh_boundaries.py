#!/usr/bin/env python3
"""Fill unintended mesh boundary loops while preserving real openings."""

import argparse
from pathlib import Path

import numpy as np
import trimesh


def boundary_components(vertices, faces):
    directed = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    undirected = np.sort(directed, axis=1)
    unique, counts = np.unique(undirected, axis=0, return_counts=True)
    boundary = unique[counts == 1]
    adjacency = {}
    for a, b in boundary:
        adjacency.setdefault(int(a), []).append(int(b))
        adjacency.setdefault(int(b), []).append(int(a))
    remaining = set(adjacency)
    groups = []
    while remaining:
        seed = remaining.pop()
        stack, group = [seed], {seed}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor not in group:
                    group.add(neighbor)
                    remaining.discard(neighbor)
                    stack.append(neighbor)
        edges = np.asarray([(a, b) for a, b in boundary if int(a) in group])
        perimeter = np.linalg.norm(vertices[edges[:, 0]] - vertices[edges[:, 1]], axis=1).sum()
        groups.append((float(perimeter), group, adjacency))
    return sorted(groups, key=lambda item: item[0], reverse=True)


def ordered_cycle(group, adjacency):
    if any(len([n for n in adjacency[v] if n in group]) != 2 for v in group):
        raise RuntimeError("boundary component is not a simple cycle")
    start = min(group)
    ordered, previous, current = [start], None, start
    while True:
        choices = [n for n in adjacency[current] if n in group and n != previous]
        nxt = choices[0]
        if nxt == start:
            return ordered
        if nxt in ordered:
            raise RuntimeError("boundary repeats before closing")
        ordered.append(nxt)
        previous, current = current, nxt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_obj", type=Path)
    parser.add_argument("output_obj", type=Path)
    parser.add_argument("--keep-open", type=int, required=True,
                        help="number of largest-perimeter real openings to preserve")
    args = parser.parse_args()
    if args.output_obj.exists():
        raise FileExistsError(args.output_obj)
    mesh = trimesh.load(args.input_obj, force="mesh", process=False, maintain_order=True)
    vertices = np.asarray(mesh.vertices, dtype=np.float64).copy()
    faces = np.asarray(mesh.faces, dtype=np.int64).copy()
    groups = boundary_components(vertices, faces)
    if len(groups) <= args.keep_open:
        raise RuntimeError(f"only {len(groups)} boundaries; nothing to fill")
    directed = {(int(a), int(b)) for tri in faces
                for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0]))}
    new_faces = [face.tolist() for face in faces]
    filled = []
    for perimeter, group, adjacency in groups[args.keep_open:]:
        cycle = ordered_cycle(group, adjacency)
        center_id = len(vertices)
        vertices = np.vstack((vertices, vertices[np.asarray(cycle)].mean(axis=0)))
        for a, b in zip(cycle, cycle[1:] + cycle[:1]):
            if (a, b) in directed:
                new_faces.append([b, a, center_id])
            elif (b, a) in directed:
                new_faces.append([a, b, center_id])
            else:
                raise RuntimeError(f"cannot orient boundary edge {(a, b)}")
        filled.append({"vertices": len(cycle), "perimeter": perimeter})
    output = trimesh.Trimesh(vertices=vertices, faces=np.asarray(new_faces), process=False)
    trimesh.repair.fix_normals(output, multibody=False)
    args.output_obj.parent.mkdir(parents=True, exist_ok=True)
    output.export(args.output_obj)
    remaining = boundary_components(np.asarray(output.vertices), np.asarray(output.faces))
    print({"source_boundaries": len(groups), "filled": filled,
           "output_boundaries": len(remaining), "output": str(args.output_obj)})


if __name__ == "__main__":
    main()
