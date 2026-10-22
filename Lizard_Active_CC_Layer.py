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
    PipeSpacing (object): define spacing of pipes
        Access: item
        Required: False
    PipeDiameter (object): define diameter of pipes
        Access: item
        Required: False
    PipeLength (object): Script variable Active_Layer
        Access: item
        Required: False
    UsageType (object): define the type of usage
        Access: item
        Required: False
    ModuleArea (float): Script variable Active_Layer
        Access: item
        Required: False
    ActiveArea (float): Script variable Active_Layer
        Access: item
        Required: False
    Coefficient (float): Script variable Active_Layer
        Access: item
        Required: False
    Exponent (float): Script variable Active_Layer
        Access: item
        Required: False
    SpecNormFlow (object): Script variable Active_Layer
        Access: item
        Required: False
    SpecMassFlow (object): Script variable Active_Layer
        Access: item
        Required: False

Returns:
    Layer (object): link to the library component
        Access: item
"""
version='2.2.1'
ghenv.Component.Name        = "Lizard_Active_CC_Layer"
ghenv.Component.NickName    = 'Active_Layer'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category    = "TRNLizard"
#ghenv.Component.SubCategory = "2 | Construction"
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import ghpythonlib.components as ghcomp
class Layer:
    def __init__(self):
        self.Name = Name
        self.Pspacing = ''
        self.Pdiameter = ''
        self.Conductivity = ''
        self.Capacity = ''
        self.Density = ''
        self.Pwallthickness = 0
        self.Pconductivity = 0
        self.Cpfluid = 4.19  #KJ/(kg.K)
        self.Resistance = ''
        self.Type = 'CL'
        self.Pert =0
        self.Penrt =0
        self.Usagetype = UsageType
        self.Cc_pspacing = PipeSpacing
        self.Cc_pidiameter = PipeDiameter
        self.Cc_cpfluid = 4.19
        self.Sp_normpower = 318 #in kJ/(hr.m2)
        self.Sp_normmflow = 43 #in kg/(hr.m2)
        self.Normarea = 15 #m2
        self.Normnloop = 1
        self.Ucomb = "GAP"
        self.Uwrx = "F(DTSURFNORM)"
        self.Dtsurfnorm = 2  #K
        self.Mflow = 0
        self.Plength = PipeLength
Layer = Layer()
Layer.Sp_normpower = Coefficient * 10**Exponent * ActiveArea / ModuleArea * 3.6  #in kJ/(hr.m?)
Layer.Sp_normmflow = SpecNormFlow * ActiveArea / ModuleArea #in kg/(hr.m?)
Layer.Normarea = ModuleArea
Layer.Mflow = SpecMassFlow
if ('LAYER' not in sc.sticky.keys()):
    sc.sticky['LAYER'] = {}
sc.sticky['LAYER'][Name] = Layer
print Layer.Type
