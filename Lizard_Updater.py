"""
Update the TRNLizard script components of this Grasshopper document from the TRNLizard scripts on GitHub or in a folder.
-
source tells where the scripts come from:
- not connected or empty: the main branch of https://github.com/Chair-of-Build-Tech-Climate-Design/better-trnlizard;
- a GitHub repository (https://github.com/<owner>/<repo>, github.com/<owner>/<repo> or git@github.com:<owner>/<repo>.git),
optionally with /tree/<branch or tag> or /commit/<sha> (default: main). The updater reads trnlizard_manifest.json of the
repository (SHA256 of every script) and downloads only new and changed scripts into its cache folder (Grasshopper AppData
folder, TRNLizard/source/<owner>_<repo>_<ref>); scripts that left the manifest are deleted from the cache. Without a
connection a complete cached copy is used; after a successful download the cache folders of other repositories and
branches are deleted. The branch is looked up as a commit on api.github.com; when that fails, the
files come from the branch on raw.githubusercontent.com, which caches them for about 5 minutes: a change pushed just now
may only show a few minutes later. Private repositories are not supported;
- anything else: a local folder with the scripts <component Name>.py.
A script component is matched by its Name (every TRNLizard script sets it, e.g. Lizard_Hygro) to <Name>.py of the
source. Its code is replaced when it differs from the file (line endings, a BOM and trailing white space are
ignored). Its inputs and outputs follow the Args/Returns docstring of the new script:
- only additions: the new params are added to the component in place, at their docstring position;
- any removal (a rename is a removal plus an addition): a copy of the component with the new code and IO is placed
next to the old one, wired by param name and put into a red group; the old component is locked and keeps its
params and wires for reference;
- order-only differences: the params are kept, a note is logged;
- inside clusters only additions are applied, anything else is reported as manual update needed.
All document changes are made right after this solution, then the report of the finished update is shown.
The updater never updates itself: when its own code differs from Lizard_Updater.py of the source, a warning is
logged and listed under errors; paste the new code into this component by hand.
Every update also writes a Grasshopper UserObject (.ghuser) per component script of the source into the subfolder
TRNLizard of the Grasshopper UserObjects folder (switch it off with makeUserObjects = False). Each UserObject is built
from the script alone: a new IronPython script component with the params of the docstring and the Name, NickName,
Message, Category and SubCategory the script declares (defaults: file name, TRNLizard, 9 | Other) and the icon of
trnlizard_icons.json of the source (made from icons/<script>.png by tools/build_manifest.py). A Rhino 8 Python 3
updater writes legacy GhPython UserObjects, since the TRNLizard scripts are IronPython 2 code. lizard_userobjects.json
in that folder keeps the hash of each script: a UserObject is only rewritten when its script or the UserObject
format changed or its file is missing; UserObjects of scripts that are gone are deleted (only files this updater
wrote). Scripts without Args/Returns docstring and without ghenv.Component.Name get no UserObject.
The presets (trnlizard_presets.json of the source, made from presets/ by tools/build_manifest.py) are written as
UserObjects too: each is rebuilt from its template cluster, with every script component inside brought to the
scripts of the source (a component that lost params is swapped for a new copy, wires moved) and the shared clusters
put in from their templates; a preset is rebuilt when its template or any script changed. Shared clusters with role
'sync' (Lizard_Building_Template) are also replaced on the canvas when they are outdated (marker in their
Description, wires moved, undo recorded); those with role 'keep' (Lizard_Database) are never replaced on the canvas,
only the scripts inside are updated.
Plain script for Rhino 7/8 GhPython (IronPython 2.7) and Rhino 8 Python 2/3 script components; it updates
components of these three kinds (Rhino 8 script components need Rhino 8 SR18 or later).
-
TRNLizard

Args:
    source (str): GitHub repository URL (optionally .../tree/<branch>) or folder of the scripts; empty = TRNLizard on GitHub
        Access: item
        Required: False
    runUpdate (bool): True = update the script components of this document
        Access: item
        Required: True
    makeUserObjects (bool): True or not connected = write a UserObject per script into <Grasshopper UserObjects folder>/TRNLizard; False = canvas update only
        Access: item
        Required: False

Returns:
    log (str): report of the last update
        Access: item
    updated (str): names of the updated components
        Access: item
    skipped (str): names of the components that are up to date or were left alone
        Access: item
    errors (str): failures and components that need a manual update
        Access: item
"""
import hashlib
import io
import json
import os
import re
import shutil

import System
import Grasshopper
import scriptcontext as sc


KIND_GHPYTHON = 'GhPython (legacy, IronPython 2.7)'
KIND_IRONPYTHON2 = 'Rhino 8 Python 2 Script (IronPython 2)'
KIND_PYTHON3 = 'Rhino 8 Python 3 Script (CPython 3)'
STANDARD_OUTPUT = 'out'                                   # code output of script components (print output)
PARAM_STRING_ID = '3ede854e-c753-40eb-84cb-b48008f14fd4'  # Param_String, the type of that code output
REPLACEMENT_OFFSET = 40                                   # canvas px right and down from the old component
GROUP_ARGB = (150, 255, 0, 0)                             # red group around a replacement
REPORT_KEY = 'Lizard_Updater_report_'                     # sc.sticky key + updater InstanceGuid
OUTDATED_KEY = 'Lizard_Updater_outdated_'                 # sc.sticky key + updater InstanceGuid: last self check
OUTDATED_MESSAGE = 'OUTDATED'                             # shown under the updater while its code is outdated
UNDO_NAME = 'Lizard_Updater'
UPDATER_SCRIPT = 'Lizard_Updater'                         # base name of this script in the source folder
DEFAULT_SOURCE = 'https://github.com/Chair-of-Build-Tech-Climate-Design/better-trnlizard'
DEFAULT_REF = 'main'                                      # branch when a GitHub URL names none
MANIFEST_NAME = 'trnlizard_manifest.json'                 # at the repository root, made by tools/build_manifest.py
ICONS_NAME = 'trnlizard_icons.json'                       # {format, icons: {script: base64 PNG 24x24}}, made from icons/*.png
PRESETS_NAME = 'trnlizard_presets.json'                   # preset templates of presets/ (tools/build_manifest.py)
BUNDLE_NAMES = (ICONS_NAME, PRESETS_NAME)                 # files of the source besides the scripts
SHARED_MARKER = u'[TRNLizard shared {0}]'                 # in the Description of a shared cluster: its template hash
MANIFEST_FORMAT = 1                                       # newest manifest format this updater reads
RAW_HOST = 'https://raw.githubusercontent.com'
API_HOST = 'https://api.github.com'
SHA_MEDIA_TYPE = 'application/vnd.github.sha'             # Accept header: the commits API answers with the bare sha
HTTP_TIMEOUT_MS = 30000
RATE_LIMIT_STATUSES = (403, 429)                          # GitHub answers a rate limit with one of these
RETRY_STATUSES = (429, 502, 503, 504)                     # raw downloads retried after a short wait
RETRY_ATTEMPTS = 3                                        # tries per download in all
RETRY_BACKOFF_S = 1.0                                     # wait before the 2nd try, doubled for each further one
MAX_RETRY_WAIT_S = 10.0                                   # cap of all waits of one update
USER_AGENT = 'TRNLizard-Updater'
CACHE_SUBFOLDER = ('TRNLizard', 'source')                 # under the Grasshopper AppData folder
USEROBJECT_SUBFOLDER = 'TRNLizard'                        # subfolder of the Grasshopper UserObjects folder
USEROBJECT_STATE = 'lizard_userobjects.json'              # in that subfolder: {format, userObjects: {script: hash, file}}
USEROBJECT_FORMAT = 2                                     # raise when the UserObject builder changes: rewrites them all
LEGACY_GHPYTHON_ID = '410755b1-224a-4c1e-a407-bf32fb45ea7e'  # GhPython Script (legacy, IronPython 2.7)
DEFAULT_CATEGORY = 'TRNLizard'                              # UserObject category of a script that declares none
DEFAULT_SUBCATEGORY = '9 | Other'                         # UserObject subcategory of a script that declares none

# docstring type -> (type hint id of legacy GhPython, .NET type for Rhino 8 script params, accepted hint names)
TYPE_HINTS = {
    'bool': ('d60527f5-b5af-4ef6-8970-5f96fe412559', 'System.Boolean', ('bool', 'boolean')),
    'int': ('48d01794-d3d8-4aef-990e-127168822244', 'System.Int32', ('int', 'integer', 'int32')),
    'float': ('39fbc626-7a01-46ab-a18e-ec1c0c41685b', 'System.Double', ('float', 'double', 'number')),
    'str': ('37261734-eec7-4f50-b6a8-b8d1f3c4396b', 'System.String', ('str', 'string', 'text')),
    'brep': ('2ceb0405-fdfe-403d-a4d6-8786da45fb9d', 'Rhino.Geometry.Brep', ('brep',)),
}
TYPE_ALIASES = {'boolean': 'bool', 'integer': 'int', 'double': 'float', 'string': 'str'}


# ---------------------------------------------------------------------------------------------------------------------
# Pure decision logic (no Rhino/Grasshopper use; unit-tested in tests/test_updater_io_sync.py)
# ---------------------------------------------------------------------------------------------------------------------

def normalizeCode(content):
    """Script text for comparisons: no BOM, LF line endings, no trailing white space at the end.

    Grasshopper rewrites the line endings of the code when it saves/loads a definition, so raw text would always differ.
    """
    if not content:
        content = u''
    normalized = content.replace(u'\r\n', u'\n').replace(u'\r', u'\n')
    return normalized.lstrip(u'\ufeff').rstrip()


def getHash(content):
    """SHA256 of the normalized script text."""
    return hashlib.sha256(normalizeCode(content).encode('utf-8')).hexdigest()


def firstDiff(a, b):
    """Short hint about the first differing line of two normalized script texts, None when they are equal."""
    aLines = normalizeCode(a).split(u'\n')
    bLines = normalizeCode(b).split(u'\n')
    for i in range(max(len(aLines), len(bLines))):
        la = aLines[i] if i < len(aLines) else u'<missing>'
        lb = bLines[i] if i < len(bLines) else u'<missing>'
        if la != lb:
            return u'line {0}: comp={1!r} vs file={2!r}'.format(i + 1, la[:60], lb[:60])
    return None


def selfCheckMessage(ownCode, fileCode, path):
    """Warning when the code of this updater differs from its script in the folder, None when they are equal or one
    of them could not be read. The updater skips itself, so its own copy on the canvas only changes by hand."""
    if ownCode is None or fileCode is None or getHash(ownCode) == getHash(fileCode):
        return None
    return (u'This Lizard_Updater is outdated: it runs other code than {0} (first diff {1}). The updater never updates '
            u'itself: replace this component by a new Lizard_Updater from the TRNLizard tab (its UserObject is rewritten '
            u'unless makeUserObjects is False; restart Grasshopper if the tab still shows the old one), or paste the '
            u'file into this component by hand.').format(path, firstDiff(ownCode, fileCode))


def parseDocstringIO(code):
    """Inputs and outputs declared in the Args/Returns sections of the first docstring of a script.

    Returns (inputs, outputs); a side is None when its section is missing, otherwise a list of dicts with the keys
    name, type, description, access ('item', 'list' or 'tree', default 'item'), required (default False) and separator.
    Param lines have exactly 4 spaces of indent, 'Name (type): description', followed by 8-space 'Access: x' and
    'Required: y' lines; a 4-space line without ': ' after the name is a separator param (e.g. '------- hygrothermal').
    """
    docMatch = re.search(r'"""(.*?)"""', code or u'', re.DOTALL)
    if not docMatch:
        return None, None
    inputs = None
    outputs = None
    section = None
    current = None
    for line in docMatch.group(1).replace(u'\r\n', u'\n').split(u'\n'):
        if line.strip() == u'Args:':
            section, inputs, current = 'in', [], None
            continue
        if line.strip() == u'Returns:':
            section, outputs, current = 'out', [], None
            continue
        if section is None:
            continue
        if re.match(r'^    \S', line):  # exactly 4-space indent: a param
            m = re.match(r'^    ([^(:]+?)(?:\s*\(([^)]*)\))?\s*:\s', line)
            if m:
                current = {'name': m.group(1).strip(), 'type': (m.group(2) or u'').strip(),
                           'description': line[m.end():].strip(), 'access': 'item', 'required': False, 'separator': False}
            else:  # separator line (no colon)
                current = {'name': line.strip(), 'type': u'', 'description': u'', 'access': 'item', 'required': False,
                           'separator': True}
            (inputs if section == 'in' else outputs).append(current)
        elif current is not None and re.match(r'^        \S', line):
            m = re.match(r'^        (Access|Required)\s*:\s*(\S+)', line)
            if m and m.group(1) == 'Access' and m.group(2).lower() in ('item', 'list', 'tree'):
                current['access'] = m.group(2).lower()
            elif m and m.group(1) == 'Required':
                current['required'] = m.group(2).lower() == 'true'
    return inputs, outputs


