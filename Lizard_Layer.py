"""
Define a new material layer.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    Name (object): material layer name
        Access: item
        Required: False
    Conductivity (object): define conductivity [kJ/(hr.m.K)]
        Access: item
        Required: False
    Capacity (object): define capacity [kJ/(kg.K)]
        Access: item
        Required: False
    Density (object): define density [kg/m3]
        Access: item
        Required: False
    PERT (object): define the renewable primary energy resources [MJ/kg]
        Access: item
        Required: False
    PENRT (object): define the non-renewable primary energy resources [MJ/kg]
        Access: item
        Required: False

Returns:
    Layer (object): link to the library component
        Access: item
"""
version='2.2.1'
ghenv.Component.Name        = "Lizard_Layer"
ghenv.Component.NickName    = 'Layer'
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
        self.Pspacing = ''
        self.Pdiameter = ''
        self.Conductivity = Conductivity
        self.Capacity = Capacity
        self.Density = Density
        self.Pwallthickness = ''
        self.Pconductivity = ''
        self.Cpfluid =''
        self.Resistance =''
        self.Pert =PERT
        self.Penrt =PENRT
        self.Type = ''
        self.Usagetype = ''
        self.Cc_pspacing = ''
        self.Cc_pidiameter = ''
        self.Cc_cpfluid = 4.19
Layer = Layer()
if ('LAYER' not in sc.sticky.keys()):
    sc.sticky['LAYER'] = {}
sc.sticky['LAYER'][Name] = Layer
