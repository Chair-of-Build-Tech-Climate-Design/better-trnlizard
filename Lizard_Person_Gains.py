"""
Define the peole gains for your building.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    ----------------- People
    SensiblePeopleGain (object): Script variable Person Gains
        Access: item
        Required: True
    LatentPeopleGain (object): Script variable Person Gains
        Access: item
        Required: True
    SchedulePeopleGain (object): select appropriate occupation schedule (refer to Schedule Library)
        Access: item
        Required: True
    CO2Production (object): Script variable Person Gains
        Access: item
        Required: True
    ----- WinterRedOfGains
    ReductionPercentage (object): winter reduction percentage
        Access: item
        Required: True
    OnTairoutside24hBelow (object): reducing the amount of people when daily mean outside ambient temperature is below this threshold
        Access: item
        Required: True
    AnnualSchedule (object): annual schedule of occupation
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    PeopleGain (object): connect to gain input in Thermal Zone component / - / HINT:Press shift key when connecting  / multiple outputs to one input node
        Access: item
"""
"""
version = '2.3.1'
ghenv.Component.Name = "Lizard_Person_Gains"
ghenv.Component.NickName = 'Person Gains'
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
        self.Conv2          = 0
        self.Rad2           = 0
        self.Annual         = ''
        self.Daylightfactor = 0.02
        self.Elpowerfrac    = 0
        self.Context        = 'ABSOLUTE'
        self.Category       = 'MISCELLANEOUS'
        self.Dctrl = None
        self.Frac_refarea = -1
        self.CO2 = 0
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
# Read Class Gain
PeopleGain = GAIN()
#Initial Settings
PeopleGain.Personsgain = 1
PeopleGain.Name = 'PEOPLE'
PeopleGain.Hum2 = 0.11
PeopleGain.Conv2 = 50
PeopleGain.Rad2 = 25
PeopleGain.Category = 'PEOPLE'
PeopleGain.Context = 'AREA_RELATED'
PeopleGain.Frac_refarea = 1
PeopleGain.Convective = 'INPUT {0}*Q_PERS_KJ'.format((PeopleGain.Conv2/(PeopleGain.Conv2+PeopleGain.Rad2+0.00000001)))
PeopleGain.Radiative  = 'INPUT {0}*Q_PERS_KJ'.format((PeopleGain.Rad2/(PeopleGain.Conv2+PeopleGain.Rad2+0.00000001)))
# Input Depending Settings
PeopleGain.Conv2   = 0.5*SensiblePeopleGain
PeopleGain.Rad2    = 0.5*SensiblePeopleGain
PeopleGain.Hum2    = LatentPeopleGain / (2257/3.6)
if 'LatentPeopleGain' in locals():
    PeopleGain.Hum2  = PeopleGain.Hum2
if 'SensiblePeopleGain' in locals():
    PeopleGain.Convective = 'INPUT {0}*Q_PERS_KJ'.format((PeopleGain.Conv2/(PeopleGain.Conv2+PeopleGain.Rad2+0.00000001)))
if 'SensiblePeopleGain' in locals():
    PeopleGain.Radiative  = 'INPUT {0}*Q_PERS_KJ'.format((PeopleGain.Rad2/(PeopleGain.Conv2+PeopleGain.Rad2+0.00000001)))
if 'SchedulePeopleGain' in locals():
    if SchedulePeopleGain != '':
        PeopleGain.Schedule    = SchedulePeopleGain
if 'AnnualSchedule' in locals():
    if AnnualSchedule != '':
        PeopleGain.Annual = AnnualSchedule
if 'ReductionPercentage' in locals():
    if ReductionPercentage != '':
        PeopleGain.Winterred = ReductionPercentage
if 'OnTairoutside24hBelow' in locals():
    if OnTairoutside24hBelow != '':
        PeopleGain.Tamb24hon = OnTairoutside24hBelow
if 'CO2Production' in locals() and CO2Production != '':
    PeopleGain.CO2 = CO2Production

#Integration of dict storage for json output
dck = dict()
dck['EQU'] = dict()
dck['EQU']['People'] = dict()
dck['EQU']['People']['SensibleLoad'] = SensiblePeopleGain
dck['EQU']['People']['LatentLoad'] = LatentPeopleGain
dck['EQU']['People']['WeeklySchedule'] = SchedulePeopleGain 
dck['EQU']['People']['Co2Emission'] = CO2Production
dck['EQU']['People']['WinterReduction'] = ReductionPercentage
dck['EQU']['People']['ReductionReleaseOutsideAirTemperature24hBelow'] = OnTairoutside24hBelow
dck['EQU']['People']['AnnualSchedule'] = AnnualSchedule

dck['TYPES'] = dict()
PeopleGain.Json   = dck

switchcomp = locals()
if '----------------- People' is not None and switchcomp['----------------- People'] == False:
    PeopleGain = None
