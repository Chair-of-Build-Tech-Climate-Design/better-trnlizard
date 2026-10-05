"""
Predefine active layer parameters for multiple active layer wall types considering Crank-Nicholson calculation.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    BRep (Brep): set one/multiple surfaces in Rhino (right click brep)
        Access: list
        Required: True
    Settings (object): Script variable Active Layer CN ID
        Access: item
        Required: True
    ------------------ hygrothermal
    datafile_assembly (object): Script variable Active Layer CN ID
        Access: item
        Required: True
    write_report (bool): True or not connected = Type 395 writes its report rows into the files Type395_0<unit>*.out (parameter 6 = 1); False = no report rows (parameter 6 = -1, Type 395 writes only for a value > 0; the files are still created with their headers)
        Access: item
        Required: False
    report_interval (float): hours between two report rows (parameter 7), > 0; not connected = 1. Type 395 rounds it to 0.0001 h and writes a row at the end of the first time step at which at least this time has passed since the last row
        Access: item
        Required: False
    add_heat_depth (float): depth [m] from the side-2 surface (the TB2 face: outside of an EXTCALEXT wall, neighbour side of an EXTCALBND wall; x = 0 in Type 395, layers in the order of the material file) to the point that receives add_heat and gives the userdef outputs 5-7 (T, RH, water) (parameter 5); linear between the two nearest cell centres, clamped to the first/last cell; not connected = t395_udepth of the System component, else 0.02
        Access: item
        Required: False
    add_heat (object): additional heat in W per m2 of wall (positive = heating), a number or a TRNSYS expression (text); Type 395 input 11 gets QheatKJ = add_heat * AREA395 * 3.6, the kJ/h of the whole wall, at add_heat_depth. Not connected = the active-layer load of the zone (as before). A value given here is not booked as add-on heating/cooling demand of the zone (Q_addon)
        Access: item
        Required: False
    layer_min_div (int): minimum number of cells per material layer (parameter 9, n_div of Type 395): a layer gets max(ceil(thickness / 0.05 m), layer_min_div) cells; a num_div of the material in the material file overrides it; Type 395 refuses more than 500 cells per layer. Not connected = t395_udivnum of the System component, else 100
        Access: item
        Required: False

Returns:
    SurfaceInfo (object): connect to the surface definition / - / HINT: Press shift key in order to connect / multiple outputs to one input node
        Access: item
"""
version='2.2.1'
ghenv.Component.Name        = "Lizard_Hygro"
ghenv.Component.NickName    = 'Hygrothermal'
ghenv.Component.Message = 'VER 2.1.2\n2020'
ghenv.Component.Category    = "Lizard"
ghenv.Component.SubCategory = "1 | Construction"
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import ghpythonlib.components as ghcomp
import uuid
import Rhino as rc
import Grasshopper.Kernel as gh
version='2.2.1'
#standard ID assignment
BRep = sc.sticky[sc.doc.Path]["CONSTRUCTION"]().addToConstruction(BRep,ghenv.Component.InstanceGuid.ToString())
class Surface:
    def __init__(self):
        self.Boundarycond = 'BOUNDARY' #Options are EXTERNAL, ADJACENT, BOUNDARY
        self.Construction = 'GFL_H' #Set wall type according to library
        self.Boundarytemp = 'Tsoil'
        self.Frontback = 'FRONT' #Options are FRONT or BACK
w = gh.GH_RuntimeMessageLevel.Warning
err = gh.GH_RuntimeMessageLevel.Error
# Type 395 settings of these surfaces: (input, attribute of the surface in Lizard_Component). An input that is not connected,
# or that does not exist yet on an older copy of this component, stays None: the System component writes the deck default.
HYGRO_SETTINGS = (
    ('write_report', 'Writereport'),
    ('report_interval', 'Reportinterval'),
    ('add_heat_depth', 'Addheatdepth'),
    ('add_heat', 'Addheat'),
    ('layer_min_div', 'Layermindiv'),
)
def hygroNumber(value):
    """float of a number or of a numeric text, None for anything else (True/False included)"""
    if isinstance(value, bool):
        return None
    try:
        number = float(value.strip() if hasattr(value, 'strip') else value)
    except (TypeError, ValueError, AttributeError):
        return None
    if number != number or abs(number) == float('inf'):
        return None
    return number
