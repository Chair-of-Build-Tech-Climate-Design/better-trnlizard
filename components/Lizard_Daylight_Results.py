"""
Rreading results from daylight simulation
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    Building (str): link with Building output from Results component (or a path to b18 file)
        Access: item
        Required: False
    HourIlluminance (int): select hour to visualize the illuminance
        Access: item
        Required: False

Returns:
    GridPts (object): daylight sensor points
        Access: item
    GridMesh (object): Script variable Daylight_Results
        Access: item
    DA (object): daylight autonomy (DA_300)
        Access: item
    CDA (object): continuous daylight autonomy (CDA_300)
        Access: item
    UDI (object): useful daylight illuminance (UDI_100_2000)
        Access: item
    DF (object): daylight factor
        Access: item
    ILL (object): illuminance on sensor points at selected hour
        Access: item
"""
version='2.2.1'
import re
import Grasshopper.Kernel as gh
import Rhino as rc
import rhinoscriptsyntax as rs
from clr import AddReference as addr
addr("Grasshopper")
from collections import defaultdict
import os
import collections
datafile                = Building
daylight_dir             = os.path.dirname(Building) + r'\Daylight'
hour_illuminance = HourIlluminance
reload = 1
zonenames               = []
zoneinfo                = defaultdict(dict)
w = gh.GH_RuntimeMessageLevel.Warning
err = gh.GH_RuntimeMessageLevel.Error
#get daylight sensor points
def getDataParagraph(startpattern,stoppattern,datararray):
    output = []
    inparagraph = 'FALSE'
    lines=datararray
    for i in range(len(lines)):
        search_start=re.search(r'{0}'.format(startpattern),lines[i])
        if search_start is not None or inparagraph == 'TRUE':
            inparagraph = 'TRUE'
            lines[i] = lines[i].split('\n')[0]
            if lines[i].startswith('*'):
                pass
            else:
                output.append(lines[i])
            search_stop=re.search(r'{0}'.format(stoppattern),lines[i])
            if search_stop is not None:
                return output
                f.close()
                break
###generate mesh start
def readMeshFile(datafile):
    surfaces = []
    column = []
    results = []
    outputnames = []
    sumdata = []
    output = {}
    pointssummary = []
    zone = {}
    zonenames = []
    pointx = 0
    pointy = 0
    test = 0
    f = open(datafile, 'r')
    lines=f.readlines()
    for i, litem in enumerate(lines):
        #if not lines[i][0].isdigit():
        #if re.match('^\S+',lines[i]) is not None:
        if len(litem.split()) < 8:
            zonename = lines[i].rstrip()
            zonename = zonename.split()[0]
            zonenames.append(zonename)
            zone[zonename] = {}
            zone[zonename]['Pts'] = []
            zone[zonename]['Mesh'] = []
            #if re.search('^\s+-?\d+',lines[i]) is not None or litem[0].isdigit():
        else:
            data    =lines[i].split('|')
            del data[-1]
            pointstest = []
            for i in range(len(data)):
                pointscoll = []
                subdata =data[i].split()
                counter = 0
                point = []
                for item in range(len(subdata)):
                    if counter < 3:
                        point.append(float(subdata[item]))
                    counter = counter + 1
                    if counter == 3:
                        counter = 0
                        dummypoint = rc.Geometry.Point3d(point[0],point[1],point[2])
                        pointx = max(pointx,point[0])
                        pointy = min(pointy,point[1])
                        pointscoll.append(dummypoint)
                        point = []
                #test += 1
                pointstest.append(pointscoll)
            #pointssummary.append(pointstest)
            zone[zonename]['Pts'].append(pointstest)
    f.close()
    #print
    for key in zonenames:
        daylight_mesh = []
        for item in range(len(zone[key]['Pts'])):
            surfaces = []
            for subitem in zone[key]['Pts'][item]:
                surface_pts = []
                for subitem2 in subitem:
                    surface_pts.append(subitem2)
                surfaces.append(rs.AddSrfPt(surface_pts))
            brep_coll = []
            for brepitem in surfaces:
                brep_coll.append(rs.coercebrep(brepitem))
            if rs.JoinSurfaces(surfaces) is None:
                joined_surfaces = surfaces[-1]
            else:
                joined_surfaces = rs.JoinSurfaces(surfaces)
            #daylight_mesh.append(joined_surfaces)
            zone[key]['Mesh'].append(joined_surfaces)
            test += 1
    refpoint = rc.Geometry.Point3d(pointx,pointy,0)
    return zone,refpoint
