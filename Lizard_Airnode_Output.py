"""
Define userdefined Airnode outputs. For definition please refer to the TRNSYS Manual
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    SelectedOutputs (object): Selected outputs to be printed out
        Access: list
        Required: False
    UserDefName (object): Renamed selected ouputs with new user-defined name
        Access: item
        Required: False

Returns:
    OutputInfo (object): output information hast to be linked to the zone component - HINT:Press shift key when connecting multiple outputs to one input node
        Access: item
"""
"""
version='2.2.1'
ghenv.Component.Name = "Lizard_Airnode_Output"
ghenv.Component.NickName = 'Airnode Output'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "5 | Tools"
"""
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import ghpythonlib.components as ghcomp
import sys
import Grasshopper.Kernel as gh
ntype_output = []
ntype_short_name = []
for item in SelectedOutputs:
    dummy = item.split(';')
    ntype_output.append(dummy[0])
    ntype_short_name.append(dummy[1])
class OUTPUT:
    def __init__(self):
        self.Name        = 'AIRNODE'
        self.Type        = 'AIRNODE'
        self.NtypesNo    = ntype_output
        self.NtypesShort = ntype_short_name
        self.Ntype = ntype_short_name
        self.SurfaceID   = []
        self.UserName    = ''
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
output         = OUTPUT()
if 'UserDefName' in locals() and UserDefName:
    output.UserName = UserDefName
OutputInfo = output
