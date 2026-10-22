"""
Export the fixed TRNLizard UserObjects (cluster presets such as TRNLizard_Template_Lite.ghuser) into a structured,
diffable form, so that Lizard_Updater can rebuild them from the latest scripts.
-
One-off helper: put it into a Python script component (GhPython, Rhino 8 Python 2 or Python 3), add the inputs below,
set run to True once. Nothing in the Grasshopper document is changed; only files under outFolder are written.
For every *.ghuser of presetFolder it writes outFolder/<UserObject file name>/:
- preset.json: UserObject description (name, nickName, description, category, subCategory, exposure) and the tree of
  the object: for a cluster its inner document with every object (type, position, params with names, access, type
  hints, wires by object id + param name), script components only by their Name and code hash, nested clusters
  recursively, other objects with the file of their GH_Archive XML;
- icon.png, object.xml (the whole UserObject object as GH_Archive XML), document.ghx (the cluster's inner document),
  native/<id>.xml (each non-script object), clusters/<id>/... (nested clusters, same layout);
and outFolder/scripts/<Name>__<hash>.py + .json: the code of every script component found, one file per distinct code,
with its params and where it was found. outFolder/index.json lists the presets, the script variants, the scripts that
the repository (repoFolder) does not have yet, and the result of the round-trip probe (GH_Cluster.CreateFromFilePath of
document.ghx) that tells whether a cluster can be rebuilt from a document.
-
TRNLizard

Args:
    presetFolder (str): folder with the preset UserObjects (*.ghuser)
        Access: item
        Required: True
    outFolder (str): folder for the export (created; existing files with the same names are overwritten)
        Access: item
        Required: True
    repoFolder (str): TRNLizard repository folder with Lizard_*.py (to list the scripts it does not have); optional
        Access: item
        Required: False
    run (bool): True = export
        Access: item
        Required: True

Returns:
    log (str): report of the export
        Access: item
"""
import hashlib
import io
import json
import os
import re

import System
import Grasshopper

EXPORT_FORMAT = 1


# ---------------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------------

def _impl(obj):
    return getattr(obj, '__implementation__', obj)


def _str(value):
    try:
        return u'' + value if isinstance(value, type(u'')) else u'{0}'.format(value)
    except Exception:
        return None


def _typeName(obj):
    try:
        return str(obj.GetType().FullName)
    except Exception:
        return type(obj).__name__


def writeText(path, text):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    handle = io.open(path, 'w', encoding='utf-8', newline='\n')
    try:
        handle.write(text if isinstance(text, type(u'')) else text.decode('utf-8'))
    finally:
        handle.close()


def writeJson(path, data):
    text = json.dumps(data, indent=1, sort_keys=True, ensure_ascii=True)
    writeText(path, u'' + text + u'\n')


def normalizeCode(content):
    content = content or u''
    return content.replace(u'\r\n', u'\n').replace(u'\r', u'\n').lstrip(u'\ufeff').rstrip()


def codeHash(content):
    return hashlib.sha256(normalizeCode(content).encode('utf-8')).hexdigest()


def safeName(name):
    name = re.sub(r'[^A-Za-z0-9_.-]+', '_', name or 'unnamed').strip('._')
    return name or 'unnamed'


def archiveXml(obj, chunkName):
    """GH_Archive XML of an object (component, param, cluster, document); None when it cannot be stored."""
    try:
        import clr
        clr.AddReference('GH_IO')
    except Exception:
        pass
    from GH_IO.Serialization import GH_Archive
    archive = GH_Archive()
    if not archive.AppendObject(obj, chunkName):
        return None
    return archive.Serialize_Xml()


def saveIcon(bitmap, path):
    if bitmap is None:
        return False
    try:
        import clr
        clr.AddReference('System.Drawing')
    except Exception:
        pass
    import System.Drawing
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    bitmap.Save(path, System.Drawing.Imaging.ImageFormat.Png)
    return True


