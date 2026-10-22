"""
Link surface to divide into two parts based on a percentage input.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    Toggle (int): if True, the brep will be divided based on the percentage
        Access: item
        Required: False
    _BRep (Brep): link one surface
        Access: item
        Required: False
    Percentage (float): set percentage for devision in %/100
        Access: item
        Required: False

Returns:
    BRep1_ (object): Script variable Grid
        Access: item
    BRep2_ (object): Script variable Percentage
        Access: item
"""
version='2.2.1'
import rhinoscriptsyntax as rs
import Rhino as rc
import ghpythonlib.components as ghcomp
import Grasshopper.Kernel as gk
from collections import defaultdict
import scriptcontext as sc
#STEP1. Get the domain of the surfaces and how many times the surface should be cut according to Grid_Size
U_Count = []
V_Count = []
Domain2 = []
Grid_Height = 0.5
Grid_Size = 0.1
Base_Surfaces = _BRep
toggle = Toggle
surface = _BRep
if _BRep:
    #surface1 = rs.coercesurface(surface)
    surface1 = surface.Faces[0]
    surface_Domain_U = rc.Geometry.Surface.Domain(surface1,0)
    surface_Domain_V = rc.Geometry.Surface.Domain(surface1,1)
    surface_Domain2 = gk.Types.UVInterval(surface_Domain_U,surface_Domain_V)
    Domain2.append(surface_Domain2)
    U_distance = abs(surface_Domain_U[1] - surface_Domain_U[0])
    V_distance = abs(surface_Domain_V[1] - surface_Domain_V[0])
    U_Count.append(int(U_distance/Grid_Size))
    V_Count.append(int(V_distance/Grid_Size))
#STEP2. Create the lines of the grid
Segments = {}
i = 0
#for i,surface in enumerate(Base_Surfaces):
if _BRep:
    #segment = ghcomp.DivideDomain2(Domain2[i],U_Count[i],V_Count[i])
    if toggle == 1:
        segment = ghcomp.DivideDomain2(Domain2[i],U_Count[i],[0,1])
    else:
        segment = ghcomp.DivideDomain2(Domain2[i],[0,1],V_Count[i])
    Segments['%s'%i] = segment
#STEP3. Cut the original untrimmed version of the surface according to the grid lines.
All_Grids = {}
j = 0
#for j,surface in enumerate(Base_Surfaces):
if _BRep:
    Grid_Surfaces = []
    for domain in Segments['%s'%j]:
        surface1 = rs.coercebrep(surface)
        grid_surface = ghcomp.Isotrim(surface1,domain)
        Grid_Surfaces.append(grid_surface)
    All_Grids['%s'%j] = Grid_Surfaces
#STEP 5. Intersect the untrimmed grid with the actual surface to get a trimmed grid according to building plan.
Grid = {}
#Breps = rc.Geometry.Brep()
object = surface
item = 0
#for item, object in enumerate(Base_Surfaces):
if _BRep:
    Single_Grid = []
    if surface is None:
        pass
    else:
        #Base_Surface = rs.coercebrep(Base_Surfaces[item])
        Base_Surface = surface
        basearea = Base_Surface.GetArea()
        dummyarea = 0
        for grid in All_Grids['%s'%item]:
            intersect = rc.Geometry.Intersect.Intersection.BrepBrep(grid,Base_Surface,0.000001)
            if len(intersect[1]) > 0:
                for citem in intersect[1]:
                   newbrep = rc.Geometry.Brep.CreatePlanarBreps(citem)
                   if newbrep:
                       dummyarea += newbrep[0].GetArea()
                if dummyarea > basearea*Percentage:
                    dummy = Base_Surface.Split(newbrep[0], 0.000001)
                    Brep_ = Base_Surface.Split(dummy[-1], 0.000001)
                    if Percentage < 0.5 and Brep_[0].GetArea() < Brep_[1].GetArea():
                        BRep1_ = rc.Geometry.Brep.CreatePlanarBreps(Brep_[0].Curves3D)
                        BRep2_ = rc.Geometry.Brep.CreatePlanarBreps(Brep_[1].Curves3D)
                    elif Percentage < 0.5:
                        BRep1_ = rc.Geometry.Brep.CreatePlanarBreps(Brep_[1].Curves3D)
                        BRep2_ = rc.Geometry.Brep.CreatePlanarBreps(Brep_[0].Curves3D)
                    elif Brep_[0].GetArea() < Brep_[1].GetArea():
                        BRep1_ = rc.Geometry.Brep.CreatePlanarBreps(Brep_[1].Curves3D)
                        BRep2_ = rc.Geometry.Brep.CreatePlanarBreps(Brep_[0].Curves3D)
                    else :
                        BRep1_ = rc.Geometry.Brep.CreatePlanarBreps(Brep_[0].Curves3D)
                        BRep2_ = rc.Geometry.Brep.CreatePlanarBreps(Brep_[1].Curves3D)
                    BRep1_ = ghcomp.Flip(BRep1_,_BRep).surface
                    BRep2_ = ghcomp.Flip(BRep2_,_BRep).surface
                    break
