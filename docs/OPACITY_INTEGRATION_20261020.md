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

Initial 2026-10-20 checks passed: 34 RealFit3D unit tests, 10 fork controller/training-helper
tests, and Playwright at 1440 x 1000 and 390 x 844. Browser checks cover slider
values, mode submission, disabled V3 for unconfigured assets, and horizontal overflow.

- The Web/API, CLI, command propagation and mobile/desktop interface are tested
  separately from full body fitting and CC simulation. No full Web GPU job has
  been accepted yet.
- The generalized training entry has CPU data-layout/loss tests and a GPU
  environment import/help check. Stage 2 assets were added on 2026-10-21 and
  verified as recorded below. Fork `5c03d7e` adds image-free camera loading and
  passes the Actor02 metadata checks below. No replacement controller was
  trained or published.
- Real overlapping transparent layers and the existing GG visibility/body-depth
  treatment require separate visual cases. The integration keeps that treatment.

## Stage 2 Supplement: 2026-10-21

The delivery now includes `outputs/frontend_handoff_actor1267/STAGE2_SUPPLEMENT_20261021.md`
and `stage2_supplement_manifest.json`. Read-only verification of every manifest
entry passed: 1,527 files, 920,091,559 bytes, no missing files or size/hash mismatches.
Each of Actor01, Actor02 upper/lower, Actor06 upper/lower and Actor07 upper/lower
has meshes, AO maps and normal maps for exactly frames 0–49. Stage 2 template
and sequence point-cloud/binding files are also present.

For Actor02, all 50 frames of each garment match its Stage 1 template's vertex
count, face count and ordered vertex-index faces: upper 7,999 vertices / 15,769
faces; lower 8,000 / 15,687. AO and normal maps are 512 × 512. This check does not
establish UV/bake correspondence or rendering parity.

Actor02 `stage1/cameras.json` contains 160 camera-name-keyed calibrations with
intrinsics, extrinsics and image shapes. Each Stage 2 camera list selects 60
cameras; all selected names and image dimensions match Stage 1, and focal values
match within 1e-3 pixels. The Stage 2 lists are rendering metadata; the full
calibration dictionary supplies the principal point and world-to-camera transform.

The delivery contains no raw camera-image input tree. Fork `5c03d7e` reads the
Stage 1 calibration, including image shapes, and uses the Stage 2 list to select
views. It checks dimensions, focal lengths and poses before creating training
cameras. V3 alpha calibration does not use RGB pixel values as training targets.
Stage 3 retraining, in contrast, requires original RGB, masks and body inputs.

The four source-code hashes and both Actor02 controller hashes above are
unchanged. The supplement adds training assets, not a new opacity algorithm.
Actor06 upper and Actor07 lower retain the Stage 3 overrides in
`frontend_runtime_modes.json`; their Stage 2 folders do not replace those models.
Actor08 is not included in this supplement. No GPU workload or remote file write
was performed during this verification.

## Image-Free Camera Reader: 2026-10-21

Implementation: GG fork `5c03d7e9a18a0cc2caaa6a30be24598647714003`.
The controller architecture, loss, optimizer and checkpoint format are unchanged.
RealFit3D's offline planner accepts the same image-free asset layout.

Local tests passed: 23 fork tests and 36 RealFit3D tests, including missing
calibration, duplicate views, mismatched focal lengths/poses/dimensions, legacy
image inputs and camera construction with a CPU stub. On cvlab-5090-p, the
CPU-only reader passed for Actor02 upper and lower against the read-only delivery:

- All 60 listed views per garment matched calibration; rotation and camera-center
  errors passed the absolute 1e-4 tolerance, focal lengths passed 1e-3 pixels.
- The default eight selected views were Cam005, Cam037, Cam077, Cam110, Cam126,
  Cam139, Cam149 and Cam160, each with `[height, width] = [1022, 747]`.
- Both calibration files: `6838e070fb9a64cf420c7de8738ac5005feb0c3918f95512c8add14da53fe150`.
- Upper view list: `c9fc7ba157622339119c6760ecbb33cd08ef45993585689779e84caccbc5a522`.
- Lower view list: `48aa512623df9bd4219143a2a789841d13335c0d0975658c33bcbdea52ad28fa`.

Only code clones under `/home/vtongroup/lin/` were updated. The reader did not
load images, models or CUDA, write to delivery assets, or run training. Full
controller retraining and end-to-end Web GPU acceptance remain separate tests.
