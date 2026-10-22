"""
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    ClimateRegion (object): Link region letter A,B or C
        Access: item
        Required: False
    Type (object): set Type: residential (RES) or non-residential (NONRES)
        Access: item
        Required: False
    FloorArea (float): link/define floor area
        Access: item
        Required: False
    NetVolume (float): link/define netto volume
        Access: item
        Required: False
    ThermalBridgeFactor (object): Script variable ThermalBridgeFactor
        Access: item
        Required: False
    DaytimeFlushing (bool): Script variable DaytimeFlushing
        Access: item
        Required: False
    NighttimeFlushing (object): Script variable NighttimeFlushing
        Access: item
        Required: False
    MaxNightACH (float): define the maximum night air change rate in 1/h
        Access: item
        Required: False

Returns:
    Regime (object): Connect to Zone Component
        Access: item
    WeatherFile (object): WeatherFile
        Access: item
"""
"""
version='2.2.1'
ghenv.Component.Name = "Lizard_Zone_Regime"
ghenv.Component.NickName = 'Zone Regime'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Regime"
"""
import scriptcontext as sc
import re
library      = sc.sticky[sc.doc.Path]["library"]
#added for 4108 cases
VentilationMode = 'NAT'
if ClimateRegion == "A":
    WeatherFile = r'w:\Wetter\eu\de\try2010_02y_rostock.109'
    SetpointCooling = 25
if ClimateRegion == "B":
    WeatherFile = r'w:\Wetter\eu\de\try2010_04y_potsdam.109'
    SetpointCooling = 26
if ClimateRegion == "C":
    WeatherFile = r'w:\Wetter\eu\de\try2010_12y_mannheim.109'
    SetpointCooling = 27
if Type == 'NONRES':
    SpecPowerOtherGain = 144/11
    SetpointHeating = 21
    NameOccupationSchedule = 'NR4108'
    NameDaytimeSchedule = NameOccupationSchedule
    OccupationSchedule = ['MON-FRI!7 to 18;1']
    InfiltrationACH = 0.24
    FreshAirChange = 4 * FloorArea/NetVolume - InfiltrationACH
    DayTimeFlush = 3 - FreshAirChange - InfiltrationACH
    NightTimeFlush = MaxNightACH - InfiltrationACH
else:
    SpecPowerOtherGain = 100/24
    SetpointHeating = 20
    NameOccupationSchedule = 'R4108'
    NameDaytimeSchedule = 'RESI'
    OccupationSchedule = ['MON-SUN!0 to 25;1']
    InfiltrationACH = 0.5
    FreshAirChange = 0
    DayTimeFlush = 3 - FreshAirChange - InfiltrationACH
    NightTimeFlush = MaxNightACH - InfiltrationACH
NamePersonsGain = 0
# reset of local variables
Infiltration       = None
StackVentilation1 = None
StackVentilation2 = None
MechanicalVentilation = None
HybridVentilation = False
if VentilationMode == "HYB":
    HybridVentilation = True
    NaturalIfTairOutsideAbove = 12
    NaturalIfTairOutsideBelow = 25
elif VentilationMode == "NAT":
    HybridVentilation = True
    NaturalIfTairOutsideAbove = -50
    NaturalIfTairOutsideBelow =  50
# preset schedule definition
name                = NameOccupationSchedule
# schedule definition
class SCHEDULE:
    def __init__(self, name=''):
        self.Name = name
        self.Hours = ''
        self.Values = ''
        self.Days = ''
        self.Hourly = ''
        self.Userdef = 0
scheduledef = {}
weekar = ['MON','TUE','WED','THU','FRI','SAT','SUN']
daynum = [1,2,3,4,5,6,7]
for index, item in enumerate(weekar):
    scheduledef[item] = {}
    scheduledef[item]['num'] = index + 1
dummy2 = ''
for index, item in enumerate(OccupationSchedule):
    dummy = item.split('!')
    if '-' in dummy[0]:
        subdummy = dummy[0].split('-')
        start = scheduledef[subdummy[0]]['num']
        stop  = scheduledef[subdummy[1]]['num']
    else:
        start = scheduledef[dummy[0]]['num']
        stop  = scheduledef[dummy[0]]['num']
    for ditem in weekar:
        if scheduledef[ditem]['num'] >= start and scheduledef[ditem]['num'] <= stop:
            datad = dummy[1].split(';')
            scheduledef[ditem]['start'] = datad[0].split()[0]
            scheduledef[ditem]['stop']  = datad[0].split()[-1]
            scheduledef[ditem]['value'] = datad[1]
            scheduledef[ditem]['domain'] = []
            for i, subitem in enumerate(dummy):
                if i > 0:
                    scheduledef[ditem]['domain'].append(subitem)