def parseIONames(code):
    """(input names, output names) of the docstring, in order and including separators; [] for a missing section."""
    inputs, outputs = parseDocstringIO(code)
    return [p['name'] for p in inputs or []], [p['name'] for p in outputs or []]


def insertionPlan(current, target):
    """(name, index) insertions, to apply one after the other, that add the target names missing in current.

    Each new name goes right after its predecessor in the target order (index 0 for the first target name), so
    existing params never move, also when they are in another order than in the target.
    """
    working = list(current)
    plan = []
    for i, name in enumerate(target):
        if name in working:
            continue
        index = working.index(target[i - 1]) + 1 if i > 0 else 0
        working.insert(index, name)
        plan.append((name, index))
    return plan


def _hasDuplicates(names):
    return len(set(names)) != len(names)


def planIOUpdate(currentInputs, currentOutputs, targetInputs, targetOutputs, hasStandardOutput=False):
    """How the params of a component follow the docstring of its new script.

    current*: param names on the component in order; target*: docstring names in order, or None when the docstring has
    no such section (that side is left alone). hasStandardOutput: the component shows the code output 'out' as its
    first output; it is compared only when the docstring lists it. Returns a dict:
      kind: 'none', 'order' (same names, other order), 'add' (only additions), 'remove' (a current name is missing in
            the docstring; a rename is a removal plus an addition) or 'ambiguous' (a name occurs twice)
      addedInputs, addedOutputs, removedInputs, removedOutputs: names
      inputInsertions, outputInsertions: (name, index) to apply one after the other after the removed params are gone;
            output indices count the code output
      reorderedInputs, reorderedOutputs: kept params in another order than in the docstring
      notes: texts for the log
    """
    notes = []
    curIn = list(currentInputs)
    curOut = list(currentOutputs)
    tgtIn = list(curIn) if targetInputs is None else list(targetInputs)
    tgtOut = list(curOut) if targetOutputs is None else list(targetOutputs)
    if targetInputs is None:
        notes.append('the docstring has no Args section: inputs not checked')
    if targetOutputs is None:
        notes.append('the docstring has no Returns section: outputs not checked')
    offset = 0
    if hasStandardOutput and curOut and curOut[0] == STANDARD_OUTPUT and STANDARD_OUTPUT not in tgtOut:
        curOut = curOut[1:]
        offset = 1
    if not hasStandardOutput and STANDARD_OUTPUT in tgtOut and STANDARD_OUTPUT not in curOut:
        tgtOut = [name for name in tgtOut if name != STANDARD_OUTPUT]
        notes.append("the docstring lists the code output '{0}', which is hidden on this component: not added".format(STANDARD_OUTPUT))
    plan = {'kind': 'none', 'addedInputs': [], 'addedOutputs': [], 'removedInputs': [], 'removedOutputs': [],
            'inputInsertions': [], 'outputInsertions': [], 'reorderedInputs': False, 'reorderedOutputs': False,
            'notes': notes}
    if _hasDuplicates(curIn) or _hasDuplicates(tgtIn) or _hasDuplicates(curOut) or _hasDuplicates(tgtOut):
        plan['kind'] = 'ambiguous'
        notes.append('a param name occurs twice: params cannot be matched by name')
        return plan
    sides = (('Inputs', curIn, tgtIn, 0), ('Outputs', curOut, tgtOut, offset))
    for side, current, target, shift in sides:
        kept = [name for name in current if name in target]
        plan['removed' + side] = [name for name in current if name not in target]
        plan['added' + side] = [name for name in target if name not in current]
        plan['reordered' + side] = kept != [name for name in target if name in current]
        plan[side[:-1].lower() + 'Insertions'] = [(name, index + shift) for name, index in insertionPlan(kept, target)]
    if plan['removedInputs'] or plan['removedOutputs']:
        plan['kind'] = 'remove'
    elif plan['addedInputs'] or plan['addedOutputs']:
        plan['kind'] = 'add'
    elif plan['reorderedInputs'] or plan['reorderedOutputs']:
        plan['kind'] = 'order'
    if plan['reorderedInputs'] or plan['reorderedOutputs']:
        notes.append('the params are in another order than in the docstring: order kept')
    return plan


def decideAction(codeChanged, plan, inCluster, locked):
    """'skip', 'code' (code only), 'add' (params added in place), 'replace' (new copy, old one locked), 'manual'
    (nothing changed, the user has to update it) or 'locked' (a locked component that lost params: probably the old
    copy kept by an earlier replacement; left alone)."""
    kind = plan['kind']
    if kind == 'ambiguous':
        return 'manual'
    if kind == 'add':
        return 'add'
    if kind == 'remove':
        if inCluster:
            return 'manual'
        return 'locked' if locked else 'replace'
    return 'code' if codeChanged else 'skip'


def wiringPlan(oldNames, newNames):
    """(name, old index, new index) for every name that occurs exactly once on both sides."""
    plan = []
    for newIndex, name in enumerate(newNames):
        if newNames.count(name) == 1 and oldNames.count(name) == 1:
            plan.append((name, oldNames.index(name), newIndex))
    return plan


def replacementLabel(componentName, removedInputs, removedOutputs):
    """NickName of the red group around a replacement component."""
    removed = []
    if removedInputs:
        removed.append('inputs removed: ' + ', '.join(removedInputs))
    if removedOutputs:
        removed.append('outputs removed: ' + ', '.join(removedOutputs))
    return ('Lizard_Updater replaced {0} ({1}). Check the wiring of this new component, then delete the old, locked '
            '{0} underneath.').format(componentName, '; '.join(removed))


def stripParamSources(xml):
    """GH_Archive XML of a component without the wires of its params, with valid item counts.

    Every 'Source' item is renamed (Read() no longer finds it) and every 'SourceCount' is set to 0. Item names are only
    matched in markup; the script text inside an item is escaped XML and is not touched.
    """
    xml = re.sub(r'<item name="Source" (index=)', r'<item name="LizardUpdaterRemovedSource" \1', xml)
    return re.sub(r'(<item name="SourceCount" [^>]*>)\s*\d+\s*(</item>)', r'\g<1>0\g<2>', xml)


def classifyScriptComponent(typeName, hasCode, hasSetSource):
    """Kind of a script component from its .NET type name; None for anything that is not a Python script component."""
    if 'Python3' in typeName:
        return KIND_PYTHON3
    if 'IronPython2' in typeName:
        return KIND_IRONPYTHON2
    if hasCode:
        return KIND_GHPYTHON
    return None


def typeHintSpec(typeName):
    """{'legacyId', 'clrType', 'names'} of a docstring type, None for object/unknown types (default hint kept)."""
    key = (typeName or '').strip().lower()
    key = TYPE_ALIASES.get(key, key)
    if key not in TYPE_HINTS:
        return None
    legacyId, clrType, names = TYPE_HINTS[key]
    return {'legacyId': legacyId, 'clrType': clrType, 'names': names}


# UserObjects (pure logic; unit-tested in tests/test_updater_userobjects.py)

_COMPONENT_INFO = re.compile(r'^ghenv\.Component\.(Name|NickName|Message|Category|SubCategory)[ \t]*=[ \t]*(.*?)[ \t]*$',
                             re.MULTILINE)
_STRING_LITERAL = re.compile(r'''^[uU]?(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")\s*(?:#.*)?$''')
_ESCAPES = {'n': u'\n', 't': u'\t', 'r': u'\r'}


def stringLiteral(text):
    """Value of a one-line string literal (a trailing comment allowed), None for anything else (e.g. an expression)."""
    m = _STRING_LITERAL.match(text or u'')
    if not m:
        return None
    raw = m.group(1) if m.group(1) is not None else m.group(2)
    return re.sub(r'\\(.)', lambda e: _ESCAPES.get(e.group(1), e.group(1)), raw)


def scriptDescription(code):
    """First paragraph of the module docstring before its first '-' line; '' when the script has no module docstring."""
    m = re.match(r'\s*(?:#[^\n]*\n\s*)*[uUrR]?"""(.*?)"""', (code or u'').replace(u'\r\n', u'\n'), re.DOTALL)
    if not m:
        return u''
    lines = []
    for line in m.group(1).split(u'\n'):
        text = line.strip()
        if text == u'-' or text in (u'Args:', u'Returns:'):
            break
        if not text:
            if lines:
                break
            continue
        lines.append(text)
    return u'\n'.join(lines)


def parseComponentInfo(code, baseName):
    """Identity of the component of a script: dict name, nickName, category, subCategory, message, description.

    Taken from the first unindented ghenv.Component.<X> = '<string literal>' line per member (commented-out lines,
    indented lines and non-literal values such as 'VER %s' % version are ignored). Defaults: name = baseName,
    nickName = name without 'Lizard_', category DEFAULT_CATEGORY, subCategory DEFAULT_SUBCATEGORY, message ''.
    description = first paragraph of the module docstring, else 'TRNLizard component <name>'.
    """
    declared = {}
    for member, value in _COMPONENT_INFO.findall((code or u'').replace(u'\r\n', u'\n')):
        literal = stringLiteral(value)
        if literal is not None and literal.strip() and member not in declared:
            declared[member] = literal
    name = declared.get('Name', baseName).strip()
    nickName = declared.get('NickName')
    if nickName is None:
        nickName = name[len('Lizard_'):] if name.startswith('Lizard_') and len(name) > len('Lizard_') else name
    return {'name': name, 'nickName': nickName,
            'category': declared.get('Category', DEFAULT_CATEGORY),
            'subCategory': declared.get('SubCategory', DEFAULT_SUBCATEGORY),
            'message': declared.get('Message', u''),
            'description': scriptDescription(code) or u'TRNLizard component ' + name}


def declaresComponentName(code):
    return any(member == 'Name' and stringLiteral(value)
               for member, value in _COMPONENT_INFO.findall((code or u'').replace(u'\r\n', u'\n')))


def isComponentScript(code):
    """True when a script gets a UserObject: its docstring has an Args or Returns section, or it declares
    ghenv.Component.Name."""
    inputs, outputs = parseDocstringIO(code)
    return inputs is not None or outputs is not None or declaresComponentName(code)


def userObjectFileName(name):
    """Safe .ghuser file name for a component name (letters, digits, space, '_', '-', '.'; anything else '_')."""
    safe = re.sub(r'[^A-Za-z0-9_. -]', '_', name or u'').strip(u' .')
    return (safe or u'Lizard_UserObject') + u'.ghuser'


def isOwnUserObjectFile(fileName):
    """A file name the state may point to: a plain .ghuser name in the UserObject folder (no path, no '..')."""
    if not fileName or not isinstance(fileName, (type(u''), str)):
        return False
    return (fileName.lower().endswith('.ghuser') and '/' not in fileName and '\\' not in fileName
            and ':' not in fileName and fileName.strip(u' .') == fileName)


