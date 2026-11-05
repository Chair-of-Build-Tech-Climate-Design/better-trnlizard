"""
Define the parameters of one building surface type.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
Modified by Junfeng Xiao, 2026.
-

Args:
    BRep (Brep): set one/multiple surfaces in Rhino (right click brep)
        Access: list
        Required: False
        Source: Lizard_Surface_Fraction.BRep1_, Lizard_Surface_Fraction.BRep2_, Lizard_Surface_SegSplitting.Brep_
    Settings (object): settings for these surfaces; empty settings keep the values a surface already has from an earlier Surface component
        Access: item
        Required: False
        Source: Lizard_Surface_Settings.Settings

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
w = gh.GH_RuntimeMessageLevel.Warning
err = gh.GH_RuntimeMessageLevel.Error
for item in BRep:
    if item.Faces.Count > 1:
        ghenv.Component.AddRuntimeMessage(w, "A Brep with {0} faces counts as one surface here: connect a solid directly to the airnode".format(item.Faces.Count))
surface = Settings
library = sc.sticky[sc.doc.Path]["library"]
found = 1
if surface and surface.Construction and surface.Construction != "Virtual":
    found = 0
    for wall_item in library.Walls:
        if surface.Construction == wall_item.Name:
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
            ghenv.Component.Message = '%s\n%s\nUval = %s W/(m?.K)'%(item.Boundarycond,item.Construction,Uvalue)
        except:
            ghenv.Component.Message = '%s\n%s\n%s'%(item.Boundarycond,item.Construction,item.Frontback)
    SurfaceInfo = BRep
