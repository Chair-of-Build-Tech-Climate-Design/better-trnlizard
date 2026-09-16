"""
Define parameters of the building's window surface.
-
TRNLizard
Copyright (c) 2017 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    -------------- Window
    Name (object): define window type (no blanks or special signs)
        Access: item
        Required: True
    WinID (object): define the window library ID number (refer to Window Type Library)
        Access: item
        Required: True
    ---------------- Frame
    FrameFraction (object): fraction of frame to window area in %
        Access: item
        Required: True
    FrameConduction (object): u-value of frame in W/(m?.K)
        Access: item
        Required: True
    -------------- Shading
    ShadingMovable (object): define a shading type: outside (OUT), inside (INT), outside + inside (IOT), no (NON)
        Access: item
        Required: True
    ShadingFractionExt (object): 0 = no shading (fully transparent) 100 = fully shaded (opaque) in %
        Access: item
        Required: True
    ShadingFractionInt (object): Script variable Window
        Access: item
        Required: True
    ShadingActive (object): when irradiation levels exceed this value in W/m?, shading is used/on
        Access: item
        Required: True
    ShadingNonActive (object): when irradiation levels drop below this value in W/m?, shading is not used/off
        Access: item
        Required: True
    ActiveIfTairRoomAbove (object): it is active if room temperature is above the set value in ?C
        Access: item
        Required: True
    --------------- Glazing
    Hinside (object): define the heat exchange inside in kJ/(h.m?)
        Access: item
        Required: True
    Houtside (object): define the heat exchange outside in kJ/(h.m?)
        Access: item
        Required: True
    ------------- Daylight
    RadMaterial0 (object): window radiance material when shading is open, for daylight simulation
        Access: item
        Required: True
    RadMaterial1 (object): window radiance material when shading is fully closed, for daylight simulation
        Access: item
        Required: True
    ShadingGroup (object): Script variable Window
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    Settings (object): connect to corresponding window surface
        Access: item
"""

version='2.0.1'


if 'Trnflow' in locals():
    pass
else:
    Trnflow = None #define as single object input

class WindowDefinition:
    def __init__(self):
        self.Type = 'WINDOW'
        self.Name = Name
        self.Winid = WinID
        self.Construction = 'WIN_' + str(self.Name) + '_' + str(self.Winid)
        self.Windows = 1
        self.Framefrac = FrameFraction/100
        self.Uframe = FrameConduction
        self.Cframe = round(1/(1/self.Uframe - 0.17)*3.6,2)
        self.Mshade = ShadingMovable #Options are OUT, INT, IOT, NON  
        self.Mshadeglazingcover = ShadingFractionExt/100
        self.Ishadeglazingcover = ShadingFractionInt/100
        self.Eshadeglazingcover = ShadingFractionExt/100
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
        self.BSDFWindows = 0
        self.Fixshade = 0
        self.Shdinput = None
    def __repr__(self):
        """Class representation."""
        return "{}".format('Settings:Window')

Settings = WindowDefinition()
