"""
Packages addon/ArchipelagoWoW and addon/ArchipelagoWoW_Bridge into addons.zip for a
release -- the equivalent, for this project, of WEBFISHING's root-level
mwmw.Archipelago.zip: a ready-to-download bundle a player unzips directly into their WoW
installation's Interface/AddOns folder, no build step of their own required.

Usage:
    python tools/build_addons_zip.py

Produces ./addons.zip containing both addon folders side by side (ArchipelagoWoW/... and
ArchipelagoWoW_Bridge/...), exactly as they need to sit inside Interface/AddOns.
"""
from __future__ import annotations

import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ADDON_DIR = ROOT / "addon"
OUTPUT = ROOT / "addons.zip"

ADDON_FOLDERS = ["ArchipelagoWoW", "ArchipelagoWoW_Bridge"]

OUTPUT.unlink(missing_ok=True)
with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for folder_name in ADDON_FOLDERS:
        folder_dir = ADDON_DIR / folder_name
        for path in sorted(folder_dir.rglob("*")):
            if path.is_dir():
                continue
            zf.write(path, path.relative_to(ADDON_DIR))

print(f"Built {OUTPUT} ({OUTPUT.stat().st_size} bytes) containing: {', '.join(ADDON_FOLDERS)}")
