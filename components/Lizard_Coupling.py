"""
Define the multizone couplings.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    AirFlowDirection (str): define the air flow by the syntax "from zone1 to zone2 to..."
        Access: item
        Required: False
    Type (str): choose type
        Access: item
        Required: False
    ACRInversion (float): choose ACR for inversion
        Access: item
        Required: False
    ACRPermanent (float): choose ACR for permanent air change
        Access: item
        Required: False
    TempCtrlStackVent (object): define which information drives the air flow, LAST or MEAN or FIRST
        Access: item
        Required: False
    ScalingFactor (object): increase the air flow by the scaling factor
        Access: item
        Required: False

Returns:
    coupling (object): connect to multizone building component - HINT: Press shift key in order to connect multiple outputs to one input node
        Access: item
"""
"""
version='2.2.1'
ghenv.Component.Name = "Lizard_Coupling"
ghenv.Component.NickName = 'Coupling'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Regime"
"""
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import ghpythonlib.components as ghcomp
air_flow_direction = AirFlowDirection
type = Type
ACR_inversion = ACRInversion
ACR_permanent = ACRPermanent
temp_ctrl_stack_vent = TempCtrlStackVent
scaling_factor = ScalingFactor
class COUPLING:
    def __init__(self):
        self.Name = 'COUPLING'
        self.Type = 'COUPLING'
        self.Temperature = 'OUTSIDE'
        self.Airchange   = 'INPUT 1*ACR_FROM_TO'
        self.Humidity    = 'OUTSIDE'
        self.Ventilation = 1
        self.Target = ''
        self.Source = ''
        self.Info = ''
        self.ACR = 0
        self.TempCtrl = temp_ctrl_stack_vent.upper()
        self.ACR_Vol = ''
        self.AllZones = dummyallzones
        self.LastZone = dummylastzone
        self.FirstZone = dummyfirstzone
        self.ScaleFactor = scaling_factor
        self.Specfanpower = 0
        self.Senshr = 0
        self.Absminhum = 'OUTSIDE'
        self.Absmaxhum = 'OUTSIDE'
        self.Calcqahu = 0
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
#Coupling integration
coupling = []
newcoupl = []
dummy = []
dummy = re.sub(';',' ',air_flow_direction)
dummy = dummy.split()
dummyallzones = []
for item2 in range(len(dummy)):
    if 'to' in dummy[item2] or 'from' in dummy[item2]:
        pass
    else:
        dummyallzones.append(dummy[item2])
dummylastzone = dummy[len(dummy)-1]
dummyfirstzone = dummy[1]
for item2 in range(len(dummy)):
    if 'to' in dummy[item2] or 'from' in dummy[item2] or item2 == 1:
        pass
    else:
        newcoupl.append(COUPLING())
        newcoupl[-1].Name = '{0}TO{1}'.format(dummy[item2-2],dummy[item2])
        newcoupl[-1].Source      = dummy[item2-2]
        newcoupl[-1].Target      = dummy[item2]
        newcoupl[-1].Type        = 'COUPLING'
        newcoupl[-1].Airchange   = 'INPUT 1*MF_{0}TO{1}'.format(dummy[item2-2],dummy[item2])
        newcoupl[-1].Humidity    = 'INPUT 1*ABSHUML_{0}'.format(dummy[item2-2])
        newcoupl[-1].Absminhum    = 'INPUT 1*ABSHUML_{0}'.format(dummy[item2-2])
        newcoupl[-1].Absmaxhum    = 'INPUT 1*ABSHUML_{0}'.format(dummy[item2-2])
        newcoupl[-1].Temperature = 'INPUT 1*TLAIR_{0}'.format(dummy[item2-2])
        newcoupl[-1].Info        = type.upper()
        newcoupl[-1].ACR_Vol     = dummy[item2-2]
        newcoupl[-1].AllZones = dummyallzones
        newcoupl[-1].LastZone = dummylastzone
        newcoupl[-1].FirstZone = dummyfirstzone
        if newcoupl[-1].Info == 'PERMANENT':
            newcoupl[-1].ACR = ACR_permanent
        elif newcoupl[-1].Info == 'INVERSION':
            newcoupl[-1].ACR = ACR_inversion
        coupling.append(newcoupl[-1])
        if newcoupl[-1].Info == 'PERMANENT' or newcoupl[-1].Info == 'INVERSION':
            newcoupl.append(COUPLING())
            newcoupl[-1].Name = '{1}TO{0}'.format(dummy[item2-2],dummy[item2])
            newcoupl[-1].Source = dummy[item2]
            newcoupl[-1].Target = dummy[item2-2]
            newcoupl[-1].Type = 'COUPLING'
            newcoupl[-1].Airchange   = 'INPUT 1*MF_{1}TO{0}'.format(dummy[item2-2],dummy[item2])
            newcoupl[-1].Humidity    = 'INPUT 1*ABSHUML_{0}'.format(dummy[item2])
            newcoupl[-1].Absminhum    = 'INPUT 1*ABSHUML_{0}'.format(dummy[item2])
            newcoupl[-1].Absmaxhum    = 'INPUT 1*ABSHUML_{0}'.format(dummy[item2])
            newcoupl[-1].Temperature = 'INPUT 1*TLAIR_{0}'.format(dummy[item2])
            newcoupl[-1].Info        = type.upper()
            newcoupl[-1].ACR_Vol     = dummy[item2-2]
            if newcoupl[-1].Info == 'PERMANENT':
                newcoupl[-1].ACR = ACR_permanent
            elif newcoupl[-1].Info == 'INVERSION':
                newcoupl[-1].ACR = ACR_inversion
            coupling.append(newcoupl[-1])