schedule = sc.sticky[sc.doc.Path]["WEEKLYSCHEDULE"]()
schedule.Name = name
schedule.Weekarray = ['','','','','','','']
for wi,wd in enumerate(weekar):
    daily_schedule = sc.sticky[sc.doc.Path]["DAILYSCHEDULE"]()
    daily_schedule.Name = name + 'WE'
    hour_view = daily_schedule.setValues('')
    schedule.Weekarray[scheduledef[wd]['num']-1] = daily_schedule
    if 'start' in scheduledef[wd]:
        daily_schedule = sc.sticky[sc.doc.Path]["DAILYSCHEDULE"]()
        if wi > 0 and scheduledef[wd]['domain'] == scheduledef[dummyname]['domain']:
            daily_schedule.Name = name + 'DAY' + str(scheduledef[dummyname]['num'])
            hour_view = daily_schedule.setValues(scheduledef[dummyname]['domain'])
        else:
            dummyname = wd
            daily_schedule.Name = name + 'DAY' + str(scheduledef[wd]['num'])
            hour_view = daily_schedule.setValues(scheduledef[wd]['domain'])
        schedule.Weekarray[scheduledef[wd]['num']-1] = daily_schedule
hour_view = []
for item in schedule.Weekarray:
    schedule.Hourly = schedule.Hourly + item.Name + ' '
    schedule.Daysarray.append(item.Name)
    schedule.Hoursarray.append(item.Hours)
    schedule.Valuesarray.append(item.Values)
    hour_view.extend(item.Data)
schedulenames = []
delcoll = []
for j in schedule.Daysarray:
    for u in range(len(library.Schedules)):
        if j == library.Schedules[u].Name or schedule.Name == library.Schedules[u].Name:
            delcoll.append(u)
dummy = list(set(delcoll))
dummy = sorted(dummy)
for item in list(reversed(dummy)):
    library.Schedules.pop(item)
for j in range (len(schedule.Daysarray)):
    if schedule.Daysarray[j] in schedulenames:
        pass
    else:
        print 'New Schedule %s found' % schedule.Daysarray[j]
        schedulenames.append(schedule.Daysarray[j])
        library.Schedules.append(SCHEDULE(schedule.Daysarray[j]))
        library.Schedules[-1].Hours = schedule.Hoursarray[j]
        library.Schedules[-1].Values = schedule.Valuesarray[j]
library.Schedules.append(SCHEDULE(schedule.Name))
library.Schedules[-1].Days = schedule.Days
library.Schedules[-1].Hourly = schedule.Hourly
library.Schedules[-1].Userdef = 1
sc.sticky[sc.doc.Path]['library'] = library
# Mechanical Ventilation pre-definition for simplified component
Activated                     = HybridVentilation
MinACH = 0
ACH = FreshAirChange
# Read Class Mechanical Ventilation
class VENTILATION:
    def __init__(self):
        self.Name           = 'VENT'
        self.Type           = 'VENTILATION'
        self.Ventilation    = 1
        self.Ach            = 0
        self.Achmin         = 0
        self.Vflow          = 0
        self.Vflowppers     = 0
        self.Aefftop        = 0
        self.Aeffbot        = 0
        self.Aefftopfl      = 0
        self.Aeffbotfl      = 0
        self.Hdiff          = 0.5
        self.Schedule       = ''
        self.Schedule2      = ''
        self.Tairon         = 25
        self.Tairoff        = 22
        self.Tambon         = 10
        self.Tamb24on       = 10
        self.Stack          = 1
        self.Toutside       = 'TAMB'
        self.Humoutside     = 'ABSHUM_AMB'
        self.Temperature    = 'INPUT 1*{0}'.format(self.Toutside)
        self.Airchange      = ''
        self.Humidity       = 'INPUT 1*{0}'.format(self.Humoutside)
        self.Maxach         = 3
        self.Hybrid         = 0
        self.Sfp            = 0.8    #W/(m?.h)
        self.Hrcsens        = 0
        self.Hrclat         = 0
        self.Tsummer        = 18
        self.Tsummer2       = 18
        self.Twinter        = 22
        self.Twinter2       = 22
        self.Humsummer      = 40
        self.Humwinter      = 0
        self.Tamb24hcl      = 12
        self.Hybrid         = 0
        self.Thyblow        = 10
        self.Thybhigh       = 26
        self.Tsuplow        = 21
        self.Tsuphigh       = 24
        self.Winterred      = 0
        self.Winterfract    = 1
        self.Toutsidemv     = 'TAMB'
        self.Humoutsidemv   = 'ABSHUM_AMB'
        self.On             = 0
        self.Specfanpower = 0
        self.Absminhum   = 'INPUT 1*ABSHUM_AMB'
        self.Absmaxhum   = 'INPUT 1*ABSHUM_AMB'
        self.Senshr = 0
        self.Calcqahu = 0
        self.Calcmode = "STANDARD" #STANDARD or AHU
        self.Humctrl = 0
        self.Tempctrl = 'AIR'
        self.Reftemp = None
        self.Adiabatic = 0 #0/1 means ON/OFF