# ---------------------------------------------------------------------------------------------------------------------
# script components
# ---------------------------------------------------------------------------------------------------------------------

def scriptKind(obj):
    if not isinstance(obj, Grasshopper.Kernel.GH_Component):
        return None
    name = _typeName(obj)
    if 'Python3' in name:
        return 'python3'
    if 'IronPython2' in name:
        return 'ironpython2'
    if hasattr(obj, 'Code'):
        return 'ghpython'
    return None


def readCode(comp, kind):
    if kind == 'ghpython':
        return comp.Code
    if not hasattr(comp, 'TryGetSource'):
        return None
    for args in ((), (None,), ('',)):
        try:
            result = comp.TryGetSource(*args)
        except TypeError:
            continue
        if isinstance(result, tuple) and len(result) == 2:
            return result[1] if result[0] else None
        return None
    return None


def typeHintOf(param):
    hint = getattr(param, 'TypeHint', None)  # legacy GhPython Param_ScriptVariable
    if hint is not None:
        return _str(getattr(hint, 'TypeName', hint))
    hints = getattr(param, 'TypeHints', None)  # Rhino 8 script param
    if hints is not None:
        for attr in ('Selected', 'Current', 'SelectedHint'):
            value = getattr(hints, attr, None)
            if value is not None:
                return _str(value)
        return _str(hints)
    return None


# ---------------------------------------------------------------------------------------------------------------------
# documents
# ---------------------------------------------------------------------------------------------------------------------

def paramInfo(param):
    param = _impl(param)
    info = {'id': _str(param.InstanceGuid), 'name': _str(param.Name), 'nickName': _str(param.NickName),
            'description': _str(param.Description), 'typeId': _str(param.ComponentGuid), 'type': _typeName(param)}
    try:
        info['access'] = _str(param.Access).lower()
        info['optional'] = bool(param.Optional)
    except Exception:
        pass
    hint = typeHintOf(param)
    if hint is not None:
        info['typeHint'] = hint
    for attr in ('Reverse', 'Simplify'):
        try:
            if bool(getattr(param, attr)):
                info[attr.lower()] = True
        except Exception:
            pass
    try:
        mapping = _str(param.DataMapping)
        if mapping and mapping != 'None':
            info['dataMapping'] = mapping
    except Exception:
        pass
    try:
        info['persistentData'] = int(param.PersistentDataCount) if hasattr(param, 'PersistentDataCount') else None
    except Exception:
        pass
    return info


def ownerOf(param):
    """(top-level object id, param name, index on its side, side) of a param; side 'self' for a standalone param."""
    param = _impl(param)
    attributes = param.Attributes
    top = attributes.GetTopLevel.DocObject if attributes is not None else None
    if top is None or str(top.InstanceGuid) == str(param.InstanceGuid):
        return _str(param.InstanceGuid), _str(param.Name), -1, 'self'
    top = _impl(top)
    params = getattr(top, 'Params', None)
    if params is not None:
        for side, items in (('input', list(params.Input)), ('output', list(params.Output))):
            for index, item in enumerate(items):
                if str(item.InstanceGuid) == str(param.InstanceGuid):
                    return _str(top.InstanceGuid), _str(param.Name), index, side
    return _str(top.InstanceGuid), _str(param.Name), -1, 'unknown'


def exportDocument(doc, folder, ctx, where):
    """Structured description of a document; writes native/<id>.xml and clusters/<id>/ under folder."""
    objects = []
    wires = []
    for obj in doc.Objects:
        obj = _impl(obj)
        try:
            objects.append(exportObject(obj, folder, ctx, where))
        except Exception as e:
            ctx['log'].append(u'Error exporting {0} in {1}: {2}'.format(_str(obj.NickName), where, e))
            objects.append({'id': _str(obj.InstanceGuid), 'error': _str(e)})
        for param in recipientParams(obj):
            for source in list(param.Sources):
                try:
                    fromObj, fromName, fromIndex, fromSide = ownerOf(source)
                    toObj, toName, toIndex, toSide = ownerOf(param)
                    wires.append({'from': {'object': fromObj, 'param': fromName, 'index': fromIndex, 'side': fromSide,
                                           'paramId': _str(source.InstanceGuid)},
                                  'to': {'object': toObj, 'param': toName, 'index': toIndex, 'side': toSide,
                                         'paramId': _str(param.InstanceGuid)}})
                except Exception as e:
                    ctx['log'].append(u'Error reading a wire in {0}: {1}'.format(where, e))
    return {'objects': objects, 'wires': wires}


