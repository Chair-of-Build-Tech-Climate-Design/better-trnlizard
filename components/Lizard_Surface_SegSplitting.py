"""
Link surface to divide it into smaller segments for the active layer.
Hint: area should be smaller than 50m?
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    Toggle (object): If True the linked surface will be divided into smaller segments.
        Access: item
        Required: False
    _BRep (Brep): Connect a surface
        Access: tree
        Required: False
    NoSegments (float): Division is made based on the set area in m²
        Access: item
        Required: False

Returns:
    Brep_ (object): Smaller Segments
        Access: item
"""
version='2.2.1'
import Rhino as rc
import Grasshopper.Kernel as gk
from collections import defaultdict
import scriptcontext as sc
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path

#STEP1. Get the domain of the surfaces and how many times the surface should be cut according to Grid_Size
Brep_ = DataTree[rc.Geometry.GeometryBase]()
for i in range(_BRep.BranchCount):
    if _BRep.Branch(i):
        pass
    else:
        continue
    branchPath = _BRep.Path(i)
    #mainbranch = branchPath[0]
    #Path = GH_Path(mainbranch)
    Path = branchPath
    for surface in _BRep.Branch(i):
        #surface = []
        #surface = _BRep.Branch(i)[0]
        U_Count = []
        V_Count = []
        Domain2 = []
        Grid_Size = 0.05
        toggle = Toggle
        Area = surface.GetArea() / NoSegments
        surface1 = surface.Faces[0]
        rc.Geometry.BrepFace.GetSurfaceSize
        surface_Domain_U = rc.Geometry.Surface.Domain(surface1,0)
        surface_Domain_V = rc.Geometry.Surface.Domain(surface1,1)
        surface_Domain2 = gk.Types.UVInterval(surface_Domain_U,surface_Domain_V)
        U_distance = (surface_Domain_U[1] - surface_Domain_U[0])
        V_distance = (surface_Domain_V[1] - surface_Domain_V[0])
        U_Count = int(U_distance/Grid_Size)
        V_Count = int(V_distance/Grid_Size)
        #STEP2. Create the lines of the grid
        curves = []
        testcurves = []
        areapos = 0
        if toggle == 1:
            u = 1
            posfound = 0
            for item in range(1,U_Count + 1):
                value = surface_Domain_U[0] + item*Grid_Size
                startpts = surface1.PointAt(value,surface_Domain_V[0])
                stoppts = surface1.PointAt(value,surface_Domain_V[1])
                curve = rc.Geometry.Line(startpts,stoppts).ToNurbsCurve()
                segment = surface1.Split([curve], 0.00000001)
                area = []
                for subitem in segment.Faces:
                    test = rc.Geometry.AreaMassProperties.Compute(subitem)
                    area.append(test.Area)
                if len(area) > 1 and area[0] < area[1] and posfound == 0:
                    areapos = 0
                    posfound = 1
                elif len(area) > 1 and area[0] > area[1] and posfound == 0:
                    areapos = 1
                    posfound = 1
                if len(area) > 1 and area[min(areapos,len(area)-1)] > Area * u:
                    curves.append(curve)
                    u += 1
        else:
            u = 1
            posfound = 0
            for item in range(1,V_Count + 1):
                value = surface_Domain_V[0] + item*Grid_Size
                startpts = surface1.PointAt(surface_Domain_U[0],value)
                stoppts = surface1.PointAt(surface_Domain_U[1],value)
                curve = rc.Geometry.Line(startpts,stoppts).ToNurbsCurve()
                segment = surface1.Split([curve], 0.00000001)
                area = []
                for subitem in segment.Faces:
                    test = rc.Geometry.AreaMassProperties.Compute(subitem)
                    area.append(test.Area)
                if len(area) > 1 and area[0] < area[1] and posfound == 0:
                    areapos = 0
                    posfound = 1
                elif len(area) > 1 and area[0] > area[1] and posfound == 0:
                    areapos = 1
                    posfound = 1
                if len(area) > 1 and area[min(areapos,len(area)-1)] > Area * u:
                    curves.append(curve)
                    u += 1
        dBrep_ = segment = surface1.Split(curves, 0.00000001)
        i = 0
        #dummyBrep_ = []
        orinormal = dBrep_.Faces[0].NormalAt(0,0)
        if dBrep_:
            for item in dBrep_.Faces:
                d2Brep = dBrep_.DuplicateSubBrep([i])
                newbrep = rc.Geometry.Brep.CreatePlanarBreps(d2Brep.Curves3D)[0]
                if orinormal == newbrep.Faces[0].NormalAt(0,0):
                    pass
                else:
                    newbrep.Flip()
                #dummyBrep_.append(newbrep)
                Brep_.Add(newbrep,Path)
                i += 1
        else:
            Brep_.Add(_BRep,Path)
