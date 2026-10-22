"""Make the TRNLizard installer of a release: the installer template with the current Lizard_Updater.py.

    python tools/build_installer.py [--out FILE] [--template FILE]

installer/TRNLizard_Installer.ghx (made once in Grasshopper by tools/make_installer.py) holds a Lizard_Updater
component; its code item is replaced by Lizard_Updater.py of the repository and the result written to --out
(default dist/TRNLizard_Installer.ghx). The code item is found by its text (the updater's docstring and runUpdater),
so nothing else of the definition is touched. Plain CPython 3, nothing from Rhino.
"""

import argparse
import html
import os
import re
import sys
from xml.sax.saxutils import escape


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO_ROOT, "installer", "TRNLizard_Installer.ghx")
UPDATER = os.path.join(REPO_ROOT, "Lizard_Updater.py")
MARKERS = ("Update the TRNLizard script components", "def runUpdater(")
STRING_ITEM = re.compile(r'(<item name="[^"]*"[^>]*type_name="gh_string"[^>]*>)(.*?)(</item>)', re.S)


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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--template", default=TEMPLATE)
    parser.add_argument("--out", default=os.path.join(REPO_ROOT, "dist", "TRNLizard_Installer.ghx"))
    args = parser.parse_args(argv)
    with open(args.template, "rb") as handle:
        raw = handle.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    xml = raw.decode("utf-8-sig")              # no newline translation: the file keeps its CRLF
    with open(UPDATER, encoding="utf-8-sig") as handle:
        code = handle.read()
    result = fillTemplate(xml, code)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as handle:
        handle.write(result.encode("utf-8-sig" if bom else "utf-8"))
    print("{0} written".format(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
