"""
Stands in for the component a wire needs: connect it to a TRNLizard component and it becomes what that input or output takes.
-
TRNLizard
Copyright (c) 2026 Junfeng Xiao
All Rights Reserved.
-
Place it on the canvas, then connect its Output to an input of a TRNLizard component, or an output of a TRNLizard component
to its Input. What that input or output takes comes from the Options and Source lines of the docstrings:
- one candidate: the Placeholder is replaced by it, at the same place and with the wire;
- several: a window asks which one, with a search box. Cancel removes the wire and leaves the Placeholder ready for the next try;
- none: the wire is removed and a warning says so.
Only a new wire counts, and it takes over: the other wires of the Placeholder go when it is replaced. Wires it already had when
it was first computed (pasted or loaded) do nothing. Several new wires at once (with the solver locked) get a warning until one is left.
Only TRNLizard components that Lizard_Updater has written notice a Placeholder on their inputs: a wire to any other component
stays and does nothing.
While the window is open, the components after that wire are not computed. Grasshopper reports this as a solution aborted by the user.
Ctrl+Z brings the Placeholder back without its wire.
-
StandardOutput: False

Args:
    Input (object): connect an output of a TRNLizard component
        Access: item
        Required: False

Returns:
    Output (object): connect to an input of a TRNLizard component
        Access: item
"""
ghenv.Component.Name = "Lizard_Placeholder"
ghenv.Component.NickName = "Placeholder"
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "5 | Tools"
import sys
import scriptcontext as sc
import Grasshopper
import Grasshopper.Kernel as gk

UNDO_NAME = 'Lizard_Placeholder'
CHECK_KEY = 'checkPlaceholder'     # sticky: the check that the line after the docstring of every script calls
STATE_KEY = 'Lizard_Placeholder'   # sticky: per instance id the wires it knows, and the (warning, status) for its next solution

