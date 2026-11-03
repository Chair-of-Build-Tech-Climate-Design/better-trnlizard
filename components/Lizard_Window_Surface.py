"""
Define parameters of the building's window surface.
-
TRNLizard
Copyright (c) 2017 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    BRep (Brep): set window surface(s) in Rhino (right click brep)
        Access: list
        Required: True
    Settings (object): Script variable Window
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    SurfaceInfo (object): connect to corresponding airnode
        Access: item
"""
version='2.0.1'


import scriptcontext as sc
import Grasshopper.Kernel as gh

#standard ID assignment
BRep = sc.sticky[sc.doc.Path]["CONSTRUCTION"]().addToConstruction(BRep,ghenv.Component.InstanceGuid.ToString())

class Surface:
    def __init__(self):
        self.Type = 'WINDOW'
        self.Name = 'W1'
        self.Winid = 3213
        self.Construction = 'WIN_' + str(self.Name) + '_' + str(self.Winid)
        self.Windows = 1
        self.Framefrac = 0.2
        self.Uframe = 1.5
        self.Cframe = round(1/(1/self.Uframe - 0.17)*3.6,2)
        self.Mshade = 'OUT' #Options are OUT, INT, IOT, NON  
        self.Mshadeglazingcover = 0.8
        self.Ishadeglazingcover = 0.7
        self.Eshadeglazingcover = 0.8
        self.Shadeopen  = 150*3.6
        self.Shadeclose = 180*3.6
        self.Shdtairabove = 18
        self.Hinside = 11
        self.Houtside = 64
        self.Spacid = 4
        self.Wwid = 1.4
        self.Wheig = 1.8
        self.Radmaterial0 = 'glass_78'
        self.Radmaterial1 = 'glass_15'
        self.Sgroup = 'A'
        self.Trnflow = ''
        self.Uglas = None
        self.Tvis = None
        self.Shgc = None

w = gh.GH_RuntimeMessageLevel.Warning
err = gh.GH_RuntimeMessageLevel.Error



if 'Settings' in locals() and Settings:
    surface = Settings
else:
    surface = Surface()

#sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstructionNew(BRep,surface)
#SurfaceInfo = BRep




library = sc.sticky[sc.doc.Path]["library"]
found = 0
for witem in library.Windows:
    if int(surface.Winid) == int(witem.Name) or surface.Construction == "Virtual":
        found = 1
        surface.Shgc = witem.Shgc
        surface.Uglas = witem.Uglas
        surface.Tvis = witem.Tvis
    if surface.BSDFWindows == 1:
        found = 1


if found == 0:
    SurfaceInfo = None
    ghenv.Component.AddRuntimeMessage(err, "WindowID not found in the library!")
    ghenv.Component.Message = 'WindowID not found in the library!'
else:
    #lizard_coll = sc.sticky[sc.doc.Path]["CONSTRUCTION"]()
    #ObjectsFromLz = lizard_coll.callFromConstruction(BRep)
    #for item in ObjectsFromLz:
    try:
        absvis = int(float(surface.Tvis) * 100)
        if surface.Radmaterial0:
            pass
        else:
            surface.Radmaterial0 = 'glass_%02d'%(absvis)
        if surface.Radmaterial1:
            pass
        else:
            if surface.Mshade == "NON":
                surface.Radmaterial1 = surface.Radmaterial0
            else:
                surface.Radmaterial1 = 'glass_%02d'%(absvis*(1-min(surface.Ishadeglazingcover,surface.Eshadeglazingcover)))
        ghenv.Component.Message = '%s\nUglas = %s W/(m?.K)\nSHGC = %s\n'%(surface.Construction,surface.Uglas,surface.Shgc)
    except:
        ghenv.Component.Message = '%s\n%s'%('WINDOW',surface.Construction)
    sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstructionNew(BRep,surface)
    sc.sticky[sc.doc.Path]["CONSTRUCTION"]().getWallThickness(BRep)
    SurfaceInfo = BRep