def recipientParams(obj):
    """Params of an object that can have sources: the inputs of a component, a standalone param itself."""
    if isinstance(obj, Grasshopper.Kernel.IGH_Param):
        return [obj]
    params = getattr(obj, 'Params', None)
    if params is None:
        return []
    return [_impl(p) for p in params.Input]


def exportObject(obj, folder, ctx, where):
    attributes = obj.Attributes
    info = {'id': _str(obj.InstanceGuid), 'typeId': _str(obj.ComponentGuid), 'type': _typeName(obj),
            'name': _str(obj.Name), 'nickName': _str(obj.NickName)}
    if attributes is not None:
        info['pivot'] = [float(attributes.Pivot.X), float(attributes.Pivot.Y)]
    for attr in ('Locked', 'Hidden'):
        try:
            info[attr.lower()] = bool(getattr(obj, attr))
        except Exception:
            pass
    params = getattr(obj, 'Params', None)
    if params is not None:
        info['inputs'] = [paramInfo(p) for p in params.Input]
        info['outputs'] = [paramInfo(p) for p in params.Output]
    kind = scriptKind(obj)
    if kind is not None:
        info['kind'] = 'script'
        info['scriptKind'] = kind
        info['sdkMode'] = bool(getattr(obj, 'IsSDKMode', False))
        code = readCode(obj, kind)
        if code is None:
            info['codeError'] = 'code not readable'
        else:
            info['codeHash'] = codeHash(code)
            registerScript(ctx, obj, kind, code, info, where)
        xml = archiveXml(obj, 'Object')  # kept for exact restore (type hints, flags) if needed
        if xml is not None:
            info['xml'] = 'native/{0}.xml'.format(info['id'])
            writeText(os.path.join(folder, info['xml']), xml)
        return info
    if isinstance(obj, Grasshopper.Kernel.Special.GH_Cluster):
        info['kind'] = 'cluster'
        sub = os.path.join(folder, 'clusters', safeName(info['id']))
        info['folder'] = 'clusters/{0}'.format(safeName(info['id']))
        info['cluster'] = exportCluster(obj, sub, ctx, u'{0} > {1}'.format(where, info['nickName']))
        return info
    info['kind'] = 'native'
    if isinstance(obj, Grasshopper.Kernel.Special.GH_Group):
        info['members'] = [_str(g) for g in obj.ObjectIDs]
    xml = archiveXml(obj, 'Object')
    if xml is None:
        info['xmlError'] = 'GH_Archive could not store it'
    else:
        info['xml'] = 'native/{0}.xml'.format(info['id'])
        writeText(os.path.join(folder, info['xml']), xml)
    return info


def exportCluster(cluster, folder, ctx, where):
    """Writes object.xml, document.ghx and the structure of a cluster; returns the structure."""
    result = {'outerInputs': [paramInfo(p) for p in cluster.Params.Input],
              'outerOutputs': [paramInfo(p) for p in cluster.Params.Output]}
    xml = archiveXml(cluster, 'Object')
    if xml is not None:
        writeText(os.path.join(folder, 'object.xml'), xml)
    doc = cluster.Document('')
    if doc is None:
        result['error'] = 'cluster is password protected or empty'
        ctx['log'].append(u'Cluster {0} is locked or empty: not exported.'.format(where))
        return result
    docXml = archiveXml(doc, 'Definition')
    if docXml is not None:
        writeText(os.path.join(folder, 'document.ghx'), docXml)
        result['document'] = 'document.ghx'
        probeClusterFromFile(cluster, os.path.join(folder, 'document.ghx'), ctx, where)
    result['content'] = exportDocument(doc, folder, ctx, where)
    return result