# Written by tools/build_manifest.py from the Options, Default and Source lines of the docstrings, do not edit.
OPTIONS = {
    "Lizard_Active_Layer_Surface.TemperatureControl": {"options": ["OPERATIVE=TOP_", "ACTIVE_SURFACE=Tsurf_al_", "AIR=TAIR_"], "type": "str"},
    "Lizard_Active_Layer_Surface.SupplyMode": {"options": ["CHILLER=0", "DRY_COOLER=1", "HYBRID_COOLER=2"], "type": "str"},
    "Lizard_Active_Layer_Surface.Circuit": {"options": ["Circuit1=1", "Circuit2=2"], "type": "object"},
    "Lizard_BSDF_Settings.ShadingGroup": {"options": ["GroupA=A", "GroupB=B"], "type": "object"},
    "Lizard_BSDF_Settings.ShdControl": {"options": ["SIMPLE=BSDFSIMPLE", "COMPLEX=BSDFCOMPLEX"], "type": "object"},
    "Lizard_BSDF_Settings.GapVentMode": {"options": ["STACK VENTILATION=STACK", "PERMANENT VENTILATION=PERMANENT"], "type": "str"},
    "Lizard_Comfort.Mode": {"options": ["PMV", "Elevated Air Speed=SET"], "type": "object"},
    "Lizard_Component.Hemisphere": {"options": ["NORTHERN", "SOUTHERN"], "type": "object"},
    "Lizard_Cooling.ControlledTemperature": {"options": ["OPERATIVE", "AIR"], "type": "object"},
    "Lizard_Coupling.Type": {"options": ["PERMANENT", "INVERSION", "STVENT1", "STVENT2", "MECHANICAL"], "type": "str"},
    "Lizard_Coupling.TempCtrlStackVent": {"options": ["FIRST", "LAST", "MEAN"], "type": "object"},
    "Lizard_Daylight_Control.DaylightIll": {"options": ["Daylight Factor=1", "SensorPts=3"], "type": "object"},
    "Lizard_Daylight_Control.CtrlMode": {"options": ["AlwaysON=1", "ON/OFF=2", "Continuous=3", "Continuous ON/OFF=4"], "type": "object"},
    "Lizard_GenMatrices.CalcMode": {"options": ["SinglePatch=0", "AllPatches=1"], "type": "int"},
    "Lizard_Heating.ControlledTemperature": {"options": ["OPERATIVE", "AIR"], "type": "object"},
    "Lizard_Mechanical_Ventilation.Mode": {"options": ["STANDARD", "AHU"], "type": "object"},
    "Lizard_Mechanical_Ventilation.RefTempSeason": {"options": ["Outside Air Temperature=Tamb", "24h Mean Outside Air Temperature=Tamb_m24"], "type": "object"},
    "Lizard_Mechanical_Ventilation.ActivateWinterReduction": {"options": ["ON=1", "OFF=0"], "type": "object"},
    "Lizard_Plot_Settings.Type": {"options": ["Scatter=SCATTER", "Sequence=SEQUENCE", "Bar=BAR", "Load=LOAD", "Heatmap=HEAT", "Histogram=HIST"], "type": "object"},
    "Lizard_Plot_Settings.Fill": {"options": ["None=none", "ToZeroY=tozeroy"], "type": "object"},
    "Lizard_Plot_Settings.Image": {"options": ["None=none", "PNG=png", "SVG=svg"], "type": "object"},
    "Lizard_Surface_Settings.Category": {"options": ["AUTOMATIC", "EXTERNAL", "ADJACENT", "BOUNDARY", "GROUND"], "type": "object"},
    "Lizard_Surface_Settings.FrontBack": {"options": ["FRONT", "BACK"], "type": "str"},
    "Lizard_System.StartMonth": {"options": ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], "type": "object"},
    "Lizard_System.StopMonth": {"options": ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], "type": "object"},
    "Lizard_Thermal_Airnode.BeamMode": {"options": ["STANDARD", "DETAILED"], "type": "object"},
    "Lizard_Thermal_Airnode.DiffuseMode": {"options": ["STANDARD", "DETAILED"], "type": "object"},
    "Lizard_Thermal_Airnode.LongwaveMode": {"options": ["STANDARD", "DETAILED"], "type": "object"},
    "Lizard_Trnflow_Network.LinkTypes": {"default": "CRACK", "options": ["CRACK", "OPENING"], "type": "str"},
    "Lizard_Window_Settings.ShadingMovable": {"options": ["OUT", "INT", "IOT", "NON"], "type": "str"},
    "Lizard_Window_Settings.ShadingGroup": {"options": ["GroupA=A", "GroupB=B"], "type": "str"},
    "Lizard_Zone_Reg4108.ClimateRegion": {"options": ["A", "B", "C"], "type": "object"},
    "Lizard_Zone_Reg4108.Type": {"options": ["RES", "NONRES"], "type": "object"},
}
SOURCES = {
    "Lizard_Active_Layer_Surface.BRep": ["Lizard_Surface.SurfaceInfo"],
    "Lizard_Complex_Shader.Shader2": ["Lizard_Operable_Shading.Shader"],
    "Lizard_Complex_Shader.Shader3": ["Lizard_Operable_Shading.Shader"],
    "Lizard_Complex_Shader.Shader4": ["Lizard_Operable_Shading.Shader"],
    "Lizard_Complex_Shader.Shader5": ["Lizard_Operable_Shading.Shader"],
    "Lizard_Complex_Shader.Shader6": ["Lizard_Operable_Shading.Shader"],
    "Lizard_Complex_Shader.Shader7": ["Lizard_Operable_Shading.Shader"],
    "Lizard_Complex_Shader.Shader8": ["Lizard_Operable_Shading.Shader"],
    "Lizard_Complex_Shader.Shader9": ["Lizard_Operable_Shading.Shader"],
    "Lizard_Complex_Shader.Control": ["Lizard_Shading_Control.Control"],
    "Lizard_Component.AddSchedules": ["Lizard_Weekly_Schedule.Schedule"],
    "Lizard_Component.AddLayers": ["Lizard_Layer.Layer", "Lizard_Layer_Resistance.Layer", "Lizard_Active_CC_Layer.Layer", "Lizard_Active_Slab_Layer.Layer"],
    "Lizard_Component.AddConstructions": ["Lizard_Construction.Construction"],
    "Lizard_Component.AnnualSchedules": ["Lizard_Annual_Schedule.Annual_Schedule"],
    "Lizard_Component.Variants": ["Lizard_Variant_Definition.Variants"],
    "Lizard_Construction.Layer": ["Lizard_Layer.Layer", "Lizard_Layer_Resistance.Layer", "Lizard_Active_CC_Layer.Layer", "Lizard_Active_Slab_Layer.Layer"],
    "Lizard_Daylight_Control.GridPts": ["Lizard_Grid.Points"],
    "Lizard_Daylight_Control.GridInfo": ["Lizard_Grid.GridInfo"],
    "Lizard_Daylight_Control.SelectedPts": ["Lizard_Grid.CtrDlPos"],
    "Lizard_Daylight_Results.Building": ["Lizard_Output_Files.Building"],
    "Lizard_Deconstruct._Box": ["Lizard_Shoebox.Box_"],
    "Lizard_GenMatrices.Multizone": ["Lizard_Multizone.Multizone"],
    "Lizard_Log_Check.Variant": ["Lizard_System.Variant"],
    "Lizard_Model_Inspect.Multizone": ["Lizard_Multizone.Multizone"],
    "Lizard_Multizone.Airnode": ["Lizard_Thermal_Airnode.Airnode"],
    "Lizard_Multizone.Shading": ["Lizard_Window_Scale.Shading"],
    "Lizard_Multizone.AddDaylightGeometry": ["Lizard_AddDaylightGeometry.AddDaylightGeometry"],
    "Lizard_Multizone.Coupling": ["Lizard_Coupling.coupling"],
    "Lizard_Multizone.ConstructionSet": ["Lizard_Construction_Set.Set"],
    "Lizard_Output_Files.Variants": ["Lizard_System.Variant"],
    "Lizard_Plot_Data.FilePath": ["Lizard_Output_Files.Temperature", "Lizard_Output_Files.Power"],
    "Lizard_Plot_Data.ShortVariantName": ["Lizard_Output_Files.VariantName"],
    "Lizard_Plot_Data.AirnodeName": ["Lizard_Output_Files.FocusAirnode"],
    "Lizard_Plot_Data.YOutput": ["Lizard_Plot_Data_Settings.Output_"],
    "Lizard_Plot_Settings.Data": ["Lizard_Plot_Data.Data_"],
    "Lizard_Plotter.Settings": ["Lizard_Plot_Settings.Settings_"],
    "Lizard_Plotter.OutputFilePath": ["Lizard_Output_Files.PlotPath"],
    "Lizard_Surface.BRep": ["Lizard_Surface_Fraction.BRep1_", "Lizard_Surface_Fraction.BRep2_", "Lizard_Surface_SegSplitting.Brep_"],
    "Lizard_Surface.Settings": ["Lizard_Surface_Settings.Settings"],
    "Lizard_Surface_Information.surfaceinfo": ["Lizard_Surface.SurfaceInfo", "Lizard_Window_Surface.SurfaceInfo", "Lizard_Active_Layer_Surface.SurfaceInfo", "Lizard_Hygro.SurfaceInfo"],
    "Lizard_Surface_Output.SurfaceInfo": ["Lizard_Surface.SurfaceInfo", "Lizard_Window_Surface.SurfaceInfo", "Lizard_Active_Layer_Surface.SurfaceInfo", "Lizard_Hygro.SurfaceInfo"],
    "Lizard_Surface_SegSplitting._BRep": ["Lizard_Surface_Fraction.BRep1_", "Lizard_Surface_Fraction.BRep2_"],
    "Lizard_System.DckTemplate": ["Lizard_DCK_Template.DckTemplate"],
    "Lizard_System.Multizone": ["Lizard_Multizone.Multizone", "Lizard_GenMatrices.Multizone"],
    "Lizard_Thermal_Airnode.SurfaceInfo": ["Lizard_Surface.SurfaceInfo", "Lizard_Window_Surface.SurfaceInfo", "Lizard_Active_Layer_Surface.SurfaceInfo", "Lizard_Hygro.SurfaceInfo"],
    "Lizard_Thermal_Airnode.Regime": ["Lizard_Zone_Regime.Regime", "Lizard_Lite_Zone_Regime.Regime", "Lizard_Zone_Reg4108.Regime"],
    "Lizard_Thermal_Airnode.DaylightCtrl": ["Lizard_Daylight_Control.DaylightCtrl"],
    "Lizard_Thermal_Airnode.OutputInfo": ["Lizard_Airnode_Output.OutputInfo", "Lizard_Comfort_Output.OutputInfo", "Lizard_Surface_Output.OutputInfo"],
    "Lizard_Thermal_Airnode.ComplexShade": ["Lizard_Complex_Shader.ComplexShade"],
    "Lizard_Thermal_Airnode.Sequence": ["Lizard_Component.Sequence"],
    "Lizard_Thermal_Airnode.ConstructionSet": ["Lizard_Construction_Set.Set"],
    "Lizard_Variant_Signal.Variants": ["Lizard_Component.Variants", "Lizard_Variant_Definition.Variants"],
    "Lizard_Weekly_Schedule.Monday": ["Lizard_Daily_Schedule.Daily_Schedule"],
    "Lizard_Weekly_Schedule.Tuesday": ["Lizard_Daily_Schedule.Daily_Schedule"],
    "Lizard_Weekly_Schedule.Wednesday": ["Lizard_Daily_Schedule.Daily_Schedule"],
    "Lizard_Weekly_Schedule.Thursday": ["Lizard_Daily_Schedule.Daily_Schedule"],
    "Lizard_Weekly_Schedule.Friday": ["Lizard_Daily_Schedule.Daily_Schedule"],
    "Lizard_Weekly_Schedule.Saturday": ["Lizard_Daily_Schedule.Daily_Schedule"],
    "Lizard_Weekly_Schedule.Sunday": ["Lizard_Daily_Schedule.Daily_Schedule"],
    "Lizard_Window_Scale.Wall": ["Lizard_Deconstruct.SouthWall", "Lizard_Deconstruct.WestWall", "Lizard_Deconstruct.NorthWall", "Lizard_Deconstruct.EastWall"],
    "Lizard_Window_Surface.Settings": ["Lizard_Window_Settings.Settings", "Lizard_BSDF_Settings.Settings"],
    "Lizard_Zone_Regime.PeopleGain": ["Lizard_Person_Gains.PeopleGain"],
    "Lizard_Zone_Regime.EquipmentGain": ["Lizard_Equipment_Gains.EquipmentGain"],
    "Lizard_Zone_Regime.LightGain": ["Lizard_Light_Gains.LightGain"],
    "Lizard_Zone_Regime.MiscGain": ["Lizard_Misc_Gains.MiscGain"],
    "Lizard_Zone_Regime.ThbGain": ["Lizard_Thermal_Bridge_Gain.ThbGain"],
    "Lizard_Zone_Regime.Heating": ["Lizard_Heating.Heating"],
    "Lizard_Zone_Regime.Dhw": ["Lizard_DHW.Dhw"],
    "Lizard_Zone_Regime.Cooling": ["Lizard_Cooling.Cooling"],
    "Lizard_Zone_Regime.Infiltration": ["Lizard_Infiltration.Infiltration"],
    "Lizard_Zone_Regime.Ventilation": ["Lizard_Mechanical_Ventilation.Ventilation", "Lizard_Infiltration.Infiltration", "Lizard_Stack_Ventilation_1.StackVentilation1", "Lizard_Stack_Ventilation_2.StackVentilation2"],
    "Lizard_Zone_Regime.StackVentilation1": ["Lizard_Stack_Ventilation_1.StackVentilation1"],
    "Lizard_Zone_Regime.StackVentilation2": ["Lizard_Stack_Ventilation_2.StackVentilation2"],
    "Lizard_Zone_Regime.Comfort": ["Lizard_Comfort.Comfort"],
    "Lizard_b18_to_Rhino.FileUrl": ["Lizard_Output_Files.Building"],
}
# End of the written part.


