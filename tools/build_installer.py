"""Make the TRNLizard installer of a release: the installer template with the current components/Lizard_Updater.py.

    python tools/build_installer.py [--out FILE] [--template FILE] [--source URL --release NAME]

installer/TRNLizard_Installer.ghx (made once in Grasshopper by tools/make_installer.py) holds a Lizard_Updater
component; its code item is replaced by components/Lizard_Updater.py and the result written to --out
(default dist/TRNLizard_Installer.ghx). The code item is found by its text (the updater's docstring and runUpdater).
With --source and --release a panel with that source is wired to the updater's input source, so the installer keeps
installing the scripts of its release, and the panels carry the name of the release. Nothing else of the definition is
touched. Plain CPython 3, nothing from Rhino.
"""

import argparse
import html
import os
import re
import sys
import uuid
from xml.sax.saxutils import escape


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO_ROOT, "installer", "TRNLizard_Installer.ghx")
UPDATER = os.path.join(REPO_ROOT, "components", "Lizard_Updater.py")
MARKERS = ("Update the TRNLizard script components", "def runUpdater(")
STRING_ITEM = re.compile(r'(<item name="[^"]*"[^>]*type_name="gh_string"[^>]*>)(.*?)(</item>)', re.S)
SOURCE_PANEL_PIVOT = (150, 240)                         # below the toggles
SOURCE_PANEL_SIZE = (260, 60)


def updaterItems(xml):
    """Matches of the string items that hold Lizard_Updater code."""
    return [m for m in STRING_ITEM.finditer(xml) if all(marker in html.unescape(m.group(2)) for marker in MARKERS)]


def fillTemplate(xml, code):
    """The template with the code of its one Lizard_Updater replaced; ValueError when there is not exactly one."""
    items = updaterItems(xml)
    if len(items) != 1:
        raise ValueError("the template holds {0} Lizard_Updater code items, expected 1".format(len(items)))
    item = items[0]
    code = code.lstrip("﻿").replace("\r\n", "\n").replace("\n", "\r\n")   # as Grasshopper stores code
    return xml[:item.start(2)] + escape(code) + xml[item.end(2):]


def stringItem(name, text):
    return '<item name="{0}" type_name="gh_string" type_code="10">{1}</item>'.format(name, escape(text))


def replaceOnce(text, old, new):
    if text.count(old) != 1:
        raise ValueError("the template holds {0} times, expected once: {1}".format(text.count(old), old))
    return text.replace(old, new)


def objectChunk(xml, position):
    """(start, end) of the Object chunk around position: it ends with the closing tag at the indentation of its opening tag."""
    start = xml.rfind('<chunk name="Object"', 0, position)
    if start < 0:
        raise ValueError("the template holds no Object around position {0}".format(position))
    indent = xml[xml.rfind('\n', 0, start)+1:start]
    closing = re.compile(r'\r?\n' + indent + '</chunk>').search(xml, position)
    if closing is None:
        raise ValueError("the Object of the template at position {0} does not end".format(position))
    return start, closing.end()


def wireSource(xml, panelguid):
    """Connects the panel to the input source of the updater: Source sorts before SourceCount, as Grasshopper writes them."""
    name = stringItem("Name", "source")
    if xml.count(name) != 1:
        raise ValueError("the template holds {0} params named source, expected 1".format(xml.count(name)))
    position = xml.index(name)
    head = xml.rfind('<items count="', 0, position)
    count = int(re.compile(r'<items count="(\d+)">').match(xml, head).group(1))
    empty = re.compile(r'( *)<item name="SourceCount" type_name="gh_int32" type_code="3">0</item>')
    match = empty.search(xml, position)
    if match is None or xml.find('</items>', position) < match.start():
        raise ValueError("the input source of the template is already connected")
    newline = '\r\n' if '\r\n' in xml else '\n'
    wired = ('{0}<item name="Source" index="0" type_name="gh_guid" type_code="9">{1}</item>{2}'
             '{0}<item name="SourceCount" type_name="gh_int32" type_code="3">1</item>').format(match.group(1), panelguid, newline)
    xml = xml[:match.start()] + wired + xml[match.end():]
    return xml[:head] + '<items count="{0}">'.format(count+1) + xml[xml.index('>', head)+1:]