MechanicalVentilation             =  VENTILATION()
# Initial Settings
MechanicalVentilation.Name        = 'VENT'
MechanicalVentilation.Temperature= 'INPUT 1*TSUP'
MechanicalVentilation.Airchange  = 'INPUT 1*ACR_AHU'
MechanicalVentilation.Humidity   = 'INPUT 1*ABSHUM_SUP'
MechanicalVentilation.Absminhum   = 'INPUT 1*ABSHUM_SUP'
MechanicalVentilation.Absmaxhum   = 'INPUT 1*ABSHUM_SUP'
MechanicalVentilation.Tsummer    = 18
MechanicalVentilation.Twinter    = 22
MechanicalVentilation.Hrclat     = 0
MechanicalVentilation.Schedule   = NameOccupationSchedule.upper()
MechanicalVentilation.Schedule2  = NameOccupationSchedule.upper()
MechanicalVentilation.Tamb24hcl  = 12
MechanicalVentilation.Humctrl  = 0
# Input Depending Settings
if 'Mode' in locals() and Mode != None:
    MechanicalVentilation.Calcmode = Mode
if 'NaturalIfTairOutsideAbove' in locals() and NaturalIfTairOutsideAbove != None:
    MechanicalVentilation.Thyblow    = NaturalIfTairOutsideAbove
if 'NaturalIfTairOutsideBelow' in locals() and NaturalIfTairOutsideBelow != None:
    MechanicalVentilation.Thybhigh   = NaturalIfTairOutsideBelow
if 'ActivateWinterReduction50P' in locals() and ActivateWinterReduction50P != None:
    MechanicalVentilation.Winterred  = ActivateWinterReduction50P
if 'ScheduleACH' in locals() and ScheduleACH != None:
    MechanicalVentilation.Schedule  = ScheduleACH.upper()
if 'ScheduleOcc' in locals() and ScheduleOcc != None:
    MechanicalVentilation.Schedule2 = ScheduleOcc.upper()
if 'ACH' in locals() and ACH != None:
    MechanicalVentilation.Ach = ACH
if 'MinACH' in locals() and MinACH != None:
    MechanicalVentilation.Achmin = MinACH
if 'OrAbsoluteVolumeFlow' in locals() and OrAbsoluteVolumeFlow != None:
    MechanicalVentilation.Vflow = OrAbsoluteVolumeFlow
if 'OrPersonRelatedVolumeFlow' in locals() and OrPersonRelatedVolumeFlow != None:
    MechanicalVentilation.Vflowppers = OrPersonRelatedVolumeFlow
if 'SupplyTempWinterOcc' in locals() and SupplyTempWinterOcc != None:
    MechanicalVentilation.Twinter = SupplyTempWinterOcc
if 'SupplyTempWinterUnocc' in locals() and SupplyTempWinterUnocc != None:
    MechanicalVentilation.Twinter2 = SupplyTempWinterUnocc
if 'MinSupplyAirHumidity' in locals() and MinSupplyAirHumidity != None:
    MechanicalVentilation.Humwinter = MinSupplyAirHumidity
if 'MaxSupplyAirHumidity' in locals() and MaxSupplyAirHumidity != None:
    MechanicalVentilation.Humsummer = MaxSupplyAirHumidity
if 'SummerTairOutside24hAbove' in locals() and SummerTairOutside24hAbove != None:
    MechanicalVentilation.Tamb24hcl = SummerTairOutside24hAbove
if 'SupplyTempSummerOcc' in locals() and SupplyTempSummerOcc != None:
    MechanicalVentilation.Tsummer = SupplyTempSummerOcc
if 'SupplyTempSummerUnocc' in locals() and SupplyTempSummerUnocc != None:
    MechanicalVentilation.Tsummer2 = SupplyTempSummerUnocc
if 'SensibleHeatRecovery' in locals() and SensibleHeatRecovery != None:
    MechanicalVentilation.Hrcsens = SensibleHeatRecovery
    if MechanicalVentilation.Calcmode == "AHU":
        MechanicalVentilation.Senshr = 0
    else:
        MechanicalVentilation.Senshr = '%s'%SensibleHeatRecovery
        #MechanicalVentilation.Senshr = 'INPUT %s*SENSHR'%SensibleHeatRecovery
