"""
Rhino model to b17 file.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    Multizone (Brep): Multizone geometry
        Access: item
        Required: False
    ShaderTransparency (object): Transparency of shader geometry
        Access: item
        Required: False
    ComfortPoints (Point3d): Script variable ComfortPoints
        Access: list
        Required: False
    CalcSHM (object): generating shading matrix
        Access: item
        Required: False
    CalcISM (bool): generating insolation matrix
        Access: item
        Required: False
    CalcMode (int): calculation mode
        Access: item
        Required: False
    NoPatch (object): ID number of skypatch
        Access: item
        Required: False
    NoWindowPrint (int): ID number of window surface
        Access: item
        Required: False
    GridSize (object): distance between grid points
        Access: item
        Required: False

Returns:
    Multizone (object): Multizone
        Access: item
    refray (object): Script variable Python
        Access: item
    SHMValues (object): values of shading matrix
        Access: item
    SHMRays (object): visualization of solar ray
        Access: item
    SHMIntersectPts (object): intersected points between solar ray and shader
        Access: item
    SHMUnshadedPts (object): unshaded points
        Access: item
    ISMRays (object): insolation ray entering the zone
        Access: item
    ISMIntersectPts (object): intersected points between insolation ray and different surfaces
        Access: item
    ISMValues (object): values of insolation matrix
        Access: item
"""
version='2.2.1'
import rhinoscriptsyntax as rs
from collections import defaultdict
import collections
import time
import Rhino as rc
import scriptcontext as sc
import math
import threading
import System.Threading.Tasks as tasks
CalcIPM = None
tolerance = sc.doc.ModelAbsoluteTolerance
if "Multizone" in locals() and Multizone:
    zonedict = {}
    Shader = []
    lizard_zones = sc.sticky[sc.doc.Path]["MULTIZONECOLL"]()
    zone = lizard_zones.callFromZones(Multizone)[0]
    surfaceinfo = []
    for zitem in zone:
        if zitem.Name in zonedict:
            pass
        else:
            zonedict[zitem.Name] = {}
        zonedict[zitem.Name][zitem.Airnode.Name] = {}
        zonedict[zitem.Name][zitem.Airnode.Name]['BREP'] = []
        zonedict[zitem.Name][zitem.Airnode.Name]['GEOM'] = zitem.Airnode.Surfaces
        for item in zonedict[zitem.Name][zitem.Airnode.Name]['GEOM']:
            zonedict[zitem.Name][zitem.Airnode.Name]['BREP'].append(item.Surface)
            zonedict[zitem.Name][zitem.Airnode.Name]['BREP'][-1].UserDictionary.Set("TYPE", item.Type)
            zonedict[zitem.Name][zitem.Airnode.Name]['BREP'][-1].UserDictionary.Set("ZONE", zitem.Name)
            zonedict[zitem.Name][zitem.Airnode.Name]['BREP'][-1].UserDictionary.Set("ANR", zitem.Anr)
            zonedict[zitem.Name][zitem.Airnode.Name]['BREP'][-1].UserDictionary.Set("ZNR", zitem.Znr)
            zonedict[zitem.Name][zitem.Airnode.Name]['BREP'][-1].UserDictionary.Set("AIRNODE", zitem.Airnode.Name)
            if "Virtual" in item.Construction:
                zonedict[zitem.Name][zitem.Airnode.Name]['BREP'][-1].UserDictionary.Set("TYPE", 'VIRTUAL')
    if len(zone[0].Shader) > 0:
        Shader = rc.Geometry.Brep.JoinBreps(zone[0].Shader,tolerance)
        for item in Shader:
            item.UserDictionary.Set("TRANS", ShaderTransparency)
    OutputFilename = zone[0].MatricesPath
    _BRep = []
    for item1 in zonedict:
        for item2 in zonedict[item1]:
            _BRep.extend(zonedict[item1][item2]['BREP'])
else:
    if Shader in locals() and Shader:
        Shader = rc.Geometry.Brep.JoinBreps(Shader,tolerance)
        for item in Shader:
            item.UserDictionary.Set("TRANS", ShaderTransparency)
#print zonedict
def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        file = open(r'c:\TRNLizard\Tools\Shading\timing.txt','a')
        file.write('%s function took %0.3f ms\n' % (f.func_name, (time2-time1)*1000.0))
        file.close()
        print '%s function took %0.3f ms' % (f.func_name, (time2-time1)*1000.0)
        return ret
    return wrap
