"""
Define gains for your building not specified in standard gains.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    --------------- MiscGain
    SpecificPower (object): specific power of gain
        Access: item
        Required: True
    Schedule (object): select gain "use" schedule (refer to Schedule Library)
        Access: item
        Required: True
    ConvectivePart (object): convective part of gain in Watts
        Access: item
        Required: True
    Humidity (object): Script variable Gains
        Access: item
        Required: True
    AnnualSchedule (object): Script variable Gains
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    MiscGain (object): connect to gain input of Thermal Zone / -  / HINT:Press shift key when connecting  / multiple outputs to one input node
        Access: item
"""
"""
version='2.2.1'
ghenv.Component.Name = "Lizard_Misc_Gains"
ghenv.Component.NickName = 'Gains'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "4 | Gains"
"""
import scriptcontext as sc
class GAIN:
    def __init__(self):
        self.Name           = ''
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
        self.Heatbymisc     = 0
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
MiscGain = GAIN()
#Initial Settings
MiscGain.Name            = "HUMID"
MiscGain.Othergain       = 1
MiscGain.Specificpower   = 1.5
MiscGain.Userdefined     = 1
MiscGain.Convaux         = 0.6
MiscGain.Convective      = 'INPUT {0}*{1}'.format(round(MiscGain.Convaux,2) , 'Q_ADDON_KJ')
MiscGain.Radiative       = 'INPUT {0}*{1}'.format(round((1-MiscGain.Convaux),2) , 'Q_ADDON_KJ')
MiscGain.Elpowerfrac = 1
MiscGain.Context         = 'ABSOLUTE'
# MiscGain.Frac_refarea = 1
#Input Depending Settings
if 'Power' in locals() and Power != None:
    MiscGain.Specificpower = Power
if 'Schedule' in locals() and Schedule != None:
    MiscGain.Schedule = Schedule
if 'ConvectivePart' in locals() and ConvectivePart != None:
    MiscGain.Convaux         = ConvectivePart
    MiscGain.Convective = 'INPUT {0}*{1}'.format(round(MiscGain.Convaux,2) , 'Q_ADDON_KJ')
    MiscGain.Radiative = 'INPUT {0}*{1}'.format(round((1-MiscGain.Convaux),2) , 'Q_ADDON_KJ')
if 'AnnualSchedule' in locals():
    if AnnualSchedule != '':
        MiscGain.Annual = AnnualSchedule
if 'Humidity' in locals() and Humidity is not None:
    MiscGain.Hum2 = Humidity
if 'HeatingBy' in locals() and HeatingBy is not None:
    MiscGain.Heatbymisc = HeatingBy
switchcomp = locals()
if '--------------- MiscGain' is not None and switchcomp['--------------- MiscGain'] == False:
    MiscGain = None
