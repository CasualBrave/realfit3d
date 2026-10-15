#!/usr/bin/env python3
"""Run GroundingDINO + SAM2ImagePredictor and build all-view review sheets."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import torch
from torchvision.ops import box_convert


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("render_root", type=Path,
                        help="folder containing numeric view folders with left.png")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--groundingdino-root", type=Path, required=True)
    parser.add_argument("--dino-config", type=Path, required=True)
    parser.add_argument("--dino-weights", type=Path, required=True)
    parser.add_argument("--sam2-root", type=Path, required=True)
    parser.add_argument("--sam2-config", required=True)
    parser.add_argument("--sam2-checkpoint", type=Path, required=True)
    parser.add_argument("--box-threshold", type=float, default=0.35)
    parser.add_argument("--text-threshold", type=float, default=0.25)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--views-per-page", type=int, default=12)
    args = parser.parse_args()

    sys.path[:0] = [str(args.groundingdino_root), str(args.sam2_root)]
    from groundingdino.util.inference import load_image, load_model, predict
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor

    dino = load_model(str(args.dino_config), str(args.dino_weights))
    sam = SAM2ImagePredictor(build_sam2(
        args.sam2_config, ckpt_path=str(args.sam2_checkpoint),
        device=args.device, apply_postprocessing=False,
    ))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records, tiles = [], []
    view_dirs = [path for path in sorted(args.render_root.iterdir())
                 if path.is_dir() and path.name.isdigit() and (path / "left.png").is_file()]
    for view_dir in view_dirs:
        rgb, dino_image = load_image(str(view_dir / "left.png"))
        height, width = rgb.shape[:2]
        boxes, logits, _ = predict(
            dino, dino_image, args.prompt,
            box_threshold=args.box_threshold, text_threshold=args.text_threshold,
        )
        selected = np.zeros((height, width), dtype=bool)
        product_score = 0.0
        if len(boxes):
            boxes_xyxy = box_convert(
                boxes * torch.tensor([width, height, width, height]),
                in_fmt="cxcywh", out_fmt="xyxy",
            ).cpu().numpy()
            sam.set_image(rgb)
            for box, dino_score in zip(boxes_xyxy, logits):
                with torch.inference_mode():
                    masks, sam_scores, _ = sam.predict(
                        box=box, multimask_output=True
                    )
                index = int(np.argmax(sam_scores))
                score = float(dino_score) * float(sam_scores[index])
                if score > product_score:
                    product_score = score
                    selected = masks[index].astype(bool)
        stem = view_dir.name
        np.save(args.output_dir / f"{stem}_mask.npy", selected)
        Image.fromarray(selected.astype(np.uint8) * 255).save(
            args.output_dir / f"{stem}_mask.png"
        )
        overlay = rgb.copy()
        overlay[selected] = (
            overlay[selected] * 0.5 + np.array([0, 150, 255]) * 0.5
        ).astype(np.uint8)
        tile = Image.new("RGB", (600, 310), "white")
        ImageDraw.Draw(tile).text(
            (5, 5),
            f"view {stem} score {product_score:.3f} area {selected.mean():.3%}",
            fill="black",
        )
        for column, image in enumerate((
            Image.fromarray(rgb),
            Image.fromarray(selected.astype(np.uint8) * 255).convert("RGB"),
            Image.fromarray(overlay),
        )):
            image.thumbnail((198, 280))
            tile.paste(image, (column * 200 + (200 - image.width) // 2, 28))
        tiles.append(tile)
        records.append({"view": stem, "product_score": product_score,
                        "area": float(selected.mean()), "boxes": len(boxes)})
        print(records[-1], flush=True)

    per_page = args.views_per_page
    columns = 3
    for start in range(0, len(tiles), per_page):
        page_tiles = tiles[start:start + per_page]
        rows = (len(page_tiles) + columns - 1) // columns
        sheet = Image.new("RGB", (columns * 600, rows * 310), "white")
        for index, tile in enumerate(page_tiles):
            sheet.paste(tile, ((index % columns) * 600, (index // columns) * 310))
        sheet.save(args.output_dir / f"review_{start // per_page + 1:02d}.jpg",
                   quality=92)
    (args.output_dir / "scores.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    print(f"complete: {len(records)} views")


if __name__ == "__main__":
    main()
