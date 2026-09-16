"""
This is the key component to store model information
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    _Box (object): input box geometry
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    Orientation (object): orientations of different surfaces
        Access: item
    Surfaces (object): list of seperated surfaces
        Access: item
    SouthWall (object): wall surface on the South side
        Access: item
    WestWall (object): wall surface on the West side
        Access: item
    NorthWall (object): wall surface on the North side
        Access: item
    EastWall (object): wall surface on the East side
        Access: item
    Floor (object): floor surface
        Access: item
    Ceiling (object): ceiling surface
        Access: item
"""
import scriptcontext as sc
import Rhino as rc
import math
import rhinoscriptsyntax as rs
version='2.2.1'
ghenv.Component.Name = "Lizard_Deconstruct"
ghenv.Component.NickName = 'Deconstruct'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Components"
# Surface orientations are defined according to their azimuth and slope
def getOrientation( vector ):
    azimuth = 0
    slope = 0
    slope_vector = rc.Geometry.Vector3d(0,0,1)
    ori_point = rc.Geometry.Point3d(0,0,0)
    oriprefix = ''
    facenormal = vector
    plane = rc.Geometry.Plane(ori_point,facenormal,slope_vector)
    slope_rad = rc.Geometry.Vector3d.VectorAngle(facenormal,slope_vector,plane)
    slope_deg = slope_rad * 180/math.pi
    slope = int(slope_deg)
    if slope == 180:
        azimuth     =  0
        oriprefix   = 'H'
    elif slope == 0:
        azimuth     =  0
        oriprefix   = 'H'
    else:
        azimuth_vector = rc.Geometry.Vector3d(0,-1,0)
        plane = rc.Geometry.Plane(ori_point,slope_vector)
        azimuth_rad = rc.Geometry.Vector3d.VectorAngle(facenormal,azimuth_vector,plane)
        azimuth_deg = azimuth_rad * 180/math.pi
        azimuth = int(azimuth_deg)
        if azimuth   < 45    or azimuth >=315: oriprefix = 'S'
        elif azimuth >= 45   and azimuth <135: oriprefix = 'W'
        elif azimuth >= 135 and azimuth  <225: oriprefix = 'N'
        elif azimuth >= 225  and azimuth <315: oriprefix = 'E'
    fmtString = "%s_%d_%d"
    vals = (oriprefix,azimuth,slope) # tuple, one value per marker
    myString = fmtString % vals
    return myString
Orientation = []
Surfaces = []
mesh = []
Floor = []
wall = []
SouthWall = []
WestWall = []
NorthWall = []
EastWall = []
Ceiling = []
brepcoll = []
new_surfaces = rs.ExplodePolysurfaces(_Box)
for item in new_surfaces:
    Surfaces.append(item)
    counter = -1
    points = []
    normal = rs.SurfaceNormal(item,(0,0))
    Orientation.append(getOrientation(normal))
    oridummy = Orientation[-1]
    slope = float(oridummy.split('_')[2])
    azimuth = float(oridummy.split('_')[1])
    if slope > 45 and slope <= 135:
        if azimuth <= 45 or azimuth > 315:
            SouthWall.append(item)
        elif azimuth > 45 and azimuth <= 135:
            WestWall.append(item)
        elif azimuth > 135 and azimuth <= 225:
            NorthWall.append(item)
        elif azimuth > 225 and azimuth <= 315:
            EastWall.append(item)
    elif slope > 135:
        Floor.append(item)
    elif slope <= 45:
        Ceiling.append(item)
