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
