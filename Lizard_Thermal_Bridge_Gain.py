"""
Define gains for thermal bridges of your building.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    ---------- ThermalBridge
    OutsideAreaFactor (object): define the heat exchange in W/(m?.K)
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    ThbGain (object): connect to gain input of Thermal Zone
        Access: item
"""
"""
version = '2.3.1'
ghenv.Component.Name = "Lizard_Thermal_Bridge_Gain"
ghenv.Component.NickName = 'TBR Gain'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
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
ThbGain = GAIN()
#Initial Settings
ThbGain.Name            = "THB"
ThbGain.Othergain       = 1
ThbGain.Userdefined     = 1
ThbGain.Specificpower   = 0.1
ThbGain.Frac_refarea = 1
#Input Depending Settings
if 'OutsideAreaFactor' in locals() and OutsideAreaFactor != None:
    ThbGain.Specificpower = OutsideAreaFactor
ThbGain.Elpowerfrac = 0
ThbGain.Category = 'THBRIDGE'
ThbGain.Convective = '%s'%(0.5 * 3.6 * OutsideAreaFactor)
ThbGain.Radiative = '%s'%(0.5 * 3.6 * OutsideAreaFactor)
ThbGain.Context = 'AREA_RELATED'
#ThbGain.Convective      = 'INPUT 0.5*Q_TBR_KJ'
#ThbGain.Radiative       = 'INPUT 0.5*Q_TBR_KJ'

#Integration of dict storage for json output
dck = dict()
dck['EQU'] = dict()
dck['EQU']['ThermalBridge'] = dict()
dck['EQU']['ThermalBridge']['OutsideAreaFactor'] = OutsideAreaFactor

dck['TYPES'] = dict()
ThbGain.Json   = dck

switchcomp = locals()
if '---------- ThermalBridge' is not None and switchcomp['---------- ThermalBridge'] == False:
    ThbGain = None
