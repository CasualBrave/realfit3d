"""Verify render command propagation without importing a CUDA runtime."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

from realfit3d.adapters.preview import WORKERS
from realfit3d.pipelines.offline import build_plan


class OpacityPipelineTests(unittest.TestCase):
    def test_both_render_commands_receive_identical_control(self):
        source = ast.parse((WORKERS / "run_outfit_preview_pipeline.py").read_text())
        selected = [n for n in source.body if isinstance(n, ast.FunctionDef)
                    and n.name in ("opacity_arguments", "render", "render_turntable")]
        calls = []
        scope = dict(Path=Path, RENDER_ENV_EXTRA={}, run=lambda command, **kwargs: calls.append(command))
        exec(compile(ast.Module(body=selected, type_ignores=[]), "render_commands", "exec"), scope)
        args = SimpleNamespace(gaugar_python="python", gaugar_root=Path("/gg"), bake_samples=4,
                               opacity_mode="v3", opacity_scale=.3,
                               v3_controller=["lower=/assets/lower/controller.pt", "upper=/assets/upper/controller.pt"])
        scope["render"](args, Path("/trajectory.pkl"), Path("/frames"))
        scope["render_turntable"](args, Path("/trajectory.pkl"), 4, Path("/turntable"), 12)
        for command in calls:
            index = command.index("--opacity-mode")
            self.assertEqual(command[index:], ["--opacity-mode", "v3", "--opacity-scale", "0.3",
                             "--v3-controller", args.v3_controller[0], "--v3-controller", args.v3_controller[1]])

    def test_offline_opacity_uses_gg_and_specific_controller_output(self):
        settings = {key: "/configured/" + key for key in
                    ("gaugar_root", "gaugar_python", "gg_output_root", "gg_data_root", "gg_aux_root")}
        plan = build_plan(settings, "opacity", "Actor02_upper").describe()
        self.assertEqual(plan["command"][1], "/configured/gaugar_root/train_opacity_v3.py")
        self.assertIn("--subject", plan["command"])
        self.assertEqual(plan["outputs"],
                         ["/configured/gg_output_root/Actor02_upper/opacity_controller_v3/controller.pt"])


if __name__ == "__main__":
    unittest.main()