if 'LatentHeatRecovery' in locals() and LatentHeatRecovery != None:
    MechanicalVentilation.Hrclat = LatentHeatRecovery
if 'SpecFanPower' in locals() and SpecFanPower != None:
    MechanicalVentilation.Sfp = SpecFanPower
    MechanicalVentilation.Specfanpower = SpecFanPower * 3.6 #*3.6 to get KJ/h
if 'Activated' in locals() and Activated == 1:
    MechanicalVentilation.Hybrid = 1
if 'OutsideTempHybrid' in locals() and OutsideTempHybrid != None:
    MechanicalVentilation.Toutside = OutsideTempHybrid
if 'OutsideHumidityHybrid' in locals() and OutsideHumidityHybrid != None:
    MechanicalVentilation.Humoutside = OutsideHumidityHybrid
    MechanicalVentilation.Humidity    = 'INPUT 1*{0}'.format(MechanicalVentilation.Humoutside)
if 'OutsideTemp' in locals() and OutsideTemp != None:
    MechanicalVentilation.Toutsidemv     = OutsideTemp
    #MechanicalVentilation.Temperature = 'INPUT 1*{0}'.format(MechanicalVentilation.Toutside)
if 'OutsideHumidity'  in locals() and OutsideTemp != None:
    MechanicalVentilation.Humoutsidemv  = OutsideHumidity
if MechanicalVentilation.Calcmode == "STANDARD":
    MechanicalVentilation.Calcqahu = 1
    if 'MinSupplyAirHumidity' in locals() and MinSupplyAirHumidity == None:
        MechanicalVentilation.Humwinter = "ABSHUM_AMB"
    if 'MaxSupplyAirHumidity' in locals() and MaxSupplyAirHumidity == None:
        MechanicalVentilation.Humsummer = "ABSHUM_AMB"
    if MechanicalVentilation.Hrclat > 0:
        ghenv.Component.AddRuntimeMessage(w, "In standard calculation mode no humidity recovery can be considered! If you want to take humidity recovery into account you have to get Type336 from your TRNSYS distributor!")
# pre-definition for simplified component
Schedule = NameOccupationSchedule
# stack ventilation 1 pre-definition for simplified component
if DaytimeFlushing == True:
    # Read Class Ventilation
    StackVentilation1 = VENTILATION()
    # Initial Settings
    StackVentilation1.Name     = 'STVENT1'
    StackVentilation1.Type     = 'STACKVENTILATION'
    StackVentilation1.Airchange= 'INPUT 1*ACR_SV1'
    StackVentilation1.Schedule = ''
    StackVentilation1.Hdiff    = 1
    StackVentilation1.Tairon   = 23
    StackVentilation1.Tairoff  = 21
    StackVentilation1.Tambon   = 5
    StackVentilation1.Tamb24on = 5
    StackVentilation1.Maxach   = DayTimeFlush
    StackVentilation1.Aefftopfl = 0.02
    StackVentilation1.Aeffbotfl = 0.02
    StackVentilation1.Humctrl  = 0
    StackVentilation1.Tempctrl = 'AIR'
    # Input Depending Settings
    if 'HeightDifference' in locals() and HeightDifference != None:
        StackVentilation1.Hdiff    = HeightDifference
    if 'Schedule' in locals() and Schedule != None:
        StackVentilation1.Schedule = Schedule.upper()
    if 'ONTairRoomAbove' in locals() and ONTairRoomAbove != None:
        StackVentilation1.Tairon = ONTairRoomAbove
    if 'OFFTairRoomBelow' in locals() and OFFTairRoomBelow != None:
        StackVentilation1.Tairoff = OFFTairRoomBelow
    if 'ONTairOutsideAbove' in locals() and ONTairOutsideAbove != None:
        StackVentilation1.Tambon = ONTairOutsideAbove
    if 'ONTairOutside24hAbove' in locals() and ONTairOutside24hAbove != None:
        StackVentilation1.Tamb24on = ONTairOutside24hAbove
    if 'MaxAirChange' in locals() and MaxAirChange != None:
        StackVentilation1.Maxach = MaxAirChange
    if 'OutsideTemp' in locals() and OutsideTemp != None:
        StackVentilation1.Toutside = OutsideTemp
        StackVentilation1.Temperature = 'INPUT 1*{0}'.format(StackVentilation1.Toutside)
    if 'OutsideHumidity'  in locals() and OutsideTemp != None:
        StackVentilation1.Humoutside = OutsideHumidity
        StackVentilation1.Humidity = 'INPUT 1*{0}'.format(StackVentilation1.Humoutside)
        StackVentilation1.Absminhum  = 'INPUT 1*{0}'.format(StackVentilation1.Humoutside)
        StackVentilation1.Absmaxhum  = 'INPUT 1*{0}'.format(StackVentilation1.Humoutside)
    if 'OrFloorRelatedEffOpAreaTop'  in locals() and OrFloorRelatedEffOpAreaTop != None:
        StackVentilation1.Aefftopfl = OrFloorRelatedEffOpAreaTop / 100
    if 'OrFloorRelatedEffOpAreaBottom'  in locals() and OrFloorRelatedEffOpAreaBottom is not None:
        StackVentilation1.Aeffbotfl = OrFloorRelatedEffOpAreaBottom / 100
    if 'EffOpeningAreaTop'  in locals() and EffOpeningAreaTop is not None:
        StackVentilation1.Aefftop = EffOpeningAreaTop
    if 'EffOpeningAreaBottom'  in locals() and EffOpeningAreaBottom is not None:
        StackVentilation1.Aeffbot = EffOpeningAreaBottom
