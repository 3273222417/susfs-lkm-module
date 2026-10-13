"""Host test for tools/susfs_probe.c: the probe is compiled and driven with a mock syscall.

No real reboot(2) is issued and no module is loaded; the mock stands in for the kernel so
every verdict the probe can reach is exercised, including the ambiguous ones.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CC = shutil.which("cc") or shutil.which("gcc")

# Appended to the probe source (one translation unit) so its headers are already included.
SHIM = r'''
#include <stdarg.h>
#include <stdlib.h>
#include <sys/types.h>

uid_t mock_geteuid(void) { return 0; }

long mock_syscall(long number, ...)
{
    const char *scenario = getenv("SCENARIO");
    va_list ap;
    struct { char text[16]; int err; } *reply;

    (void)number;
    va_start(ap, number);
    (void)va_arg(ap, unsigned int);
    (void)va_arg(ap, unsigned int);
    (void)va_arg(ap, unsigned int);
    reply = va_arg(ap, void *);
    va_end(ap);

    if (!strcmp(scenario, "untouched_success")) return 0;   /* consumed, reply left alone */
    if (!strcmp(scenario, "denied")) { errno = EPERM; return -1; }
    if (!strcmp(scenario, "answered")) {
        strcpy(reply->text, "v2.3.0");
        reply->err = 0;
        return 0;
    }
    if (!strcmp(scenario, "err_only")) { reply->err = 0; return 0; }
    errno = EINVAL;                                          /* plain kernel: unhandled magic */
    return -1;
}
'''

EXIT_ABSENT, EXIT_DETECTED, EXIT_UNKNOWN = 10, 0, 12


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not CC:
            raise unittest.SkipTest("no host C compiler")
        cls.tmp = tempfile.TemporaryDirectory()
        source = Path(cls.tmp.name) / "probe.c"
        source.write_text((ROOT / "tools/susfs_probe.c").read_text() + SHIM)
        cls.binary = Path(cls.tmp.name) / "probe"
        build = subprocess.run(
            [CC, "-O2", "-Wall", "-Wextra", "-Werror", "-Dgeteuid=mock_geteuid",
             "-Dsyscall=mock_syscall", str(source), "-o", str(cls.binary)],
            capture_output=True, text=True)
        if build.returncode != 0:
            raise AssertionError(f"probe did not compile:\n{build.stderr}")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_probe(self, scenario):
        result = subprocess.run([str(self.binary)], capture_output=True, text=True,
                                env={**os.environ, "SCENARIO": scenario})
        return result.returncode, result.stdout.strip()

    def test_plain_kernel_reports_absence(self):
        # Both probes rejected with -EINVAL is the only evidence that counts as absent.
        self.assertEqual(self.run_probe("absent"), (EXIT_ABSENT, "No responding SUSFS version/variant interface."))

    def test_responding_interface_is_detected(self):
        code, out = self.run_probe("answered")
        self.assertEqual(code, EXIT_DETECTED)
        self.assertIn("detected", out)

    def test_partial_reply_still_counts_as_detected(self):
        # A changed err alone is a responding interface: never stack on top of it.
        self.assertEqual(self.run_probe("err_only")[0], EXIT_DETECTED)

    def test_untouched_success_is_unknown_not_absent(self):
        # The real reboot(2) never returns 0 for this magic, so a zero result means
        # something swallowed the call: refusing beats loading beside an unknown SUSFS.
        self.assertEqual(self.run_probe("untouched_success")[0], EXIT_UNKNOWN)

    def test_denied_probe_is_unknown_not_absent(self):
        self.assertEqual(self.run_probe("denied")[0], EXIT_UNKNOWN)


if __name__ == "__main__":
    unittest.main()
