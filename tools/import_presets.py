"""Turn the output of tools/export_presets.py into the preset templates of the repository.

    python tools/import_presets.py <export folder>            e.g. presets_export

For every exported preset it writes presets/<preset>/:
- preset.json: the UserObject description (name, nickName, description, category, subCategory, exposure);
- object.xml: the GH_Archive XML of the preset cluster, the template that Lizard_Updater fills with the latest scripts;
- icon.png;
- structure.json: readable content (objects, scripts by name, panel texts, wires, nested clusters) to review and diff.
The shared clusters (SHARED below) are taken once, from the first preset that has them, into presets/_shared/<name>/
with a role: 'sync' = presets and canvas follow the repository copy, 'keep' = presets get the repository copy but a
copy on the canvas is never replaced (only the scripts inside are updated). tools/build_manifest.py then bundles
presets/ into trnlizard_presets.json.

Plain CPython 3, nothing from Rhino.
"""

import html
import json
import os
import re
import shutil
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRESETS = os.path.join(REPO_ROOT, "presets")
SHARED_FOLDER = "_shared"
# shared nested cluster -> (role, other nick names it has in old presets, preset to take it from)
SHARED = {
    "Lizard_Building_Template": ("sync", [], "TRNLizard_Template_Lite"),
    "Lizard_Database": ("keep", ["Database"], "TRNLizard_Template_Lite"),
}


def sharedName(nickName):
    for name, (role, aliases, source) in SHARED.items():
        if nickName == name or nickName in aliases:
            return name
    return None


def panelText(folder, obj):
    if not obj.get("xml"):
        return None
    with open(os.path.join(folder, obj["xml"]), encoding="utf-8") as handle:
        xml = handle.read()
    match = re.search(r'<item name="UserText"[^>]*>(.*?)</item>', xml, re.S)
    return html.unescape(match.group(1)) if match else None


def structure(cluster, folder, topLevel):
    """Readable content of a cluster; nested shared clusters only by reference."""
    objects = []
    for obj in cluster.get("content", {}).get("objects", []):
        kind = obj.get("kind")
        row = {"id": obj.get("id"), "kind": kind, "type": (obj.get("type") or "").split(".")[-1],
               "name": obj.get("name"), "nickName": obj.get("nickName"), "pivot": obj.get("pivot")}
        if obj.get("locked"):
            row["locked"] = True
        if kind == "script":
            row["script"] = obj.get("name")
            row["codeHash"] = (obj.get("codeHash") or "")[:12]
            row["inputs"] = [p["name"] for p in obj.get("inputs", [])]
            row["outputs"] = [p["name"] for p in obj.get("outputs", [])]
        elif kind == "cluster":
            shared = sharedName(obj.get("nickName")) if topLevel else None
            if shared:
                row["shared"] = shared
            else:
                row["cluster"] = structure(obj["cluster"], os.path.join(folder, obj["folder"]), False)
            row["outputs"] = [p["name"] for p in obj.get("outputs", [])]
            row["inputs"] = [p["name"] for p in obj.get("inputs", [])]
        elif row["type"] == "GH_Panel":
            row["text"] = panelText(folder, obj)
        if obj.get("members"):
            row["members"] = obj["members"]
        objects.append(row)
    wires = [{"from": [w["from"]["object"], w["from"]["param"], w["from"]["index"]],
              "to": [w["to"]["object"], w["to"]["param"], w["to"]["index"]]}
             for w in cluster.get("content", {}).get("wires", [])]
    return {"objects": objects, "wires": wires,
            "outerInputs": [p["name"] for p in cluster.get("outerInputs", [])],
            "outerOutputs": [p["name"] for p in cluster.get("outerOutputs", [])]}


def writeJson(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=1, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def importPreset(export, folderName, target, meta, cluster, sourceFolder, extra=None):
    os.makedirs(target, exist_ok=True)
    data = {"name": meta["name"], "nickName": meta["nickName"], "description": meta.get("description") or "",
            "category": meta.get("category") or "TRNLizard", "subCategory": meta.get("subCategory") or "",
            "exposure": meta.get("exposure") or "primary"}
    data.update(extra or {})
    writeJson(os.path.join(target, "preset.json"), data)
    shutil.copy(os.path.join(sourceFolder, "object.xml"), os.path.join(target, "object.xml"))
    writeJson(os.path.join(target, "structure.json"), structure(cluster, sourceFolder, extra is None))


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    export = os.path.abspath(argv[1])
    index = json.load(open(os.path.join(export, "index.json"), encoding="utf-8"))
    os.makedirs(PRESETS, exist_ok=True)
    shared = {}
    for entry in index["presets"]:
        folder = os.path.join(export, entry["folder"])
        preset = json.load(open(os.path.join(folder, "preset.json"), encoding="utf-8"))
        if preset.get("kind") != "cluster":
            print("skipped (not a cluster): " + entry["file"])
            continue
        base = os.path.splitext(preset["file"])[0]
        target = os.path.join(PRESETS, base)
        importPreset(export, entry["folder"], target, preset, preset["cluster"], folder)
        if os.path.isfile(os.path.join(folder, "icon.png")):
            shutil.copy(os.path.join(folder, "icon.png"), os.path.join(target, "icon.png"))
        for obj in preset["cluster"]["content"]["objects"]:
            name = sharedName(obj.get("nickName")) if obj.get("kind") == "cluster" else None
            if name and SHARED[name][2] == base:
                shared[name] = (obj, os.path.join(folder, obj["folder"]))
        print("imported " + base)
    for name, (obj, folder) in sorted(shared.items()):
        role, aliases, source = SHARED[name]
        meta = {"name": name, "nickName": name, "description": "TRNLizard shared cluster " + name,
                "category": "TRNLizard", "subCategory": "1 | Advanced", "exposure": "primary"}
        importPreset(export, None, os.path.join(PRESETS, SHARED_FOLDER, name), meta, obj["cluster"], folder,
                     {"role": role, "aliases": aliases, "source": source})
        print("imported shared " + name + " (" + role + ") from " + source)
    missing = sorted(set(SHARED) - set(shared))
    if missing:
        print("shared clusters not found: " + ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