# pre-definition for simplified component
Schedule = 'not(gt(SCHED_{0},0))'.format(NameOccupationSchedule)
# stack ventilation 1 pre-definition for simplified component
if NighttimeFlushing == True:
    # Read Class Ventilation
    StackVentilation2 = VENTILATION()
    # Initial Settings
    StackVentilation2.Name     = 'STVENT2'
    StackVentilation2.Type     = 'STACKVENTILATION'
    StackVentilation2.Airchange= 'INPUT 1*ACR_SV2'
    StackVentilation2.Schedule = ''
    StackVentilation2.Hdiff    = 1
    StackVentilation2.Tairon   = 23
    StackVentilation2.Tairoff  = 21
    StackVentilation2.Tambon   = 10
    StackVentilation2.Tamb24on = 10
    StackVentilation2.Maxach   = NightTimeFlush
    StackVentilation2.Aefftopfl = 0.02
    StackVentilation2.Aeffbotfl = 0.02
    StackVentilation2.Humctrl  = 0
    # Input Depending Settings
    if 'HeightDifference' in locals() and HeightDifference != None:
        StackVentilation2.Hdiff    = HeightDifference
    if 'Schedule' in locals() and Schedule != None:
        StackVentilation2.Schedule = Schedule.upper()
    if 'ONTairRoomAbove' in locals() and ONTairRoomAbove != None:
        StackVentilation2.Tairon = ONTairRoomAbove
    if 'OFFTairRoomBelow' in locals() and OFFTairRoomBelow != None:
        StackVentilation2.Tairoff = OFFTairRoomBelow
    if 'ONTairOutsideAbove' in locals() and ONTairOutsideAbove != None:
        StackVentilation2.Tambon = ONTairOutsideAbove
    if 'ONTairOutside24hAbove' in locals() and ONTairOutside24hAbove != None:
        StackVentilation2.Tamb24on = ONTairOutside24hAbove
    if 'MaxAirChange' in locals() and MaxAirChange != None:
        StackVentilation2.Maxach = MaxAirChange
    if 'OutsideTemp' in locals() and OutsideTemp != None:
        StackVentilation2.Toutside = OutsideTemp
        StackVentilation2.Temperature = 'INPUT 1*{0}'.format(StackVentilation2.Toutside)
    if 'OutsideHumidity'  in locals() and OutsideTemp != None:
        StackVentilation2.Humoutside  = OutsideHumidity
        StackVentilation2.Humidity    = 'INPUT 1*{0}'.format(StackVentilation2.Humoutside)
        StackVentilation1.Absminhum  = 'INPUT 1*{0}'.format(StackVentilation1.Humoutside)
        StackVentilation1.Absmaxhum  = 'INPUT 1*{0}'.format(StackVentilation1.Humoutside)
    if 'OrFloorRelatedEffOpAreaTop'  in locals() and OrFloorRelatedEffOpAreaTop != None:
        StackVentilation2.Aefftopfl = OrFloorRelatedEffOpAreaTop / 100
    if 'OrFloorRelatedEffOpAreaBottom'  in locals() and OrFloorRelatedEffOpAreaBottom is not None:
        StackVentilation2.Aeffbotfl = OrFloorRelatedEffOpAreaBottom / 100
    if 'EffOpeningAreaTop'  in locals() and EffOpeningAreaTop is not None:
        StackVentilation2.Aefftop = EffOpeningAreaTop
    if 'EffOpeningAreaBottom'  in locals() and EffOpeningAreaBottom is not None:
        StackVentilation2.Aeffbot = EffOpeningAreaBottom
