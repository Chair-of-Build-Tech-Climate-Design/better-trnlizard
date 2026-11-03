"""
This component allows you to generate window surface on your wall, based on WWR
-
TRNLizard v.1.1.0
Copyright (c) 2017 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    WinWallRatio (object): Window to Wall Ratio
        Access: item
        Required: True
    Thickness (object): Script input Thickness.
        Access: item
        Required: True
    Wall (Brep): Input wall geometry which has window
        Access: item
        Required: True

Returns:
    out (object): The execution information, as output and error streams
        Access: item
    Shading (object): Shelf-shading effect by the wall thickness
        Access: item
    Windows (object): Windows geometry
        Access: item
"""

import Grasshopper.Kernel as gk
import Rhino as rc
import rhinoscriptsyntax as rs

version='2.0.2'
ghenv.Component.Name = "Lizard_Window_Scale"
ghenv.Component.NickName = 'Window_Scale'
ghenv.Component.Message = 'VER 1.1.0\nFEB_2018'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Components"


Windows = []
Shading = []

#for wall in External_walls:
wall = Wall
Wall_thickness = Thickness
if 1> 0:
    #Create new windows based on scaling factor
    wall_area = rc.Geometry.Brep.GetArea(wall)
    win_area = wall_area*WinWallRatio
    factor = (win_area/wall_area)**0.5
    wall_centroid = rc.Geometry.AreaMassProperties.Compute(wall).Centroid
    scale_win = rc.Geometry.Transform.Scale(wall_centroid,factor)
    window = wall.DuplicateBrep()
    window.Transform(scale_win)
    Windows.append(window)

    #Extrude window
    win_normal = window.Faces[0].NormalAt(0,0)
    vec = win_normal*Wall_thickness

    #Extrude Window Curve
    curvs = rc.Geometry.Brep.DuplicateEdgeCurves(window)
    for crv in curvs:
        extrusion = rc.Geometry.Extrusion.CreateExtrusion(crv, vec)
        Shading.append(extrusion)


