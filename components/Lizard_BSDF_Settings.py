"""
Define parameters of the building's window surface.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    -------------- Window
    Name (object): define window type (no blanks or special signs)
        Access: item
        Required: False
    -------------- Shading
    ShadingActive (object): when irradiation levels exceed this value in W/m², shading is used/on
        Access: item
        Required: False
    ShadingNonActive (object): when irradiation levels drop below this value in W/m², shading is not used/off
        Access: item
        Required: False
    ActiveIfTairRoomAbove (object): it is active if room temperature is above the set value in °C
        Access: item
        Required: False
    --------------- Glazing
    Hinside (object): define the heat exchange inside in kJ/(h.m²)
        Access: item
        Required: False
    Houtside (object): define the heat exchange outside in kJ/(h.m²)
        Access: item
        Required: False
    ------------- Daylight
    RadMaterial0 (object): window radiance material when shading is open, for daylight simulation
        Access: item
        Required: False
    RadMaterial1 (object): window radiance material when shading is fully closed, for daylight simulation
        Access: item
        Required: False
    ShadingGroup (object): Script variable Window
        Access: item
        Required: False
    ----------------- BSDF
    ShdControl (object): Script variable Window
        Access: item
        Required: False
    ShdConfId (int): Script variable Window
        Access: item
        Required: False
    DataFile (str): Script variable Window
        Access: item
        Required: False
    GapToVentilate (int): Script variable Window
        Access: item
        Required: False
    GapVentMode (str): Script variable Window
        Access: item
        Required: False
    Aopen (object): Script variable Window
        Access: item
        Required: False
    TsupPermanent (object): Script variable Window
        Access: item
        Required: False
    MflowPermanent (object): Script variable Window
        Access: item
        Required: False

Returns:
    Settings (object): connect to corresponding window surface - HINT:Press shift key when connecting multiple outputs to one input node
        Access: item
"""
import re
import Grasshopper.Kernel as gh
w       = gh.GH_RuntimeMessageLevel.Warning
err     = gh.GH_RuntimeMessageLevel.Error
warn    = '*** Warning *** '
Trnflow = None #define as single object input
class WindowDefinition:
    def __init__(self):
        self.Type = 'WINDOW'
        self.Name = Name
        self.Winid = ''
        self.Construction = 'WIN_BSDF_' + str(self.Name) + '_' + str(self.Winid)
        self.Windows = ''
        #self.Framefrac = FrameFraction/100
        #self.Uframe = FrameConduction
        #self.Cframe = round(1/(1/self.Uframe - 0.17)*3.6,2)
        self.Mshade = ShdControl
        #self.Mshadeglazingcover = ShadingFractionExt/100
        #self.Ishadeglazingcover = ShadingFractionInt/100
        #self.Eshadeglazingcover = ShadingFractionExt/100
        self.Shadeopen  = ShadingNonActive*3.6
        self.Shadeclose = ShadingActive*3.6
        self.Shdtairabove = ActiveIfTairRoomAbove
        self.Hinside = Hinside
        self.Houtside = Houtside
        self.Spacid = 4
        self.Wwid = 1.4
        self.Wheig = 1.8
        self.Radmaterial0 = RadMaterial0
        self.Radmaterial1 = RadMaterial1
        self.Sgroup = ShadingGroup
        self.Trnflow = Trnflow
        self.BSDFWindows = 1
        self.Configids = ''
        self.Fname_bsdf1 = DataFile.split(':')[0].encode('string-escape')
        self.Fname_bsdf2 = DataFile.split(':')[1].encode('string-escape')
        self.Cshade = ShdConfId
        self.Gapvent1 = 0
        self.Gapmflow1 = 0
        self.Gapintemp1 = 18
        self.Gapventmode = GapVentMode #'STACK'
        self.Gapvolume = 2
        self.Gapeffopeningtop = Aopen
        self.Gapeffopeningbot = Aopen
        self.Gapheightdiffopen = 1
        self.Tsupgap = TsupPermanent
        self.Mflowperm  = MflowPermanent
    def readDatFile(self):
        file = open(DataFile)
        content = file.readlines()
        first = 1
        for i in range(0,100):
            if not re.match('^\s',content[i]) and not re.match('^!',content[i]):
                if i == 1:
                    self.Winid = content[i].split(',')[0]
                if i > 2 and first == 1:
                    print content[i].rstrip()
                    self.Baseconfigid = content[i].split(',')[0]
                    first = 0
                    continue
                if i > 2:
                    print content[i].rstrip()
                    self.Configids += '{0},'.format(content[i].split(',')[0])
            if re.match('^\s',content[i]):
                break
        file.close()
        self.Construction = 'WIN_BSDF_' + str(self.Name) + '_' + str(self.Winid)
    def modeInputs(self):
        if self.Gapventmode == 'STACK':
            self.Gapmflow1 = 'INPUT 1*MFLOW%s_'%GapToVentilate
            self.Gapintemp1 = 'INPUT 1*TAMB'
            self.Gapvent1 = GapToVentilate
        elif self.Gapventmode == 'PERMANENT':
            self.Gapmflow1 = 'INPUT 1*MFLOW%s_'%GapToVentilate
            self.Gapintemp1 = 'INPUT 1*TSUP%s_'%GapToVentilate
            self.Gapvent1 = GapToVentilate
    def __repr__(self):
        """Class representation."""
        return "{}".format('Settings:BSDFWindow')
Settings = WindowDefinition()
Settings.readDatFile()
Settings.modeInputs()
if Settings.Mshade == 'BSDFCOMPLEX':
    message = "New building input is generated with the name YSHDB_S followed by the surface ID.\n Please define an additional equation to the system component in order to generate the switch!"
    ghenv.Component.AddRuntimeMessage(w, message)
