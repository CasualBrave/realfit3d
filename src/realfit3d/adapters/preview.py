"""Command boundary for the preserved handoff pipeline, without GPU imports."""

import json
import os
import subprocess
from pathlib import Path

WORKERS = Path(__file__).resolve().parents[1] / "workers" / "contourcraft"


class RuntimeUnavailable(RuntimeError):
    pass


class PreviewRuntime:
    def __init__(self, settings):
        self.settings = settings

    def path(self, key):
        value = self.settings.get(key)
        if not value:
            raise RuntimeUnavailable(f"GPU runtime is not configured: {key}")
        return Path(value).expanduser().resolve()

    def check(self, full=False, motion=None):
        keys = ["ccraft_python", "contourcraft_root", "body_model_root", "reference_motion"]
        if full:
            keys += ["gaugar_python", "gaugar_root", "checkpoint"]
        for key in keys:
            path = self.path(key)
            if not path.exists():
                raise RuntimeUnavailable(f"Missing runtime path: {key}: {path}")
            if key.endswith("python") and not os.access(path, os.X_OK):
                raise RuntimeUnavailable(f"Python executable is not executable: {path}")
        if full:
            for filename in ["render_lean.py", "render_turntable.py", "inference.py"]:
                if not (self.path("gaugar_root") / filename).is_file():
                    raise RuntimeUnavailable(f"GG handoff runtime requires {filename}; see docs/WEB.md")
            if motion and not (self.path("contourcraft_root") / motion).is_file():
                raise RuntimeUnavailable(f"Missing motion: {motion}")

    def fit(self, directory, gender, height, weight):
        common = [str(self.path("ccraft_python"))]
        commands = [
            common + [str(WORKERS / "fit_body_from_measurements_fast.py"),
                      "--body-model-root", str(self.path("body_model_root")),
                      "--gender", gender, "--height", str(height), "--weight", str(weight),
                      "--output-betas", str(directory / "betas.pkl"), "--patience", "50"],
            common + [str(WORKERS / "render_body_preview.py"),
                      "--betas-path", str(directory / "betas.pkl"),
                      "--output-image", str(directory / "body_preview.png"),
                      "--body-model-root", str(self.path("body_model_root")),
                      "--reference-motion", str(self.path("reference_motion"))],
        ]
        for command in commands:
            subprocess.run(command, cwd=self.path("contourcraft_root"), check=True,
                           capture_output=True, text=True)
        for name in ["betas.pkl", "body_preview.png"]:
            if not (directory / name).is_file():
                raise RuntimeError(f"Worker did not produce {name}")

    def command(self, body, upper, lower, motion, run_name, outfit, output):
        command = [str(self.path("ccraft_python")), str(WORKERS / "run_outfit_preview_pipeline.py"),
                   "--garment-names", lower["name"], upper["name"],
                   "--source-genders", lower["source_gender"], upper["source_gender"],
                   "--gender", body["gender"], "--height", str(body["height"]),
                   "--weight", str(body["weight"]), "--precomputed-betas", str(body["betas_path"]),
                   "--motion", str(self.path("contourcraft_root") / motion),
                   "--run-name", run_name, "--outfit-name", outfit, "--output-root", str(output),
                   "--pin-waistband-garments", lower["name"],
                   "--pin-waistband-if-snug-garments", lower["name"]]
        for key in ["contourcraft_root", "gaugar_root", "body_model_root", "checkpoint", "ccraft_python", "gaugar_python"]:
            command.extend(["--" + key.replace("_", "-"), str(self.path(key))])
        return command

    def launch(self, command, log_path):
        with log_path.open("w") as log:
            return subprocess.Popen(command, cwd=self.path("contourcraft_root"), stdout=log,
                                    stderr=subprocess.STDOUT)


def read_status(info):
    try:
        payload = json.loads((info["dir"] / "status.json").read_text())
        if not isinstance(payload, dict):
            raise ValueError("Status must be an object")
    except (OSError, ValueError):
        payload = {"phase": "starting", "message": "Waiting for worker status"}
    code = info["process"].poll()
    if code is not None and (code != 0 or payload.get("phase") not in ("done", "error")):
        payload.update(phase="error", message=f"Worker exited ({code}); inspect the run log.")
    if payload.get("preview_ready"):
        payload["turntable_frames"] = len(list((info["dir"] / "turntable").glob("angle_*.png")))
    if payload.get("phase") == "full_rendering":
        payload["rendered_frames"] = len(list((info["dir"] / "frames/renders").glob("*.png")))
    return payload