def optionItem(text):
    """(label, value) of one entry of an Options line: 'Label=value' or just 'value'."""
    label, separator, value = text.partition('=')
    return (label.strip(), value.strip()) if separator else (text, text)


def listExpression(kind, value):
    """Expression of a Value List item: a number stays one unless the input takes text, anything else is text in quotes."""
    if kind != 'str':
        try:
            float(value)
            return value
        except ValueError:
            pass
    return '"{0}"'.format(value)


def candidatesForInput(component, port):
    """What can feed an input: [{'label', 'list'} or {'label', 'component', 'port'}], the Value List first."""
    key = component + '.' + port
    found = []
    if key in OPTIONS:
        labels = [optionItem(text)[0] for text in OPTIONS[key]['options']]
        found.append({'label': 'Value List: ' + ', '.join(labels), 'list': OPTIONS[key]})
    for source in SOURCES.get(key, ()):
        name, _, param = source.partition('.')
        found.append({'label': source, 'component': name, 'port': param})
    return found


def candidatesForOutput(component, port):
    """What takes an output, from the Source lines of the inputs: [{'label', 'component', 'port'}]."""
    key = component + '.' + port
    found = []
    for target in sorted(SOURCES):
        if key in SOURCES[target]:
            name, _, param = target.partition('.')
            found.append({'label': target, 'component': name, 'port': param})
    return found