def probeClusterFromFile(original, path, ctx, where):
    """Can a cluster be rebuilt from a .ghx of its inner document (what the packaging will do)?"""
    probe = {'where': where}
    try:
        rebuilt = Grasshopper.Kernel.Special.GH_Cluster()
        rebuilt.CreateAttributes()
        result = rebuilt.CreateFromFilePath(path)
        probe['result'] = _str(result)
        probe['inputs'] = [_str(p.Name) for p in rebuilt.Params.Input]
        probe['outputs'] = [_str(p.Name) for p in rebuilt.Params.Output]
        probe['sameParams'] = (probe['inputs'] == [_str(p.Name) for p in original.Params.Input] and
                               probe['outputs'] == [_str(p.Name) for p in original.Params.Output])
        inner = rebuilt.Document('')
        probe['objects'] = len(list(inner.Objects)) if inner is not None else None
        probe['originalObjects'] = len(list(original.Document('').Objects))
        try:
            uo = Grasshopper.Kernel.GH_UserObject()
            uo.SetDataFromObject(rebuilt)
            probe['userObject'] = True
        except Exception as e:
            probe['userObject'] = _str(e)
    except Exception as e:
        probe['error'] = _str(e)
    ctx['probes'].append(probe)


def registerScript(ctx, comp, kind, code, info, where):
    name = _str(comp.Name)
    digest = info['codeHash']
    key = (name, digest)
    entry = ctx['scripts'].get(key)
    if entry is None:
        base = 'scripts/{0}__{1}'.format(safeName(name), digest[:8])
        entry = {'name': name, 'hash': digest, 'kind': kind, 'file': base + '.py', 'foundIn': [],
                 'inputs': info.get('inputs'), 'outputs': info.get('outputs'), 'nickName': _str(comp.NickName),
                 'description': _str(comp.Description), 'category': _str(comp.Category),
                 'subCategory': _str(comp.SubCategory), 'message': _str(getattr(comp, 'Message', None))}
        writeText(os.path.join(ctx['out'], entry['file']), code)
        try:
            entry['iconSaved'] = saveIcon(comp.Icon_24x24, os.path.join(ctx['out'], base + '.png'))
        except Exception:
            entry['iconSaved'] = False
        ctx['scripts'][key] = entry
    entry['foundIn'].append({'preset': ctx['preset'], 'where': where, 'id': info['id']})


# ---------------------------------------------------------------------------------------------------------------------
# presets
# ---------------------------------------------------------------------------------------------------------------------

def exportPreset(path, ctx):
    fileName = os.path.basename(path)
    base = os.path.splitext(fileName)[0]
    ctx['preset'] = base
    folder = os.path.join(ctx['out'], safeName(base))
    uo = Grasshopper.Kernel.GH_UserObject(path)
    try:
        uo.ReadFromFile()
    except Exception:
        pass
    description = uo.Description
    preset = {'format': EXPORT_FORMAT, 'file': fileName,
              'name': _str(description.Name), 'nickName': _str(description.NickName),
              'description': _str(description.Description), 'category': _str(description.Category),
              'subCategory': _str(description.SubCategory), 'exposure': _str(uo.Exposure),
              'baseId': _str(uo.BaseGuid)}
    preset['icon'] = 'icon.png' if saveIcon(uo.Icon, os.path.join(folder, 'icon.png')) else None
    obj = _impl(uo.InstantiateObject())
    if obj is None:
        raise RuntimeError('InstantiateObject returned nothing')
    if isinstance(obj, Grasshopper.Kernel.Special.GH_Cluster):
        preset['kind'] = 'cluster'
        preset['cluster'] = exportCluster(obj, folder, ctx, base)
    else:
        preset['kind'] = 'object'
        preset['object'] = exportObject(obj, folder, ctx, base)
        xml = archiveXml(obj, 'Object')
        if xml is not None:
            writeText(os.path.join(folder, 'object.xml'), xml)
    writeJson(os.path.join(folder, 'preset.json'), preset)
    return preset


