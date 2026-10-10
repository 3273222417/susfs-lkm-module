"""Host tests only: never execute a real module loader or reboot syscall."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LoaderTests(unittest.TestCase):
    def run_loader(self, probe, kernel="6.6.118-android15-8-test", marker=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bin").mkdir()
            shutil.copy(ROOT / "module/post-fs-data.sh", root)
            scripts = {
                "susfs_probe": f"exit {probe}\n",
                "susfs_insmod": 'echo "$*" > "$TEST_ROOT/loaded"\nexit 0\n',
                "cat": f"echo '{kernel}'\n",
            }
            for name, contents in scripts.items():
                path = root / "bin" / name
                path.write_text("#!/bin/sh\n" + contents)
                path.chmod(0o755)
            if marker:
                (root / marker).touch()
            result = subprocess.run(["sh", str(root / "post-fs-data.sh")],
                                    env={**os.environ, "TEST_ROOT": str(root),
                                         "PATH": str(root / "bin") + ":" + os.environ["PATH"]})
            return result.returncode, (root / "loaded").exists()

    def test_existing_and_unknown_never_load(self):
        self.assertEqual(self.run_loader(0), (0, False))
        self.assertEqual(self.run_loader(12), (1, False))

    def test_disabled_removed_and_wrong_kernel_never_load(self):
        self.assertEqual(self.run_loader(10, marker="disable"), (0, False))
        self.assertEqual(self.run_loader(10, marker="remove"), (0, False))
        self.assertEqual(self.run_loader(10, kernel="6.1.0-android14-test"), (1, False))

    def test_only_absent_interface_attempts_load(self):
        # Mock stays absent after load: this must report failure, not pretend success.
        self.assertEqual(self.run_loader(10), (1, True))


if __name__ == "__main__":
    unittest.main()