# infiltration pre-definition for simplified component
MinACH = InfiltrationACH
ACH = 0
Schedule = NameOccupationSchedule
class INFILTRATION:
    def __init__(self):
        self.Name           = 'INF'
        self.Ach            = 0
        self.Schedule       = ''
        self.Infiltration   = 1
        self.Type           = 'INFILTRATION'
        self.Dtf            = 0
        self.Ntf            = 0
        self.Minach         = 0
        self.Airchange      = 'INPUT 1*ACR_INF'
        self.Annual         = None
# Read Class Infiltration
Infiltration = INFILTRATION()
# Initial Settings
Infiltration.Minach     = 0.1
Infiltration.Ach        = 0
# Input Depending Settings
if 'MinACH' in locals():
    Infiltration.Minach     = MinACH
if 'ACH' in locals():
    Infiltration.Ach        = float(ACH)
if 'Schedule' in locals():
    Infiltration.Schedule   = Schedule.upper()
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
        self.Annual         = None
        self.Daylightfactor = 0.02
        self.Elpowerfrac    = 0
        self.Context        = 'ABSOLUTE'
        self.Category       = 'MISCELLANEOUS'
        self.Dctrl = None
        self.Frac_refarea = -1
        self.CO2          = 0
# persons gain pre-definition for simplified component
SchedulePeopleGain = NameOccupationSchedule
NamePeopleGain = 0
# Read Class Gain
PeopleGain = GAIN()
#Initial Settings
PeopleGain.Personsgain = 1
PeopleGain.Name = 'PEOPLE'
PeopleGain.Hum2 = 0.11
PeopleGain.Conv2 = 50
PeopleGain.Rad2 = 25
PeopleGain.Category = 'PEOPLE'
PeopleGain.Context   = 'AREA_RELATED'
PeopleGain.Frac_refarea = 1
PeopleGain.Convective = 'INPUT {0}*Q_PERS_KJ'.format((PeopleGain.Conv2/(PeopleGain.Conv2+PeopleGain.Rad2+0.00000001)))
PeopleGain.Radiative  = 'INPUT {0}*Q_PERS_KJ'.format((PeopleGain.Rad2/(PeopleGain.Conv2+PeopleGain.Rad2+0.00000001)))
# Input Depending Settings
if NamePeopleGain == 0:
    sens_conv   = 0
    sens_rad    = 0
    hum         = 0
if NamePeopleGain == 2:
    sens_conv   = 43.333
    sens_rad    = 21.667
    hum         = 0.081
if NamePeopleGain == 3:
    sens_conv   = 50
    sens_rad    = 25
    hum         = 0.139
if NamePeopleGain == 4:
    sens_conv   = 50
    sens_rad    = 25
    hum         = 0.11
if 'hum' in locals():
    PeopleGain.Hum2  = hum
if 'sens_conv' in locals():
    PeopleGain.Conv2  = sens_conv
if 'sens_rad' in locals():
    PeopleGain.Rad2   = sens_rad
if 'SchedulePeopleGain' in locals():
    if SchedulePeopleGain != '':
        PeopleGain.Schedule    = SchedulePeopleGain.upper()
if 'AnnualSchedule' in locals():
    if AnnualSchedule != '':
        PeopleGain.Annual = AnnualSchedule
if 'ReductionPercentage' in locals():
    if ReductionPercentage != '':
        PeopleGain.Winterred = ReductionPercentage
if 'OnTairoutside24hBelow' in locals():
    if OnTairoutside24hBelow != '':
        PeopleGain.Tamb24hon = OnTairoutside24hBelow
PeopleGain.Convective = 'INPUT {0}*Q_PERS_KJ'.format((PeopleGain.Conv2/(PeopleGain.Conv2+PeopleGain.Rad2+0.00000001)))
PeopleGain.Radiative  = 'INPUT {0}*Q_PERS_KJ'.format((PeopleGain.Rad2/(PeopleGain.Conv2+PeopleGain.Rad2+0.00000001)))
# Special setting for simplified
ScheduleEquipmentGain  = NameOccupationSchedule
# Read Class Gain
EquipmentGain = GAIN()
#Initial Settings
EquipmentGain.Name          = 'EQUIP'
EquipmentGain.Computergain  = 1
EquipmentGain.Schedule      = ''
EquipmentGain.Specificpower = 0
EquipmentGain.Convcomp      = 0.6
EquipmentGain.Convective    = 'INPUT {0}*Q_COMP_KJ'.format((EquipmentGain.Convcomp))
EquipmentGain.Radiative     = 'INPUT {0}*Q_COMP_KJ'.format((1-EquipmentGain.Convcomp))
EquipmentGain.Winterred     = 0
EquipmentGain.Elpowerfrac = 1
EquipmentGain.Category = 'EQUIPMENT'
EquipmentGain.Context   = 'AREA_RELATED'
EquipmentGain.Frac_refarea = 1
# Input Depending Settings
if 'ScheduleEquipmentGain' in locals() and ScheduleEquipmentGain != None:
    EquipmentGain.Schedule  = ScheduleEquipmentGain.upper()
