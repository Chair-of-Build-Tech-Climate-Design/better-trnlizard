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
    ConvectivePart (object): convective part of the gain as a fraction (0-1) of its power (radiative part = 1 - ConvectivePart); not connected = 0.6
        Access: item
        Required: True
    conv_part (float): convective part of the gain [-] (0..1, radiative part = 1 - conv_part), the input name of older copies of this component for ConvectivePart; ConvectivePart wins when both are connected; not connected = 0.6
        Access: item
        Required: False
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
ghenv.Component.Category = "TRNLizard"
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
if 'SpecificPower' in locals() and SpecificPower != None:
    MiscGain.Specificpower = SpecificPower
elif 'Power' in locals() and Power != None:   # input name of older copies of this component
    MiscGain.Specificpower = Power
if 'Schedule' in locals() and Schedule != None:
    MiscGain.Schedule = Schedule
# convective part: ConvectivePart, or conv_part (input name of older copies); ConvectivePart wins when both are connected
misc_conv_part = None
if 'conv_part' in locals() and conv_part != None:
    misc_conv_part = conv_part
if 'ConvectivePart' in locals() and ConvectivePart != None:
    misc_conv_part = ConvectivePart
if misc_conv_part != None:
    MiscGain.Convaux         = misc_conv_part
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