def planUserObjects(entries, state, existingFiles):
    """Which UserObjects to (re)write, which are unchanged and which are stale.

    entries: dicts with script (base name), name, file and sha256 for every component script; state: the loaded state
    file {'format': n, 'userObjects': {script: {'sha256', 'file', ...}}} (anything else counts as empty);
    existingFiles: file names in the UserObject folder. Returns a dict:
      write: (entry, reason) for a new UserObject, a missing file, a changed script/name or another USEROBJECT_FORMAT
      unchanged: entries whose file exists and whose hash and file name are the ones of the state
      stale: (script, file) of state entries whose script is gone (or now writes another file); only files of the
             state are listed, never other files of the folder
      conflicts: (entry, script) when two scripts would write the same file; the later one is not written
    """
    previous = {}
    if isinstance(state, dict) and isinstance(state.get('userObjects'), dict):
        previous = state['userObjects']
    sameFormat = isinstance(state, dict) and state.get('format') == USEROBJECT_FORMAT
    existing = set(name.lower() for name in existingFiles)
    plan = {'write': [], 'unchanged': [], 'stale': [], 'conflicts': []}
    used = {}
    for entry in sorted(entries, key=lambda e: e['script']):
        key = entry['file'].lower()
        if key in used:
            plan['conflicts'].append((entry, used[key]))
            continue
        used[key] = entry['script']
        old = previous.get(entry['script'])
        if not isinstance(old, dict):
            old = None
        if old is None:
            reason = 'new' if key not in existing else 'not in the state file'
        elif key not in existing:
            reason = 'file missing'
        elif not sameFormat:
            reason = 'UserObject format changed'
        elif old.get('sha256') != entry['sha256']:
            reason = 'script changed'
        elif old.get('file') != entry['file']:
            reason = 'component name changed'
        else:
            plan['unchanged'].append(entry)
            continue
        plan['write'].append((entry, reason))
    for script in sorted(previous):
        old = previous[script]
        fileName = old.get('file') if isinstance(old, dict) else None
        if isOwnUserObjectFile(fileName) and fileName.lower() not in used:
            plan['stale'].append((script, fileName))
    return plan


# ---------------------------------------------------------------------------------------------------------------------
# Pure source logic: GitHub sources, manifest and cache plan (no Rhino/Grasshopper use; unit-tested in
# tests/test_updater_github.py)
# ---------------------------------------------------------------------------------------------------------------------

class SourceError(Exception):
    """A source that cannot be used; status: HTTP status of a failed request, None when there was no answer;
    retryAfter: seconds of a Retry-After header, None when there was none."""

    def __init__(self, message, status=None, retryAfter=None):
        Exception.__init__(self, message)
        self.status = status
        self.retryAfter = retryAfter


GITHUB_PREFIXES = (                                       # what clearly is GitHub; the repository path follows
    r'^https?://(?:www\.)?github\.com(?::\d+)?(?=/|$)',
    r'^ssh://git@github\.com(?::\d+)?(?=/|$)',
    r'^git@github\.com:',
    r'^(?:www\.)?github\.com(?=/|$)',
)
GITHUB_USAGE = 'use https://github.com/<owner>/<repo> or https://github.com/<owner>/<repo>/tree/<branch>'
REPO_NAME_PATTERN = r'^[A-Za-z0-9_.-]+$'
SCRIPT_NAME_PATTERN = r'^[A-Za-z0-9][A-Za-z0-9_.-]*\.py$'  # manifest entries: top-level scripts only, no paths


def parseSource(source):
    """Where the scripts come from: {'kind': 'github', 'owner', 'repo', 'ref'} or {'kind': 'folder', 'path'}.

    Not connected or empty is DEFAULT_SOURCE. GitHub only when it clearly is: an http(s) URL with the host github.com,
    git@github.com:<owner>/<repo>(.git) or github.com/<owner>/<repo>. The ref comes from a /tree/<ref> or /commit/<sha>
    suffix, else DEFAULT_REF. Any other URL raises ValueError (only GitHub is supported); everything else, e.g. a
    Windows path, a UNC path or a posix path, is a folder path (surrounding white space and quotes removed).
    """
    text = u'' if source is None else str(source).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in u'"\'':
        text = text[1:-1].strip()
    if not text:
        text = DEFAULT_SOURCE
    for prefix in GITHUB_PREFIXES:
        match = re.match(prefix, text, re.IGNORECASE)
        if match:
            return parseGitHubPath(text, text[match.end():])
    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]+://', text):
        raise ValueError(u"Source '{0}' is a URL of another host: only GitHub repositories are supported ({1}), or a "
                         u"local folder.".format(text, GITHUB_USAGE))
    return {'kind': 'folder', 'path': text}


def parseGitHubPath(source, path):
    """{'kind': 'github', 'owner', 'repo', 'ref'} of the part of a GitHub source after the host; ValueError if invalid."""
    path = re.split(r'[?#]', path, maxsplit=1)[0]
    parts = [part for part in path.split(u'/') if part]
    if len(parts) < 2:
        raise ValueError(u"GitHub source '{0}' names no repository: {1}.".format(source, GITHUB_USAGE))
    owner, repo = parts[0], parts[1]
    if repo.lower().endswith(u'.git'):
        repo = repo[:-4]
    for name in (owner, repo):
        if not re.match(REPO_NAME_PATTERN, name) or name in (u'.', u'..'):
            raise ValueError(u"GitHub source '{0}': invalid owner or repository name '{1}'.".format(source, name))
    rest = parts[2:]
    if not rest:
        ref = DEFAULT_REF
    elif rest[0] == u'tree' and len(rest) > 1:
        ref = u'/'.join(rest[1:])
    elif rest[0] == u'commit' and len(rest) == 2 and re.match(r'^[0-9a-fA-F]{7,40}$', rest[1]):
        ref = rest[1]
    else:
        raise ValueError(u"GitHub source '{0}': cannot tell the branch from '/{1}': {2}.".format(
            source, u'/'.join(rest), GITHUB_USAGE))
    if not isValidRef(ref):
        raise ValueError(u"GitHub source '{0}': invalid branch, tag or commit '{1}'.".format(source, ref))
    return {'kind': 'github', 'owner': owner, 'repo': repo, 'ref': ref}


def isValidRef(ref):
    """True for a plausible git branch, tag or commit name (no white space, no ~^:?*[\\, no '..')."""
    return bool(ref) and re.match(r'^[^\s~^:?*\[\\]+$', ref) is not None and u'..' not in ref and u'@{' not in ref


def isCommitSha(text):
    """True for a full 40-digit commit sha."""
    return re.match(r'^[0-9a-fA-F]{40}$', text or u'') is not None


def sanitizeRef(ref):
    """A folder-name-safe form of a ref; a short hash is appended when characters had to be replaced, so 'a/b' and 'a_b'
    get different cache folders."""
    safe = re.sub(r'[^A-Za-z0-9._-]', u'_', ref)[:60].rstrip(u'.')
    if safe != ref:
        safe = u'{0}-{1}'.format(safe, hashlib.sha1(ref.encode('utf-8')).hexdigest()[:8])
    return safe


def cacheFolderName(owner, repo, ref):
    """Name of the cache folder of a GitHub source, e.g. Owner_repo_main."""
    return u'{0}_{1}_{2}'.format(owner, repo, sanitizeRef(ref))


def quoteUrlPath(text):
    """Percent-encoded UTF-8 form of a URL path; '/' and the unreserved characters are kept."""
    safe = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~/'
    quoted = []
    for byte in bytearray(text.encode('utf-8')):
        char = chr(byte)
        quoted.append(char if char in safe else '%{0:02X}'.format(byte))
    return ''.join(quoted)


def rawUrl(owner, repo, ref, path):
    """URL of a file of a GitHub repository at a ref or commit on raw.githubusercontent.com."""
    return '{0}/{1}/{2}/{3}/{4}'.format(RAW_HOST, owner, repo, quoteUrlPath(ref), quoteUrlPath(path))


def commitApiUrl(owner, repo, ref):
    """GitHub API URL that answers with the commit sha of a ref (Accept: SHA_MEDIA_TYPE)."""
    return '{0}/repos/{1}/{2}/commits/{3}'.format(API_HOST, owner, repo, quoteUrlPath(ref))


def describeHttpFailure(url, status, detail):
    """Log text of a failed request; status None means there was no answer (no connection, timeout, TLS)."""
    if status == 404:
        return u'{0}: not found (HTTP 404): repository or ref not found, or the repository is private'.format(url)
    if status in RATE_LIMIT_STATUSES:
        return u'{0}: GitHub rate limit (HTTP {1}) - try again later or set source to a local folder'.format(url, status)
    if status is None:
        return u'{0}: no answer ({1})'.format(url, detail)
    return u'{0}: HTTP {1} ({2})'.format(url, status, detail)


def parseRetryAfter(value):
    """Seconds of a Retry-After header value, None when it is missing or an HTTP date (then the backoff applies)."""
    try:
        seconds = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return max(seconds, 0.0)


def retryDelay(status, retryAfter, attempts, waited):
    """Seconds to wait before the next try of a failed download, None for no retry.

    Only RETRY_STATUSES are retried (rate limit and temporary server errors; a missing answer already took the
    timeout), at most RETRY_ATTEMPTS tries in all; the delay is Retry-After when given, else RETRY_BACKOFF_S doubled
    per try; no retry when the total wait would exceed MAX_RETRY_WAIT_S, so Grasshopper does not freeze for long.
    attempts: tries made so far; waited: seconds already waited.
    """
    if status not in RETRY_STATUSES or attempts >= RETRY_ATTEMPTS:
        return None
    delay = retryAfter if retryAfter is not None else RETRY_BACKOFF_S * 2 ** (attempts - 1)
    if waited + delay > MAX_RETRY_WAIT_S:
        return None
    return delay


def canUseCache(status):
    """True when a failed GitHub request may fall back to a complete cached copy: no answer, a rate limit or a server
    error; not a 404 (wrong repository or ref, or a private repository) or another client error."""
    return status is None or status in RATE_LIMIT_STATUSES or status >= 500


def parseManifest(text):
    """{'format', 'generated', 'files': {file name: {'sha256', 'size'}}, 'ignored': [file names]} of a
    trnlizard_manifest.json text.

    Files this updater does not know (neither a top-level script without leading '_' nor trnlizard_icons.json) are
    left out and listed under 'ignored', so a newer manifest with new kinds of files still works. ValueError when the
    text is no valid manifest: not JSON, a format newer than MANIFEST_FORMAT, no files, a file name with a path, names
    that only differ in case, or a sha256 that is not 64 hex digits. sha256 is getHash of the script text; size (bytes
    of the normalized UTF-8 text) is informative only.
    """
    try:
        data = json.loads(text)
    except ValueError as e:
        raise ValueError(u'not valid JSON ({0})'.format(e))
    if not isinstance(data, dict):
        raise ValueError(u'not a JSON object')
    version = data.get('format')
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError(u'no valid format number')
    if version > MANIFEST_FORMAT:
        raise ValueError(u'format {0} is newer than this updater reads ({1}): paste the new Lizard_Updater.py into this '
                         u'component by hand'.format(version, MANIFEST_FORMAT))
    files = data.get('files')
    if not isinstance(files, dict) or not files:
        raise ValueError(u'no files listed')
    result = {}
    ignored = []
    for name in files:
        entry = files[name]
        if not isinstance(name, str) or not name.strip() or re.search(r'[/\\:]', name) or name.strip('.') == '':
            raise ValueError(u"invalid file name '{0}'".format(name))
        if not (re.match(SCRIPT_NAME_PATTERN, name) or name in BUNDLE_NAMES):
            ignored.append(name)
            continue
        if not isinstance(entry, dict):
            raise ValueError(u'entry of {0} is not an object'.format(name))
        sha = entry.get('sha256')
        if not isinstance(sha, str) or not re.match(r'^[0-9a-fA-F]{64}$', sha):
            raise ValueError(u'invalid sha256 of {0}'.format(name))
        size = entry.get('size')
        if size is not None and (not isinstance(size, int) or isinstance(size, bool) or size < 0):
            raise ValueError(u'invalid size of {0}'.format(name))
        result[name] = {'sha256': sha.lower(), 'size': size}
    if not result:
        raise ValueError(u'no files listed that this updater uses')
    lowered = [name.lower() for name in result]
    if len(set(lowered)) != len(lowered):
        raise ValueError(u'file names that only differ in case')
    generated = data.get('generated')
    return {'format': version, 'generated': generated if isinstance(generated, str) else None, 'files': result,
            'ignored': sorted(ignored)}


def planDownloads(files, cachedHashes):
    """(file names to download, file names whose cached copy is up to date), both sorted.

    files: manifest files; cachedHashes: {file name: getHash of the cached text, None when unreadable}. A file is
    downloaded when its cached copy is missing, unreadable or has another hash than the manifest.
    """
    download, unchanged = [], []
    for name in sorted(files):
        if cachedHashes.get(name) == files[name]['sha256']:
            unchanged.append(name)
        else:
            download.append(name)
    return download, unchanged