def pinRelease(xml, source, release):
    """The template with a panel holding source wired to the updater, and the name of the release on the panels."""
    instructions = stringItem("NickName", "Instructions")
    if xml.count(instructions) != 1:
        raise ValueError("the template holds {0} Instructions panels, expected 1".format(xml.count(instructions)))
    start, end = objectChunk(xml, xml.index(instructions))
    template = xml[start:end]
    guids = re.findall(r'<item name="InstanceGuid"[^>]*>([^<]+)</item>', template)
    if len(guids) != 1:
        raise ValueError("the Instructions panel holds {0} instance ids, expected 1".format(len(guids)))
    count = re.compile(r'<item name="ObjectCount" type_name="gh_int32" type_code="3">(\d+)</item>').search(xml)
    if count is None:
        raise ValueError("the template names no ObjectCount")
    objects = int(count.group(1))
    panelguid = str(uuid.uuid5(uuid.NAMESPACE_URL, source))
    panel = template.replace('<chunk name="Object" index="{0}">'.format(objects-1), '<chunk name="Object" index="{0}">'.format(objects))
    panel = replaceOnce(panel, guids[0], panelguid)
    panel = replaceOnce(panel, instructions, stringItem("NickName", "source " + release))
    panel = re.sub(r'<item name="UserText"[^>]*>.*?</item>', lambda m: stringItem("UserText", source), panel, flags=re.S)
    panel = re.sub(r'(<item name="Pivot"[^>]*>\s*<X>)[^<]*(</X>\s*<Y>)[^<]*(</Y>)',
                   lambda m: "{0}{1}{2}{3}{4}".format(m.group(1), SOURCE_PANEL_PIVOT[0], m.group(2), SOURCE_PANEL_PIVOT[1], m.group(3)), panel)
    panel = re.sub(r'(<item name="Bounds"[^>]*>.*?<W>)[^<]*(</W>\s*<H>)[^<]*(</H>)',
                   lambda m: "{0}{1}{2}{3}{4}".format(m.group(1), SOURCE_PANEL_SIZE[0], m.group(2), SOURCE_PANEL_SIZE[1], m.group(3)), panel, flags=re.S)
    newline = '\r\n' if '\r\n' in xml else '\n'
    indent = xml[xml.rfind('\n', 0, start)+1:start]
    result = xml[:end] + newline + indent + panel + xml[end:]
    count = re.compile(r'<item name="ObjectCount" type_name="gh_int32" type_code="3">(\d+)</item>').search(result)
    result = result[:count.start(1)] + str(objects+1) + result[count.end(1):]
    chunks = re.compile(r'<chunks count="(\d+)">').search(result, count.end())
    if int(chunks.group(1)) != objects:
        raise ValueError("the template holds {0} objects, its ObjectCount says {1}".format(chunks.group(1), objects))
    result = result[:chunks.start(1)] + str(objects+1) + result[chunks.end(1):]
    result = wireSource(result, panelguid)
    result = replaceOnce(result, instructions, stringItem("NickName", "TRNLizard " + release))
    result = replaceOnce(result, ">TRNLizard installer" + newline, ">" + escape("TRNLizard installer " + release) + newline)
    return replaceOnce(result, '1. Optional: connect a GitHub URL or a folder to "source" (empty = TRNLizard on GitHub).',
                       '1. The panel at "source" fixes the scripts to this release. Replace it by a GitHub URL or a folder for other scripts (empty = TRNLizard on GitHub).')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--template", default=TEMPLATE)
    parser.add_argument("--out", default=os.path.join(REPO_ROOT, "dist", "TRNLizard_Installer.ghx"))
    parser.add_argument("--source", help="what the updater of the installer reads, e.g. https://github.com/<owner>/<repo>/commit/<sha>")
    parser.add_argument("--release", help="name of the release, shown on the panels")
    args = parser.parse_args(argv)
    if bool(args.source) != bool(args.release):
        parser.error("--source and --release belong together")
    with open(args.template, "rb") as handle:
        raw = handle.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    xml = raw.decode("utf-8-sig")              # no newline translation: the file keeps its CRLF
    with open(UPDATER, encoding="utf-8-sig") as handle:
        code = handle.read()
    result = fillTemplate(xml, code)
    if args.source:
        result = pinRelease(result, args.source, args.release)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as handle:
        handle.write(result.encode("utf-8-sig" if bom else "utf-8"))
    print("{0} written".format(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
