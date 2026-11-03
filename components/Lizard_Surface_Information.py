"""
Search specific surfaces depending to their property.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    surfaceinfo (Brep): link the wall informations
        Access: list
        Required: False
    information (str): search information
        Access: item
        Required: False
    filter (object): define search target
        Access: item
        Required: False

Returns:
    _brep (object): resulting brep after filtering - HINT:Press shift key when connecting multiple outputs to one input node
        Access: item
"""
version='2.2.1'
#ghenv.Component.Name = "Lizard_Surface_Information"
#ghenv.Component.NickName = 'Surface Search'
#ghenv.Component.Message = 'VER 2.2.1\n2020'
#ghenv.Component.Category = "Lizard"
#ghenv.Component.SubCategory = "2 | Construction"
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import ghpythonlib.components as ghcomp
import sys
import Grasshopper.Kernel as gh
lizard_coll = sc.sticky[sc.doc.Path]["CONSTRUCTION"]()
ObjectsFromLz = lizard_coll.callFromConstruction(surfaceinfo)
_brep = []
info = []
for LO in range(len(ObjectsFromLz)):
    if filter and str(ObjectsFromLz[LO].__dict__[information]) == str(filter):
        print ObjectsFromLz[LO].__dict__[information]
        _brep.append(surfaceinfo[LO])
    elif filter is None:
        print ObjectsFromLz[LO].__dict__[information]
        info.append(ObjectsFromLz[LO].__dict__[information])
        _brep.append(surfaceinfo[LO])
infostr = ''
for item in info:
    infostr += '%s\n'%item
ghenv.Component.Message = '%s'%infostr
