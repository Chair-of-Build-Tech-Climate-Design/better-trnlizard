"""
Probe: does an edit of a cluster's inner document (cluster.Document('')) survive saving the cluster as a UserObject?
-
One-off helper for the preset packaging of Lizard_Updater. Put it into a Python script component, add the inputs,
set run to True once. Nothing in the Grasshopper document is changed; it writes outFolder/probe_<preset>.ghuser and
outFolder/probe_log.txt.
Steps: load the preset, take its cluster, change the code of the first script component inside (a marker comment),
add a panel wired into that component's first input, then (1) copy the cluster through GH_Archive and (2) save it as a
UserObject and load that again, and check whether the marker, the panel and the wire are still there and the outer
params are unchanged. It also lists the GH_Cluster members whose names hint at document handling.
-
TRNLizard

Args:
    presetFile (str): a preset UserObject, e.g. ...\\TRNLizard_Grid.ghuser
        Access: item
        Required: True
    outFolder (str): folder for the probe files
        Access: item
        Required: True
    run (bool): True = probe
        Access: item
        Required: True

Returns:
    log (str): probe report
        Access: item
"""
import io
import os
import traceback

import Grasshopper

MARKER = u'# LIZARD_PROBE_MARKER'


def _impl(obj):
    return getattr(obj, '__implementation__', obj)


def scriptCode(comp):
    if hasattr(comp, 'Code'):
        return comp.Code, 'Code'
    if hasattr(comp, 'TryGetSource'):
        for args in ((), (None,), ('',)):
            try:
                result = comp.TryGetSource(*args)
            except TypeError:
                continue
            if isinstance(result, tuple) and len(result) == 2:
                return (result[1] if result[0] else None), 'SetSource'
    return None, None


def isScript(obj):
    return isinstance(obj, Grasshopper.Kernel.GH_Component) and scriptCode(obj)[1] is not None


def firstScript(doc):
    for obj in doc.Objects:
        obj = _impl(obj)
        if isScript(obj):
            return obj
    return None


def archiveCopy(cluster):
    try:
        import clr
        clr.AddReference('GH_IO')
    except Exception:
        pass
    from GH_IO.Serialization import GH_Archive
    archive = GH_Archive()
    archive.AppendObject(cluster, 'Object')
    reader = GH_Archive()
    reader.Deserialize_Xml(archive.Serialize_Xml())
    copy = _impl(Grasshopper.Instances.ComponentServer.EmitObject(cluster.ComponentGuid))
    copy.CreateAttributes()
    if not reader.ExtractObject(copy, 'Object'):
        raise RuntimeError('ExtractObject failed')
    return copy


def check(cluster, scriptId, panelId, log, label):
    doc = cluster.Document('')
    if doc is None:
        log.append(u'{0}: Document("") is None'.format(label))
        return
    script = doc.FindObject(scriptId, True) if scriptId is not None else None
    script = _impl(script) if script is not None else None
    code = scriptCode(script)[0] if script is not None else None
    panel = doc.FindObject(panelId, True) if panelId is not None else None
    wired = False
    if script is not None and panel is not None and list(script.Params.Input):
        wired = any(str(s.InstanceGuid) == str(panelId) for s in script.Params.Input[0].Sources)
    log.append(u'{0}: script found={1}, marker kept={2}, panel kept={3}, wire kept={4}, objects={5}, outer in={6}, '
               u'out={7}'.format(label, script is not None, bool(code and MARKER in code), panel is not None, wired,
                                 len(list(doc.Objects)), [str(p.Name) for p in cluster.Params.Input],
                                 [str(p.Name) for p in cluster.Params.Output]))


def probe(presetFile, outFolder):
    log = []
    uo = Grasshopper.Kernel.GH_UserObject(presetFile)
    cluster = _impl(uo.InstantiateObject())
    log.append(u'Preset: {0} ({1})'.format(presetFile, type(cluster).__name__))
    names = sorted(set(n for n in dir(cluster) if any(k in n for k in ('Doc', 'Intern', 'Synch', 'Cluster', 'File',
                                                                          'Password', 'Expire', 'Update', 'Set'))))
    log.append(u'GH_Cluster members: ' + u', '.join(names))
    doc = cluster.Document('')
    if doc is None:
        log.append(u'Document("") is None: cluster locked or empty')
        return log
    sameDoc = cluster.Document('') is doc or cluster.Document('').Equals(doc)
    log.append(u'Document("") returns the same instance twice: {0}'.format(sameDoc))
    log.append(u'Outer params before: in={0}, out={1}'.format([str(p.Name) for p in cluster.Params.Input],
                                                               [str(p.Name) for p in cluster.Params.Output]))
    script = firstScript(doc)
    if script is None:
        log.append(u'No script component inside: choose another preset')
        return log
    code, how = scriptCode(script)
    newCode = (code or u'') + u'\n' + MARKER + u'\n'
    if how == 'Code':
        script.Code = newCode
    else:
        script.SetSource(newCode)
    panel = Grasshopper.Kernel.Special.GH_Panel()
    panel.CreateAttributes()
    panel.UserText = u'probe'
    doc.AddObject(panel, False)
    if list(script.Params.Input):
        script.Params.Input[0].AddSource(panel)
    log.append(u'Edited {0} ({1}): marker added, panel added and wired'.format(script.Name, script.InstanceGuid))
    scriptId, panelId = script.InstanceGuid, panel.InstanceGuid
    check(cluster, scriptId, panelId, log, u'Same cluster')
    try:
        check(archiveCopy(cluster), scriptId, panelId, log, u'GH_Archive copy')
    except Exception as e:
        log.append(u'GH_Archive copy failed: {0}'.format(e))
    try:
        if not os.path.isdir(outFolder):
            os.makedirs(outFolder)
        path = os.path.join(outFolder, u'probe_' + os.path.basename(presetFile))
        saved = Grasshopper.Kernel.GH_UserObject()
        saved.SetDataFromObject(cluster)
        saved.Description.Name = u'Lizard_Probe'
        saved.Description.Category = u'TRNLizardProbe'
        saved.Description.SubCategory = u'Probe'
        saved.Path = path
        log.append(u'SaveToFile: {0} -> {1}'.format(saved.SaveToFile(), path))
        loaded = _impl(Grasshopper.Kernel.GH_UserObject(path).InstantiateObject())
        check(loaded, scriptId, panelId, log, u'Saved and loaded UserObject')
        log.append(u'(the probe file is in the probe folder only, not in the UserObjects folder; delete it after)')
    except Exception as e:
        log.append(u'UserObject save/load failed: {0}'.format(e))
    return log


def main(presetFile, outFolder, run):
    if not run:
        return u'Set run to True to probe.'
    try:
        lines = probe(presetFile, outFolder)
    except Exception as e:
        lines = [u'Probe stopped: {0}'.format(e), u'{0}'.format(traceback.format_exc())]
    text = u'\n'.join(lines)
    try:
        handle = io.open(os.path.join(outFolder, 'probe_log.txt'), 'w', encoding='utf-8')
        try:
            handle.write(text + u'\n')
        finally:
            handle.close()
    except Exception:
        pass
    return text


if 'ghenv' in globals():
    log = main(globals().get('presetFile'), globals().get('outFolder'), globals().get('run'))