def planRemovals(files, cachedNames):
    """Sorted cached .py file names (and the icons file) that the manifest no longer lists (exact case: a file whose
    name changed case is removed and downloaded again under its new name)."""
    return sorted(name for name in cachedNames if (name.endswith('.py') or name in BUNDLE_NAMES) and name not in files)


def otherCacheFolders(names, current, hasManifest):
    """Sorted cache folder names to delete after a successful download into current: every other folder of the cache
    root that holds a trnlizard_manifest.json (hasManifest(name)), i.e. a cache of another repository or branch."""
    return sorted(name for name in names if name != current and hasManifest(name))


def parseIcons(text):
    """{script base name: base64 PNG} of a trnlizard_icons.json text; ValueError when it is no valid icons file."""
    try:
        data = json.loads(text)
    except ValueError as e:
        raise ValueError(u'not valid JSON ({0})'.format(e))
    icons = data.get('icons') if isinstance(data, dict) else None
    if not isinstance(icons, dict):
        raise ValueError(u'no icons listed')
    result = {}
    for name in icons:
        value = icons[name]
        if not isinstance(value, str) or not re.match(r'^[A-Za-z0-9+/]+={0,2}$', value):
            raise ValueError(u'icon of {0} is not base64'.format(name))
        result[name] = value
    return result


def userObjectHash(code, icon):
    """Hash that decides whether a UserObject is rewritten: the script text, plus its icon when it has one."""
    return getHash(code) if not icon else getHash(code + u'\n#icon ' + icon)


# ---------------------------------------------------------------------------------------------------------------------
# Pure preset logic (trnlizard_presets.json; unit-tested in tests/test_updater_presets.py)
# ---------------------------------------------------------------------------------------------------------------------

def _text(value, default=u''):
    return value if isinstance(value, str) and value else default


def parsePresets(text):
    """{'presets': {name: entry}, 'shared': {name: entry}} of a trnlizard_presets.json text; ValueError when invalid.

    entry: name, nickName, description, category, subCategory, xml (GH_Archive XML of the cluster, the template),
    icon (base64 PNG or None); a shared cluster also has role ('sync': presets and canvas copies follow the template;
    'keep': presets get the template, a canvas copy is never replaced) and aliases (its other nick names).
    """
    try:
        data = json.loads(text)
    except ValueError as e:
        raise ValueError(u'not valid JSON ({0})'.format(e))
    if not isinstance(data, dict):
        raise ValueError(u'not a JSON object')
    result = {}
    for group in ('presets', 'shared'):
        entries = data.get(group) or {}
        if not isinstance(entries, dict):
            raise ValueError(u'{0} is not an object'.format(group))
        result[group] = {}
        for name in entries:
            entry = entries[name]
            if not isinstance(entry, dict) or not _text(entry.get('xml')).strip():
                raise ValueError(u'{0} {1} has no template'.format(group, name))
            role = entry.get('role')
            if group == 'shared' and role not in ('sync', 'keep'):
                raise ValueError(u"shared {0} has no role 'sync' or 'keep'".format(name))
            aliases = entry.get('aliases') if isinstance(entry.get('aliases'), list) else []
            result[group][name] = {
                'name': _text(entry.get('name'), name), 'nickName': _text(entry.get('nickName'), name),
                'description': _text(entry.get('description')), 'category': _text(entry.get('category'), DEFAULT_CATEGORY),
                'subCategory': _text(entry.get('subCategory'), DEFAULT_SUBCATEGORY), 'xml': entry['xml'],
                'icon': entry.get('icon') if _text(entry.get('icon')) else None, 'role': role,
                'aliases': [alias for alias in aliases if isinstance(alias, str)]}
    return result


def sharedNameOf(nickName, shared):
    """Name of the shared cluster a cluster with this nick name is a copy of, None for any other cluster."""
    for name in sorted(shared or {}):
        if nickName == name or nickName in shared[name]['aliases']:
            return name
    return None


def scriptsFingerprint(hashes):
    """One hash of all scripts ({base name: hash}): a preset is rebuilt when any script changed."""
    return getHash(u'\n'.join(u'{0}:{1}'.format(name, hashes[name]) for name in sorted(hashes)))


def presetHash(entry, shared, fingerprint):
    """Hash that decides whether a preset UserObject is rewritten: its template and icon, the shared templates it may
    contain and the scripts."""
    parts = [entry['xml'], entry.get('icon') or u'', fingerprint] + [shared[name]['xml'] for name in sorted(shared or {})]
    return getHash(u'\n#part\n'.join(parts))


def sharedMarker(entry):
    """Text in the Description of a shared cluster made from this template; a canvas copy without it is outdated."""
    return SHARED_MARKER.format(getHash(entry['xml'])[:12])


def pairParams(oldNames, newNames):
    """(old index, new index) to rewire: by position when both sides have the same names in the same order (also with
    repeated names such as Data, Data), else by the names that occur once on both sides."""
    if list(oldNames) == list(newNames):
        return [(index, index) for index in range(len(oldNames))]
    return [(oldIndex, newIndex) for name, oldIndex, newIndex in wiringPlan(oldNames, newNames)]


def verifyDownload(name, text, expected):
    """None when getHash of a downloaded text is the manifest sha256, else the error text."""
    actual = getHash(text)
    if actual == expected:
        return None
    return (u'{0}: the download does not match the manifest (sha256 {1}... instead of {2}...), it was not written. The '
            u'manifest may be out of date (tools/build_manifest.py) or raw.githubusercontent.com still serves an older '
            u'copy: try again in a few minutes.').format(name, actual[:12], expected[:12])


def cacheIsComplete(files, cachedHashes):
    """True when every manifest file is cached with the manifest hash."""
    return all(cachedHashes.get(name) == files[name]['sha256'] for name in files)


# ---------------------------------------------------------------------------------------------------------------------
# Grasshopper glue (runs inside Grasshopper; the same text works in IronPython 2.7 and in CPython 3 / pythonnet)
# ---------------------------------------------------------------------------------------------------------------------

def _impl(obj):
    """The object itself: pythonnet may hand out an interface view (e.g. IGH_DocumentObject) of a .NET object."""
    return getattr(obj, '__implementation__', obj)


def _typeName(obj):
    try:
        return str(obj.GetType().Name)
    except Exception:
        return type(obj).__name__


def _setIfPresent(obj, name, value):
    """Set a property that only some param types have; True when it was set."""
    if not hasattr(obj, name):
        return False
    try:
        setattr(obj, name, value)
        return True
    except Exception:
        return False


def scriptKind(obj):
    """Kind of a Python script component (KIND_*), None for any other object."""
    if not isinstance(obj, Grasshopper.Kernel.GH_Component):
        return None
    return classifyScriptComponent(_typeName(obj), hasattr(obj, 'Code'), hasattr(obj, 'SetSource'))


def readComponentCode(comp, kind):
    """Script text of a component: Code of legacy GhPython, TryGetSource(out text) of the Rhino 8 script components."""
    if kind == KIND_GHPYTHON:
        return comp.Code
    if not hasattr(comp, 'TryGetSource'):  # Rhino 8 before SR18
        return None
    for args in ((), (None,), ('',)):  # the out argument: omitted (IronPython, pythonnet 3) or a placeholder
        try:
            result = comp.TryGetSource(*args)
        except TypeError:
            continue
        if isinstance(result, tuple) and len(result) == 2:
            return result[1] if result[0] else None
        return None
    return None


def writeComponentCode(comp, kind, code):
    if kind == KIND_GHPYTHON:
        comp.Code = code
    else:
        comp.SetSource(code)  # Rhino 8 SR18 or later


def readScript(path):
    """Text of a script file without BOM (a BOM in the code breaks IronPython components)."""
    try:
        handle = io.open(path, 'r', encoding='utf-8-sig')
    except LookupError:
        handle = io.open(path, 'r', encoding='utf-8')
    try:
        text = handle.read()
    finally:
        handle.close()
    return text.lstrip(u'\ufeff')


def findScripts(folder, log):
    """{base name: path} of the .py files of a folder (not recursive, files starting with '_' left out)."""
    scripts = {}
    try:
        for fileName in os.listdir(folder):
            path = os.path.join(folder, fileName)
            if fileName.endswith('.py') and not fileName.startswith('_') and os.path.isfile(path):
                scripts[os.path.splitext(fileName)[0]] = path
    except Exception as e:
        log.append('Error scanning folder: {0}'.format(e))
    return scripts


def collectScriptComponents(doc, selfGuid, log):
    """(component, owning cluster or None) for every Python script component of the document and of its clusters."""
    found = []
    for obj in doc.Objects:
        obj = _impl(obj)
        try:
            if isinstance(obj, Grasshopper.Kernel.Special.GH_Cluster):
                inner = obj.Document('')
                if inner is None:
                    log.append('Cluster {0} is locked or empty: not searched.'.format(obj.NickName))
                    continue
                for innerObj in inner.Objects:
                    innerObj = _impl(innerObj)
                    if scriptKind(innerObj) is not None:
                        found.append((innerObj, obj))
            elif scriptKind(obj) is not None and str(obj.InstanceGuid) != str(selfGuid):
                found.append((obj, None))
        except Exception as e:
            log.append('Error collecting components: {0}'.format(e))
    return found


def paramNames(params):
    return [str(p.Name) for p in params]


def hasStandardOutput(comp):
    """True when the first output is the code output 'out' (Param_String) of the script component."""
    outputs = list(comp.Params.Output)
    if not outputs:
        return False
    return str(outputs[0].Name) == STANDARD_OUTPUT and str(outputs[0].ComponentGuid) == PARAM_STRING_ID


class VariableParams(object):
    """IGH_VariableParameterComponent members of a component, also when they are implemented explicitly."""

    def __init__(self, comp):
        self.comp = comp

    def call(self, name, *args):
        method = getattr(self.comp, name, None)
        if method is not None:
            return method(*args)
        face = Grasshopper.Kernel.IGH_VariableParameterComponent
        try:
            method = getattr(face(self.comp), name)  # pythonnet: interface view of the object
        except Exception:
            return getattr(face, name)(self.comp, *args)  # IronPython: unbound interface method
        return method(*args)


def accessValue(access):
    return getattr(Grasshopper.Kernel.GH_ParamAccess, access if access in ('item', 'list', 'tree') else 'item')


def clrType(typeName):
    """System.Type of a type name, None if it cannot be found."""
    try:
        found = System.Type.GetType(typeName)
        if found is not None:
            return found
    except Exception:
        pass
    if typeName == 'Rhino.Geometry.Brep':
        try:
            import clr
            import Rhino
            return clr.GetClrType(Rhino.Geometry.Brep)
        except Exception:
            return None
    return None


def createParam(vpc, side, index, spec, kind, isInput):
    """A new param from the component's own factory, named and configured after its docstring spec."""
    param = _impl(vpc.call('CreateParameter', side, index))
    if param is None:
        raise RuntimeError('CreateParameter returned no param for ' + spec['name'])
    name = spec['name']
    param.Name = name
    param.NickName = name
    _setIfPresent(param, 'VariableName', name)  # Rhino 8 script params: name of the script variable
    _setIfPresent(param, 'PrettyName', name)
    if kind == KIND_GHPYTHON or not _setIfPresent(param, 'ToolTip', spec['description']):
        param.Description = spec['description']
    if isInput:
        param.Access = accessValue(spec['access'])
        param.Optional = not spec['required']  # legacy GhPython keeps all its inputs optional
    if param.Attributes is None:
        param.CreateAttributes()
    return param


def applyTypeHint(param, spec):
    """Set the type hint of a new input; returns a note when it could not be set (the default hint stays)."""
    hint = typeHintSpec(spec['type'])
    if hint is None:
        return None
    if hasattr(param, 'TypeHints'):  # Rhino 8 script param
        candidates = [clrType(hint['clrType'])] + list(hint['names'])
        for candidate in candidates:
            if candidate is None:
                continue
            try:
                if param.TypeHints.Select(candidate) is not False:
                    return None
            except Exception:
                continue
    hints = getattr(param, 'Hints', None)  # legacy GhPython Param_ScriptVariable
    if hints is not None:
        for candidate in hints:
            if str(candidate.HintID) == hint['legacyId'] or str(candidate.TypeName).lower() in hint['names']:
                param.TypeHint = candidate
                return None
    return "type hint '{0}' of {1} not available: default hint kept".format(spec['type'], spec['name'])


