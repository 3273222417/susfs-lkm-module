"""Host tests only: never execute a real module loader or reboot syscall."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
KMIS = {
    "5.10.198-android12-9-test": "android12-5.10",
    "5.10.209-android13-4-test": "android13-5.10",
    "5.15.123-android13-8-test": "android13-5.15",
    "5.15.170-android14-11-test": "android14-5.15",
    "6.1.118-android14-11-test": "android14-6.1",
    "6.6.118-android15-8-test": "android15-6.6",
}


class LoaderTests(unittest.TestCase):
    def run_loader(self, probe, kernel="6.6.118-android15-8-test", marker=None,
                   after=None, missing=False, loader_result=0):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bin").mkdir()
            shutil.copy(ROOT / "module/post-fs-data.sh", root)
            shutil.copy(ROOT / "module/kmi.sh", root)
            (root / "lib").mkdir()
            if not missing:
                for kmi in KMIS.values():
                    (root / "lib" / f"susfs_guard_lkm-{kmi}.ko").write_bytes(b"mock")
            scripts = {
                "susfs_probe": (f'[ ! -f "$TEST_ROOT/loaded" ] || exit {after if after is not None else probe}\n'
                                f"exit {probe}\n"),
                "susfs_insmod": 'echo "$*" > "$TEST_ROOT/loaded"\n' + f'exit {loader_result}\n',
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
            loaded = root / "loaded"
            if loaded.exists():
                expected = f"{root}/lib/susfs_guard_lkm-{KMIS[kernel]}.ko expose_proc=1"
                self.assertEqual(loaded.read_text().strip(), expected)
            return result.returncode, loaded.exists()

    def test_existing_and_unknown_never_load(self):
        self.assertEqual(self.run_loader(0), (0, False))
        self.assertEqual(self.run_loader(12), (1, False))

    def test_disabled_removed_and_wrong_kernel_never_load(self):
        self.assertEqual(self.run_loader(10, marker="disable"), (0, False))
        self.assertEqual(self.run_loader(10, marker="remove"), (0, False))
        for kernel in ("6.12.0-android16-1-test", "6.18.0-android17-1-test",
                       "6.6.118-vendor", "6.6.118-android14-1-test", "5.4.0-android12-1-test"):
            with self.subTest(kernel=kernel):
                self.assertEqual(self.run_loader(10, kernel=kernel), (1, False))

    def test_only_absent_interface_attempts_load(self):
        # Mock stays absent after load: this must report failure, not pretend success.
        self.assertEqual(self.run_loader(10), (1, True))

    def test_all_packaged_kmis_select_correct_binary(self):
        for kernel in KMIS:
            with self.subTest(kernel=kernel):
                self.assertEqual(self.run_loader(10, kernel=kernel, after=0), (0, True))

    def test_missing_binary_and_loader_failure(self):
        self.assertEqual(self.run_loader(10, missing=True), (1, False))
        self.assertEqual(self.run_loader(10, loader_result=7), (7, True))

    def test_install_selection_and_rejection(self):
        for kernel in (*KMIS, "6.12.0-android16-1-test"):
            with self.subTest(kernel=kernel), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copytree(ROOT / "module", root / "module")
                mod = root / "module"
                (mod / "lib").mkdir()
                for kmi in KMIS.values():
                    (mod / "lib" / f"susfs_guard_lkm-{kmi}.ko").write_bytes(b"mock")
                harness = (f'cat() {{ echo "{kernel}"; }}\n'
                           'abort() { echo "$*"; exit 1; }\n'
                           'set_perm_recursive() { :; }\nset_perm() { :; }\nui_print() { :; }\n'
                           '. "$MODPATH/customize.sh"\n')
                result = subprocess.run(["sh", "-c", harness], capture_output=True,
                                        env={**os.environ, "KSU": "true", "ARCH": "arm64", "MODPATH": str(mod)})
                self.assertEqual(result.returncode, 0 if kernel in KMIS else 1)
                self.assertEqual((mod / "skip_mount").exists(), kernel in KMIS)


if __name__ == "__main__":
    unittest.main()
