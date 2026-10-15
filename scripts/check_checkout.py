"""Read-only verification of dependency origins, pins and working trees."""

import argparse
import configparser
import json
import subprocess
from pathlib import Path


def git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


def check(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "upstream.lock.json").read_text())
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported lock schema")
    modules = configparser.ConfigParser(interpolation=None)
    modules.read(root / ".gitmodules")
    results = []
    for dep in manifest["dependencies"]:
        errors = []
        relative = Path(dep["path"])
        directory = (root / relative).resolve()
        if relative.is_absolute() or not directory.is_relative_to(root):
            raise ValueError("Dependency path must stay inside the project")
        sections = [s for s in modules.sections() if modules.get(s, "path", fallback=None) == dep["path"]]
        if len(sections) != 1 or modules.get(sections[0], "url", fallback=None) != dep["repository"]:
            errors.append(".gitmodules source does not match the lock")
        entry = git(root, "ls-files", "--stage", "--", dep["path"]).split()
        if len(entry) != 4 or entry[:3] != ["160000", dep["commit"], "0"]:
            errors.append("Staged gitlink does not match the lock; stage the intended submodule revision")
        if not (directory / ".git").exists():
            errors.append("Submodule not initialized; run git submodule update --init --recursive")
        else:
            if git(directory, "rev-parse", "HEAD") != dep["commit"]:
                errors.append("Checked-out HEAD does not match the lock")
            if git(directory, "remote", "get-url", "origin") != dep["repository"]:
                errors.append("Submodule origin does not match the lock")
            if git(directory, "status", "--porcelain", "--untracked-files=normal"):
                errors.append("Submodule has uncommitted or untracked changes")
        results.append({"name": dep["name"], "commit": dep["commit"], "ok": not errors, "errors": errors})
    if not results:
        raise ValueError("Lock contains no dependencies")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        results = check(args.root)
    except (OSError, ValueError, KeyError, RuntimeError, configparser.Error) as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        return 1
    print(json.dumps({"scope": "Source checkout only; no GPU readiness check", "dependencies": results}, indent=2))
    return 0 if all(item["ok"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
