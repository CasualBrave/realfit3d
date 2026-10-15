"""Read-only inventory; presence is not proof of model compatibility."""
import json
from pathlib import Path
import subprocess

from realfit3d.settings import ROOT


def inspect(settings, probe=False):
    results = []
    keys = ('ccraft_python', 'gaugar_python', 'reconstruction_python', 'contourcraft_root',
            'gaugar_root', 'actorshq_root', 'ccraft_data_root', 'cmu_root', 'body_model_root',
            'reference_motion', 'checkpoint', 'gg_data_root', 'gg_output_root', 'gg_aux_root', 'actorshq_data_root')
    for key in keys:
        value = settings.get(key)
        results.append(dict(name=key, ok=bool(value and Path(value).exists()), path=value))
    lock = json.loads((ROOT / 'upstream.lock.json').read_text())
    for dep in lock['dependencies']:
        directory = ROOT / dep['path']
        process = subprocess.run(['git', '-C', str(directory), 'rev-parse', 'HEAD'], capture_output=True, text=True)
        results.append(dict(name=dep['name'] + ':pin', ok=process.returncode == 0 and process.stdout.strip() == dep['commit']))
    if probe:
        modules = {'ccraft_python': ['torch', 'smplx', 'numpy', 'scipy', 'open3d', 'moviepy'],
                   'gaugar_python': ['torch', 'bpy', 'aitviewer', 'diff_gaussian_rasterization'],
                   'reconstruction_python': ['torch', 'sam2', 'groundingdino', 'open3d', 'pyvista']}
        for key, names in modules.items():
            if not settings.get(key) or not Path(settings[key]).is_file():
                continue
            code = ('import importlib.util,json; '
                    f'print(json.dumps({{n: importlib.util.find_spec(n) is not None for n in {names!r}}}))')
            try:
                response = subprocess.run([settings[key], '-c', code], capture_output=True, text=True, timeout=30)
                found = json.loads(response.stdout) if response.returncode == 0 else {}
                results.append(dict(name=key + ':imports', ok=bool(found) and all(found.values()), modules=found))
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                results.append(dict(name=key + ':imports', ok=False, error=str(exc)))
    return dict(checks=results, paths_ready=all(r['ok'] for r in results), gpu_parity_verified=False,
                opacity='blocked: V3 implementation/checkpoint not delivered',
                note='Paths/import specs only; no model is loaded, no training or CUDA inference is run.')
