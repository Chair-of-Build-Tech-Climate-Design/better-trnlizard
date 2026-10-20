"""
Update the TRNLizard script components of this Grasshopper document from the .py files of a folder.
-
A script component is matched by its Name (every TRNLizard script sets it, e.g. Lizard_Hygro) to <Name>.py in
sourceFolder. Its code is replaced when it differs from the file (line endings, a BOM and trailing white space are
ignored). Its inputs and outputs follow the Args/Returns docstring of the new script:
- only additions: the new params are added to the component in place, at their docstring position;
- any removal (a rename is a removal plus an addition): a copy of the component with the new code and IO is placed
next to the old one, wired by param name and put into a red group; the old component is locked and keeps its
params and wires for reference;
- order-only differences: the params are kept, a note is logged;
- inside clusters only additions are applied, anything else is reported as manual update needed.
All document changes are made right after this solution, then the report of the finished update is shown.
The updater never updates itself: when its own code differs from Lizard_Updater.py in sourceFolder, a warning is
logged and listed under errors; paste the new code into this component by hand.
Plain script for Rhino 7/8 GhPython (IronPython 2.7) and Rhino 8 Python 2/3 script components; it updates
components of these three kinds (Rhino 8 script components need Rhino 8 SR18 or later).
-
TRNLizard

Args:
    sourceFolder (str): folder with the TRNLizard scripts <component Name>.py
        Access: item
        Required: True
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
UPDATER_SCRIPT = 'Lizard_Updater'                         # base name of this script in sourceFolder

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


def runUpdater(sourceFolder, runUpdate):
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
    if not sourceFolder or not os.path.isdir(sourceFolder):
        errors.append('Invalid source folder path.')
        return log, updated, skipped, errors
    log.append('=== TRNLizard Updater Started ===')
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
    log, updated, skipped, errors = runUpdater(globals().get('sourceFolder'), globals().get('runUpdate'))
