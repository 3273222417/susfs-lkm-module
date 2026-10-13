#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
[ "$KSU" = true ] || abort "KernelSU-compatible managers only; Magisk is not supported."
[ "$ARCH" = arm64 ] || abort "Only arm64 is packaged."
REAL_KERNEL=$(cat /proc/sys/kernel/osrelease) || abort "Cannot read real kernel release."
. "$MODPATH/kmi.sh" || abort "Missing KMI selector."
KMI=$(select_kmi "$REAL_KERNEL" "$MODPATH") || abort "Unsupported kernel KMI: $REAL_KERNEL."
[ -s "$MODPATH/lib/susfs_guard_lkm-$KMI.ko" ] || abort "Missing packaged LKM for $KMI."
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/post-fs-data.sh" 0 0 0755
set_perm "$MODPATH/bin/susfs_probe" 0 0 0755
set_perm "$MODPATH/bin/susfs_insmod" 0 0 0755
touch "$MODPATH/skip_mount"
ui_print "- Installs loader only; does not load anything during installation."
ui_print "- Selected kernel KMI: $KMI (arm64). Vendor ABI compatibility is not guaranteed."
ui_print "- Reboot to activate. Disable/remove also takes effect after reboot."
ui_print "- Existing SUSFS is never replaced or unloaded."
ui_print "- FolkSU dynamic kstat pre-mount snapshots are NOT supported by this loading stage."