def filterCandidates(found, text):
    """The candidates whose label has all words of a search text, in any case."""
    words = text.lower().split()
    return [candidate for candidate in found if all(word in candidate['label'].lower() for word in words)]


def state():
    return sc.sticky.setdefault(STATE_KEY, {'placeholders': {}, 'warnings': {}})


def ownerOf(param):
    return param.Attributes.GetTopLevel.DocObject


def sameObject(a, b):
    return str(a.InstanceGuid) == str(b.InstanceGuid)


def wiresOf(placeholder):
    """All wires of a Placeholder, on both sides: [(source, recipient)]."""
    return ([(source, param) for param in placeholder.Params.Input for source in param.Sources]
            + [(param, recipient) for param in placeholder.Params.Output for recipient in param.Recipients])


def wireKey(wire):
    return str(wire[0].InstanceGuid) + '>' + str(wire[1].InstanceGuid)


def newWires(entry):
    """The wires of a Placeholder that count as new: not known yet, on its Input or to a TRNLizard component. A known wire that is
    gone is forgotten, so connecting it again counts."""
    placeholder = entry['component']
    wires = wiresOf(placeholder)
    entry['known'] &= set(wireKey(wire) for wire in wires)
    return [wire for wire in wires if wireKey(wire) not in entry['known']
            and (sameObject(ownerOf(wire[1]), placeholder) or str(ownerOf(wire[1]).Name).startswith('Lizard_'))]