def getDaylightPoints(dummy_data):
    DaylightPoints = defaultdict(dict)
    zone_list  = []
    zone_positions = []
    f = getDataParagraph("_EXTENSION_DaylightSensorPoints_START_", "_EXTENSION_DaylightSensorPoints_END_", dummy_data)
    if f != None:
        for item in f:
            if item.startswith('zone'):
                zone_name = item.upper()
                zone_list.append(zone_name)
                zone_positions.append(f.index(item))
                zone_positions.append(f.index(item))
        last_item = f[-1]
        zone_positions.append(f.index(last_item))
        zone_positions = zone_positions[1:]
        i = 0
        for item in zone_list:
            DaylightPoints[item] = {}
            zone_start = zone_positions[i]
            zone_end = zone_positions[i+1]
            for item1 in f[zone_start:zone_end+1]:
                if item1.startswith('dgeopos'):
                    point_name = item1.split(' ')[0] + ' ' + item1.split(' ')[1]
                    points = item1.split(' ')[2] + ' ' + item1.split(' ')[3] + ' ' + item1.split(' ')[4]
                    DaylightPoints[item][point_name] = points
            i += 2
    return DaylightPoints, zone_list
f = open(datafile, 'r')
lines=f.readlines()
f.close()
points_dict = {}
points_dict, zone_order = getDaylightPoints(lines)
for key in points_dict:
    dummy = key.split()
    zonenames.append(dummy[-1])
#print zonename
if 'FocusZone' in locals() and len(FocusZone) > 0:
    zonenames = FocusZone
###start reading output file
illuminancedata = []
if reload == 1:
    # 1 read grid data file from the printer file
    zonejumps = []
    zonejumpscounter = 0
    results_dict = {}
    foundresults = []
    # 2 read data file from the printer file
    collids = []
    gridfilename = ''
    for item in zonenames:
        illfilename = ''
        for dummyname in os.listdir(daylight_dir):
            if dummyname.endswith(".ill") and item in dummyname:
                #print(os.path.join(directory, filename))
                illfilename = '{0}\\{1}'.format(daylight_dir, dummyname)
                print illfilename
                foundresults.append(item)
                break
        if illfilename == '':
            continue
        gridfilename = '{0}\\{1}'.format(os.path.dirname(Building), 'model.grid')
        #3 read in ill file data and apply occupation and shading switches to get the illuminance
        illfile = open(illfilename, 'r')
        baselines   = illfile.readlines()
        firstline = baselines[0]
        ptids = firstline.split()
        del ptids[0]
        for did in ptids:
            collids.append(did)
            results_dict[did] = {}
            results_dict[did]['dacoll'] = 0
            results_dict[did]['cdacoll'] = 0
            results_dict[did]['udicoll'] = 0
            results_dict[did]['dfcoll'] = 0
            results_dict[did]['illcoll'] = []
        del baselines[0]
        del baselines[0]
        database    = baselines[0].split()
        del database[0]
        dummyDF = baselines[-1].split()
        del dummyDF[0]
        dummyUDI = baselines[-2].split()
        del dummyUDI[0]
        dummyCDA = baselines[-3].split()
        del dummyCDA[0]
        dummyDA = baselines[-4].split()
        del dummyDA[0]
        dummyILL = baselines[HourIlluminance-1].split()
        del dummyILL[0]
        illfile.close()
        for column in range(len(database)):
            results_dict[ptids[column]]['dacoll'] = dummyDA[column]
            results_dict[ptids[column]]['cdacoll'] = dummyCDA[column]
            results_dict[ptids[column]]['udicoll'] = dummyUDI[column]
            results_dict[ptids[column]]['dfcoll'] = dummyDF[column]
            results_dict[ptids[column]]['illcoll'] = dummyILL[column]
            #print results_dict[ptids[column]]['dfcoll']
    GridPts = []
    DA = []
    CDA = []
    UDI = []
    DF = []
    ILL = []
    GridMesh = []
    print gridfilename
    if gridfilename != '':
        meshinfo,RefPt = readMeshFile(gridfilename)
    #for key, value in meshinfo.iteritems() :
    #    print key
    #print meshinfo
    for key in zone_order:
        od = collections.OrderedDict(sorted(points_dict[key].items()))
        #print od
        #print key.split()[-1]
        #print foundresults
        if key.split()[-1] in foundresults:
            #print 'found'
            for subkey in collids:
                #print subkey
                if 'dgeopos %s'%subkey in od:
                    #print 'found'
                    #break
                    x,y,z = od['dgeopos %s'%subkey].split()
                    #id = subkey.split()[-1]
                    id = subkey
                    dummyPt = rc.Geometry.Point3d(float(x),float(y),float(z))
                    GridPts.append(dummyPt)
                    DA.append(results_dict[id]['dacoll'])
                    CDA.append(results_dict[id]['cdacoll'])
                    UDI.append(results_dict[id]['udicoll'])
                    DF.append(results_dict[id]['dfcoll'])
                    ILL.append(results_dict[id]['illcoll'])
            if gridfilename != '':
                #print meshinfo['FLUR']
                GridMesh.extend(meshinfo[key.split()[-1]]['Mesh'])
                #print GridMesh
