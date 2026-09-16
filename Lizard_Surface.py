"""
Define the parameters of one building surface type.
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
    Settings (object): Script variable Surface
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    SurfaceInfo (object): connect to corresponding airnode
        Access: item
"""
import scriptcontext as sc
import Grasshopper.Kernel as gh
version='2.2.1'
ghenv.Component.Name = "Lizard_Surface"
#ghenv.Component.NickName = 'Lizard Surface'
#ghenv.Component.Category = "Lizard"
#ghenv.Component.SubCategory = "0 | Project"
#standard ID assignment
BRep = sc.sticky[sc.doc.Path]["CONSTRUCTION"]().addToConstruction(BRep,ghenv.Component.InstanceGuid.ToString())
class Surface:
    def __init__(self):
        self.Boundarycond = 'BOUNDARY' #Options are EXTERNAL, ADJACENT, BOUNDARY
        self.Construction = 'IFL_L' #Set wall type according to library
        self.Boundarytemp = 'TAIR_@ANAME'
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
    sc.sticky[sc.doc.Path]["CONSTRUCTION"]().getWallThickness(BRep)
    lizard_coll = sc.sticky[sc.doc.Path]["CONSTRUCTION"]()
    ObjectsFromLz = lizard_coll.callFromConstruction(BRep)
    for item in ObjectsFromLz:
        try:
            Uvalue = round(item.Uvalue,2)
            ghenv.Component.Message = '%s\n%s\nUval = %s W/(m?.K)'%(surface.Boundarycond,surface.Construction,Uvalue)
        except:
            ghenv.Component.Message = '%s\n%s\n%s'%(surface.Boundarycond,surface.Construction,surface.Frontback)
    SurfaceInfo = BRep
