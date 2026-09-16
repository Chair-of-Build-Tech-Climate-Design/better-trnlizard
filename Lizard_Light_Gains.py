"""
Define the lighting gains for your building.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    -------- ArtificialLight
    ScheduleLightGain (object): select artificial lighting use schedule (refer to Schedule Library)
        Access: item
        Required: True
    SpecPowerLightGain (object): Define the area specific lighting power in W/m?
        Access: item
        Required: True
    ConvPartLightGain (object): convective part of lighting gain
        Access: item
        Required: True
    ----- Daylight Control
    UseDaylightCtrl (object): Define if daylight grid with airnode specific control settings should be applied.
        Access: item
        Required: True
    AnnualSchedule (object): Script variable Light Gains
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    LightGain (object): connect to gain input in Thermal Zone component
        Access: item
"""
"""
version = '2.3.1'
ghenv.Component.Name = "Lizard_Light_Gains"
ghenv.Component.NickName = 'Light Gains'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "4 | Gains"
"""
import scriptcontext as sc
class GAIN:
    def __init__(self):
        self.Name           = ''
        self.Class = "Gain"
        self.Existing       = 0
        self.Specificpower  = 0
        self.Schedule       = ''
        self.Type           = 'GAIN'
        self.Gain           = 1
        self.Standardgain   = 0
        self.Personsgain    = 0
        self.Computergain   = 0
        self.Lightinggain   = 0
        self.Othergain      = 0
        self.Userdefined    = 0
        self.Convective     = 0
        self.Radiative      = 0
        self.Humidity       = 0
        self.Lighting       = 0
        self.Luxlevel       = 500
        self.Dimming        = 0
        self.Efflight       = 90
        self.Convlight      = 0.4
        self.Permlight      = 0
        self.Convcomp       = 0.4
        self.Convaux        = 0.6
        self.Appers         = 0
        self.Winterred      = 0
        self.Tamb24hon      = 12
        self.Heatbylight    = 0
        self.Heatbycomp     = 0
        self.Hum2           = 0
        self.Conv           = 0
        self.Rad            = 0
        self.Annual         = ''
        self.Daylightfactor = 0.02
        self.Elpowerfrac    = 0
        self.Context        = 'ABSOLUTE'
        self.Category       = 'MISCELLANEOUS'
        self.Dctrl = None
        self.Frac_refarea = -1
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
# Read Class Gain
LightGain = GAIN()
#Initial Settings
LightGain.Name       = "LIGHT"
LightGain.Lightinggain = 1
LightGain.Lighting   = 1
LightGain.Convlight  = 0.4
LightGain.Convective = 'INPUT {0}*Q_LIGHT_KJ'.format((LightGain.Convlight))
LightGain.Radiative  = 'INPUT {0}*Q_LIGHT_KJ'.format((1-LightGain.Convlight))
LightGain.Luxlevel   = ''
LightGain.Efflight   = 50
LightGain.Elpowerfrac = 1
LightGain.Category = 'LIGHTS'
LightGain.Context   = 'AREA_RELATED'
LightGain.Frac_refarea = 1
#Input Depending Settings
if 'ScheduleLightGain' in locals() and ScheduleLightGain != None:
    LightGain.Schedule   = ScheduleLightGain
if 'SetpointLuxLevel' in locals() and SetpointLuxLevel != None:
    LightGain.Luxlevel   = SetpointLuxLevel
if 'DimmingFunction' in locals() and DimmingFunction != None:
    LightGain.Dimming    = DimmingFunction
if 'PermanentLight' in locals() and PermanentLight != None:
    LightGain.Permlight  = PermanentLight
if 'EfficiencyLight' in locals() and EfficiencyLight != None:
    LightGain.Efflight   = EfficiencyLight
if 'ConvPartLightGain' in locals() and ConvPartLightGain != None:
    LightGain.Convlight  = ConvPartLightGain
    LightGain.Convective = 'INPUT {0}*Q_LIGHT_KJ'.format((ConvPartLightGain))
    LightGain.Radiative  = 'INPUT {0}*Q_LIGHT_KJ'.format((1-ConvPartLightGain))
if 'LightHeatingON' in locals() and LightHeatingON != None:
    LightGain.Heatbylight = LightHeatingON
if 'DaylightFactor' in locals() and DaylightFactor != None:
    LightGain.Daylightfactor = DaylightFactor
if 'UseDaylightCtrl' in locals() and UseDaylightCtrl == True:
    LightGain.Dctrl = 'DLC'
    LightGain.Frac_refarea = 1
if 'SpecPowerLightGain' in locals() and SpecPowerLightGain != None:
    LightGain.Specificpower = SpecPowerLightGain
if 'AnnualSchedule' in locals():
    if AnnualSchedule != '':
        LightGain.Annual = AnnualSchedule

#Integration of dict storage for json output
dck = dict()
dck['EQU'] = dict()
dck['EQU']['ArtificialLight'] = dict()
dck['EQU']['ArtificialLight']['SensibleLoad'] = SpecPowerLightGain
dck['EQU']['ArtificialLight']['WeeklySchedule'] = ScheduleLightGain 
dck['EQU']['ArtificialLight']['AnnualSchedule'] = AnnualSchedule

dck['TYPES'] = dict()
LightGain.Json   = dck

switchcomp = locals()
if '-------- ArtificialLight' is not None and switchcomp['-------- ArtificialLight'] == False:
    LightGain = None
