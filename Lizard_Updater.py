"""
Update the TRNLizard script components of this Grasshopper document from the TRNLizard scripts on GitHub or in a folder.
-
source tells where the scripts come from:
- not connected or empty: the main branch of https://github.com/Chair-of-Build-Tech-Climate-Design/better-trnlizard;
- a GitHub repository (https://github.com/<owner>/<repo>, github.com/<owner>/<repo> or git@github.com:<owner>/<repo>.git),
optionally with /tree/<branch or tag> or /commit/<sha> (default: main). The updater reads trnlizard_manifest.json of the
repository (SHA256 of every script) and downloads only new and changed scripts into its cache folder (Grasshopper AppData
folder, TRNLizard/source/<owner>_<repo>_<ref>); scripts that left the manifest are deleted from the cache. Without a
connection a complete cached copy is used. The branch is looked up as a commit on api.github.com; when that fails, the
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
UNDO_NAME = 'Lizard_Updater'
UPDATER_SCRIPT = 'Lizard_Updater'                         # base name of this script in the source folder
DEFAULT_SOURCE = 'https://github.com/Chair-of-Build-Tech-Climate-Design/better-trnlizard'
DEFAULT_REF = 'main'                                      # branch when a GitHub URL names none
MANIFEST_NAME = 'trnlizard_manifest.json'                 # at the repository root, made by tools/build_manifest.py
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
    return (u'This Lizard_Updater runs other code than {0} (first diff {1}). The updater never updates itself: if the '
            u'file is the newer one, paste it into this component by hand.').format(path, firstDiff(ownCode, fileCode))


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
    """{'format', 'generated', 'files': {file name: {'sha256', 'size'}}} of a trnlizard_manifest.json text.

    ValueError when the text is no valid manifest: not JSON, a format newer than MANIFEST_FORMAT, no files, a file name
    that is not a top-level script (no paths, no leading '_'), names that only differ in case, or a sha256 that is not
    64 hex digits. sha256 is getHash of the script text; size (bytes of the normalized UTF-8 text) is informative only.
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
    for name in files:
        entry = files[name]
        if not isinstance(name, str) or not re.match(SCRIPT_NAME_PATTERN, name):
            raise ValueError(u"invalid file name '{0}'".format(name))
        if not isinstance(entry, dict):
            raise ValueError(u'entry of {0} is not an object'.format(name))
        sha = entry.get('sha256')
        if not isinstance(sha, str) or not re.match(r'^[0-9a-fA-F]{64}$', sha):
            raise ValueError(u'invalid sha256 of {0}'.format(name))
        size = entry.get('size')
        if size is not None and (not isinstance(size, int) or isinstance(size, bool) or size < 0):
            raise ValueError(u'invalid size of {0}'.format(name))
        result[name] = {'sha256': sha.lower(), 'size': size}
    lowered = [name.lower() for name in result]
    if len(set(lowered)) != len(lowered):
        raise ValueError(u'file names that only differ in case')
    generated = data.get('generated')
    return {'format': version, 'generated': generated if isinstance(generated, str) else None, 'files': result}


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
    """Sorted cached .py file names that the manifest no longer lists (exact case: a file whose name changed case is
    removed and downloaded again under its new name)."""
    return sorted(name for name in cachedNames if name.endswith('.py') and name not in files)


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


def applyActions(doc, actions, report, reportKey, updater):
    """ScheduleSolution callback: make the planned document changes and keep the final report for the next run."""
    log, updated, skipped, errors = report
    try:
        log.append('')
        log.append('=== Applying changes ===')
        for action in actions:
            try:
                if action['what'] == 'replace':
                    notes = applyReplacement(doc, action, log)
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
    """Log and list as an error when the code of this updater differs from Lizard_Updater.py of the folder."""
    path = scripts.get(UPDATER_SCRIPT)
    if path is None:
        return
    updater = _impl(updater)
    try:
        message = selfCheckMessage(readComponentCode(updater, scriptKind(updater)), readScript(path), path)
    except Exception as e:
        log.append('Note: could not compare this updater with {0}: {1}'.format(path, e))
        return
    if message:
        log.append('WARNING: ' + message)
        errors.append(message)


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
    """{file name: getHash of the text, None when unreadable} of the .py files of a cache folder (empty when it is missing)."""
    hashes = {}
    if not os.path.isdir(folder):
        return hashes
    for fileName in os.listdir(folder):
        path = os.path.join(folder, fileName)
        if fileName.endswith('.py') and os.path.isfile(path):
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
    return folder


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


def runUpdater(source, runUpdate):
    """Plan the update of every matching script component and schedule the document changes; (log, updated, skipped,
    errors). The run right after the scheduled changes shows the final report instead."""
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
    checkSelf(updater, scripts, log, errors)
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
    if actions:
        report = (log, updated, skipped, errors)

        def callback(document):
            applyActions(document, actions, report, reportKey, updater)
        doc.ScheduleSolution(1, Grasshopper.Kernel.GH_Document.GH_ScheduleDelegate(callback))
        log.append('')
        log.append('{0} component(s) are changed right after this solution; this report is then completed.'.format(len(actions)))
    else:
        log.append('')
        log.append('=== Update Summary ===')
        log.append('Updated: 0')
        log.append('Skipped: {0}'.format(len(skipped)))
        log.append('Errors:  {0}'.format(len(errors)))
    return log, updated, skipped, errors


if 'ghenv' in globals():
    log, updated, skipped, errors = runUpdater(globals().get('source'), globals().get('runUpdate'))