def report(component, level, text, status):
    """A runtime message, and in short on the bar under the component."""
    component.AddRuntimeMessage(level, text)
    component.Message = status


def choose(port, found):
    """Modal window on top of Grasshopper with the labels of the candidates and a search box; the chosen one, None when cancelled."""
    import clr
    clr.AddReference('System.Windows.Forms')
    clr.AddReference('System.Drawing')
    import System.Drawing as drawing
    import System.Windows.Forms as forms
    dialog = forms.Form()
    dialog.Text = 'TRNLizard: what should connect to ' + port + '? Type to search.'
    dialog.TopMost = True
    dialog.MinimizeBox = dialog.MaximizeBox = False
    dialog.ShowInTaskbar = False
    dialog.StartPosition = forms.FormStartPosition.CenterParent
    dialog.ClientSize = drawing.Size(520, 260)
    search = forms.TextBox()
    search.Dock = forms.DockStyle.Top
    box = forms.ListBox()
    box.Dock = forms.DockStyle.Fill
    box.IntegralHeight = False
    box.HorizontalScrollbar = True
    ok = forms.Button()
    ok.Text = 'OK'
    ok.Dock = forms.DockStyle.Right
    ok.DialogResult = forms.DialogResult.OK
    shown = []

    def fill(sender=None, args=None):
        shown[:] = filterCandidates(found, search.Text)
        box.Items.Clear()
        for candidate in shown:
            box.Items.Add(candidate['label'])
        if shown:
            box.SelectedIndex = 0
        ok.Enabled = bool(shown)

    def move(sender, args):
        step = {forms.Keys.Down: 1, forms.Keys.Up: -1}.get(args.KeyCode)
        if step and shown:
            box.SelectedIndex = max(0, min(len(shown) - 1, box.SelectedIndex + step))
            args.Handled = args.SuppressKeyPress = True

    def accept(sender, args):
        if box.SelectedIndex >= 0:
            dialog.DialogResult = forms.DialogResult.OK
    search.TextChanged += fill
    search.KeyDown += move
    box.DoubleClick += accept
    fill()
    cancel = forms.Button()
    cancel.Text = 'Cancel'
    cancel.Dock = forms.DockStyle.Right
    cancel.DialogResult = forms.DialogResult.Cancel
    buttons = forms.Panel()
    buttons.Dock = forms.DockStyle.Bottom
    buttons.Height = 30
    buttons.Controls.Add(ok)
    buttons.Controls.Add(cancel)
    dialog.Controls.Add(box)
    dialog.Controls.Add(search)
    dialog.Controls.Add(buttons)
    dialog.AcceptButton = ok
    dialog.CancelButton = cancel
    dialog.ActiveControl = search
    result = dialog.ShowDialog(Grasshopper.Instances.DocumentEditor)
    return shown[box.SelectedIndex] if result == forms.DialogResult.OK and box.SelectedIndex >= 0 else None


