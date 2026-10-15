#!/usr/bin/env python3
"""Slice full Stage 4 pose/registration data into explicit finetune windows."""

import argparse
import csv
import hashlib
import json
import pickle
from pathlib import Path

import numpy as np


def parse_window(value):
    try:
        start, end = (int(item) for item in value.split(":", 1))
    except Exception as exc:
        raise argparse.ArgumentTypeError("window must be START:END") from exc
    if start < 0 or end <= start:
        raise argparse.ArgumentTypeError("window must satisfy 0 <= START < END")
    return start, end


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def slice_frames(data, start, end, frame_count):
    output = {}
    for key, value in data.items():
        if isinstance(value, np.ndarray) and value.ndim and value.shape[0] == frame_count:
            output[key] = value[start:end]
        else:
            output[key] = value
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pose_npz", type=Path)
    parser.add_argument("registration_pkl", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--gender", choices=("male", "female", "neutral"), required=True)
    parser.add_argument("--train", action="append", type=parse_window, required=True)
    parser.add_argument("--valid", action="append", type=parse_window, required=True)
    parser.add_argument("--expected-vertices", type=int)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)

    poses = dict(np.load(args.pose_npz))
    with args.registration_pkl.open("rb") as handle:
        registration = pickle.load(handle)
    if "vertices" not in registration:
        raise KeyError("registration has no vertices")
    frame_count = int(np.asarray(registration["vertices"]).shape[0])
    pose_lengths = {
        value.shape[0] for value in poses.values()
        if isinstance(value, np.ndarray) and value.ndim and value.shape[0] > 1
    }
    if frame_count not in pose_lengths:
        raise RuntimeError(f"pose data does not contain {frame_count} frames")
    if args.expected_vertices is not None:
        actual = int(np.asarray(registration["vertices"]).shape[1])
        if actual != args.expected_vertices:
            raise RuntimeError(f"registration vertices {actual} != {args.expected_vertices}")
    all_windows = [("train", item) for item in args.train] + [
        ("valid", item) for item in args.valid
    ]
    for kind, (start, end) in all_windows:
        if end > frame_count:
            raise ValueError(f"{kind} window {start}:{end} exceeds {frame_count}")
    train_frames = {index for start, end in args.train for index in range(start, end)}
    valid_frames = {index for start, end in args.valid for index in range(start, end)}
    overlap = sorted(train_frames & valid_frames)
    if overlap:
        raise RuntimeError(f"train/valid overlap begins at frame {overlap[0]}")

    pose_dir = args.output_dir / "smplx"
    registration_dir = args.output_dir / "registrations"
    split_dir = args.output_dir / "splits"
    pose_dir.mkdir(parents=True)
    registration_dir.mkdir()
    split_dir.mkdir()

    def emit(kind, windows):
        rows = []
        for index, (start, end) in enumerate(windows):
            name = f"{kind}_{index:02d}"
            np.savez_compressed(
                pose_dir / f"{name}.npz",
                **slice_frames(poses, start, end, frame_count),
            )
            with (registration_dir / f"{name}.pkl").open("wb") as handle:
                pickle.dump(
                    slice_frames(registration, start, end, frame_count),
                    handle, protocol=pickle.HIGHEST_PROTOCOL,
                )
            rows.append([name, end - start, args.experiment, args.gender])
        with (split_dir / f"{kind}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "length", "garment", "gender"])
            writer.writerows(rows)
        return rows

    train_rows = emit("train", args.train)
    valid_rows = emit("valid", args.valid)
    manifest = {
        "experiment": args.experiment,
        "gender": args.gender,
        "source_frames": frame_count,
        "registration_shape": list(np.asarray(registration["vertices"]).shape),
        "train_windows": args.train,
        "train_frames": sum(row[1] for row in train_rows),
        "valid_windows": args.valid,
        "valid_frames": sum(row[1] for row in valid_rows),
        "pose_sha256": digest(args.pose_npz),
        "registration_sha256": digest(args.registration_pkl),
    }
    (args.output_dir / "split_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
