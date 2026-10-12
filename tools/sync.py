#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Pin the module to the latest upstream LKM release.

Fetches the newest inforcqb/susfs4ksu-lkm release, records every asset's
SHA-256 into upstream.lock.json, and refreshes module.prop's version metadata.
The build stays reproducible: the lock is what build.py verifies against.
Prints the resolved tag; exits 0 when the lock changed, 100 when already current.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "upstream.lock.json"
PROP = ROOT / "module/module.prop"
REPO = "inforcqb/susfs4ksu-lkm"
API = f"https://api.github.com/repos/{REPO}"


def api_get(url):
    headers = {"User-Agent": "susfs-lkm-module-sync", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        return json.load(response)


def fetch(url):
    headers = {"User-Agent": "susfs-lkm-module-sync"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as response:
        return response.read()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def kmi_range(kmis):
    versions = sorted({k.split("-", 1)[1] for k in kmis},
                      key=lambda v: tuple(int(n) for n in v.split(".")))
    return versions[0], versions[-1]


def main():
    release = api_get(f"{API}/releases/latest")
    tag = release["tag_name"]
    commit = api_get(f"{API}/commits/{tag}")["sha"]

    assets = {}
    kmis = []
    for asset in release["assets"]:
        name = asset["name"]
        if not (name.endswith(".ko") or name == "susfs_insmod"):
            continue
        assets[name] = sha256(fetch(asset["browser_download_url"]))
        if name.endswith(".ko"):
            kmis.append(name.removeprefix("susfs_guard_lkm-").removesuffix(".ko"))
    kmis.sort()
    if not kmis or "susfs_insmod" not in assets:
        sys.exit("unexpected upstream release layout")

    source_sha = sha256(fetch(f"{API}/tarball/{commit}"))
    lock = {"repository": f"https://github.com/{REPO}", "tag": tag, "commit": commit,
            "architecture": "arm64", "supported_kmis": kmis,
            "assets": dict(sorted(assets.items())), "source_sha256": source_sha}

    old = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    if old.get("tag") == tag and old.get("assets") == lock["assets"]:
        print(tag)
        sys.exit(100)

    LOCK.write_text(json.dumps(lock, indent=2) + "\n")

    low, high = kmi_range(kmis)
    text = PROP.read_text()
    code = int(re.search(r"^versionCode=(\d+)", text, re.M).group(1)) + 1
    text = re.sub(r"^version=.*$", f"version={tag}", text, flags=re.M)
    text = re.sub(r"^versionCode=.*$", f"versionCode={code}", text, flags=re.M)
    text = re.sub(r"^description=.*$",
                  "description=KernelSU-compatible SUSFS loader with automatic selection across "
                  f"{len(kmis)} upstream arm64 KMIs ({low}-{high}). No rule management. Reboot required.",
                  text, flags=re.M)
    PROP.write_text(text)
    print(tag)


if __name__ == "__main__":
    main()
