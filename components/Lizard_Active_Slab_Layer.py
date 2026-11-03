"""
Define a new active layer.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    Name (object): material layer name
        Access: item
        Required: False
    PipeSpacing (float): define spacing of pipes
        Access: item
        Required: False
    PipeDiameter (float): define diameter of pipes
        Access: item
        Required: False
    PipeWallThickness (object): define pipe wall thickness
        Access: item
        Required: False
    PipeConductivity (object): define pipe conductivity
        Access: item
        Required: False
    PipeLength (object): Script variable Active_Layer
        Access: item
        Required: False
    SpecMassFlow (object): Script variable Active_Layer
        Access: item
        Required: False
    UsageType (object): define the type of usage
        Access: item
        Required: False

Returns:
    Layer (object): link to the library component
        Access: item
"""
version='2.2.1'
ghenv.Component.Name        = "Lizard_Active_Slab_Layer"
ghenv.Component.NickName    = 'Active_Layer'
ghenv.Component.Message     = 'VER %s'%version
ghenv.Component.Category    = "TRNLizard"
#ghenv.Component.SubCategory = "2 | Construction"
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import ghpythonlib.components as ghcomp
class Layer:
    def __init__(self):
        self.Name = Name
        self.Pspacing = PipeSpacing
        self.Pdiameter = PipeDiameter
        self.Conductivity = ''
        self.Capacity = ''
        self.Density = ''
        self.Pwallthickness = PipeWallThickness
        self.Pconductivity = PipeConductivity
        self.Cpfluid = 4.19  #KJ/(kg.K)
        self.Resistance = ''
        self.Type = 'AL'
        self.Pert =0
        self.Penrt =0
        self.Usagetype = UsageType
        self.Cc_pspacing = ''
        self.Cc_pidiameter = ''
        self.Cc_cpfluid = 4.19
        self.Mflow = SpecMassFlow
        self.Plength = PipeLength
Layer = Layer()
if ('LAYER' not in sc.sticky.keys()):
    sc.sticky['LAYER'] = {}
sc.sticky['LAYER'][Name] = Layer
print Layer.Type
