"""
Build the TRNLizard installer definition: one Lizard_Updater (legacy GhPython, runs in Rhino 7 and 8), a toggle per
switch (makeUserObjects = True, cleanOldUserObjects = True, runUpdate = False), a panel on its log and a panel with
the instructions; saved as a .ghx that tools/build_installer.py fills with the Lizard_Updater.py of each release.
-
One-off helper: put it into a Python script component (Rhino 7 GhPython or Rhino 8), add the inputs, set run to True
once. The current Grasshopper document is not changed; the installer is built in a new document and saved.
-
TRNLizard

Args:
    updaterFile (str): Lizard_Updater.py of the repository
        Access: item
        Required: True
    outFile (str): the installer template to write, e.g. ...\\installer\\TRNLizard_Installer.ghx
        Access: item
        Required: True
    run (bool): True = build and save
        Access: item
        Required: True

Returns:
    log (str): report
        Access: item
"""
import io
import os
import traceback

import System
import Grasshopper

LEGACY_GHPYTHON_ID = '410755b1-224a-4c1e-a407-bf32fb45ea7e'
INSTRUCTIONS = (u'TRNLizard installer\n'
                u'1. Optional: connect a GitHub URL or a folder to "source" (empty = TRNLizard on GitHub).\n'
                u'2. Set runUpdate to True (double-click the toggle).\n'
                u'3. Wait for the log; then restart Grasshopper: the TRNLizard tab holds all components and presets.\n'
                u'makeUserObjects = True writes them into UserObjects\\TRNLizard; cleanOldUserObjects = True moves the '
                u'UserObjects of earlier TRNLizard installs out of the UserObjects folder.')


def loadUpdater(path):
    """The functions of Lizard_Updater.py (its own builder makes the component, the same as its UserObject)."""
    handle = io.open(path, 'r', encoding='utf-8-sig')
    try:
        code = handle.read()
    finally:
        handle.close()
    namespace = {'__name__': 'Lizard_Updater_installer'}
    exec(compile(code, path, 'exec'), namespace)  # no ghenv in namespace: only definitions run
    return code, namespace


def point(x, y):
    try:
        import clr
        clr.AddReference('System.Drawing')
    except Exception:
        pass
    import System.Drawing
    return System.Drawing.PointF(x, y)


def place(obj, x, y):
    if obj.Attributes is None:
        obj.CreateAttributes()
    obj.Attributes.Pivot = point(x, y)
    obj.Attributes.ExpireLayout()


def toggle(name, value):
    item = Grasshopper.Kernel.Special.GH_BooleanToggle()
    item.CreateAttributes()
    item.NickName = name
    item.Value = value
    return item


def panel(name, text):
    item = Grasshopper.Kernel.Special.GH_Panel()
    item.CreateAttributes()
    item.NickName = name
    item.UserText = text
    return item


def build(updaterFile, outFile):
    log = []
    code, updater = loadUpdater(updaterFile)
    info = updater['parseComponentInfo'](code, 'Lizard_Updater')
    notes = []
    comp = updater['buildUserObjectComponent'](System.Guid(LEGACY_GHPYTHON_ID), {'code': code, 'info': info}, notes)
    inputs = [str(p.Name) for p in comp.Params.Input]
    outputs = [str(p.Name) for p in comp.Params.Output]
    log.append(u'Updater component: inputs {0}, outputs {1}{2}'.format(inputs, outputs, u'; ' + u'; '.join(notes) if notes else u''))
    doc = Grasshopper.Kernel.GH_Document()
    place(comp, 420, 160)
    doc.AddObject(comp, False)
    switches = (('runUpdate', False), ('makeUserObjects', True), ('cleanOldUserObjects', True))
    for row, (name, value) in enumerate(switches):
        if name not in inputs:
            raise RuntimeError(u'the updater has no input {0}'.format(name))
        item = toggle(name, value)
        place(item, 150, 120 + 40 * row)
        doc.AddObject(item, False)
        comp.Params.Input[inputs.index(name)].AddSource(item)
    report = panel('log', u'')
    place(report, 640, 120)
    doc.AddObject(report, False)
    report.AddSource(comp.Params.Output[outputs.index('log')])
    note = panel('Instructions', INSTRUCTIONS)
    place(note, 150, 0)
    doc.AddObject(note, False)
    folder = os.path.dirname(outFile)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    saved = Grasshopper.Kernel.GH_DocumentIO(doc).SaveQuiet(outFile)
    log.append(u'Saved: {0} -> {1}'.format(saved, outFile))
    log.append(u'Open it in Rhino 7 and 8 to check, then commit it as the installer template.')
    return log


def main(updaterFile, outFile, run):
    if not run:
        return u'Set run to True to build the installer.'
    try:
        return u'\n'.join(build(updaterFile, outFile))
    except Exception as e:
        return u'Installer not built: {0}\n{1}'.format(e, traceback.format_exc())


if 'ghenv' in globals():
    log = main(globals().get('updaterFile'), globals().get('outFile'), globals().get('run'))
