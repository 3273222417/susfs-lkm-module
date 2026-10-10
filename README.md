# SUSFS LKM Loader

Independent **KernelSU-compatible module ZIP**, packaging the
[inforcqb/susfs4ksu-lkm](https://github.com/inforcqb/susfs4ksu-lkm) release
`v2.3.0-r17-fix-51c2169` (`51c2169e728c8c5c0f47e733839f6d1f187d504e`).
Not an upstream release, not a Magisk-supported module, and not a boot image.

## Scope

- Initial package: arm64, **android15-6.6 kernel KMI** only (not Android OS version).
- KernelSU installs it under `/data/adb/modules/susfs_lkm_loader/` after staging updates.
- Loads the pinned `.ko` at the standard module `post-fs-data` stage using the upstream loader.
- Detects an existing SUSFS interface before loading; refuses stacking, ambiguous probes and
  unsupported kernel families. Family checks do not guarantee compatibility with every vendor kernel.
- Does not load anything during install, unload active modules, change rule configurations,
  install common boot scripts, inject init RC, modify sepolicy or flash partitions.
- Rules remain managed by FolkSU or another explicitly chosen configuration tool.
- `expose_proc=1` is explicit to make capability-gated LKM extensions available.
- Loading is privileged kernel code execution. The upstream loader performs symbol relocation and
  may adjust vermagic after the kernel rejects it; this is **not proof of ABI compatibility**.
  Use only on backed-up, supported devices with a recovery path.

## Install / disable / uninstall

Install the ZIP in a KernelSU-compatible manager; **reboot manually** to activate it.
Installation uses the standard manager installer, not recovery flashing or Magisk.
Disable or uninstall in the module list, then reboot. No live `rmmod` is attempted.
Deleting an on-disk `.ko` does not unload the running module.
Never load this alongside built-in SUSFS or another SUSFS loader.
Check `/data/adb/modules/susfs_lkm_loader/load.log` and the manager's actual ABI capability probe,
not `lsmod` (SUSFS can hide its module).

**FolkSU dynamic kstat limitation:** its current pre-mount snapshot runs *before* standard module
`post-fs-data.sh`. Loading here is therefore too late for that initial snapshot. A later apply must
remain pending reboot, not fabricate pre-mount metadata. This wrapper does not solve early-loader
integration, and does not automatically call `ksud susfs apply`. Other supported live rules can be
applied explicitly after detection. Test safe-mode/module-disable behavior on your manager before
relying on unattended boot loading. Standard manager safe mode should skip module scripts.

## Build

Requires Python 3, network access and Android NDK on Linux. Set `ANDROID_NDK_HOME`, or
`ANDROID_HOME` (defaults to `~/Android/Sdk`). Run:

```sh
python3 tools/build.py
```

Output: `dist/susfs-lkm-module-0.1.0-android15-6.6.zip`.
Upstream binaries are pinned and checked against SHA-256 from the GitHub release assets.
The corresponding pinned complete upstream source archive, wrapper probe source, license and
provenance are included in each ZIP. No upstream kernel functionality is reimplemented here.
Package building does not install or load the module.

## License and attribution

GPL-2.0-only; see `LICENSE`. Upstream LKM and loader by inforcqb; upstream credits include
susfs4ksu, SukiSU-Ultra and their respective contributors. Wrapper scripts, probe and packaging
by matsuzaka-yuki. Upstream source archive preserves original notices and license files.
