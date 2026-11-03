"""
Define a new material layer.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    Name (object): weekly schedule name
        Access: item
        Required: False
    Resistance (object): define resistance [(h.m2.K)/kJ]
        Access: item
        Required: False

Returns:
    Layer (object): link to the library component
        Access: item
"""
version='2.2.1'
ghenv.Component.Name        = "Lizard_Layer_Resistance"
ghenv.Component.NickName    = 'Layer_Resistance'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category    = "TRNLizard"
ghenv.Component.SubCategory = "2 | Construction"
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import ghpythonlib.components as ghcomp
class Layer:
    def __init__(self):
        self.Name = Name
        self.Pspacing   = ''
        self.Pdiameter  = ''
        self.Conductivity = ''
        self.Capacity   = ''
        self.Density    = ''
        self.Pwallthickness = ''
        self.Pconductivity = ''
        self.Cpfluid    =''
        self.Resistance =''
        self.Pert       =0
        self.Penrt      =0
        self.Type = ''
        self.Usagetype = ''
        self.Cc_pspacing = ''
        self.Cc_pidiameter = ''
        self.Cc_cpfluid = 4.19
Layer = Layer()
if Resistance:
    Layer.Resistance = Resistance
if ('LAYER' not in sc.sticky.keys()):
    sc.sticky['LAYER'] = {}
sc.sticky['LAYER'][Name] = Layer