def applyParamChanges(comp, kind, action, notes):
    """Unregister the removed params and insert the added ones (component's own factory, docstring position)."""
    plan = action['plan']
    kernel = Grasshopper.Kernel
    vpc = VariableParams(comp)
    for name in plan['removedInputs']:
        comp.Params.UnregisterInputParameter(list(comp.Params.Input)[paramNames(comp.Params.Input).index(name)], True)
    for name in plan['removedOutputs']:
        comp.Params.UnregisterOutputParameter(list(comp.Params.Output)[paramNames(comp.Params.Output).index(name)], True)
    created = []
    for isInput, insertions, specs, side in ((True, plan['inputInsertions'], action['inputSpecs'], kernel.GH_ParameterSide.Input),
                                             (False, plan['outputInsertions'], action['outputSpecs'], kernel.GH_ParameterSide.Output)):
        for name, index in insertions:
            if not vpc.call('CanInsertParameter', side, index):
                raise RuntimeError('the component does not accept a new param at index {0} ({1})'.format(index, name))
            param = createParam(vpc, side, index, specs[name], kind, isInput)
            if isInput:
                comp.Params.RegisterInputParam(param, index)
            else:
                comp.Params.RegisterOutputParam(param, index)
            created.append((param, specs[name], isInput))
    comp.Params.OnParametersChanged()
    vpc.call('VariableParameterMaintenance')
    for param, spec, isInput in created:
        if isInput:
            note = applyTypeHint(param, spec)
            if note:
                notes.append(note)
        if hasattr(param, 'VariableName') and str(param.VariableName) != spec['name']:
            notes.append("the script variable of {0} is '{1}': rename it by hand".format(spec['name'], param.VariableName))
    if comp.Attributes is not None:
        comp.Attributes.ExpireLayout()


def recordUndo(doc, obj, how='change'):
    """Undo record for a change ('change'), an added object ('add') or the wires of a param ('wire'); False if not possible."""
    try:
        if how == 'add':
            doc.UndoUtil.RecordAddObjectEvent(UNDO_NAME, obj)
        elif how == 'wire':
            doc.UndoUtil.RecordWireEvent(UNDO_NAME, obj)
        else:
            obj.RecordUndoEvent(UNDO_NAME)
        return True
    except Exception:
        return False


def copyComponent(old):
    """New instance of the same component type and language with the saved state of ``old`` (code, flags, params
    with their names, access, type hints, data mapping and internalised data), but without wires and with new ids.

    The state goes through GH_Archive (what copy/paste and file saving use), so it works for every kind of script
    component without knowing its properties; ComponentServer.EmitObject creates the same component type.
    """
    try:
        import clr
        clr.AddReference('GH_IO')
    except Exception:
        pass
    from GH_IO.Serialization import GH_Archive
    archive = GH_Archive()
    if not archive.AppendObject(old, 'LizardComponent'):
        raise RuntimeError('GH_Archive could not store the component')
    reader = GH_Archive()
    if not reader.Deserialize_Xml(stripParamSources(archive.Serialize_Xml())):
        raise RuntimeError('GH_Archive could not read the stored component')
    new = Grasshopper.Instances.ComponentServer.EmitObject(old.ComponentGuid)
    if new is None:
        raise RuntimeError('no component type registered for ' + str(old.ComponentGuid))
    new = _impl(new)
    new.CreateAttributes()
    if not reader.ExtractObject(new, 'LizardComponent'):
        raise RuntimeError('GH_Archive could not restore the copy')
    new.NewInstanceGuid()
    for param in list(new.Params.Input) + list(new.Params.Output):
        param.NewInstanceGuid()
        if param.Attributes is None:
            param.CreateAttributes()
        if list(param.Sources):
            param.RemoveAllSources()
    return new


def drawing():
    """The System.Drawing namespace (PointF, Color)."""
    try:
        import clr
        clr.AddReference('System.Drawing')
    except Exception:
        pass
    import System.Drawing
    return System.Drawing


def makeGroup(doc, member, label):
    group = Grasshopper.Kernel.Special.GH_Group()
    group.CreateAttributes()
    group.NickName = label
    group.Colour = drawing().Color.FromArgb(GROUP_ARGB[0], GROUP_ARGB[1], GROUP_ARGB[2], GROUP_ARGB[3])
    group.AddObject(member.InstanceGuid)
    doc.AddObject(group, False)
    return group


def moveSource(recipient, oldSource, newSource):
    """Rewire one recipient from the old output to the new one, keeping its place in the source list."""
    try:
        recipient.ReplaceSource(oldSource, newSource)
    except Exception:
        recipient.RemoveSource(oldSource)
        recipient.AddSource(newSource)


def applyInPlace(doc, action, log):
    """Code update, plus params added in place for an 'add' action."""
    comp = action['component']
    notes = []
    if not recordUndo(doc, comp):
        notes.append('no undo record')
    if action['what'] == 'add':
        applyParamChanges(comp, action['kind'], action, notes)
    if action['codeChanged']:
        writeComponentCode(comp, action['kind'], action['code'])
    comp.ExpireSolution(False)
    if action['cluster'] is not None:
        action['cluster'].ExpireSolution(False)
    return notes


def applyReplacement(doc, action, log):
    """New copy with the new code and IO next to the old component, wired by name, in a red group; old one locked."""
    old = action['component']
    plan = action['plan']
    notes = []
    new = copyComponent(old)
    applyParamChanges(new, action['kind'], action, notes)
    writeComponentCode(new, action['kind'], action['code'])
    pivot = old.Attributes.Pivot
    new.Attributes.Pivot = drawing().PointF(pivot.X + REPLACEMENT_OFFSET, pivot.Y + REPLACEMENT_OFFSET)
    new.Attributes.ExpireLayout()
    doc.AddObject(new, False)
    recordUndo(doc, new, 'add')
    group = makeGroup(doc, new, replacementLabel(action['name'], plan['removedInputs'], plan['removedOutputs']))
    recordUndo(doc, group, 'add')
    # lock the old one first: TRNLizard components register their data by instance id, two live copies would count twice
    if not recordUndo(doc, old):
        notes.append('no undo record for the old component')
    old.Locked = True
    old.ExpireSolution(False)
    oldIn, newIn = list(old.Params.Input), list(new.Params.Input)
    for name, oldIndex, newIndex in wiringPlan(paramNames(oldIn), paramNames(newIn)):
        for source in list(oldIn[oldIndex].Sources):
            newIn[newIndex].AddSource(source)
    oldOut, newOut = list(old.Params.Output), list(new.Params.Output)
    for name, oldIndex, newIndex in wiringPlan(paramNames(oldOut), paramNames(newOut)):
        for recipient in list(oldOut[oldIndex].Recipients):  # moved, so downstream data does not arrive twice
            recordUndo(doc, recipient, 'wire')
            moveSource(recipient, oldOut[oldIndex], newOut[newIndex])
    new.ExpireSolution(False)
    return notes


def applyActions(doc, actions, report, reportKey, updater, userObjectsSummary=None):
    """ScheduleSolution callback: make the planned document changes and keep the final report for the next run."""
    log, updated, skipped, errors = report
    try:
        log.append('')
        log.append('=== Applying changes ===')
        for action in actions:
            try:
                if action['what'] == 'replace':
                    notes = applyReplacement(doc, action, log)
                elif action['what'] == 'sync':
                    notes = applySharedSync(doc, action)
                else:
                    notes = applyInPlace(doc, action, log)
                log.append('Done: {0} ({1}){2}'.format(action['name'], action['what'], ': ' + '; '.join(notes) if notes else ''))
            except Exception as e:
                message = 'Error updating {0} ({1}): {2}'.format(action['name'], action['what'], e)
                log.append(message)
                errors.append(message)
                if action['name'] in updated:
                    updated.remove(action['name'])
        log.append('')
        log.append('=== Update Summary ===')
        log.append('Updated: {0}'.format(len(updated)))
        log.append('Skipped: {0}'.format(len(skipped)))
        if userObjectsSummary:
            log.append(userObjectsSummary)
        log.append('Errors:  {0}'.format(len(errors)))
    finally:
        sc.sticky[reportKey] = (log, updated, skipped, errors)
        try:
            updater.ExpireSolution(False)  # runs once more in this solution and shows the final report
        except Exception:
            pass


def describePlan(plan):
    parts = []
    for key, text in (('addedInputs', 'inputs added'), ('addedOutputs', 'outputs added'),
                      ('removedInputs', 'inputs removed'), ('removedOutputs', 'outputs removed')):
        if plan[key]:
            parts.append('{0}: {1}'.format(text, ', '.join(plan[key])))
    return '; '.join(parts)


def planComponent(comp, cluster, path, log):
    """Plan the update of one component; returns (status, action or message) with status 'action', 'skipped' or 'error'."""
    name = str(comp.Name)
    kind = scriptKind(comp)
    log.append('')
    log.append('--- Processing: {0}{1} ---'.format(name, ' (in cluster {0})'.format(cluster.NickName) if cluster is not None else ''))
    log.append('Source: {0}'.format(path))
    log.append('Component type: {0}'.format(kind))
    newCode = readScript(path)
    currentCode = readComponentCode(comp, kind)
    if currentCode is None:
        return 'error', 'Could not read the code of {0} ({1}).'.format(name, kind)
    currentHash, newHash = getHash(currentCode), getHash(newCode)
    log.append('Current hash: {0}'.format(currentHash[:12]))
    log.append('New hash:     {0}'.format(newHash[:12]))
    codeChanged = currentHash != newHash
    if codeChanged:
        diffHint = firstDiff(currentCode, newCode)
        if diffHint:
            log.append('First diff: {0}'.format(diffHint))
    currentInputs, currentOutputs = paramNames(comp.Params.Input), paramNames(comp.Params.Output)
    inputSpecs, outputSpecs = parseDocstringIO(newCode)
    log.append('Current inputs:  {0}'.format(currentInputs))
    log.append('Current outputs: {0}'.format(currentOutputs))
    log.append('New script inputs:  {0}'.format([p['name'] for p in inputSpecs or []]))
    log.append('New script outputs: {0}'.format([p['name'] for p in outputSpecs or []]))
    plan = planIOUpdate(currentInputs, currentOutputs,
                        None if inputSpecs is None else [p['name'] for p in inputSpecs],
                        None if outputSpecs is None else [p['name'] for p in outputSpecs],
                        hasStandardOutput(comp))
    for note in plan['notes']:
        log.append('Note: ' + note)
    what = decideAction(codeChanged, plan, cluster is not None, bool(comp.Locked))
    if what == 'skip':
        return 'skipped', 'Component {0} is already up to date.'.format(name)
    if what == 'locked':
        return 'skipped', ('Component {0} is locked and its IO would lose params ({1}): left alone, it is probably the old '
                           'copy of an earlier replacement. Delete it, or unlock it and run the updater again.').format(name, describePlan(plan))
    if what == 'manual':
        where = 'inside cluster {0}'.format(cluster.NickName) if cluster is not None else 'on the canvas'
        return 'error', 'Manual update needed for {0} {1}: {2}. Nothing was changed.'.format(
            name, where, describePlan(plan) or plan['notes'][-1])
    if kind != KIND_GHPYTHON and not hasattr(comp, 'SetSource'):
        return 'error', 'Cannot set the code of {0} ({1}): Rhino 8 SR18 or later is needed.'.format(name, kind)
    if getattr(comp, 'IsSDKMode', False) and what in ('add', 'replace'):
        log.append('Note: SDK-mode script: check that RunScript takes the new inputs')
    action = {'name': name, 'component': comp, 'cluster': cluster, 'kind': kind, 'what': what, 'plan': plan,
              'code': newCode, 'codeChanged': codeChanged,
              'inputSpecs': dict((p['name'], p) for p in inputSpecs or []),
              'outputSpecs': dict((p['name'], p) for p in outputSpecs or [])}
    descriptions = {'code': 'code update', 'add': 'params added in place', 'replace': 'replaced by a new copy, old one locked'}
    detail = describePlan(plan)
    log.append('Planned: {0}{1}'.format(descriptions[what], ' (' + detail + ')' if detail else ''))
    return 'action', action


