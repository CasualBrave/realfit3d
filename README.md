# RealFit3D

A research virtual try-on integration built on
[Gaussian Garments](https://github.com/eth-ait/Gaussian-Garments),
ContourCraft, and ActorsHQ preprocessing.

The website, API, and workflow adapters live here. GG is included as a
**pinned submodule of our maintained fork**.
Detailed GG changes: [English](upstream/Gaussian-Garments/REALFIT3D_CHANGES.md) |
[Traditional Chinese](upstream/Gaussian-Garments/REALFIT3D_CHANGES.zh-TW.md).

## Status

The local web interface, CLI, and runtime adapters are implemented.
**End-to-end GPU try-on and training validation are pending.**
Opacity V3 code and Actor02 controller files have been located in a remote
delivery; integration is scheduled after source and asset review.

## Quick Start

Python 3.10+ and Git are required for the source checkout check.

```bash
git clone --recurse-submodules https://github.com/CasualBrave/realfit3d.git
cd realfit3d
python scripts/check_checkout.py
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m apps.api.server
```

Open http://127.0.0.1:5000. Without GPU runtime configuration, generation requests return 503.
Use `PORT=5001` if port 5000 is occupied.

Copy `configs/paths.example.json` to `configs/paths.local.json`, configure the
runtime/data paths, and set `REALFIT3D_CONFIG` to that file before starting GPU
work. GG, ContourCraft, and reconstruction need their own environments and assets;
the web `.venv` contains the API and interface dependencies.

**Local, single-user, single-process use only.** There is no authentication.
Do not expose the service publicly or run Web and CLI GPU jobs concurrently.
Do not execute upstream installation scripts without reviewing them.

## Documentation

| Topic | Guide |
|---|---|
| GG fork changes, sources, and exclusions | [English](upstream/Gaussian-Garments/REALFIT3D_CHANGES.md) / [Traditional Chinese](upstream/Gaussian-Garments/REALFIT3D_CHANGES.zh-TW.md) |
| Web configuration, API, and deployment limits | [Web integration](docs/WEB.md) (Traditional Chinese) |
| Offline stages, CLI, prerequisites, and acceptance gaps | [Integration status](docs/INTEGRATION_STATUS.md) (Traditional Chinese) |
| Dependency sources and pinned versions | [Upstream dependencies](docs/UPSTREAM.md), [version lock](upstream.lock.json) |
| Fork/submodule development workflow | [Development](docs/DEVELOPMENT.md) (Traditional Chinese) |

For an existing checkout, `git submodule update --init --recursive` selects the
versions recorded by this project, not the latest upstream versions.

## Data and Validation

Datasets, body models, checkpoints, generated outputs, and private configuration
are not bundled. Obtain authorized assets separately and follow their terms.
Runtime configuration must point to these assets before generation.

Run CPU tests with `python -m unittest discover -s tests -v` in the configured
development environment. Source checkout checks do not load models or install CUDA.

Release licensing is under review. Dependency sources and terms are tracked in
[upstream notes](docs/UPSTREAM.md).
