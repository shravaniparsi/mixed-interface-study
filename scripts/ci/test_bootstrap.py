"""Pure bootstrap checks; no dependency downloads, installations or app launches."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from prepare_quartz import artifact_path, verify_artifact
from prepare_realworld import BACKEND, FRONTEND, PROJECT


class BootstrapTests(unittest.TestCase):
    def test_jar_paths_cannot_escape_runtime_or_select_platform_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(artifact_path(root, "declared-dependencies/library.jar"), (root / "declared-dependencies/library.jar").resolve())
            for name in ("../outside.jar", "jre21.tar.gz", "/outside.jar"):
                with self.assertRaises(ValueError):
                    artifact_path(root, name)

    def test_corrupt_same_length_artifact_fails_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.jar"
            path.write_bytes(b"good")
            item = {"name": "sample.jar", "size_bytes": 4, "sha256": hashlib.sha256(b"good").hexdigest()}
            verify_artifact(path, item)
            path.write_bytes(b"evil")
            with self.assertRaises(ValueError):
                verify_artifact(path, item)

    def test_backend_and_frontend_are_explicit_independent_commit_pins(self):
        source = json.loads((PROJECT / "manifests/realworld-boundary-registry-v1.json").read_text())
        self.assertEqual(BACKEND[1], source["backend_commit"])
        self.assertEqual(FRONTEND[1], source["frontend_commit"])
        self.assertNotEqual(BACKEND[0], FRONTEND[0])
        for url, commit in (BACKEND, FRONTEND):
            self.assertTrue(url.startswith("https://github.com/"))
            self.assertEqual(len(commit), 40)
            int(commit, 16)


if __name__ == "__main__":
    unittest.main()