def checkSelf(updater, scripts, log, errors):
    """Log and list as an error when the code of this updater differs from Lizard_Updater.py of the folder; returns
    the message when it is outdated, '' when it is up to date, None when it could not be checked."""
    path = scripts.get(UPDATER_SCRIPT)
    if path is None:
        return None
    updater = _impl(updater)
    try:
        ownCode = readComponentCode(updater, scriptKind(updater))
        message = selfCheckMessage(ownCode, readScript(path), path)
    except Exception as e:
        log.append('Note: could not compare this updater with {0}: {1}'.format(path, e))
        return None
    if message:
        log.append('WARNING: ' + message)
        errors.append(message)
        return message
    return None if ownCode is None else u''


def showSelfState(updater):
    """Orange balloon and OUTDATED under the component while the last self check found this updater outdated (kept in
    sc.sticky, as Grasshopper clears the runtime messages on every solution)."""
    updater = _impl(updater)
    message = sc.sticky.get(OUTDATED_KEY + str(updater.InstanceGuid))
    try:
        if message:
            updater.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, message)
            updater.Message = OUTDATED_MESSAGE
        elif message is not None and getattr(updater, 'Message', None) == OUTDATED_MESSAGE:
            updater.Message = ''
    except Exception:
        pass


def sourceCacheRoot():
    """Folder of the cached GitHub sources: TRNLizard/source in the Grasshopper AppData folder, else in %APPDATA% or in
    the temp folder."""
    base = None
    try:
        base = str(Grasshopper.Folders.AppDataFolder)
    except Exception:
        base = None
    if not base:
        base = os.environ.get('APPDATA')
    if not base:
        import tempfile
        base = tempfile.gettempdir()
    return os.path.join(base, *CACHE_SUBFOLDER)


def cachedScriptHashes(folder):
    """{file name: getHash of the text, None when unreadable} of the .py files and the icons file of a cache folder
    (empty when it is missing)."""
    hashes = {}
    if not os.path.isdir(folder):
        return hashes
    for fileName in os.listdir(folder):
        path = os.path.join(folder, fileName)
        if (fileName.endswith('.py') or fileName in BUNDLE_NAMES) and os.path.isfile(path):
            try:
                hashes[fileName] = getHash(readScript(path))
            except Exception:
                hashes[fileName] = None
    return hashes


def readCachedManifest(folder):
    """Parsed manifest of the last download into a cache folder, None when there is none or it is invalid."""
    path = os.path.join(folder, MANIFEST_NAME)
    if not os.path.isfile(path):
        return None
    try:
        return parseManifest(readScript(path))
    except Exception:
        return None


def writeTextFile(path, text):
    """Write UTF-8 text (line endings as given) to a temporary file that then replaces path, so an interrupted write
    never leaves half a file under the real name."""
    tmp = path + '.tmp'
    handle = io.open(tmp, 'w', encoding='utf-8', newline='')
    try:
        handle.write(text)
    finally:
        handle.close()
    replace = getattr(os, 'replace', None)  # IronPython 2.7 has no os.replace, and os.rename does not overwrite on Windows
    if replace is not None:
        replace(tmp, path)
    else:
        if os.path.exists(path):
            os.remove(path)
        os.rename(tmp, path)


def _webErrorDetails(error):
    """(HTTP status or None, Retry-After seconds or None) of a .NET WebException."""
    response = getattr(error, 'Response', None)
    if response is None:
        return None, None
    response = _impl(response)
    status, retryAfter = None, None
    try:
        status = int(response.StatusCode)
        retryAfter = parseRetryAfter(response.Headers.Get('Retry-After'))
    except Exception:
        pass
    finally:
        try:
            response.Close()
        except Exception:
            pass
    return status, retryAfter


def httpGetText(url, accept=None):
    """GET a URL with .NET (HttpWebRequest, TLS 1.2, HTTP_TIMEOUT_MS) and return the response as text (UTF-8).

    Raises SourceError with the HTTP status (None without an answer) and the Retry-After seconds.
    """
    from System.Net import ServicePointManager, SecurityProtocolType, WebException, WebRequest
    from System.IO import StreamReader
    from System.Text import Encoding
    try:
        current = ServicePointManager.SecurityProtocol
        # .NET Framework apps may still default to TLS 1.0/1.1; SystemDefault (0) is left alone (the OS picks)
        if int(current) != 0 and not int(current) & int(SecurityProtocolType.Tls12):
            ServicePointManager.SecurityProtocol = current | SecurityProtocolType.Tls12
    except Exception:
        pass
    try:
        request = _impl(WebRequest.Create(url))  # an HttpWebRequest (pythonnet hands out the WebRequest view)
        request.Method = 'GET'
        request.Timeout = HTTP_TIMEOUT_MS
        request.ReadWriteTimeout = HTTP_TIMEOUT_MS
        request.UserAgent = USER_AGENT
        if accept:
            request.Accept = accept
        response = _impl(request.GetResponse())
    except WebException as e:
        status, retryAfter = _webErrorDetails(e)
        raise SourceError(describeHttpFailure(url, status, e.Message), status, retryAfter)
    except Exception as e:
        raise SourceError(describeHttpFailure(url, None, e))
    try:
        reader = StreamReader(response.GetResponseStream(), Encoding.UTF8)  # .NET decodes: same in IronPython and pythonnet
        try:
            return reader.ReadToEnd()
        finally:
            reader.Close()
    except Exception as e:
        raise SourceError(describeHttpFailure(url, None, e))
    finally:
        response.Close()


def fetchWithRetry(fetch, url, log, waits, sleep=None):
    """fetch(url, None) with retries after a rate limit or a temporary server error (see retryDelay); the last
    SourceError is raised when every try failed. waits: [seconds waited], shared by all downloads of one update, so
    MAX_RETRY_WAIT_S caps the waits of the whole update."""
    if sleep is None:
        import time
        sleep = time.sleep
    attempts = 0
    while True:
        try:
            return fetch(url, None)
        except SourceError as e:
            attempts += 1
            delay = retryDelay(e.status, e.retryAfter, attempts, waits[0])
            if delay is None:
                raise
            log.append('Note: HTTP {0} for {1}, try {2} of {3} in {4:.1f} s'.format(e.status, url, attempts + 1,
                                                                                  RETRY_ATTEMPTS, delay))
            sleep(delay)
            waits[0] += delay


def resolveCommit(owner, repo, ref, fetch, log):
    """Commit sha of a ref from api.github.com, so that the manifest and the scripts come from one commit; None when
    the lookup fails (optional: e.g. the API rate limit of 60 requests per hour and IP), then the files come by ref."""
    if isCommitSha(ref):
        return ref.lower()
    try:
        sha = (fetch(commitApiUrl(owner, repo, ref), SHA_MEDIA_TYPE) or u'').strip()
        if not isCommitSha(sha):
            raise SourceError(u'unexpected answer of the GitHub API')
    except SourceError as e:
        log.append(u'Note: the commit of {0} could not be looked up ({1}); the files come by ref from '
                   u'raw.githubusercontent.com, which caches them for about 5 minutes: a change pushed just now may '
                   u'only show a few minutes later.'.format(ref, e))
        return None
    return sha.lower()


def fallBackToCache(folder, failure, log, errors):
    """The cache folder when GitHub cannot be used now but the last download is complete there, else None (error)."""
    status = getattr(failure, 'status', None)
    manifest = readCachedManifest(folder) if canUseCache(status) else None
    if manifest is not None and cacheIsComplete(manifest['files'], cachedScriptHashes(folder)):
        log.append(u'WARNING: {0}. Using the cached copy (manifest generated {1}) in {2}.'.format(
            failure, manifest['generated'], folder))
        return folder
    message = u'{0}.'.format(failure)
    if canUseCache(status):
        message += u' No complete cached copy to fall back to in {0}.'.format(folder)
    errors.append(message)
    log.append(u'Error: ' + message)
    return None


def syncGitHubSource(info, log, errors, fetch=None, root=None):
    """Bring the cache folder of a GitHub source up to date with its trnlizard_manifest.json; the folder or None.

    Only missing and changed scripts are downloaded (getHash against the manifest); every download must match its
    manifest hash, and nothing is written unless all downloads succeeded. Cached scripts the manifest no longer lists
    are deleted (only .py files of this cache folder). Without a usable answer of GitHub a complete cached copy is used.
    fetch(url, accept) -> text, raising SourceError (default httpGetText); root: cache root (default sourceCacheRoot()).
    """
    fetch = fetch or httpGetText
    owner, repo, ref = info['owner'], info['repo'], info['ref']
    folder = os.path.join(root or sourceCacheRoot(), cacheFolderName(owner, repo, ref))
    log.append(u'Source: GitHub {0}/{1}, ref {2}'.format(owner, repo, ref))
    commit = resolveCommit(owner, repo, ref, fetch, log)
    if commit:
        log.append(u'Commit: {0}'.format(commit))
    fetchRef = commit or ref
    waits = [0.0]  # seconds waited for retries in this update
    manifestUrl = rawUrl(owner, repo, fetchRef, MANIFEST_NAME)
    try:
        manifestText = fetchWithRetry(fetch, manifestUrl, log, waits)
    except SourceError as e:
        if e.status == 404 and commit:  # the commit exists, only the manifest is missing
            e = SourceError(u'{0} has no {1} at {2} (commit {3}): the branch predates the manifest, or '
                            u'tools/build_manifest.py was not run and committed'.format(
                                u'{0}/{1}'.format(owner, repo), MANIFEST_NAME, ref, commit[:12]), 404)
        return fallBackToCache(folder, e, log, errors)
    try:
        manifest = parseManifest(manifestText)
    except ValueError as e:
        message = u'Invalid manifest {0}: {1}'.format(manifestUrl, e)
        errors.append(message)
        log.append(u'Error: ' + message)
        return None
    files = manifest['files']
    log.append(u'Manifest generated: {0} ({1} scripts)'.format(manifest['generated'], len(files)))
    if manifest['ignored']:
        log.append(u'Note: files of the manifest this updater does not use: {0}'.format(u', '.join(manifest['ignored'])))
    log.append(u'Cache folder: {0}'.format(folder))
    cached = cachedScriptHashes(folder)
    toDownload, unchanged = planDownloads(files, cached)
    downloads = []
    for name in toDownload:
        try:
            text = fetchWithRetry(fetch, rawUrl(owner, repo, fetchRef, name), log, waits)
        except SourceError as e:
            return fallBackToCache(folder, e, log, errors)
        problem = verifyDownload(name, text, files[name]['sha256'])
        if problem:
            errors.append(problem)
            log.append(u'Error: ' + problem)
            return None
        downloads.append((name, text))
    removals = planRemovals(files, cached)
    try:
        if not os.path.isdir(folder):
            os.makedirs(folder)
        for name in removals:  # before the writes: a file whose name changed case is then written under its new name
            os.remove(os.path.join(folder, name))
        for name, text in downloads:
            writeTextFile(os.path.join(folder, name), text)
        writeTextFile(os.path.join(folder, MANIFEST_NAME), manifestText)  # last: it marks a complete cache
    except Exception as e:
        message = u'Could not update the cache folder {0}: {1}'.format(folder, e)
        errors.append(message)
        log.append(u'Error: ' + message)
        return None
    log.append(u'Downloaded: {0}, unchanged: {1}, removed: {2}'.format(len(downloads), len(unchanged), len(removals)))
    for name in removals:
        log.append(u'Removed from the cache: {0}'.format(name))
    removeOtherCaches(os.path.dirname(folder), os.path.basename(folder), log)
    return folder


def removeOtherCaches(root, current, log):
    """Delete the cache folders of other repositories and branches once the current one is complete; a folder that
    cannot be deleted (e.g. a file in use) is only noted."""
    try:
        names = [name for name in os.listdir(root) if os.path.isdir(os.path.join(root, name))]
    except Exception:
        return
    for name in otherCacheFolders(names, current, lambda n: os.path.isfile(os.path.join(root, n, MANIFEST_NAME))):
        try:
            shutil.rmtree(os.path.join(root, name))
            log.append(u'Removed the old cache folder {0}'.format(name))
        except Exception as e:
            log.append(u'Note: could not remove the old cache folder {0}: {1}'.format(name, e))