def buildValueList(spec, nickName):
    """A dropdown Value List with the options of an input, on its Default if it has one: (object, its output)."""
    special = gk.Special
    valueList = special.GH_ValueList()
    valueList.CreateAttributes()
    valueList.ListMode = special.GH_ValueListMode.DropDown
    valueList.NickName = nickName
    valueList.ListItems.Clear()
    items = [optionItem(text) for text in spec['options']]
    for label, value in items:
        valueList.ListItems.Add(special.GH_ValueListItem(label, listExpression(spec['type'], value)))
    default = spec.get('default')
    selected = [i for i, item in enumerate(items) if default in item]
    valueList.SelectItem(selected[0] if selected else 0)
    return valueList, valueList


def buildComponent(candidate, side):
    """The component of a candidate from its UserObject, and its param of that name: (object, param)."""
    proxy = Grasshopper.Instances.ComponentServer.FindObjectByName(candidate['component'], True, True)
    if proxy is None:
        raise LookupError('{0} is not in the TRNLizard tab: run Lizard_Updater with makeUserObjects'.format(candidate['component']))
    new = proxy.CreateInstance()
    if new.Attributes is None:
        new.CreateAttributes()
    params = [param for param in (new.Params.Output if side == 'output' else new.Params.Input) if str(param.Name) == candidate['port']]
    if not params:
        raise LookupError('{0} has no {1} {2}: run Lizard_Updater with makeUserObjects'.format(candidate['component'], side, candidate['port']))
    return new, params[0]


def disconnect(placeholder, source, recipient, warning=None, status=None):
    """Remove the wire; the next solution shows the warning and its short status. The other wires stay."""
    recipient.RemoveSource(source)
    if warning:
        state()['warnings'][str(placeholder.InstanceGuid)] = (warning, status)
    placeholder.ExpireSolution(False)


def replace(doc, placeholder, new, newParam, source, recipient, onOutput):
    """Put new where the Placeholder is, on its wire. All wires go before the undo records: Ctrl+Z brings the Placeholder back
    without them, ready for the next try."""
    index = [str(item.InstanceGuid) for item in recipient.Sources].index(str(source.InstanceGuid))
    for otherSource, otherRecipient in wiresOf(placeholder):
        otherRecipient.RemoveSource(otherSource)
    new.Attributes.Pivot = placeholder.Attributes.Pivot
    new.Attributes.ExpireLayout()
    doc.AddObject(new, False)
    undo = doc.UndoUtil
    if onOutput:
        undo.RecordWireEvent(UNDO_NAME, recipient)
        recipient.AddSource(newParam, index)
    else:
        newParam.AddSource(source)
    undo.RecordAddObjectEvent(UNDO_NAME, new)
    undo.RecordRemoveObjectEvent(UNDO_NAME, placeholder)
    doc.RemoveObject(placeholder, False)
    undo.MergeRecords(3 if onOutput else 2)
    new.ExpireSolution(False)


