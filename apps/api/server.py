import json
import os
import shutil
import threading
from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from realfit3d.adapters.preview import PreviewRuntime, RuntimeUnavailable, read_status

ROOT = Path(__file__).resolve().parents[2]


def create_app(settings=None, runtime=None):
    if settings is None:
        config = os.environ.get("REALFIT3D_CONFIG")
        settings = json.loads(Path(config).read_text()) if config else {}
    app = Flask(__name__, template_folder=str(ROOT / "apps/web/templates"),
                static_folder=str(ROOT / "apps/web/static"))
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    output = Path(settings.get("output_root", ROOT / "storage")).expanduser().resolve()
    catalog = json.loads(Path(settings.get("catalog", ROOT / "configs/catalog.json")).read_text())
    garments = {g["name"]: g for g in catalog["garments"]}
    for name in garments:
        if not name or name in (".", "..") or any(c in name for c in "/\\"):
            raise ValueError("Invalid catalog asset ID")
    runtime = runtime or PreviewRuntime(settings)
    state = {"body": None, "runs": {}, "lock": threading.Lock()}
    app.extensions["realfit3d"] = state

    def busy():
        return any(info["process"].poll() is None for info in state["runs"].values())

    @app.errorhandler(RuntimeUnavailable)
    def unavailable(exc):
        return str(exc), 503

    @app.get("/")
    def index():
        return render_template("index.html", uppers=[g for g in garments.values() if g["slot"] == "upper"],
                               lowers=[g for g in garments.values() if g["slot"] == "lower"],
                               motions=catalog["motions"], genders=catalog["genders"], enumerate=enumerate)

    @app.get("/garment_thumbnail/<name>")
    def thumbnail(name):
        garment = garments.get(name)
        if garment is None:
            abort(404)
        return send_from_directory(ROOT / "apps/web/static/catalog", garment["thumbnail"])

    @app.get("/body_status")
    def body_status():
        body = state["body"]
        if body is None:
            return jsonify(has_body=False)
        return jsonify(has_body=True, preview_image="/body_preview.png", **{
            key: body[key] for key in ("gender", "height", "weight")})

    @app.get("/body_preview.png")
    def body_image():
        body = state["body"]
        if body is None:
            abort(404)
        response = send_from_directory(body["directory"], "body_preview.png")
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/fit_body")
    def fit_body():
        try:
            height, weight = float(request.form["height"]), float(request.form["weight"])
        except (KeyError, ValueError):
            return "Invalid height or weight", 400
        gender = request.form.get("gender", "female")
        if not (1 <= height <= 2.2 and 25 <= weight <= 180) or gender not in {g["value"] for g in catalog["genders"]}:
            return "Invalid body measurements or gender", 400
        if not state["lock"].acquire(blocking=False):
            return "GPU is busy", 409
        directory = output / "bodies" / uuid4().hex
        try:
            if busy():
                return "GPU is busy", 409
            runtime.check()
            directory.mkdir(parents=True)
            runtime.fit(directory, gender, height, weight)
            old = state["body"]
            state["body"] = dict(directory=directory, betas_path=directory / "betas.pkl",
                                 gender=gender, height=height, weight=weight)
            if old:
                shutil.rmtree(old["directory"], ignore_errors=True)
            return jsonify(preview_image=f"/body_preview.png?t={directory.name}")
        except RuntimeUnavailable:
            raise
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            app.logger.exception("Body worker failed")
            return "Body worker failed; see server log", 500
        finally:
            state["lock"].release()

    @app.post("/discard_body")
    def discard_body():
        if not state["lock"].acquire(blocking=False):
            return "GPU is busy", 409
        try:
            if busy():
                return "GPU is busy", 409
            if state["body"]:
                shutil.rmtree(state["body"]["directory"], ignore_errors=True)
            state["body"] = None
            return jsonify(ok=True)
        finally:
            state["lock"].release()

    @app.post("/generate")
    def generate():
        if not state["lock"].acquire(blocking=False):
            return "GPU is busy", 409
        try:
            if busy():
                return "GPU is busy", 409
            body = state["body"]
            if body is None:
                return "Create a body first", 400
            upper = garments.get(request.form.get("upper"))
            lower = garments.get(request.form.get("lower"))
            if not upper or upper["slot"] != "upper" or not lower or lower["slot"] != "lower":
                return "Select one upper and one lower garment", 400
            try:
                index = int(request.form["motion"])
                if not 0 <= index < len(catalog["motions"]):
                    raise ValueError("Invalid motion index")
                motion = catalog["motions"][index]["path"]
            except (KeyError, ValueError):
                return "Invalid motion", 400
            runtime.check(full=True, motion=motion)
            outfit = lower["name"] + "+" + upper["name"]
            if body["gender"] != "female":
                outfit += "_" + body["gender"]
            run_id = "web_" + uuid4().hex
            directory = output / "outfits" / outfit / "runs_preview" / run_id
            directory.parent.mkdir(parents=True, exist_ok=True)
            command = runtime.command(body, upper, lower, motion, run_id, outfit, output)
            try:
                process = runtime.launch(command, directory.with_suffix(".log"))
            except OSError:
                app.logger.exception("Could not launch pipeline")
                return "Could not launch pipeline; see server log", 500
            state["runs"][run_id] = {"dir": directory, "process": process}
            return jsonify(run_id=run_id)
        finally:
            state["lock"].release()

    def get_run(run_id):
        if run_id not in state["runs"]:
            abort(404)
        return state["runs"][run_id]

    @app.get("/status/<run_id>")
    def status(run_id):
        response = jsonify(read_status(get_run(run_id)))
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/latest_frame/<run_id>")
    def latest_frame(run_id):
        frames = sorted((get_run(run_id)["dir"] / "frames/renders").glob("*.png"))
        response = jsonify(frame=frames[-1].name if frames else None)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/file/<run_id>/<path:relpath>")
    def media(run_id, relpath):
        directory = get_run(run_id)["dir"].resolve()
        path = (directory / relpath).resolve()
        if directory not in path.parents:
            abort(403)
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".mp4"}:
            abort(403)
        return send_from_directory(path.parent, path.name)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