#@timing
def genTregSky(radius = 100, mode = 1):
    rs.EnableRedraw(False)
    rad_shm = float(radius)            # radius of sphere
    polylines = []
    points = []
    toppoints = []
    surfaces = []
    mesh = []
    dummystorage = []
    #generates the tregenza sky
    patch_beg_row = [0]
    counter = 0
    i = 0
    o = 0
    u = 6
    Fpow=int(2**mode)
    tregOriRow = 7                      # number of rows (zenith subdivisions) in original tregenzia model (F_TREGENZA=0)
    tregRow = tregOriRow*(2**mode)      # number of rows (zenith subdivisions) in actual tregenzia model
    dzen=90/((2**mode)*tregOriRow+0.5)  # zenith interval
    row=0                               # row index initialization
    zen1=90                             # first zenith value initialization
    azm1=0                              # first azimuth value initialization
    global ZEN_AZM_AREA_LIST
    ZEN_AZM_AREA_LIST=[]
    global sumArea
    sumArea=0
    patch_beg_row.append(1)                  # index id of first patch number in actual row
    tregList = [0]
    dazm = [0]
    azmcoll = []
    patch_end_row = [0]
    ZEN_AZM_AREA_LIST = []
    ZEN_AZM_AREA_LIST.append([])
    areacoll = []
    x1 = [0]
    x2 = [0]
    x3 = [0]
    x4 = [0]
    y1 = [0]
    y2 = [0]
    y3 = [0]
    y4 = [0]
    z1 = [0]
    z2 = [0]
    z3 = [0]
    z4 = [0]
    tregOriList = (0,30,30,24,24,18,12,6); # CCF 0 added as dummy at the beginning, original tregenza list - no of segments (azimuth subdivisions) per row
    for i in range(1,tregOriRow+1):
        for j in range(1,Fpow+1):
            row = row + 1
            tregList.append(tregOriList[i]*Fpow)
            dazm.append(360/tregList[row])        # azimuth interval
            zen2 = zen1 - dzen                         # second zenith value
            patch_end_row.append(patch_beg_row[row] + tregList[row]-1) # index id of final patch number in actual row
            for k in range(patch_beg_row[row],patch_end_row[row]+1):
                counter = counter + 1
                azm2 = azm1 + dazm[row]         # second azimuth value
                azmcoll.append(dazm[row])
                zen1_rad = zen1/180*math.pi     # conversion to rad
                zen2_rad = zen2/180*math.pi     # conversion to rad
                azm1_rad = azm1/180*math.pi     # conversion to rad
                azm2_rad = azm2/180*math.pi     # conversion to rad
                area = abs(rad_shm**2*(azm2_rad - azm1_rad)*(math.cos(zen1_rad)-math.cos(zen2_rad)))   # area of sphere segment
                areacoll.append(area)
                sumArea  = sumArea + area
                ZEN_AZM_AREA_LIST.append([])
                ZEN_AZM_AREA_LIST[-1].append('')
                ZEN_AZM_AREA_LIST[k].append((zen1+zen2)/2)              #center point of zenith interval
                if (((azm1+azm2)/2 >= 0) and ((azm1+azm2)/2 < 90)):
                    ZEN_AZM_AREA_LIST[k].append(-(azm1+azm2)/2 - 90)    #center point of azimuth interval
                elif (((azm1+azm2)/2 >= 90) and ((azm1+azm2)/2 < 360)):
                    ZEN_AZM_AREA_LIST[k].append(-(azm1+azm2)/2 + 270)   # center point of azimuth interval
                ZEN_AZM_AREA_LIST[k].append(area)
                solidAngle=abs((math.cos(zen1_rad)-math.cos(zen2_rad))*(azm2_rad-azm1_rad))
                ZEN_AZM_AREA_LIST[k].append(solidAngle)
                z1.append(math.sin(0.5*math.pi-zen2_rad)*rad_shm)
                r_dummy1 = z1[counter]/math.tan(0.5*math.pi-zen2_rad)
                x1.append(math.cos(azm1_rad)*r_dummy1)
                y1.append(math.sin(azm1_rad)*r_dummy1)
                z2.append(math.sin(0.5*math.pi-zen1_rad)*rad_shm)
                if(z2[counter]<(0.01)):
                    r_dummy2=rad_shm
                else:
                    r_dummy2=z2[counter]/math.tan(0.5*math.pi-zen1_rad)
                x2.append(math.cos(azm1_rad)*r_dummy2)
                y2.append(math.sin(azm1_rad)*r_dummy2)
                x3.append(math.cos(azm2_rad)*r_dummy2)
                y3.append(math.sin(azm2_rad)*r_dummy2)
                z3.append(math.sin(0.5*math.pi-zen1_rad)*rad_shm)
                x4.append(math.cos(azm2_rad)*r_dummy1)
                y4.append(math.sin(azm2_rad)*r_dummy1)
                z4.append(math.sin(0.5*math.pi-zen2_rad)*rad_shm)
                pnt1 = rc.Geometry.Point3d(x1[counter],y1[counter],z1[counter])
                pnt2 = rc.Geometry.Point3d(x2[counter],y2[counter],z2[counter])
                pnt3 = rc.Geometry.Point3d(x3[counter],y3[counter],z3[counter])
                pnt4 = rc.Geometry.Point3d(x4[counter],y4[counter],z4[counter])
                points.extend([pnt1,pnt2,pnt3,pnt4])
                polylines.append(rc.Geometry.Polyline((pnt1,pnt2,pnt3,pnt4,pnt1)))
                ncurve = rc.Geometry.Polyline.ToNurbsCurve(polylines[-1])
                surfaces.append(rc.Geometry.Brep.CreatePlanarBreps(ncurve)[0])
                if i == tregOriRow and j == Fpow:
                    toppoints.append(rc.Geometry.Point3d(x1[counter],y1[counter],z1[counter]))
                    if o == 0:
                        dummystorage = toppoints[-1]
                    o = o + 1
                azm1 = azm1+dazm[row]   # first azimuth value
            if i == tregOriRow and j == Fpow:
                toppoints.append(dummystorage)
                polylines.append(rc.Geometry.Polyline((toppoints)))
                ncurve = rc.Geometry.Polyline.ToNurbsCurve(polylines[-1])
                surfaces.append(rc.Geometry.Brep.CreatePlanarBreps(ncurve)[0])
                zen2 = dzen/2 # second zenith value
                ZEN_AZM_AREA_LIST.append([])
                ZEN_AZM_AREA_LIST[-1].append('')
                ZEN_AZM_AREA_LIST[k+1].append(0.) # center point of zenith interval
                ZEN_AZM_AREA_LIST[k+1].append(0.)
                zen1_rad = zen2/180*math.pi #conversion to rad
                zen2_rad = 0.0/180*math.pi  #conversion to rad
                area = abs(rad_shm**2*2*math.pi*(math.cos(zen1_rad)-math.cos(zen2_rad))) #area of sphere segment
                ZEN_AZM_AREA_LIST[k+1].append(area)
                areacoll.append(area)
                solidAngle=abs(2*math.pi*(1-math.cos(zen1_rad)))
                ZEN_AZM_AREA_LIST[k+1].append(solidAngle)
            azm1=0; # first azimuth value initialization
            patch_beg_row.append(patch_beg_row[row]+tregList[row]) # index id of first patch number in actual row
            zen1=zen1-dzen              # first zenith value
        surfmax=counter
    rs.EnableRedraw(True)
    return surfaces, areacoll, dzen, dazm, azmcoll
