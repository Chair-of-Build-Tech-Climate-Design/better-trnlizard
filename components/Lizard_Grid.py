"""
Link building surface definitions and regime data
to this Thermal Zone to generate b17 file and other airnode information needed for daylight and thermal simulations.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    Base_Surfaces (Brep): Based surface for generating grid points
        Access: list
        Required: False
    Grid_Size (float): Distance between grid points
        Access: item
        Required: False
    Grid_Height (object): Distance between grid points to based surface
        Access: item
        Required: False

Returns:
    Points (object): Grid points Author: Mark Sen Dong Date: 20160322 Description: This component can create daylight analysis grid according to the exact shape of the surface. It can cope with multiple surfaces, but right now is limited to 3 maximum.
        Access: item
    GridInfo (object): Script variable Grid
        Access: item
    CtrDlPos (object): Script variable Grid
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
for surface in Base_Surfaces:
    info, width, height = surface.Faces[0].UnderlyingSurface().GetSurfaceSize()
    if info:
        # create new UV intervals
        interval_u = rc.Geometry.Interval(0.0, width)
        interval_v = rc.Geometry.Interval(0.0, height)
        # set domains
        surface.Faces[0].SetDomain(0, interval_u)
        surface.Faces[0].SetDomain(1, interval_v)
    surface1 = rs.coercesurface(surface)
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
for i,surface in enumerate(Base_Surfaces):
    segment = ghcomp.DivideDomain2(Domain2[i],U_Count[i],V_Count[i])
    Segments['%s'%i] = segment
#STEP3. Cut the original untrimmed version of the surface according to the grid lines.
All_Grids = {}
for j,surface in enumerate(Base_Surfaces):
    Grid_Surfaces = []
    for domain in Segments['%s'%j]:
        surface1 = rs.coercebrep(surface)
        grid_surface = ghcomp.Isotrim(surface1,domain)
        Grid_Surfaces.append(grid_surface)
    All_Grids['%s'%j] = Grid_Surfaces
#STEP4. Create the class container for outputting the information
class DAYLIGHT:
    def __init__(self):
        self.Mesh1 = []
        self.Sensorpts1 = []
        self.Aratio1 = 1
        self.Area1 = 0
        self.Mesh2 = []
        self.Sensorpts2 = []
        self.Aratio2 = 0
        self.Area2 = 0
        self.Mesh3 = []
        self.Sensorpts3 = []
        self.Aratio3 = 0
        self.Area3 = 0
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, 'GRID')
DaylightInfo = DAYLIGHT()
meshes = ['mesh1','mesh2','mesh3']
data = defaultdict()
#STEP 5. Intersect the untrimmed grid with the actual surface to get a trimmed grid according to building plan.
Grid = {}
firstmesh = defaultdict()
firstmesh['BRep'] = []
firstmesh['base_srf_grid'] = []
firstmesh['mesh'] = []
firstmesh['area'] = []
firstmesh['oripts'] = []
Single_Grid = []
distance_surface_center = 10
for item, surface in enumerate(Base_Surfaces):
    if surface is None:
        pass
    else:
        Base_Surface = rs.coercebrep(surface)
        firstmesh['BRep'].append(Base_Surface)
        surfcenter = rc.Geometry.AreaMassProperties.Compute(Base_Surface).Centroid
        for grid in All_Grids['%s'%item]:
            intersect = rc.Geometry.Intersect.Intersection.BrepBrep(grid,Base_Surface,0.000001)
            if len(intersect[1]) > 0:
                point = rc.Geometry.AreaMassProperties.Compute(grid).Centroid
                line = rc.Geometry.Line(surfcenter,point)
                firstmesh['oripts'].append(point)
                move = rc.Geometry.Transform.Translation(0,0,float(Grid_Height))
                grid.Transform(move)
                inv_vector = rc.Geometry.Vector3d(0,0,-float(Grid_Height))
                if len(rc.Geometry.Intersect.Intersection.ProjectPointsToBreps([Base_Surface],[point],inv_vector,0.00001)) > 0:
                    Single_Grid.append(grid)
                    firstmesh['mesh'].append(grid)
                    point = rc.Geometry.AreaMassProperties.Compute(grid).Centroid
                    firstmesh['base_srf_grid'].append(point)
                    area = rc.Geometry.AreaMassProperties.Compute(grid).Area
                    firstmesh['area'].append(area)
                    if line.Length < distance_surface_center:
                        distance_surface_center = line.Length
                        CtrDlPos = len(firstmesh['base_srf_grid'])
Grid = Single_Grid
sc.sticky['Grid'] = Grid
Points = []
#if 'mesh1' in data:
if 1 > 0:
    DaylightInfo.Mesh1 = firstmesh['mesh']
    DaylightInfo.Sensorpts1 = firstmesh['base_srf_grid']
    DaylightInfo.Area1 = sum(firstmesh['area'])
    Points.extend(DaylightInfo.Sensorpts1)
    print 'found mesh1'
if 'mesh2' in data:
    DaylightInfo.Mesh2 = data['mesh2']['mesh']
    DaylightInfo.Sensorpts2 = data['mesh2']['base_srf_grid']
    DaylightInfo.Area2 = sum(data['mesh2']['area'])
    Points.extend(DaylightInfo.Sensorpts2)
    print 'found mesh2'
if 'mesh3' in data:
    DaylightInfo.Mesh3 = data['mesh3']['mesh']
    DaylightInfo.Sensorpts3 = data['mesh3']['base_srf_grid']
    DaylightInfo.Area3 = sum(data['mesh3']['area'])
    Points.extend(DaylightInfo.Sensorpts3)
    print 'found mesh3'
atot = DaylightInfo.Area1 + DaylightInfo.Area2 + DaylightInfo.Area3
DaylightInfo.Aratio1 = DaylightInfo.Area1 / atot
DaylightInfo.Aratio2 = DaylightInfo.Area2 / atot
DaylightInfo.Aratio3 = DaylightInfo.Area3 / atot
GridInfo = DaylightInfo