def resolve(doc, placeholder, source, recipient):
    """After the solution that found the wire source -> recipient of a Placeholder: replace it, or remove the wire."""
    if not any(sameObject(item, source) for item in recipient.Sources):
        placeholder.ExpireSolution(False)  # the wire is gone already
        return
    onOutput = sameObject(ownerOf(source), placeholder)
    other = recipient if onOutput else source
    component, port = str(ownerOf(other).Name), str(other.Name)
    found = candidatesForInput(component, port) if onOutput else candidatesForOutput(component, port)
    if not found:
        side = 'input' if onOutput else 'output'
        disconnect(placeholder, source, recipient, "No idea what to do with {0} {1} of {2}: its docstring names no Options or Source for it".format(side, port, component), 'Unknown: ' + port)
        return
    candidate = found[0] if len(found) == 1 else choose(component + '.' + port, found)
    if candidate is None:
        disconnect(placeholder, source, recipient)
        return
    if 'list' in candidate:
        new, newParam = buildValueList(candidate['list'], port)
    else:
        new, newParam = buildComponent(candidate, 'output' if onOutput else 'input')
    replace(doc, placeholder, new, newParam, source, recipient, onOutput)


def schedule(placeholder, source, recipient, stopped=None):
    """A document can only change after the solution; a failure must not end up in the solver.
    stopped: the component that sys.exit left with an error, which is none: it runs again with the changed wire."""
    doc = placeholder.OnPingDocument()

    def callback(document):
        try:
            if stopped is not None:
                stopped.ClearRuntimeMessages()
                Grasshopper.Instances.RedrawCanvas()
            resolve(document, placeholder, source, recipient)
        except Exception as e:
            disconnect(placeholder, source, recipient, str(e), 'Failed')
    doc.ScheduleSolution(1, gk.GH_Document.GH_ScheduleDelegate(callback))


def expireLater(placeholder):
    """Its warning needs a solution of the Placeholder, which a wire on its Output does not start."""
    def callback(document):
        placeholder.ExpireSolution(False)
    placeholder.OnPingDocument().ScheduleSolution(1, gk.GH_Document.GH_ScheduleDelegate(callback))


def checkPlaceholder(component):
    """Called first by every script, for the wire that the Placeholder itself does not hear of: connecting its Output only expires
    the component at the other end. When that is this component, stops the script, which would run with an empty input, and the
    solution, so that what follows does not compute now and again after the change: it stays expired until the solution that
    comes with the change. Looks at all Placeholders: removing one of several wires here can leave one for another component."""
    entries = state()['placeholders']
    for key, entry in list(entries.items()):
        placeholder = entry['component']
        if placeholder.OnPingDocument() is None:
            del entries[key]
            continue
        new = newWires(entry)
        if len(new) == 1:
            del entries[key]
            source, recipient = new[0]
            stopped = component if sameObject(ownerOf(recipient), component) else None
            schedule(placeholder, source, recipient, stopped)
            if stopped is not None:
                component.OnPingDocument().RequestAbortSolution()
                sys.exit()
        elif new and entry.get('warned') != len(new):
            entry['warned'] = len(new)
            expireLater(placeholder)


def run(component):
    """The wires that are there when a Placeholder is first computed are known: only a wire connected after that counts."""
    sc.sticky[CHECK_KEY] = checkPlaceholder
    current = state()
    key = str(component.InstanceGuid)
    component.Message = ''
    warning = current['warnings'].pop(key, None)
    if warning:
        report(component, gk.GH_RuntimeMessageLevel.Warning, warning[0], warning[1])
    entry = current['placeholders'].get(key)
    if entry is None:
        entry = {'known': set(wireKey(wire) for wire in wiresOf(component))}
        current['placeholders'][key] = entry
    entry['component'] = component
    new = newWires(entry)
    if len(new) == 1:
        del current['placeholders'][key]
        schedule(component, new[0][0], new[0][1])
    elif new:
        entry['warned'] = len(new)
        report(component, gk.GH_RuntimeMessageLevel.Warning, "{0} new wires at once: remove all but one".format(len(new)), 'Several new wires')
    elif wiresOf(component) and not warning:
        report(component, gk.GH_RuntimeMessageLevel.Remark, "These wires do nothing: connect a new one to a TRNLizard component", 'Waiting for a wire')


run(ghenv.Component)
