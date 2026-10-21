"""Write or check trnlizard_manifest.json, the list of the TRNLizard scripts that Lizard_Updater reads from GitHub,
and trnlizard_icons.json, the UserObject icons of icons/<script base name>.png (24x24 PNG) as base64.

    python tools/build_manifest.py            write the icons file and the manifest of the repository root
    python tools/build_manifest.py --check    exit 1 when the committed icons file or manifest is out of date

The manifest also lists trnlizard_icons.json (same hash rule), so the updater downloads it like a script.

The manifest lists every top-level *.py of the repository that Lizard_Updater.findScripts picks up (not starting with
'_') with the SHA256 of its normalized text (Lizard_Updater.getHash: no BOM, LF line endings, no trailing white space
at the end, UTF-8) and the byte size of that normalized text, so CRLF checkouts and a BOM give the same manifest.
Only 'files' is compared: 'generated' (UTC time of the last change of 'files') is kept when the files are unchanged,
so writing the manifest again changes nothing.

Plain CPython 3, nothing from Rhino. normalizeCode/getHash are copies of the updater's; tests/test_updater_github.py
checks that both agree.
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import sys


MANIFEST_NAME = "trnlizard_manifest.json"
MANIFEST_FORMAT = 1
ICONS_NAME = "trnlizard_icons.json"
ICONS_FOLDER = "icons"
ICONS_FORMAT = 1
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def normalizeCode(content):
    """Same as Lizard_Updater.normalizeCode."""
    if not content:
        content = ""
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.lstrip("﻿").rstrip()


def getHash(content):
    """Same as Lizard_Updater.getHash."""
    return hashlib.sha256(normalizeCode(content).encode("utf-8")).hexdigest()


def scriptNames(root):
    """Sorted file names of the scripts of a folder, as Lizard_Updater.findScripts selects them."""
    return sorted(name for name in os.listdir(root)
                  if name.endswith(".py") and not name.startswith("_") and os.path.isfile(os.path.join(root, name)))


def buildIcons(root):
    """Text of trnlizard_icons.json for icons/*.png of a folder, None when there is no icons folder."""
    folder = os.path.join(root, ICONS_FOLDER)
    if not os.path.isdir(folder):
        return None
    icons = {}
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(".png"):
            with open(os.path.join(folder, name), "rb") as handle:
                icons[os.path.splitext(name)[0]] = base64.b64encode(handle.read()).decode("ascii")
    return json.dumps({"format": ICONS_FORMAT, "icons": icons}, indent=1, sort_keys=True) + "\n"


def manifestFiles(root):
    """{file name: {'sha256', 'size'}} of the scripts (and trnlizard_icons.json) of a folder."""
    files = {}
    names = scriptNames(root)
    if os.path.isfile(os.path.join(root, ICONS_NAME)):
        names.append(ICONS_NAME)
    for name in names:
        with open(os.path.join(root, name), "rb") as handle:
            text = handle.read().decode("utf-8-sig")
        files[name] = {"sha256": getHash(text), "size": len(normalizeCode(text).encode("utf-8"))}
    return files


def readManifest(path):
    """The manifest dict of a file, None when it is missing or no valid JSON."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def buildManifest(root, previous=None, now=None):
    """The manifest of a folder; 'generated' of previous is kept when its files are the same."""
    files = manifestFiles(root)
    if previous and previous.get("files") == files and previous.get("generated"):
        generated = previous["generated"]
    else:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        generated = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"format": MANIFEST_FORMAT, "generated": generated, "files": files}


def dumpManifest(manifest):
    return json.dumps(manifest, indent=2, sort_keys=False) + "\n"


def staleFiles(root, manifest):
    """Sorted names whose manifest entry is missing, outdated or no longer a script; [] when it is up to date."""
    current = manifestFiles(root)
    listed = (manifest or {}).get("files") or {}
    if (manifest or {}).get("format") != MANIFEST_FORMAT:
        return sorted(set(current) | set(listed))
    return sorted(name for name in set(current) | set(listed) if current.get(name) != listed.get(name))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write or check " + MANIFEST_NAME)
    parser.add_argument("--check", action="store_true", help="exit 1 when the manifest is out of date")
    parser.add_argument("--root", default=REPO_ROOT, help="repository root (default: the parent of tools/)")
    args = parser.parse_args(argv)
    path = os.path.join(args.root, MANIFEST_NAME)
    previous = readManifest(path)
    iconsText = buildIcons(args.root)
    iconsPath = os.path.join(args.root, ICONS_NAME)
    try:
        with open(iconsPath, "r", encoding="utf-8", newline="") as handle:
            iconsCurrent = handle.read() == iconsText
    except OSError:
        iconsCurrent = iconsText is None
    if args.check:
        if not iconsCurrent:
            print("{0} is out of date; run: python tools/build_manifest.py".format(ICONS_NAME))
            return 1
        stale = staleFiles(args.root, previous)
        if previous is None or stale:
            print("{0} is out of date ({1}); run: python tools/build_manifest.py".format(
                MANIFEST_NAME, ", ".join(stale) if previous is not None else "missing or invalid"))
            return 1
        print("{0} is up to date ({1} scripts)".format(MANIFEST_NAME, len(previous["files"])))
        return 0
    if not iconsCurrent and iconsText is not None:
        with open(iconsPath, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(iconsText)
        print("{0} written".format(ICONS_NAME))
    text = dumpManifest(buildManifest(args.root, previous))
    try:
        with open(path, "r", encoding="utf-8", newline="") as handle:
            unchanged = handle.read() == text
    except OSError:
        unchanged = False
    if unchanged:
        print("{0} unchanged".format(MANIFEST_NAME))
        return 0
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("{0} written".format(MANIFEST_NAME))
    return 0


if __name__ == "__main__":
    sys.exit(main())
