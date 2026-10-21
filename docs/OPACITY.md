# Opacity

[Traditional Chinese](OPACITY.zh-TW.md)

## Flow

The simulated mesh supplies the garment's shape. GG's Stage 3 checkpoint supplies
its Gaussian appearance. Before rasterization, the opacity module adjusts each
Gaussian's alpha; the renderer then composites the clothing with the body.
The same setting is passed to the turntable preview and animation renderer.
Changing this setting does not train a model.

- `direct`: multiply each Gaussian opacity by the requested scale.
- `optical_depth`: use `1 - (1 - alpha)^s`.
- `v3`: a trained `4 -> 32 -> 32 -> 8` network uses base opacity and normalized
  canonical position to construct a monotonic function `m(s)`, then applies
  `1 - (1 - alpha)^m(s)`.

All modes preserve the original Gaussian opacity at 1 and hide garments at 0.
V3 shares one requested scale across the outfit but loads one controller per
garment. It controls rendered transparency, not cloth mechanics or refraction.

## Configure a V3 Asset

Keep the controller with the Stage 3 asset it was trained for. In each garment's
catalog entry, add a path relative to `gg_output_root/<garment-name>/`:

```json
{
  "name": "Actor02_upper",
  "opacity_controller": "opacity_controller_v3/controller.pt"
}
```

This fragment supplements the entry's existing slot, label, thumbnail and
source-gender fields. For Actor02 lower, the delivered relative path is
`opacity_controller_v3_valid_cameras/controller.pt`.
The API does not accept checkpoint paths from browser requests.
V3 is selectable only when both selected catalog entries specify a controller.
The default example catalog has no V3 controllers assigned.

## Render

Select the mode and opacity on the outfit form before generating a result.
The current pipeline starts a new try-on job; it does not re-render an existing
job immediately when the slider moves.

`POST /generate` accepts `opacity_mode` and `opacity_scale`, defaulting to
`direct` and `1`. Invalid or non-finite scales are rejected before launching.
CLI uses the same configuration:

```bash
python -m realfit3d.cli --config configs/paths.local.json tryon \
  --betas /trusted/body/betas.pkl --height 1.70 --weight 58 --gender female \
  --upper Actor02_upper --lower Actor02_lower --motion 0 \
  --opacity-mode v3 --opacity-scale 0.5
```

This prints a plan; add `--execute` to run it. Body and garment assets must already
be configured for the chosen IDs. Standalone rendering commands are in the
[GG guide](../upstream/Gaussian-Garments/REALFIT3D_CHANGES.md#opacity-control).

## Train After Stage 3

The optional offline `opacity` stage reads Stage 2 meshes, point clouds and baked
AO/normal maps, camera calibration and image sizes, and the Stage 3 checkpoint.
It freezes GG, renders its original alpha image A1, samples s, and trains only
the controller to make the new alpha image approach `s * A1`.
The output controller is installed alongside the same garment's Stage 3 weights.

```bash
python -m realfit3d.cli --config configs/paths.local.json offline opacity \
  --subject Actor02_upper --sequence Sequence1
```

Review the plan and add `--execute`. The default output is
`gg_output_root/Actor02_upper/opacity_controller_v3/`; existing directories are
rejected. The fork's `train_opacity_v3.py` also provides explicit frame, camera,
step-count and output-directory options.

Training is an asset preparation step, not a per-user request. Importing an
already trained controller skips training.

The current training reader expects a camera-name-keyed calibration dictionary
and camera image directories under `gg_data_root/<subject>/<sequence>`; it reads
a PNG to determine image dimensions. A Stage 2 rendering-camera list alone does
not satisfy that input layout.

The 2026-10-21 supplement includes 50 registered meshes, 50 AO maps and 50 normal
maps per garment, plus Stage 2 point clouds. Actor02 also has full calibration
and image dimensions in `stage1/cameras.json`. These assets are available, but
the training reader does not yet consume this image-free delivery layout.
Full retraining has not been run. Existing-controller inference is unchanged.