def hygroSetting(name, value):
    """(value stored on the surfaces, warning text or None) of one HYGRO_SETTINGS input; an unusable value keeps the default"""
    if value is None or (hasattr(value, 'strip') and not value.strip()):
        return None, None
    number = hygroNumber(value)
    if name == 'write_report':
        text = str(value).strip().lower()
        if isinstance(value, bool):
            return value, None
        if text in ('true', 'yes', 'on'):
            return True, None
        if text in ('false', 'no', 'off'):
            return False, None
        if number is not None:
            return number > 0, None
        return None, "write_report: %s ignored, it must be True or False; the reports are written (parameter 6 = 1)" % (value,)
    if name == 'report_interval':
        if number is None or round(number, 4) <= 0:
            return None, "report_interval: %s ignored, it must be a number of hours > 0 (Type 395 rounds it to 0.0001 h); 1 h is used" % (value,)
        return number, None
    if name == 'add_heat_depth':
        if number is None or number < 0:
            return None, "add_heat_depth: %s ignored, it must be a depth >= 0 m from the side-2 surface; the default depth is used" % (value,)
        return number, None
    if name == 'add_heat':
        if isinstance(value, bool):
            return None, "add_heat: %s ignored, it must be W per m2 of wall (a number or a TRNSYS expression); the active-layer load is used" % (value,)
        if number is not None:
            return (value.strip() if hasattr(value, 'strip') else value), None
        text = str(value).strip()
        for forbidden in ('@', '!', '\n', '\r'):
            if forbidden in text:
                return None, "add_heat: %s ignored, '@', '!' and line breaks cannot be written into the deck; the active-layer load is used" % (text,)
        return '(' + text + ')', None
    if name == 'layer_min_div':
        if number is None or number < 1 or number != int(number):
            return None, "layer_min_div: %s ignored, it must be a whole number >= 1; the default number of cells is used" % (value,)
        return int(number), None
    return None, None
hygro_values = []
for hygro_name, hygro_attribute in HYGRO_SETTINGS:
    hygro_value, hygro_warning = hygroSetting(hygro_name, locals().get(hygro_name))
    hygro_values.append((hygro_attribute, hygro_value))
    if hygro_warning:
        ghenv.Component.AddRuntimeMessage(w, hygro_warning)
if Settings:
    surface = Settings
else:
    surface = Surface()
library = sc.sticky[sc.doc.Path]["library"]
found = 0
for wall_item in library.Walls:
    if surface.Construction == wall_item.Name or surface.Construction == "Virtual":
        found = 1
if found == 0:
    SurfaceInfo = None
    ghenv.Component.AddRuntimeMessage(err, "Construction name not found in the library!")
    ghenv.Component.Message = 'Construction name not found in the library!'
else:
    sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstructionNew(BRep,surface)
    for items in BRep:
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Filemat',datafile_assembly)
        for hygro_attribute, hygro_value in hygro_values:
            sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,hygro_attribute,hygro_value)
        if surface.Boundarycond == 'BOUNDARY':
            sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Boundarycond','EXTCALBND')
        if surface.Boundarycond == 'EXTERNAL':
            sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Boundarycond','EXTCALEXT')
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().getWallThickness(BRep)
    lizard_coll = sc.sticky[sc.doc.Path]["CONSTRUCTION"]()
    
    ObjectsFromLz = lizard_coll.callFromConstruction(BRep)
    print(ObjectsFromLz)
    for item in ObjectsFromLz:
        print(item.__dict__.keys())
        if hasattr(item, 'Filemat') and item.Filemat is not None:
            ghenv.Component.Message = '%s'%(surface.Boundarycond)
        else:
            try:
                Uvalue = round(item.Uvalue,2)
                ghenv.Component.Message = '%s\n%s\nUval = %s W/(m?.K)'%(surface.Boundarycond,surface.Construction,Uvalue)
            except:
                ghenv.Component.Message = '%s\n%s\n%s'%(surface.Boundarycond,surface.Construction,surface.Frontback)
    SurfaceInfo = BRep
