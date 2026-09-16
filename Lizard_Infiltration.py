"""
Define the infiltration rate (air leakage) of your building/zone envelope.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    --------------- Infiltration
    ACH (object): air changes per hour due to fresh air demand
        Access: item
        Required: True
    Schedule (object): ALLDAY Schedule should be selected
        Access: item
        Required: True
    AnnualSchedule (object): Script variable Infiltration
        Access: item
        Required: True
    MinACH (object): air changes per hour due to air leakage
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    Infiltration (object): connect to infiltration input of Thermal Zone
        Access: item
"""
"""
version = '2.3.1'
ghenv.Component.Name = "Lizard_Infiltration"
ghenv.Component.NickName = 'Infiltration'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "3 | Regime"
"""
import scriptcontext as sc
class INFILTRATION:
    def __init__(self):
        # Building file input
        self.Airchange      = 'INPUT 1*ACR_INF'
        # Lizard dependent definitions
        self.Name           = 'INF'
        self.Ach            = 0
        self.Schedule       = 'WORK'
        self.Infiltration   = 1
        self.Type           = self.__class__.__name__
        self.Minach         = 0.1
        self.Annual         = None
        self.Windredfac    = 1
        self.Width       = 10
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
# Read Class Infiltration
Infiltration = INFILTRATION()
# Input Depending Settings
if 'MinACH' in locals():
    Infiltration.Minach     = MinACH
if 'ACH' in locals():
    Infiltration.Ach        = ACH
if 'Schedule' in locals():
    Infiltration.Schedule   = Schedule
if 'AnnualSchedule' in locals():
    Infiltration.Annual   = AnnualSchedule
if 'OC_wind_red' in locals():
    Infiltration.Windredfac        = float(OC_wind_red)
if 'OC_width' in locals():
    Infiltration.Width      = float(OC_width)

#Integration of dict storage for json output
dck = dict()
dck['EQU'] = dict()
dck['EQU']['Infiltration'] = dict()
dck['EQU']['Infiltration']['AirChange'] = ACH 
dck['EQU']['Infiltration']['WeeklySchedule'] = Schedule 
dck['EQU']['Infiltration']['AnnualSchedule'] = AnnualSchedule
dck['EQU']['Infiltration']['MinimumAirChange'] = MinACH
dck['TYPES'] = dict()
Infiltration.Json   = dck

switchcomp = locals()
if '--------------- Infiltration' in switchcomp and switchcomp['--------------- Infiltration'] == False:
    Infiltration = None