mode = 1
breps, areas, dzen, dazm, azmcoll = genTregSky(radius = 500, mode = 1)
abstol = sc.doc.ModelAbsoluteTolerance
rs.EnableRedraw(False)
sky_patches = breps
patch_areas = areas
dzen        = dzen
dazm        = azmcoll
def mean(dummy_array):
    sum = 0
    for item in dummy_array:
        sum += item
    return sum/(len(dummy_array))
#@timing
def getRaysForPatch(grid,patch):
    areaprop        = rc.Geometry.AreaMassProperties.Compute(patch)
    center_patch    = areaprop.Centroid
    rs_ori_point    = rc.Geometry.Point3d(0,0,0)
    dummyray = []
    for item in grid:
        vector = rc.Geometry.Vector3f(item[0],item[1],item[2])
        rs_ori = rc.Geometry.Point3d.Add(rs_ori_point, vector)
        rs_pat = rc.Geometry.Point3d.Add(center_patch, vector)
        dummyray.append(rc.Geometry.Line(rs_pat,rs_ori))
    return dummyray
#@timing
def getRaysForZones(grid,patch):
    areaprop        = rc.Geometry.AreaMassProperties.Compute(patch)
    center_patch    = areaprop.Centroid
    rs_ori_point    = rc.Geometry.Point3d(0,0,0)
    rs_ori_ray      = rc.Geometry.Line(center_patch,rs_ori_point)
    interior_vector = rs_ori_ray.Direction
    dummyray = []
    interiorray = []
    for item in grid:
        vector = rc.Geometry.Vector3f(item[0],item[1],item[2])
        rs_ori = rc.Geometry.Point3d.Add(rs_ori_point, vector)
        rs_ori = rc.Geometry.Point3d.Add(rs_ori, interior_vector)
        rs_pat = rc.Geometry.Point3d.Add(center_patch, vector)
        rs_pat = rc.Geometry.Point3d.Add(rs_pat, interior_vector)
        interiorray.append(rc.Geometry.Line(rs_pat,rs_ori))
    return interiorray
#@timing
def getAngle(ray, normal):
    vector_ray      = ray[0].Direction
    vector_rad      = rc.Geometry.Vector3d.VectorAngle(normal,vector_ray)
    vector_degree   = math.degrees(vector_rad)
    abs_angle       = abs(vector_degree)
    return abs_angle
#@timing
def findShadingIntersections(ray,matched_points):
        startpoint = ray.From
        if len(matched_points) > 0:
            line = rc.Geometry.Line(matched_points[0], startpoint)
            linelength = line.Length
        else:
            linelength = 0
        return linelength
