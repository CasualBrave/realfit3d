import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("check_checkout", Path(__file__).resolve().parents[1] / "scripts/check_checkout.py")
CHECKOUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKOUT)
COMMIT = "a" * 40
URL = "https://example.invalid/gg.git"


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dep = self.root / "upstream/GG"
        self.dep.mkdir(parents=True)
        (self.dep / ".git").write_text("gitdir: unused-test-fixture\n")
        self.manifest = {"schema_version": 1, "dependencies": [{"name": "GG", "path": "upstream/GG", "repository": URL, "commit": COMMIT}]}
        self.write_manifest()
        (self.root / ".gitmodules").write_text(f'[submodule "upstream/GG"]\n path = upstream/GG\n url = {URL}\n')

    def write_manifest(self):
        (self.root / "upstream.lock.json").write_text(json.dumps(self.manifest))

    def fake_git(self, root, *args):
        if args[0] == "ls-files":
            return f"160000 {COMMIT} 0\tupstream/GG"
        if args[0] == "rev-parse":
            return COMMIT
        if args[0] == "remote":
            return URL
        if args[0] == "status":
            return ""
        raise AssertionError(args)

    def test_matching_checkout(self):
        with patch.object(CHECKOUT, "git", side_effect=self.fake_git):
            self.assertTrue(CHECKOUT.check(self.root)[0]["ok"])

    def test_uninitialized_checkout(self):
        (self.dep / ".git").unlink()
        with patch.object(CHECKOUT, "git", side_effect=self.fake_git):
            self.assertIn("not initialized", " ".join(CHECKOUT.check(self.root)[0]["errors"]))

    def test_dirty_checkout(self):
        def dirty(root, *args):
            return " M inference.py" if args[0] == "status" else self.fake_git(root, *args)
        with patch.object(CHECKOUT, "git", side_effect=dirty):
            self.assertFalse(CHECKOUT.check(self.root)[0]["ok"])

    def test_wrong_commit(self):
        self.manifest["dependencies"][0]["commit"] = "b" * 40
        self.write_manifest()
        with patch.object(CHECKOUT, "git", side_effect=self.fake_git):
            errors = CHECKOUT.check(self.root)[0]["errors"]
            self.assertTrue(any("gitlink" in error for error in errors))
            self.assertTrue(any("HEAD" in error for error in errors))

    def test_wrong_source(self):
        self.manifest["dependencies"][0]["repository"] = "https://example.invalid/other.git"
        self.write_manifest()
        with patch.object(CHECKOUT, "git", side_effect=self.fake_git):
            errors = CHECKOUT.check(self.root)[0]["errors"]
            self.assertTrue(any(".gitmodules" in error for error in errors))
            self.assertTrue(any("origin" in error for error in errors))

    def test_reject_outside_path(self):
        self.manifest["dependencies"][0]["path"] = "../outside"
        self.write_manifest()
        with self.assertRaises(ValueError):
            CHECKOUT.check(self.root)

    def test_reject_unknown_schema(self):
        self.manifest["schema_version"] = 99
        self.write_manifest()
        with self.assertRaises(ValueError):
            CHECKOUT.check(self.root)


if __name__ == "__main__":
    unittest.main()
