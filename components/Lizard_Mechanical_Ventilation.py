"""
Define properties of mechanical ventilation system.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    ------- Hybr.Ventilation
    Mode (object): Script variable Mechanical Ventilation
        Access: item
        Required: True
    ACH (object): air changes per hour driven by mechanical ventilation
        Access: item
        Required: True
    OrAbsoluteVolumeFlow (object): optional you can define the volume flow instead of ACH
        Access: item
        Required: False
    OrPersonRelatedVolumeFlow (object): in m?/(h.Person), persons are defined in the zone component
        Access: item
        Required: True
    MinACH (object): min. air changes for 24/7
        Access: item
        Required: True
    ScheduleACH (object): define the schedule when ACH definitions for ventilation rates are to be applied
        Access: item
        Required: True
    ScheduleOcc (object): define the schedule when OCC definitions for temperatures are to be applied
        Access: item
        Required: True
    -------- MechanicalVentilation
    SupplyTempWinterOcc (object): Supply temperature in occupied hours
        Access: item
        Required: True
    SupplyTempWinterUnocc (object): Supply temperature in unoccupied hours
        Access: item
        Required: True
    MinSupplyAirHumidity (object): to set minimum humidity level of supply air in winter
        Access: item
        Required: True
    SupplyTempSummerOcc (object): Supply temperature in occupied hours
        Access: item
        Required: True
    SupplyTempSummerUnocc (object): Supply temperature in unoccupied hours
        Access: item
        Required: True
    MaxSupplyAirHumidity (object): to set maximum humidity level of supply air in summer
        Access: item
        Required: True
    SensibleHeatRecovery (object): Sensible Heat recovery efficiency in %/100
        Access: item
        Required: True
    LatentHeatRecovery (object): Latent Heat recovery efficiency in %/100
        Access: item
        Required: True
    SpecFanPower (object): Script input spec_fan_power.
        Access: item
        Required: True
    -------- NaturalVentilation
    Activated (object): Use hybrid ventilation
        Access: item
        Required: True
    NaturalIfTairOutsideAbove (object): in natural mode if ambient temperature is above this value
        Access: item
        Required: True
    NaturalIfTairOutsideBelow (object): in natural mode if ambient temperature is below this value
        Access: item
        Required: True
    -------------------- Additional
    RefTempSeason (object): define which temperature is used to determine the seasonal operation between summer and winter
        Access: item
        Required: True
    SummerRefTempSeasonAbove (object): setpoint temperature above that summer operation mode is active
        Access: item
        Required: True
    ActivateWinterReduction (object): Use reduced ventilation rates in winter
        Access: item
        Required: True
    WinterFraction (object): Define the fraction of winter ventilation
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    Ventilation (object): connect to ventilation input in Thermal Zone component / - / HINT:Press shift key when connecting  / multiple outputs to one input node
        Access: item
"""
version = '2.3.1'
ghenv.Component.Name = "Lizard_Mechanical_Ventilation"
ghenv.Component.NickName = 'Mechanical Ventilation'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Regime"
import scriptcontext as sc
import Grasshopper.Kernel as gh
w = gh.GH_RuntimeMessageLevel.Warning
err = gh.GH_RuntimeMessageLevel.Error
warn = '*** Warning *** '
#Additional Inputs
OutsideTemp = None #this Input is only having an impact in AHU mode
OutsideHumidity = None #this Input is only having an impact in AHU mode
HumidityControl = 0
class VENTILATION:
    def __init__(self):
        self.Name           = 'VENT'
        self.Type           = 'VENTILATION'
        self.Class = "Ventilation"
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
        self.Maxach         = 0
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
        self.Thyblow        = 10
        self.Thybhigh       = 26
        self.Tsuplow        = 21
        self.Tsuphigh       = 24
        self.Winterred      = 0
        self.Winterfract    = 0.5
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
        self.Reftemp = None
        self.Adiabatic = 0 #0/1 means ON/OFF
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
MechanicalVentilation             =  VENTILATION()
MechanicalVentilation.Name        = 'VENT'
MechanicalVentilation.Temperature= 'INPUT 1*TSUP'
MechanicalVentilation.Airchange  = 'INPUT 1*ACR_AHU'
MechanicalVentilation.Humidity   = 'INPUT 1*ABSHUM_SUP'
MechanicalVentilation.Absminhum   = 'INPUT 1*ABSHUM_SUP'
MechanicalVentilation.Absmaxhum   = 'INPUT 1*ABSHUM_SUP'
if 'Mode' in locals() and Mode != None:
    MechanicalVentilation.Calcmode = Mode
if 'NaturalIfTairOutsideAbove' in locals() and NaturalIfTairOutsideAbove != None:
    MechanicalVentilation.Thyblow    = NaturalIfTairOutsideAbove
