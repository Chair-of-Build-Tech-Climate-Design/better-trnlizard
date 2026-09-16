"""
Define userdefined surface outputs. For definition please refer to the TRNSYS Manual
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    SurfaceInfo (Brep): link the wall informations
        Access: list
        Required: True
    SelectedOutputs (object): Selected outputs to be printed out
        Access: list
        Required: True
    Filter (object): 
        Access: item
        Required: True
    UserDefName (object): Renamed selected ouputs with new user-defined name
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    OutputInfo (object): output information hast to be linked to the zone component
        Access: item
    OutputName (object): Script variable Surface Output
        Access: item
    SurfaceId (object): Script variable Surface Output
        Access: item
"""
"""
version='2.2.1'
ghenv.Component.Name = "Lizard_Surface_Output"
ghenv.Component.NickName = 'Surface Output'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "5 | Tools"
"""
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import ghpythonlib.components as ghcomp
import sys
import Grasshopper.Kernel as gh
NTypeOutput = []
NTypeShortName = []
for item in SelectedOutputs:
    dummy = item.split(';')
    NTypeOutput.append(dummy[0])
    NTypeShortName.append(dummy[1])
class OUTPUT:
    def __init__(self):
        self.Name        = 'SURFACE'
        self.Type        = 'SURFACE'
        self.NtypesNo    = NTypeOutput
        self.NtypesShort = []
        self.Ntype = NTypeShortName
        self.SurfaceID   = []
        self.UserName    = ''
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
output         = OUTPUT()
information = 'Surfnum'
lizard_coll = sc.sticky[sc.doc.Path]["CONSTRUCTION"]()
ObjectsFromLz = lizard_coll.callFromConstruction(SurfaceInfo)
_brep = []
for LO in range(len(ObjectsFromLz)):
    if Filter and str(ObjectsFromLz[LO].__dict__[information]) == str(Filter):
        #print ObjectsFromLz[LO].__dict__[information]
        _brep.append(SurfaceInfo[LO])
        output.SurfaceID.append(ObjectsFromLz[LO].__dict__[information])
    elif Filter is None:
        #print ObjectsFromLz[LO].__dict__[information]
        _brep.append(SurfaceInfo[LO])
        output.SurfaceID.append(ObjectsFromLz[LO].__dict__[information])
OutputName = []
SurfaceId = []
for items in NTypeShortName:
    for Surface_item in output.SurfaceID:
        output.NtypesShort.append('{0}_S{1}'.format(items,Surface_item))
        OutputName.append(output.NtypesShort[-1])
        SurfaceId.append(Surface_item)
        if 'UserDefName' in locals() and UserDefName:
            output.UserName = UserDefName
if SurfaceInfo:
    OutputInfo = output
else:
    OutputInfo = None