if 'PowerComputerGain' in locals() and PowerComputerGain != None:
    EquipmentGain.Specificpower  = PowerComputerGain
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
# Special setting for simplified
ScheduleLightGain  = NameOccupationSchedule
UseDaylightCtrl = True
# Read Class Gain
LightGain = GAIN()
#Initial Settings
LightGain.Name       = "LIGHT"
LightGain.Lightinggain = 1
LightGain.Lighting   = 1
LightGain.Convlight  = 0.4
LightGain.Convective = 'INPUT {0}*Q_LIGHT_KJ'.format((LightGain.Convlight))
LightGain.Radiative  = 'INPUT {0}*Q_LIGHT_KJ'.format((1-LightGain.Convlight))
LightGain.Luxlevel   = 0
LightGain.Efflight   = 50
LightGain.Elpowerfrac = 1
LightGain.Category = 'LIGHTS'
LightGain.Context   = 'AREA_RELATED'
LightGain.Frac_refarea = 1
#Input Depending Settings
if 'ScheduleLightGain' in locals() and ScheduleLightGain != None:
    LightGain.Schedule   = ScheduleLightGain.upper()
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
# Regime definition from standard component
# Special setting for simplified
SpecificPower = SpecPowerOtherGain
Schedule = NameOccupationSchedule
# Read Class Gain
MiscGain = GAIN()
#Initial Settings
MiscGain.Name            = "MISC"
MiscGain.Othergain       = 1
MiscGain.Specificpower   = 1.5
MiscGain.Userdefined     = 1
MiscGain.Convaux         = 1
MiscGain.Convective      = 'INPUT {0}*{1}'.format(round(MiscGain.Convaux,2) , 'Q_ADDON_KJ')
MiscGain.Radiative       = 'INPUT {0}*{1}'.format(round((1-MiscGain.Convaux),2) , 'Q_ADDON_KJ')
MiscGain.Elpowerfrac = 1
MiscGain.Context   = 'AREA_RELATED'
MiscGain.Frac_refarea = 1
#Input Depending Settings
if 'SpecificPower' in locals() and SpecificPower != None:
    MiscGain.Specificpower = SpecificPower
if 'Schedule' in locals() and Schedule != None:
    MiscGain.Schedule = Schedule.upper()
if 'ConvectivePart' in locals() and ConvectivePart != None:
    MiscGain.Convaux         = ConvectivePart
    MiscGain.Convective = 'INPUT {0}*{1}'.format(round(MiscGain.Convaux,2) , 'Q_ADDON_KJ')
    MiscGain.Radiative = 'INPUT {0}*{1}'.format(round((1-MiscGain.Convaux),2) , 'Q_ADDON_KJ')
# Special setting for simplified
OutsideAreaFactor = ThermalBridgeFactor
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
class HEATING:
    def __init__(self):
        self.Name           = ''
        self.Settemperature = 20
        self.Schedule       = ''
        self.Maxpower       = 200
        self.Heating        = 1
        self.Humidity       = 0
        self.On             = ''
        self.Power          = 'INPUT 1*HT_BUI'
        self.Type           = 'heating'
        self.Setback        = 0
        self.Tamb24hon      = 20
        self.Ctrl           = 'OPERATIVE'
        self.Space          = None
        self.Area_related_power = 1
        self.Elpowerfrac    = 0
        self.Rrad           = 0
# Special setting for simplified
SetTemperature = SetpointHeating
Schedule = NameOccupationSchedule
# Read Class Gain
Heating = HEATING()
#Initial Settings
Heating.Name        = "HEAT"
Heating.On          = 'INPUT 1*TAIR_SET_HT'
Heating.Maxpower    = 200
Heating.Settemperature = 20
Heating.Setback     = 0
Heating.Tamb24hon   = 20
#Input Depending Settings
if 'MaxSpecHeatPower' in locals() and MaxSpecHeatPower != None:
    Heating.Maxpower = MaxSpecHeatPower
if 'ControlledTemperature' in locals() and ControlledTemperature != None:
    Heating.Ctrl = ControlledTemperature
if 'MinRelHum' in locals() and MinRelHum != None:
    Heating.Humidity = MinRelHum