if 'NaturalIfTairOutsideBelow' in locals() and NaturalIfTairOutsideBelow != None:
    MechanicalVentilation.Thybhigh   = NaturalIfTairOutsideBelow
if 'SetTemperatureCooling' in locals() and SetTemperatureCooling != None:
    MechanicalVentilation.Tsuphigh    = SetTemperatureCooling
if 'SetTemperatureHeating' in locals() and SetTemperatureHeating != None:
    MechanicalVentilation.Tsuplow   = SetTemperatureHeating
if 'ActivateWinterReduction50P' in locals() and ActivateWinterReduction50P != None:
    MechanicalVentilation.Winterred  = ActivateWinterReduction50P
if 'ActivateWinterReduction' in locals() and ActivateWinterReduction != None:
    MechanicalVentilation.Winterred  = ActivateWinterReduction
if 'WinterFraction' in locals() and WinterFraction != None:
    MechanicalVentilation.Winterfract  = WinterFraction
if 'ScheduleACH' in locals() and ScheduleACH != None:
    MechanicalVentilation.Schedule  = ScheduleACH
if 'ScheduleOcc' in locals() and ScheduleOcc != None:
    MechanicalVentilation.Schedule2 = ScheduleOcc
if 'ACH' in locals() and ACH != None:
    MechanicalVentilation.Ach = ACH
if 'MinACH' in locals() and MinACH != None:
    MechanicalVentilation.Achmin = MinACH
if 'MaxACH' in locals() and MaxACH != None:
    MechanicalVentilation.Maxach = MaxACH
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
if 'SummerRefTempSeasonAbove' in locals() and SummerRefTempSeasonAbove != None:
    MechanicalVentilation.Tamb24hcl = SummerRefTempSeasonAbove
if 'RefTempSeason' in locals() and RefTempSeason != None:
    MechanicalVentilation.Reftemp = RefTempSeason
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
if 'OutsideTempNatural' in locals() and OutsideTempNatural != None:
    MechanicalVentilation.Toutside = OutsideTempNatural
if 'OutsideHumidityNatural' in locals() and OutsideHumidityNatural != None:
    MechanicalVentilation.Humoutside = OutsideHumidityNatural
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
if 'HumidityControl'  in locals() and HumidityControl != None:
    MechanicalVentilation.Humctrl  = HumidityControl
Ventilation =  MechanicalVentilation

#Integration of dict storage for json output
dck = dict()
dck['EQU'] = dict()
dck['EQU']['Ventilation'] = dict()
dck['EQU']['Ventilation']['AirChangeRate'] = 'max(%s, %s/AirnodeVolume, %s*NumberOfPerson/AirnodeVolume)'%(ACH, OrAbsoluteVolumeFlow, OrPersonRelatedVolumeFlow)
dck['EQU']['Ventilation']['MinimumAirChangeRate'] = MinACH
dck['EQU']['Ventilation']['WeeklySchedule'] = ScheduleACH 
dck['EQU']['Ventilation']['MinimumSupplyTemperatureMechanical'] = SupplyTempWinterOcc
dck['EQU']['Ventilation']['MaximumSupplyTemperatureMechanical'] = SupplyTempSummerOcc
dck['EQU']['Ventilation']['MinimumSupplyHumidityMechanical'] = MinSupplyAirHumidity
dck['EQU']['Ventilation']['MaximumSupplyHumidityMechanical'] = MaxSupplyAirHumidity
dck['EQU']['Ventilation']['SensibleHeatRecoveryMechanical'] = SensibleHeatRecovery
dck['EQU']['Ventilation']['LatentHeatRecoveryMechanical'] = LatentHeatRecovery
dck['EQU']['Ventilation']['SpecificFanPowerMechanical'] = SpecFanPower
dck['EQU']['Ventilation']['HybridModeSwitch'] = Activated
dck['EQU']['Ventilation']['NaturalActiveAboveOutsideAirTemperature'] = NaturalIfTairOutsideAbove
dck['EQU']['Ventilation']['NaturalActiveBelowOutsideAirTemperature'] = NaturalIfTairOutsideBelow

dck['TYPES'] = dict()
Ventilation.Json   = dck


switchcomp = locals()
if '------- Hybr.Ventilation' in locals() and '------- Hybr.Ventilation' is not None and switchcomp['------- Hybr.Ventilation'] == False:
    Ventilation = None
    MechanicalVentilation = None
if '------- Mech.Ventilation' in locals() and '------- Mech.Ventilation' is not None and switchcomp['------- Mech.Ventilation'] == False:
    Ventilation = None
    MechanicalVentilation = None