def genGrid(surface, min_edge = 0.1):
    tolerance = sc.doc.ModelAbsoluteTolerance
    mesh_set = rc.Geometry.MeshingParameters()
    mesh_set.MinimumEdgeLength = min_edge
    mesh_set.MaximumEdgeLength = min_edge + 0.1
    new_mesh = rc.Geometry.Mesh.CreateFromBrep(surface,mesh_set)
    centerpts = []
    breps     = []
    for face_items in new_mesh[0].Faces:
        if face_items.IsQuad:
            pta = new_mesh[0].Vertices[face_items.A]
            ptb = new_mesh[0].Vertices[face_items.B]
            ptc = new_mesh[0].Vertices[face_items.C]
            ptd = new_mesh[0].Vertices[face_items.D]
            breps.append(rc.Geometry.Brep.CreateFromCornerPoints(pta,ptb,ptc,ptd,tolerance))
            massprop = rc.Geometry.AreaMassProperties.Compute(breps[-1])
            centerpts.append(massprop.Centroid)
        if face_items.IsTriangle:
            pta = new_mesh[0].Vertices[face_items.A]
            ptb = new_mesh[0].Vertices[face_items.B]
            ptc = new_mesh[0].Vertices[face_items.C]
            breps.append(rc.Geometry.Brep.CreateFromCornerPoints(pta,ptb,ptc,tolerance))
            massprop = rc.Geometry.AreaMassProperties.Compute(breps[-1])
            centerpts.append(massprop.Centroid)
    return centerpts
ID = 0
zones_number_list = []
for surface_item in _BRep:
    zones_number_list.append(surface_item.UserDictionary.TryGetValue('ZNR')[1])
    #print surface_item.UserDictionary.TryGetValue('ID')
    if surface_item.UserDictionary.TryGetValue('TYPE')[0]:
        pass
    else:
        surface_item.UserDictionary.Set('TYPE', 'WINDOW')
    if surface_item.UserDictionary.TryGetValue('ID')[0]:
        pass
    else:
        surface_item.UserDictionary.Set('ID', ID)
        ID += 1
zones_number_list = list(set(zones_number_list))
brepintersect = []
for si, surface_item in enumerate(_BRep):
    brepintersect.append(surface_item.DuplicateBrep())
dummys2 = []
for si, surface_item in enumerate(brepintersect):
    differencefound = 0
    type = surface_item.UserDictionary.TryGetValue('TYPE')[1]
    id = surface_item.UserDictionary.TryGetValue('ID')[1]
    zone = surface_item.UserDictionary.TryGetValue('ZONE')[1]
    airnode = surface_item.UserDictionary.TryGetValue('AIRNODE')[1]
    #print '%s %s %s'%(id,type,airnode)
    if type == 'WALL' or type == 'ROOF' or type == 'CEILING' or type == 'FLOOR':
        for subi, subsurface_item in enumerate(brepintersect):
            type2 = subsurface_item.UserDictionary.TryGetValue('TYPE')[1]
            if si != subi and type2 == 'WINDOW':
                difference = rc.Geometry.Brep.CreateBooleanDifference(surface_item,subsurface_item,tolerance)
                #print '%s %s'%(si,subi)
                if difference:
                    differencefound = 1
                    for i,item in enumerate(difference):
                        item.UserDictionary.Set("TYPE", type)
                        item.UserDictionary.Set("ID", id)
                        dummys2.append(item)
    if differencefound == 0 and type != 'VIRTUAL':
        dummys2.append(surface_item)
_BRep = dummys2
Zone = _BRep
PI = math.pi
SHMValues = []
window_data = {}
ipm_data = {}
for i, pts in enumerate(ComfortPoints):
    ipm_data[i] = {}
    ipm_data[i]['pts'] = []
window = []
surface_data = {}
idlist = []
for bi,brep_item in enumerate(_BRep):
    typedict = brep_item.UserDictionary.TryGetValue('TYPE')
    iddict   = brep_item.UserDictionary.TryGetValue('ID')
    surface_data['%s'%iddict[1]] = {}
    surface_data['%s'%iddict[1]]['shmintersect'] = []
    surface_data['%s'%iddict[1]]['shmunshaded'] = []
    surface_data['%s'%iddict[1]]['shmdiff'] = []
    surface_data['%s'%iddict[1]]['shmun'] = []
    surface_data['%s'%iddict[1]]['shm'] = []
    surface_data['%s'%iddict[1]]['ismnounshaded'] = []
    surface_data['%s'%iddict[1]]['gridrays'] = []
    surface_data['%s'%iddict[1]]['shmintersect'] = []
    surface_data['%s'%iddict[1]]['shmunshaded'] = []
    surface_data['%s'%iddict[1]]['ismintersect'] = []
    surface_data['%s'%iddict[1]]['ismgridrays'] = []
    surface_data['%s'%iddict[1]]['ism'] = []
    #surface_data['%s'%iddict[1]]['anr'] = brep_item.UserDictionary.TryGetValue('ANR')[1]
    surface_data['%s'%iddict[1]]['znr'] = brep_item.UserDictionary.TryGetValue('ZNR')[1]
    idlist.append(iddict[1])
    #print typedict
    if typedict[0] is True and typedict[1] == 'WINDOW':
        #print iddict
        grid = genGrid(brep_item, GridSize)
        surface_data['%s'%iddict[1]]['grid'] = grid
        window.append('%s'%iddict[1])
