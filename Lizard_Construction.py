"""
Define a new construction composition.
-
TRNLizard 
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    Name (object): construction name
        Access: item
        Required: True
    Layer (object): define the construction layers starting from interior to exterior
        Access: item
        Required: True
    Abs_Front (object): define solar absorptance at front side [%/100]
        Access: item
        Required: True
    Abs_Back (object): define solar absorptance at back side [%/100]
        Access: item
        Required: True
    H_Front (object): define convective heat exchange coefficient at front side [kJ/(h.m2.K)]
        Access: item
        Required: True
    H_Back (object): define convective heat exchange coefficient at back side [kJ/(h.m2.K)]
        Access: item
        Required: True

Returns:
    out (object): The execution information, as output and error streams
        Access: item
    Construction (object): link to the library component
        Access: item
"""
version = '2.3.1'
ghenv.Component.Name        = "Lizard_Construction"
ghenv.Component.NickName    = 'Construction'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category    = "Lizard"
ghenv.Component.SubCategory = "2 | Construction"
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import Grasshopper.Kernel as gh
w = gh.GH_RuntimeMessageLevel.Warning
err = gh.GH_RuntimeMessageLevel.Error
error = 0
class Wall:
    def __init__(self):
        self.Name = Name
        self.Layers = ''
        self.Wall = 1
        self.Thickness   = ''
        self.Abs_front   = 0.6
        self.Abs_back    = 0.6
        self.Eps_front   = 0.9
        self.Eps_back    = 0.9
        self.Hfront      = 11
        self.Hback       = 64
        self.Uvalue      = 0
Construction = Wall()
layers = []
thickness = []
dummy_layer = Layer.split()
#print dummy_layer
for item in dummy_layer:
    layers.append(item.split(';')[0])
    Construction.Layers    = Construction.Layers    + ' {0:12s}'.format(layers[-1])
    thickness.append(item.split(';')[1])
    Construction.Thickness = Construction.Thickness + ' {0:<12.6}'.format(thickness[-1])
if Abs_Front:
    Construction.Abs_front = Abs_Front
if Abs_Back:
    Construction.Abs_back  = Abs_Back
if H_Front:
    Construction.Hfront = H_Front
if H_Back:
    Construction.Hback  = H_Back
info_not_found  = 0
u_value         = 0
s_l             = 0
a_i             = 7.7 #standard interior heat exchange coefficient 7.7 W/m?K
a_o             = 25  #standard exterior heat exchange coefficient 25 W/m?K
foundal = 0
for item in range(len(layers)):
    if (layers[item] in sc.sticky['LAYER'].keys()):
        if sc.sticky['LAYER'][layers[item]].Conductivity != '':
            s_l += float(thickness[item])*3.6/sc.sticky['LAYER'][layers[item]].Conductivity
        if sc.sticky['LAYER'][layers[item]].Resistance != '':
            if float(thickness[item]) > 0:
                error = 1
                ghenv.Component.AddRuntimeMessage(err, "Resistance Layers must have a thickness of zero!")
                print "Resistance Layers must have a thickness of zero!"
            s_l += 3.6*sc.sticky['LAYER'][layers[item]].Resistance
        if sc.sticky['LAYER'][layers[item]].Pdiameter != '':
            print 'Active layer included!'
            #print sc.sticky['LAYER'][layers[item]].Usagetype
            foundal = 1
            ActiveLayer = sc.sticky['LAYER'][layers[item]]
            ActLPos = item
            pass
    else:
        print 'Note: Layer Info not found for {0}'.format(layers[item])
        info_not_found = 1
if info_not_found == 0:
    u_value =  1 / (1 / a_i + s_l + 1 / a_o)
    Construction.Uvalue = u_value
    print 'U-Value: {0:.3f} W/(m2.K)'.format( u_value )
def checkWall(ActiveLayer,Layernames, AlPos):
    errorfound = 0
    diameterrho = float(ActiveLayer.Pdiameter)
    spacing = float(ActiveLayer.Pspacing)
    overlap = float(Construction.Thickness.split()[AlPos-1])
    backthickness = float(Construction.Thickness.split()[AlPos+1])
    lambdains = sc.sticky['LAYER'][Layernames[AlPos+2]].Conductivity
    insthickness = float(Construction.Thickness.split()[AlPos+2])
    radheat = 0
    capheat = 0
    floheat = 0
    if diameterrho/spacing < 0.2:
        if overlap/spacing > 0.3 and backthickness/spacing > 0.3:
            if spacing >= 5.8*diameterrho:
                radheat = 1
            if spacing < 5.8*diameterrho:
                capheat = 1
    alpha2 = float(lambdains) / float(insthickness) / 3.6
    if spacing >= 5.8*diameterrho:
        if alpha2 < 1.212:
            if diameterrho/2 < backthickness:
                if overlap/spacing >= 0.3:
                    floheat = 1
    if ActiveLayer.Usagetype == "FLOOR":
        if floheat == 0:
            errorfound = 1
            ghenv.Component.AddRuntimeMessage(err, "Floor heating definition in the Construction is not correct!")
            print "Floor heating definition in the Construction is not correct!"
    if ActiveLayer.Usagetype == "SLAB":
        if radheat == 0:
            errorfound = 1
            ghenv.Component.AddRuntimeMessage(err, "Slab heating definition in the Construction is not correct!")
            print "Slab heating definition in the Construction is not correct!"
    if ActiveLayer.Usagetype == "CAPILLARY":
        if capheat == 0:
            errorfound = 1
            ghenv.Component.AddRuntimeMessage(err, "Capillary heating definition in the Construction is not correct!")
            print "Capillary heating definition in the Construction is not correct!"
    return errorfound
if foundal == 1:
    error = checkWall(ActiveLayer, layers, ActLPos)
if error == 1:
    Construction = None