def resolveSource(source, log, errors):
    """The folder with the scripts of the source input (see parseSource): a local folder as it is, a GitHub repository
    through its cache folder (syncGitHubSource). None, with the reason in errors, when there is none."""
    try:
        info = parseSource(source)
    except ValueError as e:
        errors.append(str(e))
        return None
    if info['kind'] == 'folder':
        if not os.path.isdir(info['path']):
            errors.append(u'Invalid source folder path: {0}'.format(info['path']))
            return None
        return info['path']
    return syncGitHubSource(info, log, errors)


def userObjectFolder():
    """<Grasshopper UserObjects folder>/TRNLizard, None when this Grasshopper has no UserObject API."""
    folders = getattr(Grasshopper, 'Folders', None)
    root = getattr(folders, 'DefaultUserObjectFolder', None) if folders is not None else None
    if not root or getattr(Grasshopper.Kernel, 'GH_UserObject', None) is None:
        return None
    return os.path.join(str(root), USEROBJECT_SUBFOLDER)


def userObjectComponentGuid(updater, log):
    """ComponentGuid of the script component type of the UserObjects: the kind of this updater when it runs
    IronPython (legacy GhPython or Rhino 8 Python 2), legacy GhPython when it is a Rhino 8 Python 3 component (the
    TRNLizard scripts are IronPython 2 code)."""
    updater = _impl(updater)
    kind = scriptKind(updater)
    if kind in (KIND_GHPYTHON, KIND_IRONPYTHON2):
        return updater.ComponentGuid
    log.append('UserObjects: this updater is a {0} component; the UserObjects are legacy GhPython (IronPython 2.7) '
               'components, as the TRNLizard scripts are IronPython 2 code.'.format(kind))
    guid = System.Guid(LEGACY_GHPYTHON_ID)
    if Grasshopper.Instances.ComponentServer.EmitObject(guid) is None:
        raise RuntimeError('the legacy GhPython Script component ({0}) is not available in this Grasshopper: no '
                           'UserObjects written'.format(LEGACY_GHPYTHON_ID))
    return guid


def loadIcons(folder, log):
    """{script base name: base64 PNG} of trnlizard_icons.json in the source folder; empty when there is none."""
    path = os.path.join(folder, ICONS_NAME)
    if not os.path.isfile(path):
        log.append('No {0} in the source: UserObjects keep the default icon.'.format(ICONS_NAME))
        return {}
    try:
        return parseIcons(readScript(path))
    except Exception as e:
        log.append('Note: {0} not used: {1}'.format(ICONS_NAME, e))
        return {}


def iconBitmap(base64Png):
    """System.Drawing.Bitmap of a base64 PNG (a copy, so the stream can be closed)."""
    stream = System.IO.MemoryStream(System.Convert.FromBase64String(base64Png))
    try:
        loaded = drawing().Bitmap(stream)
        try:
            return drawing().Bitmap(loaded)
        finally:
            loaded.Dispose()
    finally:
        stream.Dispose()


def loadPresets(folder, log):
    """Parsed trnlizard_presets.json of the source folder, None when there is none or it is invalid."""
    path = os.path.join(folder, PRESETS_NAME)
    if not os.path.isfile(path):
        log.append('No {0} in the source: no preset UserObjects.'.format(PRESETS_NAME))
        return None
    try:
        return parsePresets(readScript(path))
    except Exception as e:
        log.append('Note: {0} not used: {1}'.format(PRESETS_NAME, e))
        return None


def loadClusterXml(xml):
    """A new GH_Cluster restored from the GH_Archive XML of a preset template."""
    try:
        import clr
        clr.AddReference('GH_IO')
    except Exception:
        pass
    from GH_IO.Serialization import GH_Archive
    reader = GH_Archive()
    if not reader.Deserialize_Xml(xml):
        raise RuntimeError('GH_Archive could not read the template')
    cluster = Grasshopper.Kernel.Special.GH_Cluster()
    cluster.CreateAttributes()
    if not reader.ExtractObject(cluster, 'Object'):
        raise RuntimeError('the template holds no cluster')
    return cluster


def rewire(doc, old, new):
    """Move the wires of an old object to its replacement (inputs: same sources; outputs: recipients moved)."""
    oldIn, newIn = list(old.Params.Input), list(new.Params.Input)
    for oldIndex, newIndex in pairParams(paramNames(oldIn), paramNames(newIn)):
        for source in list(oldIn[oldIndex].Sources):
            newIn[newIndex].AddSource(source)
    oldOut, newOut = list(old.Params.Output), list(new.Params.Output)
    for oldIndex, newIndex in pairParams(paramNames(oldOut), paramNames(newOut)):
        for recipient in list(oldOut[oldIndex].Recipients):
            recordUndo(doc, recipient, 'wire')
            moveSource(recipient, oldOut[oldIndex], newOut[newIndex])


def joinGroups(doc, old, new):
    """Put the replacement into every group of the old object."""
    for obj in doc.Objects:
        obj = _impl(obj)
        if isinstance(obj, Grasshopper.Kernel.Special.GH_Group):
            try:
                if any(str(guid) == str(old.InstanceGuid) for guid in obj.ObjectIDs):
                    obj.AddObject(new.InstanceGuid)
            except Exception:
                pass


def swapObject(doc, old, new):
    """Put new where old is (position, wires, groups) and remove old from the document."""
    new.Attributes.Pivot = old.Attributes.Pivot
    new.Attributes.ExpireLayout()
    doc.AddObject(new, False)
    rewire(doc, old, new)
    joinGroups(doc, old, new)
    doc.RemoveObject(old, False)


def updateTemplateDocument(doc, scripts, shared, counts):
    """Bring the script components of a template document (and of its nested clusters) to the scripts of the source
    and put the template of every shared cluster in place. A script that lost params is swapped for a new copy (the
    template keeps no old one). counts: {'scripts': n, 'shared': n, 'errors': [...]}."""
    for obj in list(doc.Objects):
        obj = _impl(obj)
        name = str(getattr(obj, 'Name', ''))
        try:
            if isinstance(obj, Grasshopper.Kernel.Special.GH_Cluster):
                sharedName = sharedNameOf(str(obj.NickName), shared)
                if sharedName is not None:
                    swapObject(doc, obj, buildSharedCluster(shared[sharedName], scripts, counts))
                    counts['shared'] += 1
                else:
                    inner = obj.Document('')
                    if inner is not None:
                        updateTemplateDocument(inner, scripts, shared, counts)
                continue
            if scriptKind(obj) is None or name not in scripts:
                continue
            status, result = planComponent(obj, None, scripts[name], [])
            if status == 'error':
                counts['errors'].append(result)
                continue
            if status != 'action':
                continue
            notes = []
            if result['what'] == 'replace':
                new = copyComponent(obj)
                applyParamChanges(new, result['kind'], result, notes)
                writeComponentCode(new, result['kind'], result['code'])
                swapObject(doc, obj, new)
            else:
                if result['what'] == 'add':
                    applyParamChanges(obj, result['kind'], result, notes)
                if result['codeChanged']:
                    writeComponentCode(obj, result['kind'], result['code'])
            counts['scripts'] += 1
        except Exception as e:
            counts['errors'].append(u'{0}: {1}'.format(name, e))


def buildSharedCluster(entry, scripts, counts):
    """A shared cluster from its template, scripts updated, marked with its template hash."""
    cluster = loadClusterXml(entry['xml'])
    inner = cluster.Document('')
    if inner is not None:
        updateTemplateDocument(inner, scripts, None, counts)
    cluster.Description = u'{0} {1}'.format(entry['description'], sharedMarker(entry)).strip()
    return cluster


def buildPresetCluster(entry, scripts, shared, counts):
    """A preset cluster from its template: shared clusters put in place, scripts updated."""
    cluster = loadClusterXml(entry['xml'])
    inner = cluster.Document('')
    if inner is None:
        raise RuntimeError('the template cluster has no document (password protected?)')
    updateTemplateDocument(inner, scripts, shared, counts)
    return cluster


def planSharedSync(doc, shared, scripts, log, updated, skipped):
    """Actions that replace the outdated canvas copies of shared clusters with role 'sync' by their template."""
    actions = []
    for obj in doc.Objects:
        obj = _impl(obj)
        if not isinstance(obj, Grasshopper.Kernel.Special.GH_Cluster):
            continue
        name = sharedNameOf(str(obj.NickName), shared)
        if name is None:
            continue
        if shared[name]['role'] != 'sync':
            log.append('Shared cluster {0}: kept as it is (your data); only the scripts inside are updated.'.format(name))
            continue
        if sharedMarker(shared[name]) in str(obj.Description or ''):
            log.append('Shared cluster {0} is up to date.'.format(name))
            skipped.append(name)
            continue
        log.append('Planned: shared cluster {0} replaced by the repository copy (wires moved).'.format(name))
        actions.append({'name': name, 'what': 'sync', 'component': obj, 'entry': shared[name], 'scripts': scripts})
        updated.append(name)
    return actions


def applySharedSync(doc, action):
    """Replace a canvas copy of a shared cluster by its template: same place, wires and groups moved, old removed."""
    old = action['component']
    counts = {'scripts': 0, 'shared': 0, 'errors': []}
    new = buildSharedCluster(action['entry'], action['scripts'], counts)
    new.NewInstanceGuid()
    notes = list(counts['errors'])
    try:
        doc.UndoUtil.RecordRemoveObjectEvent(UNDO_NAME, old)
    except Exception:
        notes.append('no undo record for the removal')
    swapObject(doc, old, new)
    recordUndo(doc, new, 'add')
    new.ExpireSolution(False)
    return notes


def buildUserObjectComponent(componentGuid, entry, notes):
    """A new script component made from the script alone: default params removed (the code output 'out' kept),
    params of the docstring added in docstring order (separators too), identity of the script set, code set."""
    comp = Grasshopper.Instances.ComponentServer.EmitObject(componentGuid)
    if comp is None:
        raise RuntimeError('no component type registered for ' + str(componentGuid))
    comp = _impl(comp)
    comp.CreateAttributes()
    kind = scriptKind(comp)
    if kind is None:
        raise RuntimeError('{0} is not a Python script component'.format(componentGuid))
    if kind != KIND_GHPYTHON and not hasattr(comp, 'SetSource'):
        raise RuntimeError('cannot set the code of a {0} component: Rhino 8 SR18 or later is needed'.format(kind))
    standard = hasStandardOutput(comp)
    for param in list(comp.Params.Input):
        comp.Params.UnregisterInputParameter(param, True)
    for param in list(comp.Params.Output)[1 if standard else 0:]:
        comp.Params.UnregisterOutputParameter(param, True)
    inputSpecs, outputSpecs = parseDocstringIO(entry['code'])
    plan = planIOUpdate([], [STANDARD_OUTPUT] if standard else [],
                        None if inputSpecs is None else [p['name'] for p in inputSpecs],
                        None if outputSpecs is None else [p['name'] for p in outputSpecs], standard)
    if plan['kind'] == 'ambiguous':
        raise RuntimeError(plan['notes'][-1])
    notes.extend(note for note in plan['notes'] if 'docstring has no' not in note)
    action = {'plan': plan, 'inputSpecs': dict((p['name'], p) for p in inputSpecs or []),
              'outputSpecs': dict((p['name'], p) for p in outputSpecs or [])}
    applyParamChanges(comp, kind, action, notes)
    info = entry['info']
    comp.Name = info['name']
    comp.NickName = info['nickName']
    comp.Description = info['description']
    comp.Category = info['category']
    comp.SubCategory = info['subCategory']
    if info['message']:
        _setIfPresent(comp, 'Message', info['message'])
    if entry.get('icon') is not None and hasattr(comp, 'SetIconOverride'):
        comp.SetIconOverride(entry['icon'])  # the component placed from the UserObject shows the icon too
    writeComponentCode(comp, kind, entry['code'])
    return comp


