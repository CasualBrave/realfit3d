# Opacity Integration Record: 2026-10-20

Maintainer record. User workflow: [English](OPACITY.md) /
[Traditional Chinese](OPACITY.zh-TW.md).

GG implementation commit: `0a04dbf7fc4d233b64dce24481148a9cac0f4d28`.

## Source

Source root read without modification:
`/home/vtongroup/iismtl5197096_actor1267_delivery_20261020/Gaussian-Garments`.
The delivery does not identify a Git revision for these files; SHA256 identifies
the inspected source bytes:

| File | SHA256 |
|---|---|
| opacity_controller_v3_common.py | d9f0d2f25f1476e72466e1f34baadf15a559bca7064eff2e40098a1d39094d68 |
| inference_opacity.py | 9e9dc5917850c53e1dd7e4b0cd12780f899de685a6a8775369e9f5e9993c6bd0 |
| train_opacity_controller_v3.py | 68ff83895b0816c717b3b81719767fec73040712a13f8b9e59a25f8215fef52e |
| opacity_controller_common.py | f9e596bdd54a46c0217d4915d08fcc06074e9c48a8ad1585e479a32aec6a29ee |

The fork retains the spline equations, network/state-dict layout, canonical
normalization, and training objective. Runtime validation and CLI mappings are
new. Training combines the delivered helpers in a subject/sequence-based entry,
allows explicit cameras/frame splits, records the Stage 3 SHA256, and rejects
existing output directories. The fixed Actor02/epoch-5 restriction is removed.

## Real Checkpoints

| Asset | SHA256 |
|---|---|
| Actor02_upper/opacity_controller_v3/controller.pt | 4d7f0dbd2e31c613761fd10d18665885b17d5ed4b6a18aeca2ba812395cfda5d |
| Actor02_lower/opacity_controller_v3_valid_cameras/controller.pt | 255e9b0dea842e228b49dd8c52fc6f7ac3aca2d0c66283514ba89c755d458d61 |

Actor02 assets were copied into `/home/vtongroup/lin/opacity-validation/assets/`.
Tests use `gaugar-rtx5090/bin/python` and an RTX 5090. Generated meshes, bakes,
images, temporary files and caches stay below `lin/opacity-validation/`.
Existing group checkouts, assets and environments were not edited.

## Rendering Results

`tests/smoke_opacity_render.py` runs one copied trajectory frame through:
original, repeated original, V3 at 1, V3 at 0.5, V3 at 0, and lean V3 at 0.5.
Images are 940 x 1280 RGB.

Results: `/home/vtongroup/lin/opacity-validation/regression-02/report.json`.
Each command's output is saved in a separate `.log` beside that report.

| Comparison | Maximum 8-bit channel difference | Changed pixels |
|---|---:|---:|
| Original against repeated original | 1 | 1 |
| V3 at 1 against original | 1 | 10 |
| Lean against turntable at V3 0.5 | 1 | 12 |

Gaussian opacity tensors have exact endpoints in unit tests. Independently
rendered PNGs are not byte-identical. Image acceptance allows at most one channel
level on at most 0.01% of pixels; the repeated baseline also exhibits rounding
variation. V3 at 0.5 changes 106,796 pixels, and V3 at 0 changes 106,790 pixels
relative to the original. The half-opacity image was visually inspected.

The initial regression-01 run used byte equality and failed on 10/8 one-level
differences. The second run adds a repeated-original control and records explicit
tolerances. Both reports remain available.

Blender 3.6 emits an add-on cleanup warning at interpreter exit. Rendering exits
with code 0 and all expected images exist; no environment changes were made.

## Remaining Acceptance

Local checks passed: 34 RealFit3D unit tests, 10 fork controller/training-helper
tests, and Playwright at 1440 x 1000 and 390 x 844. Browser checks cover slider
values, mode submission, disabled V3 for unconfigured assets, and horizontal overflow.

- The Web/API, CLI, command propagation and mobile/desktop interface are tested
  separately from full body fitting and CC simulation. No full Web GPU job has
  been accepted yet.
- The generalized training entry has CPU data-layout/loss tests and a GPU
  environment import/help check. Full training requires Actor02 Stage 2 meshes,
  point clouds, AO/normal maps and camera images, absent from this inference
  delivery. No replacement controller was trained or published.
- Real overlapping transparent layers and the existing GG visibility/body-depth
  treatment require separate visual cases. The integration keeps that treatment.