ipm_collection = []
patch_switch = NoPatch  #set number of patch to calculate or 'ALL'
raycoll = []
program_starts = time.time()
for pi, item in enumerate(sky_patches):
    if (pi == patch_switch or CalcMode == 1) and CalcSHM == 1:
        refray      = getRaysForPatch([[0,0,0]],item)
        for wi,window_item in enumerate(_BRep):
            typedict = window_item.UserDictionary.TryGetValue('TYPE')
            type     = typedict[1]
            iddict   = window_item.UserDictionary.TryGetValue('ID')
            id       = iddict[1]
            adjacent = window_item.UserDictionary.TryGetValue('BOUNDARY')[1]
            zone   = window_item.UserDictionary.TryGetValue('ZONE')[1]
            if typedict[0] is True and type != 'WINDOW':
                continue
            if typedict[0] is True and type == 'WINDOW' and adjacent == 'ADJACENT':
                continue
            base_srf_grid = surface_data['%s'%id]['grid']
            surface_data['%s'%id]['shmintersect'] = []
            surface_data['%s'%id]['shmunshaded'] = []
            surface_data['%s'%id]['shmshaded'] = []
            #shm values calculation
            vdummy = window_item.Faces[0].NormalAt(0,0)
            dummy_vector3 = [vdummy[0],vdummy[1],vdummy[2]]
            normal_vector = rc.Geometry.Vector3d(dummy_vector3[0],dummy_vector3[1],dummy_vector3[2])
            normal_vector.Reverse()
            reversed_normal = normal_vector
            sunlitfactor_coll = []
            unshaded_points = []
            abs_angle       = getAngle(refray,reversed_normal)
            if abs_angle < 90:
                surface_data['%s'%id]['gridrays'] = getRaysForPatch(base_srf_grid,item)
                no_ray = 0
                def rayShaderIntersection(ray):
                    rayinfo = defaultdict(dict)
                    for Shader_item, Shaderel in enumerate(_BRep):
                        typedict2 = Shaderel.UserDictionary.TryGetValue('TYPE')
                        type2     = typedict2[1]
                        iddict2   = Shaderel.UserDictionary.TryGetValue('ID')
                        id2       = iddict2[1]
                        #print id2
                        if id2 == id:
                            continue
                        intersection = rc.Geometry.Intersect.Intersection.CurveBrep(ray.ToNurbsCurve(),Shaderel,abstol)
                        matched_points = intersection[2]
                        if len(matched_points) > 0:
                            linelen = findShadingIntersections(ray,matched_points)
                            surface_data['%s'%id]['shmintersect'].append(matched_points[0])
                            #print matched_points[0]
                            #print '%s %s'%(id, id2)
                            Shaderdef = Shaderel.UserDictionary.TryGetValue('TRANS')
                            if Shaderdef[0] is False:
                                rayinfo[linelen] = 0
                            else:
                                rayinfo[linelen] = Shaderdef[1]
                            if rayinfo[linelen] == 0:
                                break
                    for Shader_item, Shaderel in enumerate(Shader):
                        intersection = rc.Geometry.Intersect.Intersection.CurveBrep(ray.ToNurbsCurve(),Shaderel,abstol)
                        matched_points = intersection[2]
                        if len(matched_points) > 0:
                            linelen = findShadingIntersections(ray,matched_points)
                            surface_data['%s'%id]['shmintersect'].append(matched_points[0])
                            Shaderdef = Shaderel.UserDictionary.TryGetValue('TRANS')
                            if Shaderdef[0] is False:
                                rayinfo[linelen] = 0
                            else:
                                rayinfo[linelen] = Shaderdef[1]
                            if rayinfo[linelen] == 0:
                                break
                    od = collections.OrderedDict(sorted(rayinfo.items()))
                    sunlitray = 1
                    for oitem in od:
                        if sunlitray > 0:
                            sunlitray = sunlitray * od[oitem]
                        else:
                            break
                    if sunlitray == 0:
                        surface_data['%s'%id]['shmshaded'].append(ray.To)
                    else:
                        surface_data['%s'%id]['shmunshaded'].append(ray.To)
                    sunlitfactor_coll.append(sunlitray)
                    od = {}
                    od.clear()
                    rayinfo= {}
                    rayinfo.clear()
                tasks.Parallel.ForEach(surface_data['%s'%id]['gridrays'], rayShaderIntersection)
                sunlitfactor = mean(sunlitfactor_coll)
                normal_vector2 = rc.Geometry.Vector3d(0,0,-1)
                angle_2 = getAngle(refray, normal_vector2)
                if pi == len(sky_patches)-1:
                    factorrad = (ZEN_AZM_AREA_LIST[pi+1][3]) / sumArea * abs(math.cos(abs_angle))  #Tregenza based model
                else:
                    factorrad = math.radians(dzen) * math.radians(dazm[pi]) * abs(math.cos(math.radians(abs_angle))) * abs(math.sin(math.radians(angle_2))) #Sky division model
                sunlitfactordiff = sunlitfactor * factorrad
                undisturbed_factor = factorrad
                surface_data['%s'%id]['shmdiff'].append(sunlitfactordiff)
                surface_data['%s'%id]['shmun'].append(undisturbed_factor)
                surface_data['%s'%id]['ismnounshaded'].append(len(surface_data['%s'%id]['shmunshaded']))
            else:
                sunlitfactor = 99
                surface_data['%s'%id]['ismnounshaded'].append(len(base_srf_grid))
            surface_data['%s'%id]['shm'].append(sunlitfactor)
            SHMValues.append(sunlitfactor)
            #starting from here the ism calculation begins
            if CalcISM == 1:
                rayinfo = {}
                surfaceinfo = []
                surface_data['%s'%id]['ismtotintersect'] = []
                surface_data['%s'%id]['ismintersect'] = []
                surface_data['%s'%id]['ismfact'] = []
                abs_angle   = getAngle(refray,reversed_normal)
                if abs_angle < 90:
                    surface_data['%s'%id]['ismgridrays'] = getRaysForZones(surface_data['%s'%id]['shmunshaded'],item)
                    no_ray = 0
                    for ray_item, ray in enumerate(surface_data['%s'%id]['ismgridrays']):
                        if 1 > 0:
                            found_int  = 0
                            dummy_data = 0
                            for sitem, surfaceitem in enumerate(_BRep):
                                vdummy = surfaceitem.Faces[0].NormalAt(0,0)
                                normal_vector3 = [vdummy[0],vdummy[1],vdummy[2]]
                                normal_vector2 = rc.Geometry.Vector3d(normal_vector3[0],normal_vector3[1],normal_vector3[2])
                                reversed_normal2 = normal_vector2
                                surf_abs_angle   = getAngle(refray,reversed_normal2)
                                typedict2 = surfaceitem.UserDictionary.TryGetValue('TYPE')
                                type2     = typedict2[1]
                                iddict2   = surfaceitem.UserDictionary.TryGetValue('ID')
                                id2       = iddict2[1]
                                if id2 == id or surfaceitem.UserDictionary.TryGetValue('ZONE')[1] != zone:
                                    continue
                                intersection = rc.Geometry.Intersect.Intersection.CurveBrep(ray.ToNurbsCurve(),surfaceitem,abstol)
                                matched_points = intersection[2]
                                if surf_abs_angle < 90:
                                    if len(matched_points) > 0:
                                        dummy_data =1
                                        linelen = findShadingIntersections(surface_data['%s'%id]['ismgridrays'][ray_item],matched_points)
                                        surface_data['%s'%id]['ismtotintersect'].append(matched_points[0])
                                        found_int = 1
                                        if linelen in rayinfo:
                                            continue
                                        rayinfo[linelen] = {}
                                        rayinfo[linelen]['point']   = matched_points[0]
                                        rayinfo[linelen]['surface'] = sitem
                                    else:
                                        linelen = 0
                            if dummy_data == 1:
                                od = collections.OrderedDict(sorted(rayinfo.items()))
                                surface_data['%s'%id]['ismintersect'].append(od.values()[0]['point'])
                                surface_data['%s'%id]['ismfact'].append(sunlitfactor_coll[ray_item])
                                surfaceinfo.append(od.values()[0]['surface'])
                            od = {}
                            od.clear()
                            rayinfo= {}
                            rayinfo.clear()
                    data = {}
                    for sitem, surfaceitem in enumerate(_BRep):
                        data[sitem] = 0
                else:
                    data = {}
                    for sitem, surfaceitem in enumerate(_BRep):
                        data[sitem] = -1
                nogridpoints = len(base_srf_grid)
                dummyarray = list(set(surfaceinfo))
                if len(surface_data['%s'%id]['ismintersect']) > 0:
                    for sind,suritem in enumerate(surfaceinfo):
                        data[suritem] = data[suritem] + 1 * surface_data['%s'%id]['ismfact'][sind]
                datadummy = []
                for y,yitem in enumerate(idlist):
                    datadummy.append(0)
                    for zitem, surfacezitem in enumerate(_BRep):
                        iddict3   = surfacezitem.UserDictionary.TryGetValue('ID')
                        id3       = iddict3[1]
                        if id3 == yitem:
                            datadummy[y] += data.values()[y]
                surface_data['%s'%id]['ism'].append(datadummy)
                if CalcMode == 0:
                    pass
                    #print datadummy
        #starting from here the ipm calculation begins #CCF check order of patches compared to usual way and integrate Shader influence
        if CalcIPM == 1:
            rayinfoipm = {}
            surfaceinfoipm = []
            IPMIntersectPts = []
            ipm_rays_start  = []
            ipm_rays_end    = []
            IPMRays     = getRaysForPatch(ComfortPoints,item)
            match_found = 0
            collection = []
            for ray_item, ray in enumerate(IPMRays):
                ipm_rays_start.append(ray.From)
                ipm_rays_end.append(ray.To)
                matchedwallID = 0
                matchedwinID  = 0
                found_shading_ipm = 0
                for sitem, surface in enumerate(_BRep):
                    typeipm = surface.UserDictionary.TryGetValue('TYPE')[1]
                    idipm   = surface.UserDictionary.TryGetValue('ID')[1]
                    intersection = rc.Geometry.Intersect.Intersection.CurveBrep(ray.ToNurbsCurve(),surface,abstol)
                    matched_points = intersection[2]
                    if len(matched_points) > 0:
                        if typeipm == 'WALL' or typeipm == 'ROOF' or typeipm == 'CEILING' or typeipm == 'FLOOR':
                            matchedwallID = idipm
                            continue
                        matchedwinID = idipm
                        linelen = findShadingIntersections(IPMRays[ray_item],matched_points)
                        rayinfoipm[linelen] = {}
                        rayinfoipm[linelen]['point'] = matched_points[0]
                        rayinfoipm[linelen]['surface'] = sitem
                        rayinfoipm[linelen]['center'] = rs.SurfaceAreaCentroid(surface)
                        match_found = 1
                    else:
                        match_found = 0
                    if match_found == 1:
                        od = collections.OrderedDict(sorted(rayinfoipm.items()))
                        IPMIntersectPts.append(od.values()[0]['point'])
                        ipm_data[ray_item]['pts'].append(IPMIntersectPts[-1])
                        surfaceinfoipm.append(od.values()[0]['surface'])
                        match_found = 0
                    od = {}
                    od.clear()
                    rayinfo= {}
                    rayinfo.clear()
                for Shader_item, Shaderel in enumerate(Shader):
                    intersection = rc.Geometry.Intersect.Intersection.CurveBrep(ray.ToNurbsCurve(),Shaderel,abstol)
                    matched_points = intersection[2]
                    if len(matched_points) > 0:
                        found_shading_ipm = 1
                if matchedwallID == 0 and matchedwinID > 0 and found_shading_ipm == 0:
                    collection.append(matchedwinID)
                else:
                    collection.append(0)
            ipm_collection.append(collection)
            if CalcMode == 0:
                print collection
