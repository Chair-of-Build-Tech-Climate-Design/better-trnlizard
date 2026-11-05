"""Write or check trnlizard_manifest.json, the list of the TRNLizard scripts that Lizard_Updater reads from GitHub,
and trnlizard_icons.json, the UserObject icons of icons/<script base name>.png (24x24 PNG) as base64.

    python tools/build_manifest.py            write the icons file and the manifest of the repository root
    python tools/build_manifest.py --check    exit 1 when the committed icons file or manifest is out of date

The manifest also lists trnlizard_icons.json (same hash rule), so the updater downloads it like a script, and
trnlizard_presets.json, the preset templates of presets/<preset>/ and presets/_shared/<cluster>/ (preset.json,
object.xml, icon.png; see tools/import_presets.py) in one file.

It also writes the tables of components/Lizard_Placeholder.py from the Options, Default and Source lines of the docstrings
of all scripts. A Source line that names an output no script has stops the tool.

The manifest lists every *.py of components/ that Lizard_Updater.findScripts picks up (not starting with '_'), named
components/<script>.py, with the SHA256 of its normalized text (Lizard_Updater.getHash: no BOM, LF line endings, no trailing white space
at the end, UTF-8) and the byte size of that normalized text, so CRLF checkouts and a BOM give the same manifest.
The entry 'updater' names components/Lizard_Updater.py with its UPDATER_VERSION and hash; an older updater reads it before
the format check and upgrades itself. Every change of that script must raise UPDATER_VERSION: otherwise nothing is written.
Only 'files' is compared: 'generated' (UTC time of the last change of 'files') is kept when the files are unchanged,
so writing the manifest again changes nothing.

Plain CPython 3, nothing from Rhino. normalizeCode/getHash are copies of the updater's; tests/test_updater_github.py
checks that both agree. parseParams reads the same docstrings as the updater's parseDocstringIO; tests/test_placeholder.py checks that too.
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import sys


MANIFEST_NAME = "trnlizard_manifest.json"
MANIFEST_FORMAT = 2
SCRIPTS_FOLDER = "components"
UPDATER_PATH = SCRIPTS_FOLDER + "/Lizard_Updater.py"
ICONS_NAME = "trnlizard_icons.json"
ICONS_FOLDER = "icons"
ICONS_FORMAT = 1
PRESETS_NAME = "trnlizard_presets.json"
PRESETS_FOLDER = "presets"
PRESETS_FORMAT = 1
SHARED_FOLDER = "_shared"
PLACEHOLDER_PATH = SCRIPTS_FOLDER + "/Lizard_Placeholder.py"
PLACEHOLDER_TABLES = re.compile(r"(?<=do not edit\.\n).*?(?=# End of the written part\.\n)", re.DOTALL)
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
    """Sorted file names of the scripts of a repository, as Lizard_Updater.findScripts selects them."""
    folder = os.path.join(root, SCRIPTS_FOLDER)
    return sorted(name for name in os.listdir(folder)
                  if name.endswith(".py") and not name.startswith("_") and os.path.isfile(os.path.join(folder, name)))


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


def buildPresets(root):
    """Text of trnlizard_presets.json for presets/ of a folder, None when there is no presets folder."""
    folder = os.path.join(root, PRESETS_FOLDER)
    if not os.path.isdir(folder):
        return None
    presets, shared = {}, {}
    for parent, target in ((folder, presets), (os.path.join(folder, SHARED_FOLDER), shared)):
        if not os.path.isdir(parent):
            continue
        for name in sorted(os.listdir(parent)):
            path = os.path.join(parent, name)
            if name == SHARED_FOLDER or not os.path.isfile(os.path.join(path, "object.xml")):
                continue
            with open(os.path.join(path, "preset.json"), encoding="utf-8") as handle:
                entry = json.load(handle)
            with open(os.path.join(path, "object.xml"), encoding="utf-8-sig") as handle:
                entry["xml"] = handle.read()
            icon = os.path.join(path, "icon.png")
            if os.path.isfile(icon):
                with open(icon, "rb") as handle:
                    entry["icon"] = base64.b64encode(handle.read()).decode("ascii")
            target[name] = entry
    return json.dumps({"format": PRESETS_FORMAT, "presets": presets, "shared": shared}, indent=1, sort_keys=True) + "\n"


def parseParams(code):
    """(inputs, outputs) of the first docstring of a script: lists of {'name', 'type', 'options', 'default', 'sources'}; no separators."""
    match = re.search(r'"""(.*?)"""', code, re.DOTALL)
    sides = {"Args:": [], "Returns:": []}
    side, current = None, None
    for line in (match.group(1) if match else "").replace("\r\n", "\n").split("\n"):
        if line.strip() in sides:
            side, current = sides[line.strip()], None
        elif side is not None and re.match(r"^    \S", line):
            found = re.match(r"^    ([^(:]+?)(?:\s*\(([^)]*)\))?\s*:\s", line)
            current = {"name": found.group(1).strip(), "type": (found.group(2) or "").strip(), "options": [], "default": None, "sources": []} if found else None
            if current:
                side.append(current)
        elif current is not None:
            found = re.match(r"^        (Options|Default|Source)\s*:\s*(.*\S)", line)
            if found and found.group(1) == "Default":
                current["default"] = found.group(2)
            elif found:
                current["options" if found.group(1) == "Options" else "sources"] = [text.strip() for text in found.group(2).split(",") if text.strip()]
    return sides["Args:"], sides["Returns:"]


def placeholderTables(root):
    """Text of the tables of Lizard_Placeholder for the docstrings of a repository, one line per input.
    Raises ValueError for a Source that names an output no script has."""
    params = {}
    for name in scriptNames(root):
        with open(os.path.join(root, SCRIPTS_FOLDER, name), encoding="utf-8-sig") as handle:
            params[name[:-len(".py")]] = parseParams(handle.read())
    outputs = set(script + "." + param["name"] for script, (_, out) in params.items() for param in out)
    options, sources = [], []
    for script in sorted(params):
        for param in params[script][0]:
            key = json.dumps(script + "." + param["name"])
            if param["options"]:
                spec = {"type": param["type"], "options": param["options"]}
                if param["default"] is not None:
                    spec["default"] = param["default"]
                options.append("    {0}: {1},\n".format(key, json.dumps(spec, sort_keys=True)))
            if param["sources"]:
                unknown = sorted(set(param["sources"]) - outputs)
                if unknown:
                    raise ValueError("Source of {0}.{1} names what no script gives: {2}".format(script, param["name"], ", ".join(unknown)))
                sources.append("    {0}: {1},\n".format(key, json.dumps(param["sources"])))
    return "OPTIONS = {{\n{0}}}\nSOURCES = {{\n{1}}}\n".format("".join(options), "".join(sources))


def updatedPlaceholder(root):
    """(path, its text, its text with the current tables) of Lizard_Placeholder, None when the repository does not have it."""
    path = os.path.join(root, *PLACEHOLDER_PATH.split("/"))
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    tables = placeholderTables(root)
    return path, text, PLACEHOLDER_TABLES.sub(lambda match: tables, text, count=1)


def manifestFiles(root):
    """{file name: {'sha256', 'size'}} of the scripts (components/<script>.py) and the bundle files of a repository."""
    files = {}
    names = [SCRIPTS_FOLDER + "/" + name for name in scriptNames(root)]
    for extra in (ICONS_NAME, PRESETS_NAME):
        if os.path.isfile(os.path.join(root, extra)):
            names.append(extra)
    for name in names:
        with open(os.path.join(root, name), "rb") as handle:
            text = handle.read().decode("utf-8-sig")
        files[name] = {"sha256": getHash(text), "size": len(normalizeCode(text).encode("utf-8"))}
    return files


def updaterEntry(root, files):
    """{'path', 'version', 'sha256'} of the updater script of a repository, None when it has none; version None when the
    script does not say it."""
    if UPDATER_PATH not in files:
        return None
    with open(os.path.join(root, *UPDATER_PATH.split("/")), "rb") as handle:
        match = re.search(r"^UPDATER_VERSION\s*=\s*(\d+)", handle.read().decode("utf-8-sig"), re.MULTILINE)
    return {"path": UPDATER_PATH, "version": int(match.group(1)) if match else None, "sha256": files[UPDATER_PATH]["sha256"]}


def updaterVersionProblem(entry, previous):
    """Why a manifest with this updater entry must not be written after the previous manifest, None when it may."""
    if entry is None:
        return None
    if entry["version"] is None:
        return "{0} does not say its UPDATER_VERSION".format(UPDATER_PATH)
    old = (previous or {}).get("updater")
    if isinstance(old, dict) and old.get("sha256") != entry["sha256"] and entry["version"] <= (old.get("version") or 0):
        return "{0} changed: raise its UPDATER_VERSION above {1}".format(UPDATER_PATH, old.get("version"))
    return None


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
    manifest = {"format": MANIFEST_FORMAT, "generated": generated}
    entry = updaterEntry(root, files)
    if entry is not None:
        manifest["updater"] = entry
    manifest["files"] = files
    return manifest


def dumpManifest(manifest):
    return json.dumps(manifest, indent=2, sort_keys=False) + "\n"


def staleFiles(root, manifest):
    """Sorted names whose manifest entry is missing, outdated or no longer a script; [] when it is up to date."""
    current = manifestFiles(root)
    listed = (manifest or {}).get("files") or {}
    if (manifest or {}).get("format") != MANIFEST_FORMAT:
        return sorted(set(current) | set(listed))
    stale = set(name for name in set(current) | set(listed) if current.get(name) != listed.get(name))
    if (manifest or {}).get("updater") != updaterEntry(root, current):
        stale.add(UPDATER_PATH)
    return sorted(stale)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write or check " + MANIFEST_NAME)
    parser.add_argument("--check", action="store_true", help="exit 1 when the manifest is out of date")
    parser.add_argument("--root", default=REPO_ROOT, help="repository root (default: the parent of tools/)")
    args = parser.parse_args(argv)
    path = os.path.join(args.root, MANIFEST_NAME)
    previous = readManifest(path)
    try:
        placeholder = updatedPlaceholder(args.root)
    except ValueError as error:
        print(error)
        return 1
    if placeholder and placeholder[1] != placeholder[2]:
        if args.check:
            print("{0} out of date; run: python tools/build_manifest.py".format(PLACEHOLDER_PATH))
            return 1
        with open(placeholder[0], "w", encoding="utf-8", newline="\n") as handle:
            handle.write(placeholder[2])
        print("{0} written".format(PLACEHOLDER_PATH))
    if not args.check:
        problem = updaterVersionProblem(updaterEntry(args.root, manifestFiles(args.root)), previous)
        if problem:
            print(problem)
            return 1
    bundles = []
    for bundleName, bundleText in ((ICONS_NAME, buildIcons(args.root)), (PRESETS_NAME, buildPresets(args.root))):
        bundlePath = os.path.join(args.root, bundleName)
        try:
            with open(bundlePath, "r", encoding="utf-8", newline="") as handle:
                current = handle.read() == bundleText
        except OSError:
            current = bundleText is None
        bundles.append((bundleName, bundlePath, bundleText, current))
    if args.check:
        stale = [name for name, path, text, current in bundles if not current]
        if stale:
            print("{0} out of date; run: python tools/build_manifest.py".format(", ".join(stale)))
            return 1
        stale = staleFiles(args.root, previous)
        if previous is None or stale:
            print("{0} is out of date ({1}); run: python tools/build_manifest.py".format(
                MANIFEST_NAME, ", ".join(stale) if previous is not None else "missing or invalid"))
            return 1
        print("{0} is up to date ({1} scripts)".format(MANIFEST_NAME, len(previous["files"])))
        return 0
    for bundleName, bundlePath, bundleText, current in bundles:
        if not current and bundleText is not None:
            with open(bundlePath, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(bundleText)
            print("{0} written".format(bundleName))
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
