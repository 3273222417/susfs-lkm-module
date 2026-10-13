# SPDX-License-Identifier: GPL-2.0-only
# Match the real kernel release, not the Android OS version or spoofable uname.
# The packaged KMIs are listed in "$2/kmis" (one <android-os>-<kver> per line),
# so a new upstream KMI needs no change here.
select_kmi() {
  rel="$1"
  while IFS= read -r kmi; do
    [ -n "$kmi" ] || continue
    os="${kmi%-*}"
    kver="${kmi#*-}"
    case "$rel" in
      "$kver".*-"$os"-*) echo "$kmi"; return 0 ;;
    esac
  done < "$2/kmis"
  return 1
}