def repoScripts(repoFolder):
    if not repoFolder or not os.path.isdir(repoFolder):
        return None
    return dict((os.path.splitext(n)[0].lower(), os.path.splitext(n)[0]) for n in os.listdir(repoFolder)
                if n.endswith('.py') and not n.startswith('_'))


def runExport(presetFolder, outFolder, repoFolder, run):
    log = []
    if not run:
        return ['Set run to True to export.']
    if not presetFolder or not os.path.isdir(presetFolder):
        return ['Invalid presetFolder: {0}'.format(presetFolder)]
    if not outFolder:
        return ['No outFolder.']
    if not os.path.isdir(outFolder):
        os.makedirs(outFolder)
    ctx = {'out': outFolder, 'log': log, 'scripts': {}, 'probes': [], 'preset': None}
    presets = []
    for fileName in sorted(os.listdir(presetFolder)):
        if not fileName.lower().endswith('.ghuser'):
            continue
        try:
            preset = exportPreset(os.path.join(presetFolder, fileName), ctx)
            presets.append({'file': fileName, 'name': preset['name'], 'kind': preset['kind'],
                            'folder': safeName(os.path.splitext(fileName)[0])})
            log.append(u'Exported {0} ({1})'.format(fileName, preset['kind']))
        except Exception as e:
            log.append(u'Error exporting {0}: {1}'.format(fileName, e))
            presets.append({'file': fileName, 'error': _str(e)})
    known = repoScripts(repoFolder)
    byName = {}
    for entry in ctx['scripts'].values():
        byName.setdefault(entry['name'], []).append(entry)
    scripts = []
    for name in sorted(byName):
        variants = byName[name]
        inRepo = None if known is None else known.get((name or '').lower())
        scripts.append({'name': name, 'repoScript': inRepo, 'variants': [
            {'hash': v['hash'], 'file': v['file'], 'kind': v['kind'], 'foundIn': v['foundIn']} for v in variants]})
        writeJson(os.path.join(outFolder, 'scripts', '{0}.json'.format(safeName(name))), variants)
    missing = [s['name'] for s in scripts if known is not None and s['repoScript'] is None]
    writeJson(os.path.join(outFolder, 'index.json'), {
        'format': EXPORT_FORMAT, 'presets': presets, 'scripts': scripts, 'notInRepo': missing,
        'probes': ctx['probes'], 'grasshopper': _str(Grasshopper.Versioning.Version) if hasattr(Grasshopper, 'Versioning') else None})
    log.append(u'')
    log.append(u'{0} presets, {1} script components ({2} distinct codes, {3} names)'.format(
        len(presets), sum(len(v['foundIn']) for v in ctx['scripts'].values()), len(ctx['scripts']), len(byName)))
    if known is not None:
        log.append(u'Not in the repository: {0}'.format(', '.join(missing) or '-'))
    multi = [name for name in sorted(byName) if len(byName[name]) > 1]
    log.append(u'Names with more than one code: {0}'.format(', '.join(multi) or '-'))
    good = [p for p in ctx['probes'] if p.get('sameParams') and p.get('objects') == p.get('originalObjects')]
    log.append(u'Round-trip probe (cluster from document.ghx): {0} of {1} identical'.format(len(good), len(ctx['probes'])))
    for probe in ctx['probes']:
        if probe not in good:
            log.append(u'  probe differs: {0}'.format(json.dumps(probe, sort_keys=True)))
    log.append(u'Written to {0}'.format(outFolder))
    return log


if 'ghenv' in globals():
    log = u'\n'.join(runExport(globals().get('presetFolder'), globals().get('outFolder'), globals().get('repoFolder'),
                               globals().get('run')))