#tasks.Parallel.ForEach(sky_patches, calculation)
now = time.time()
print("It has been {0} seconds to run through the loop".format(now - program_starts))
#dummy = ipm_data[0]['pts']
if CalcSHM == 1:
    for bi,brep_item in enumerate(_BRep):
        typedict = brep_item.UserDictionary.TryGetValue('TYPE')
        type     = typedict[1]
        iddict   = brep_item.UserDictionary.TryGetValue('ID')
        id       = iddict[1]
        adjacent = brep_item.UserDictionary.TryGetValue('BOUNDARY')[1]
        if typedict[0] is True and type == 'WINDOW' and adjacent != 'ADJACENT':
            diffuse_factor = sum(surface_data['%s'%id]['shmdiff'])/(sum(surface_data['%s'%id]['shmun'])+0.0000000000000001)
            surface_data['%s'%id]['difffact'] = diffuse_factor
            print 'Diffuse Factor ID {1}\n{0}'.format(diffuse_factor,id)
if NoWindowPrint is None:
    for key in surface_data:
        SHMRays            = surface_data['%s'%key]['gridrays']
        SHMIntersectPts   = surface_data['%s'%key]['shmintersect']
        SHMUnshadedPts    = surface_data['%s'%key]['shmunshaded']
        ISMIntersectPts   = surface_data['%s'%key]['ismintersect']
        ISMRays            = surface_data['%s'%key]['ismgridrays']
        ISMValues          = surface_data['%s'%key]['ism']