if 'SetTemperature' in locals() and SetTemperature != None:
    Heating.Settemperature = SetTemperature
if 'NightSetBack' in locals() and NightSetBack != None:
    Heating.Setback = NightSetBack
if 'OnTairOutside24hBelow' in locals() and OnTairOutside24hBelow != None:
    Heating.Tamb24hon = OnTairOutside24hBelow
if 'Schedule' in locals() and Schedule != None:
    Heating.Schedule = Schedule.upper()
else:
    Heating.On = SetTemperature
# Special setting for simplified
SetTemperature = SetpointCooling
Schedule = NameOccupationSchedule
class COOLING:
    def __init__(self):
        self.Name           = 'COOL'
        self.Settemperature = 26
        self.Schedule       = ''
        self.Maxpower       = 100
        self.Cooling        = 1
        self.Humidity       = 100
        self.On             = ''
        self.Power          = 'INPUT 1*CL_BUI'
        self.Type           = 'cooling'
        self.Setback        = 0
        self.Ctrl           = 'OPERATIVE'
        self.Tamb24hon      = 26
        self.Space          = None
        self.Area_related_power = 1
        self.Elpowerfrac    = 0
# Read Class Gain
Cooling = COOLING()
#Initial Settings
Cooling.Name        = "COOL"
Cooling.On          = 'INPUT 1*TAIR_SET_CL'
Cooling.Maxpower    = 0
Cooling.Settemperature = 26
Cooling.Setback     = 0
Cooling.Tamb24hon   = 12
#Input Depending Settings
if 'MaxSpecCoolPower' in locals() and MaxSpecCoolPower != None:
    Cooling.Maxpower = MaxSpecCoolPower
if 'ControlledTemperature' in locals() and ControlledTemperature != None:
    Cooling.Ctrl = ControlledTemperature
if 'MaxRelHum' in locals() and MaxRelHum != None:
    Cooling.Humidity = MaxRelHum
if 'SetTemperature' in locals() and SetTemperature != None:
    Cooling.Settemperature = SetTemperature
if 'NightSetUp' in locals() and NightSetUp != None:
    Cooling.Setback = NightSetUp
if 'OnTairOutside24hAbove' in locals() and OnTairOutside24hAbove != None:
    Cooling.Tamb24hon = OnTairOutside24hAbove
if 'Schedule' in locals() and Schedule != None:
    Cooling.Schedule = Schedule.upper()
else:
    Cooling.On = SetTemperature
class REGIME:
    def __init__(self):
        self.Persgain       = ""
        self.Compgain       = ""
        self.Lightgain      = ""
        self.Othergain      = ""
        self.Udefgain       = ""
        self.Thbgain        = ""
        self.Heating        = ""
        self.Domestic       = ""
        self.Cooling        = ""
        self.Infiltration   = ""
        self.Mechvent       = ""
        self.Earthduct      = ""
        self.Stvent1        = ""
        self.Stvent2        = ""
        self.Pmvcomfort     = ""
        self.Setcomfort     = ""
Regime = REGIME()
if 'PeopleGain' in locals():
    if PeopleGain is not None:
        Regime.Persgain = PeopleGain
"""
if 'EquipmentGain' in locals():
    if EquipmentGain is not None:
        Regime.Compgain = EquipmentGain
if 'LightGain' in locals():
    if LightGain is not None:
        Regime.Lightgain = LightGain
"""
if 'MiscGain' in locals():
    if MiscGain is not None:
        Regime.Othergain = MiscGain
if 'ThbGain' in locals():
    if ThbGain is not None:
        Regime.Thbgain = ThbGain
if 'Heating' in locals():
    if Heating is not None:
        Regime.Heating = Heating
"""
if 'Dhw' in locals():
    if Dhw is not None:
        Regime.Domestic = Dhw
if 'Cooling' in locals():
    if Cooling is not None:
        Regime.Cooling = Cooling
"""
if 'Infiltration' in locals():
    if Infiltration is not None:
        Regime.Infiltration = Infiltration
if 'MechanicalVentilation' in locals():
    if MechanicalVentilation is not None:
        Regime.Mechvent = MechanicalVentilation
"""
if 'EarthDuct' in locals():
    if EarthDuct is not None:
        Regime.Earthduct = EarthDuct
"""
if 'StackVentilation1' in locals():
    if StackVentilation1 is not None:
        Regime.Stvent1 = StackVentilation1
if 'StackVentilation2' in locals():
    if StackVentilation2 is not None:
        Regime.Stvent2 = StackVentilation2
"""
if 'Comfort' in locals():
    if Comfort is not None:
        Regime.Pmvcomfort = Comfort
"""
