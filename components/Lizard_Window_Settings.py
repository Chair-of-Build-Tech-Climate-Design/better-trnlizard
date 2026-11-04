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
    Name (str): define window type (no blanks or special signs)
        Access: item
        Required: False
    WinID (int): define the window library ID number (refer to Window Type Library)
        Access: item
        Required: True
    ---------------- Frame
    FrameFraction (float): fraction of frame to window area in %
        Access: item
        Required: True
    FrameConduction (float): u-value of frame in W/(m?.K)
        Access: item
        Required: True
    -------------- Shading
    ShadingMovable (str): define a shading type: outside (OUT), inside (INT), outside + inside (IOT), no (NON)
        Access: item
        Required: False
        Options: OUT, INT, IOT, NON
    ShadingFractionExt (float): 0 = no shading (fully transparent) 100 = fully shaded (opaque) in %
        Access: item
        Required: True
    ShadingFractionInt (float): Script variable Window
        Access: item
        Required: True
    ShadingActive (float): when irradiation levels exceed this value in W/m?, shading is used/on
        Access: item
        Required: True
    ShadingNonActive (float): when irradiation levels drop below this value in W/m?, shading is not used/off
        Access: item
        Required: True
    ActiveIfTairRoomAbove (float): it is active if room temperature is above the set value in ?C
        Access: item
        Required: True
    --------------- Glazing
    Hinside (float): define the heat exchange inside in kJ/(h.m?)
        Access: item
        Required: True
    Houtside (float): define the heat exchange outside in kJ/(h.m?)
        Access: item
        Required: True
    ------------- Daylight
    RadMaterial0 (str): window radiance material when shading is open, for daylight simulation
        Access: item
        Required: False
    RadMaterial1 (str): window radiance material when shading is fully closed, for daylight simulation
        Access: item
        Required: False
    ShadingGroup (str): Script variable Window
        Access: item
        Required: False

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
        self.Winid = int(WinID)
        self.Construction = 'WIN_' + str(self.Name) + '_' + str(self.Winid)
        self.Windows = 1
        self.Framefrac = float(FrameFraction)/100
        self.Uframe = float(FrameConduction)
        self.Cframe = round(1/(1/self.Uframe - 0.17)*3.6,2)
        self.Mshade = ShadingMovable #Options are OUT, INT, IOT, NON  
        self.Mshadeglazingcover = float(ShadingFractionExt)/100
        self.Ishadeglazingcover = float(ShadingFractionInt)/100
        self.Eshadeglazingcover = float(ShadingFractionExt)/100
        self.Shadeopen  = float(ShadingNonActive)*3.6
        self.Shadeclose = float(ShadingActive)*3.6
        self.Shdtairabove = float(ActiveIfTairRoomAbove)
        self.Hinside = float(Hinside)
        self.Houtside = float(Houtside)
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