else:
    SHMRays            = surface_data['%s'%NoWindowPrint]['gridrays']
    SHMIntersectPts   = surface_data['%s'%NoWindowPrint]['shmintersect']
    SHMUnshadedPts    = surface_data['%s'%NoWindowPrint]['shmunshaded']
    ISMIntersectPts   = surface_data['%s'%NoWindowPrint]['ismintersect']
    ISMRays            = surface_data['%s'%NoWindowPrint]['ismgridrays']
    ISMValues          = surface_data['%s'%NoWindowPrint]['ism']
if CalcMode == 1 and CalcSHM == 1:
    file = open(OutputFilename + '.shm','w')
    dummy = ''
    for item in window:
        dummy +='       {0}'.format(item)
    file.write('     -{0}\n\n\n\n      {1}\n{2}\n'.format(mode,len(window),dummy))
    for si,sitem in enumerate(sky_patches):
        dummy = ''
        for wi,window_item in enumerate(window):
            dummy += ' {0:8.3f}'.format(float(surface_data[window_item]['shm'][si]))
        dummy += '\n'
        file.write(dummy)
    dummy = '!Diffuse Sunlit fraction\n'
    for wi,window_item in enumerate(window):
        dummy += ' {0:8.3f}'.format(float(surface_data[window_item]['difffact']))
    dummy += '\n'
    file.write(dummy)
    file.close()
    if CalcISM == 1:
        if Multizone:
            zone = lizard_zones.callFromZones(Multizone)[0]
            foundzones = []
            for zitem in zone:
                if str(zitem.Znr) in foundzones:
                    continue
                else:
                    foundzones.append(str(zitem.Znr))
                file = open(OutputFilename + '_%03d.ism'%zitem.Znr, 'w')
                dummy1 = ''
                counter = 0
                idcoll = []
                for item in idlist:
                    if surface_data['%s'%item]['znr'] == zitem.Znr:
                        dummy1 +='       {0}'.format(item)
                        idcoll.append(item)
                        counter += 1
                file.write('     -{0}\n\n\n\n'.format(mode,counter,dummy1))
                for wi,window_item in enumerate(window):
                    if surface_data[window_item]['znr'] != zitem.Znr:
                        continue
                    file.write('      {1}\n{2}\n'.format(mode,window_item,dummy1))
                    for si,sitem in enumerate(sky_patches):
                        dummy = ''
                        test = []
                        for i, it in enumerate(idcoll):
                            if float(surface_data[window_item]['ism'][si][i]) == -1:
                                pass
                            else:
                                test.append(float(surface_data[window_item]['ism'][si][i])/(surface_data[window_item]['ismnounshaded'][si]+0.0000001))
                        if sum(test) > 0:
                            factor = 1 / sum(test)
                        else:
                            factor = 1
                        for i, it in enumerate(idcoll):
                            if float(surface_data[window_item]['ism'][si][i]) == -1:
                                dummy += ' {0:8.3f}'.format(float(99))
                            else:
                                dummy += ' {0:8.3f}'.format(factor * float(surface_data[window_item]['ism'][si][i])/(surface_data[window_item]['ismnounshaded'][si]+0.0000001))
                        dummy += '\n'
                        file.write(dummy)
                file.close()
        else:
            foundzones = []
            for zitem in zones_number_list:
                if str(zitem) in foundzones:
                    continue
                else:
                    foundzones.append(str(zitem))
                file = open(OutputFilename + '_%03d.ism'%zitem, 'w')
                dummy1 = ''
                counter = 0
                idcoll = []
                for item in idlist:
                    if surface_data['%s'%item]['znr'] == zitem:
                        dummy1 +='       {0}'.format(item)
                        idcoll.append(item)
                        counter += 1
                file.write('     -{0}\n\n\n\n'.format(mode,counter,dummy1))
                for wi,window_item in enumerate(window):
                    if surface_data[window_item]['znr'] != zitem:
                        continue
                    file.write('      {1}\n{2}\n'.format(mode,window_item,dummy1))
                    for si,sitem in enumerate(sky_patches):
                        dummy = ''
                        test = []
                        for i, it in enumerate(idcoll):
                            if float(surface_data[window_item]['ism'][si][i]) == -1:
                                pass
                            else:
                                test.append(float(surface_data[window_item]['ism'][si][i])/(surface_data[window_item]['ismnounshaded'][si]+0.0000001))
                        if sum(test) > 0:
                            factor = 1 / sum(test)
                        else:
                            factor = 1
                        for i, it in enumerate(idcoll):
                            if float(surface_data[window_item]['ism'][si][i]) == -1:
                                dummy += ' {0:8.3f}'.format(float(99))
                            else:
                                dummy += ' {0:8.3f}'.format(factor * float(surface_data[window_item]['ism'][si][i])/(surface_data[window_item]['ismnounshaded'][si]+0.0000001))
                        dummy += '\n'
                        file.write(dummy)
                file.close()
    if CalcIPM == 1:
        file = open(OutputFilename + '.ipm','w')
        dummy1 = ''
        for i,item in enumerate(ComfortPoints):
            dummy1 +='{0:5.0f}'.format(float(i+1))
        file.write('     -{0}\n\n\n\n      {1}\n{2}\n'.format(mode,1,dummy1))
        for pi,ipm_item in enumerate(ipm_collection):
            dummy = ''
            for sub1 in ipm_item:
                dummy += '{0:5.0f}'.format(float(sub1))
            dummy += '\n'
            file.write(dummy)
        file.close()
rs.EnableRedraw(True)
dummys2 = []
_BRep = []
Zone = []
