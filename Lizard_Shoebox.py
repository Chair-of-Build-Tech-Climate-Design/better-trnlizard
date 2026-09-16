"""
This is the key component to store model information
-
TRNLizard 
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    Width (object): Width of the box
        Access: item
        Required: True
    Depth (object): Depth of the box
        Access: item
        Required: True
    Height (object): Height of the box
        Access: item
        Required: True
    Rotation (object): Rotation of the box
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    Box_ (object): Brep representing the geometry
        Access: item
"""
import Rhino as rc
import scriptcontext as sc
import math
version='2.2.1'
ghenv.Component.Name = "Lizard_Shoebox"
ghenv.Component.NickName = 'Shoebox'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Components"
abstol = sc.doc.ModelAbsoluteTolerance
rad = math.radians(Rotation)
rot_vector = rc.Geometry.Vector3d(0,0,1)
ori_point = rc.Geometry.Point3d(0,0,0)
max_point = rc.Geometry.Point3d(Width,Depth,Height)
box = rc.Geometry.BoundingBox(ori_point, max_point)
Box_ = rc.Geometry.Brep.CreateFromBox(box)
Box_.Rotate(rad,rot_vector,ori_point)