def saveUserObject(comp, info, path, icon=None):
    """Write the UserObject file of a component (icon: a Bitmap, else the component's own); returns the GH_UserObject."""
    kernel = Grasshopper.Kernel
    uo = kernel.GH_UserObject()
    uo.Exposure = kernel.GH_Exposure.primary
    if icon is None:
        try:
            icon = comp.Icon_24x24
        except Exception:
            icon = None
    if icon is not None:
        _setIfPresent(uo, 'Icon', icon)
    _setIfPresent(uo, 'BaseGuid', comp.ComponentGuid)
    uo.SetDataFromObject(comp)
    description = uo.Description  # set after SetDataFromObject, so the script's identity is the one saved
    description.Name = info['name']
    description.NickName = info['nickName']
    description.Description = info['description']
    description.Category = info['category']
    description.SubCategory = info['subCategory']
    uo.Path = path
    if uo.SaveToFile() is False:
        raise RuntimeError('GH_UserObject.SaveToFile failed for ' + path)
    return uo


def loadUserObjectState(path, log):
    """The state file as a dict, None when it is missing or unreadable (every UserObject is then written)."""
    if not os.path.isfile(path):
        return None
    try:
        handle = io.open(path, 'r', encoding='utf-8')
        try:
            return json.loads(handle.read())
        finally:
            handle.close()
    except Exception as e:
        log.append('Note: could not read {0} ({1}): every UserObject is written again.'.format(path, e))
        return None


def saveUserObjectState(path, state):
    text = json.dumps(state, indent=2, sort_keys=True)
    if not isinstance(text, type(u'')):
        text = text.decode('utf-8')
    handle = io.open(path, 'w', encoding='utf-8')
    try:
        handle.write(text)
    finally:
        handle.close()


def refreshRibbon(newUserObjects, log):
    """Show new UserObjects in the ribbon without a restart, as far as this Grasshopper offers it."""
    server = Grasshopper.Instances.ComponentServer
    try:
        if newUserObjects and hasattr(server, 'AddUserObject'):
            for uo in newUserObjects:
                server.AddUserObject(uo)
        componentServer = getattr(Grasshopper.Kernel, 'GH_ComponentServer', None)
        if componentServer is not None and hasattr(componentServer, 'UpdateRibbonUI'):
            componentServer.UpdateRibbonUI()
    except Exception as e:
        log.append('Note: could not refresh the ribbon ({0}): restart Grasshopper to see the UserObjects.'.format(e))


def writeUserObjects(scripts, updater, log, errors, icons=None, presets=None):
    """Write a UserObject per component script into <UserObjects folder>/TRNLizard; returns the summary line.

    Only new and changed scripts (or icons) are written (lizard_userobjects.json); icons: {script: base64 PNG} of
    trnlizard_icons.json. presets: parsed trnlizard_presets.json; every preset and shared cluster is written as a
    UserObject too, rebuilt from its template with the scripts of the source whenever a template or a script changed.
    Every failure goes to errors and never stops the canvas update.
    """
    icons = icons or {}
    log.append('')
    log.append('=== UserObjects ===')
    folder = userObjectFolder()
    if folder is None:
        log.append('UserObjects not written: this Grasshopper has no UserObject folder/API.')
        return 'UserObjects: not available'
    log.append('UserObject folder: {0}'.format(folder))
    entries = []
    for script in sorted(scripts):
        try:
            code = readScript(scripts[script])
            if not isComponentScript(code):
                log.append('No UserObject for {0}.py: no Args/Returns docstring and no ghenv.Component.Name.'.format(script))
                continue
            info = parseComponentInfo(code, script)
            entries.append({'script': script, 'name': info['name'], 'file': userObjectFileName(info['name']),
                            'sha256': userObjectHash(code, icons.get(script)), 'info': info, 'code': code,
                            'iconData': icons.get(script)})
        except Exception as e:
            errors.append('UserObject {0}: could not read the script: {1}'.format(script, e))
    if presets:
        fingerprint = scriptsFingerprint(dict((e['script'], getHash(e['code'])) for e in entries))
        for group, kind in (('presets', 'preset'), ('shared', 'shared')):
            for key in sorted(presets[group]):
                preset = presets[group][key]
                info = dict((field, preset[field]) for field in ('name', 'nickName', 'description', 'category',
                                                                  'subCategory'))
                entries.append({'script': kind + ':' + key, 'kind': kind, 'name': preset['name'],
                                'file': userObjectFileName(preset['name']), 'info': info, 'preset': preset,
                                'sha256': presetHash(preset, presets['shared'] if kind == 'preset' else {}, fingerprint),
                                'iconData': preset['icon']})
    try:
        if not os.path.isdir(folder):
            os.makedirs(folder)
        statePath = os.path.join(folder, USEROBJECT_STATE)
        state = loadUserObjectState(statePath, log)
        plan = planUserObjects(entries, state, os.listdir(folder))
    except Exception as e:
        errors.append('UserObjects not written: {0}'.format(e))
        return 'UserObjects: failed'
    previous = state.get('userObjects') if isinstance(state, dict) and isinstance(state.get('userObjects'), dict) else {}
    records = {}
    for entry in plan['unchanged']:
        records[entry['script']] = previous[entry['script']]
    for entry, other in plan['conflicts']:
        errors.append('UserObject {0}: {1} would overwrite the UserObject of {2}.py; not written. Give the script '
                      'another ghenv.Component.Name.'.format(entry['script'], entry['file'], other))

    def keepPrevious(entry):
        """A failed write keeps tracking the last written file, without a hash so that it is retried next time."""
        old = previous.get(entry['script'])
        if isinstance(old, dict) and old.get('file') == entry['file']:
            records[entry['script']] = {'sha256': '', 'file': old['file'], 'name': old.get('name', entry['name'])}

    componentGuid = None
    if any(entry.get('kind') is None for entry, reason in plan['write']):
        try:
            componentGuid = userObjectComponentGuid(updater, log)
        except Exception as e:
            errors.append('UserObjects of the scripts not written: {0}'.format(e))
    written, newUserObjects = 0, []
    for entry, reason in plan['write']:
        if entry.get('kind') is None and componentGuid is None:
            keepPrevious(entry)
            continue
        path = os.path.join(folder, entry['file'])
        isNew = not os.path.isfile(path)
        notes = []
        try:
            entry['icon'] = None
            if entry['iconData']:
                try:
                    entry['icon'] = iconBitmap(entry['iconData'])
                except Exception as e:
                    notes.append('icon not used: {0}'.format(e))
            if entry.get('kind') is None:
                comp = buildUserObjectComponent(componentGuid, entry, notes)
            else:
                counts = {'scripts': 0, 'shared': 0, 'errors': []}
                if entry['kind'] == 'preset':
                    comp = buildPresetCluster(entry['preset'], scripts, presets['shared'], counts)
                else:
                    comp = buildSharedCluster(entry['preset'], scripts, counts)
                notes.append('{0} script components updated, {1} shared clusters put in'.format(
                    counts['scripts'], counts['shared']))
                for problem in counts['errors']:
                    errors.append(u'Preset {0}: {1}'.format(entry['name'], problem))
            uo = saveUserObject(comp, entry['info'], path, entry['icon'])
        except Exception as e:
            errors.append('UserObject {0} not written: {1}'.format(entry['name'], e))
            keepPrevious(entry)
            continue
        written += 1
        if isNew:
            newUserObjects.append(uo)
        records[entry['script']] = {'sha256': entry['sha256'], 'file': entry['file'], 'name': entry['name']}
        log.append('UserObject written: {0} -> {1} ({2}; {3} / {4}){5}'.format(
            entry['name'], entry['file'], reason, entry['info']['category'], entry['info']['subCategory'],
            ': ' + '; '.join(notes) if notes else ''))
    removed = 0
    for script, fileName in plan['stale']:
        path = os.path.join(folder, fileName)
        try:
            if os.path.isfile(path):
                os.remove(path)
            removed += 1
            log.append('UserObject removed: {0} ({1} is gone or now writes another file)'.format(fileName, script))
        except Exception as e:
            records[script] = previous[script]
            errors.append('UserObject {0} of {1} is stale but could not be removed: {2}'.format(fileName, script, e))
    try:
        saveUserObjectState(statePath, {'format': USEROBJECT_FORMAT, 'userObjects': records})
    except Exception as e:
        errors.append('Could not write {0}: {1}'.format(statePath, e))
    if written or removed:
        refreshRibbon(newUserObjects, log)
    summary = 'UserObjects: {0} written, {1} unchanged'.format(written, len(plan['unchanged']))
    if removed:
        summary += ', {0} removed'.format(removed)
    return summary


def runUpdater(source, runUpdate, makeUserObjects=None):
    """Plan the update of every matching script component and schedule the document changes, and write the UserObjects
    (unless makeUserObjects is False); (log, updated, skipped, errors). The run right after the scheduled changes shows
    the final report instead. An outdated updater is marked on the canvas on every run."""
    try:
        return updateDocument(source, runUpdate, makeUserObjects)
    finally:
        showSelfState(ghenv.Component)  # noqa: F821


def updateDocument(source, runUpdate, makeUserObjects):
    updater = ghenv.Component  # noqa: F821 (global of every Grasshopper script component)
    reportKey = REPORT_KEY + str(updater.InstanceGuid)
    finished = sc.sticky.pop(reportKey, None)
    if finished is not None:
        return finished
    log, updated, skipped, errors = [], [], [], []
    if not runUpdate:
        log.append('Set runUpdate to True to execute the updater.')
        return log, updated, skipped, errors
    log.append('=== TRNLizard Updater Started ===')
    sourceFolder = resolveSource(source, log, errors)
    if sourceFolder is None:
        return log, updated, skipped, errors
    log.append('Source folder: {0}'.format(sourceFolder))
    doc = updater.OnPingDocument()
    if not doc:
        errors.append('Could not access the current Grasshopper document.')
        return log, updated, skipped, errors
    scripts = findScripts(sourceFolder, log)
    if not scripts:
        log.append('No Python files found in source folder.')
        return log, updated, skipped, errors
    log.append('Found {0} Python files in source.'.format(len(scripts)))
    selfState = checkSelf(updater, scripts, log, errors)
    if selfState is not None:
        sc.sticky[OUTDATED_KEY + str(updater.InstanceGuid)] = selfState
    components = collectScriptComponents(doc, updater.InstanceGuid, log)
    log.append('Found {0} Python script components in document.'.format(len(components)))
    actions = []
    for comp, cluster in components:
        name = str(comp.Name)
        if name not in scripts:
            continue
        try:
            status, result = planComponent(comp, cluster, scripts[name], log)
        except Exception as e:
            status, result = 'error', 'Error processing {0}: {1}'.format(name, e)
        if status == 'action':
            actions.append(result)
            updated.append(name)
        elif status == 'skipped':
            log.append(result)
            skipped.append(name)
        else:
            log.append(result)
            errors.append(result)
    presets = loadPresets(sourceFolder, log)
    if presets:
        try:
            actions.extend(planSharedSync(doc, presets['shared'], scripts, log, updated, skipped))
        except Exception as e:
            errors.append('Shared clusters not checked: {0}'.format(e))
    userObjectsSummary = None
    if makeUserObjects is not False:
        try:
            userObjectsSummary = writeUserObjects(scripts, updater, log, errors, loadIcons(sourceFolder, log), presets)
        except Exception as e:  # never stops the canvas update
            errors.append('UserObjects not written: {0}'.format(e))
            userObjectsSummary = 'UserObjects: failed'
    if actions:
        report = (log, updated, skipped, errors)

        def callback(document):
            applyActions(document, actions, report, reportKey, updater, userObjectsSummary)
        doc.ScheduleSolution(1, Grasshopper.Kernel.GH_Document.GH_ScheduleDelegate(callback))
        log.append('')
        log.append('{0} component(s) are changed right after this solution; this report is then completed.'.format(len(actions)))
    else:
        log.append('')
        log.append('=== Update Summary ===')
        log.append('Updated: 0')
        log.append('Skipped: {0}'.format(len(skipped)))
        if userObjectsSummary:
            log.append(userObjectsSummary)
        log.append('Errors:  {0}'.format(len(errors)))
    return log, updated, skipped, errors


if 'ghenv' in globals():
    log, updated, skipped, errors = runUpdater(globals().get('source'), globals().get('runUpdate'),
                                               globals().get('makeUserObjects'))
