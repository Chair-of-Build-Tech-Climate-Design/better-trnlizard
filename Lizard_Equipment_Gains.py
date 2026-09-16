"""
Define the equipment gains for your building.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    --------------- Equipment
    PowerEquipmentGain (object): specific power of computer in Watts
        Access: item
        Required: True
    ScheduleEquipmentGain (object): select computer use schedule (refer to Schedule Library)
        Access: item
        Required: True
    ConvPartEquipmentGain (object): convective part of computer gain
        Access: item
        Required: True
    ----- WinterRedOfGains
    ReductionPercentage (object): Script variable Gains
        Access: item
        Required: True
    OnTairoutside24hBelow (object): Script variable Gains
        Access: item
        Required: True
    AnnualSchedule (object): Script variable Equipment Gains
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    EquipmentGain (object): connect to gain input in Thermal Zone component / - / HINT:Press shift key when connecting  / multiple outputs to one input node
        Access: item
"""
"""
version = '2.3.1'
ghenv.Component.Name = "Lizard_Equipment_Gains"
ghenv.Component.NickName = 'Equipment Gains'
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
EquipmentGain = GAIN()
#Initial Settings
EquipmentGain.Name          = 'EQUIP'
EquipmentGain.Computergain  = 1
EquipmentGain.Schedule      = ''
EquipmentGain.Specificpower = 140
EquipmentGain.Convcomp      = 0.6
EquipmentGain.Convective    = 'INPUT {0}*Q_COMP_KJ'.format((EquipmentGain.Convcomp))
EquipmentGain.Radiative     = 'INPUT {0}*Q_COMP_KJ'.format((1-EquipmentGain.Convcomp))
EquipmentGain.Winterred     = 0
EquipmentGain.Elpowerfrac = 1
EquipmentGain.Category = 'EQUIPMENT'
EquipmentGain.Context     = 'AREA_RELATED'
EquipmentGain.Frac_refarea = 1
# Input Depending Settings
if 'ScheduleEquipmentGain' in locals() and ScheduleEquipmentGain != None:
    EquipmentGain.Schedule  = ScheduleEquipmentGain
if 'PowerEquipmentGain' in locals() and PowerEquipmentGain != None:
    EquipmentGain.Specificpower  = PowerEquipmentGain
if 'ConvPartEquipmentGain' in locals() and ConvPartEquipmentGain != None:
    EquipmentGain.Convcomp  = ConvPartEquipmentGain
    EquipmentGain.Convective    = 'INPUT {0}*Q_COMP_KJ'.format((EquipmentGain.Convcomp))
    EquipmentGain.Radiative     = 'INPUT {0}*Q_COMP_KJ'.format((1-EquipmentGain.Convcomp))
if 'ReductionPercentage' in locals() and ReductionPercentage != None:
    EquipmentGain.Winterred  = ReductionPercentage
if 'OnTairoutside24hBelow' in locals() and OnTairoutside24hBelow != None:
    EquipmentGain.Tamb24hon  = OnTairoutside24hBelow
if 'EquipmentHeatingON' in locals() and EquipmentHeatingON != None:
    EquipmentGain.Heatbycomp  = EquipmentHeatingON
if 'AnnualSchedule' in locals():
    if AnnualSchedule != '':
        EquipmentGain.Annual = AnnualSchedule

#Integration of dict storage for json output
dck = dict()
dck['EQU'] = dict()
dck['EQU']['Equipment'] = dict()
dck['EQU']['Equipment']['SensibleLoad'] = PowerEquipmentGain
dck['EQU']['Equipment']['WeeklySchedule'] = ScheduleEquipmentGain 
dck['EQU']['Equipment']['WinterReduction'] = ReductionPercentage
dck['EQU']['Equipment']['ReductionOutsideAirTemperature24hBelow'] = OnTairoutside24hBelow
dck['EQU']['Equipment']['AnnualSchedule'] = AnnualSchedule

dck['TYPES'] = dict()
EquipmentGain.Json   = dck

switchcomp = locals()
if '--------------- Equipment' is not None and switchcomp['--------------- Equipment'] == False:
    EquipmentGain = None
