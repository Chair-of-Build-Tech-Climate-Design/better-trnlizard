"""
Created by Mark Sen Dong, 2015 Oct 28 17:17
This component reads in the BaseInf database and convert the data into Grasshopper Geometry.
It also prints out other associated data.
Development log:
    20151104 MSD Added the output of Daylight, Comfort, Gain point
    20151109 MSD Added the output of adjacent_windows geometry
    20151109 MSD The script outputs both the Surfaces and the Surface ID at the same time
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    FileUrl (object): *.b18 file path
        Access: item
        Required: True
    BakeBuilding (object): bake building
        Access: item
        Required: True
    BakeShader (object): bake shader
        Access: item
        Required: True
    BakeVirtual (object): bake virtual surfaces
        Access: item
        Required: True
    BakePoints (object): bake sensor points
        Access: item
        Required: True
    CutOutWindow (object): cut out windows overlapping on wall surfaces
        Access: item
        Required: True
    ShowSurfaceID (object): show surface ID
        Access: item
        Required: True
    ShowConstruction (object): show construction type of surface
        Access: item
        Required: True
    ShowShading (object): show shading information
        Access: item
        Required: True
    AirnodeScale (object): Script variable b18_to_Rhino
        Access: item
        Required: True
    SurfaceScale (object): Script variable b18_to_Rhino
        Access: item
        Required: True

Returns:
    out (object): Log information!!
        Access: item
"""
"""2016-11-15: vhoang
              line 1719: defining roofsurfaces to avoid errors - it was not defined before"""
version='2.2.1'
import Rhino as rc
import scriptcontext as sc
import rhinoscriptsyntax as rs
from clr import AddReference as addr
addr("Grasshopper")
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path
from System import Object
from System import Array
from collections import OrderedDict
import System
rs.EnableRedraw(False)
#START from here the information is extracted from the building description
import re
from collections import defaultdict
from subprocess import Popen
import os
import sys
#optional inputs
Type = 'SHADER'
#FileUrl = r'p:\Darmstadt_Alnatura_140103\Sim-Thermal\150109_Multizone\150723_MZ_WoodRoof\Model\04_DIN\04_DIN.inf'
#FileUrl = r'c:\TRNLizard_dev\Model\Base\Base.inf'
#FileUrl = r'c:\TRNLizard_dev\TestCases\VAR4.b17'
#FileUrl = r'c:\TRNLizard_dev\TestCases\DLR_atrium_1Z_4A.b17'
#BaseInf_template = r'c:\TRNLizard_dev\Templates\ODT_Template20151026.txt'
BaseInf_template = r''
Zone = ''
Category = ''
Data_key = ''
AirnodeCategory = ''
vertex_number = ''
WriteReport = 0
write_odt = WriteReport
Reload = 1
rhino = 1
ShowUVal = ''
if rhino == 0:
    import plotly
    import plotly.graph_objs as go
    import plotly.offline as offline
    import numpy as np
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    head, tail = os.path.split(sys.argv[1])
    FileUrl = sys.argv[1]
else:
    head, tail = os.path.split(FileUrl)
#color definitions
colordef = defaultdict(dict)
colordef['red'] = 'rgb(255, 0, 0)'
colordef['tomato'] = 'rgb(255, 99, 71)'
colordef['deeppink'] = 'rgb(255, 20, 147)'
colordef['brown'] = 'rgb(165, 42, 42)'
colordef['darkturquoise'] = 'rgb(0, 206, 209)'
colordef['blue'] = 'rgb(0, 0, 255)'
colordef['mediumseagreen'] = 'rgb(60, 179, 113)'
colordef['firebrick'] = 'rgb(178, 34, 34)'
colordef['salmon'] = 'rgb(250, 128, 114)'
colordef['yellow'] = 'rgb(255, 255, 0)'
colordef['gold'] = 'rgb(255, 215, 0)'
colordef['lightskyblue'] = 'rgb(135, 206, 250)'
colordef['darkslateblue'] = 'rgb(72, 61, 139)'
colorscatter = ['mediumseagreen']
colorlines = ['tomato','mediumseagreen','darkturquoise','brown','deeppink','red','blue']
colormap = ['firebrick','salmon','yellow','lightskyblue','darkslateblue']
file_folder = '\\'.join(FileUrl.split('\\')[:-1])#to get the directory address without the file name
file_name_base1 = FileUrl.split('\\')[-1]
file_name_base = file_name_base1.split('.')[0]
file_name = '%s\\%s.txt'%(file_folder, file_name_base)
Database_name = file_name_base
output_dir = head + '/Results/'
if os.path.isdir(output_dir) is False:
    os.mkdir(output_dir)
f = open('%s'%FileUrl, 'r')
dummy_data_original = f.readlines() #this is needed because it reread the lines from the beginning everytime getDataParagraph is called
f.close()
#this function gets rid of the ;(line breaker) in text and join the brocken line into 1 line
def cleanBuiLinebreak(data):
    dummy_data = []
    string_coll = ''
    for i, item in enumerate(data):
        if ';' in item:
            item = item.replace(';','')
            item = item.rstrip()
            string_coll = string_coll + item
        elif ';' not in data[i] and ';' in data[i-1]:
            string_coll = string_coll + item
            dummy_data.append(string_coll)
            string_coll = ''
        else:
            dummy_data.append(item)
    return dummy_data
if Reload == 1:
    dummy_data = cleanBuiLinebreak(dummy_data_original)
    if Type != None:
        Type = Type
    else:
        pass
    if Zone != None:
        Zone = Zone.upper()
    else:
        pass
    if Category != None:
        Category = Category.upper()
    else:
        pass
    if Data_key != None:
        Data_key = Data_key.upper()
    else:
        pass
    if AirnodeCategory != None:
        AirnodeCategory = AirnodeCategory.upper()
    else:
        pass
#Chapter 1. This chapter processes building geometry data
def makeVertexDict(inputData):#This module put vertexes into separate dictionaries
    vertex = defaultdict(dict)
    for item in inputData:
        if item.startswith('vertex'):
            key = item.split(' ')[1]
            value = item.split(' ')[2] + ' ' + item.split(' ')[3] + ' ' + item.split(' ')[4]
            vertex[key] = value
        else:
            pass
    return vertex
def vertexToSurface(inputVertex,inputData,vertex): #This module associates vertexes into surfaces
    surfaceVertexes = defaultdict(dict)
    for item in inputData:
        if item.startswith('wall') or item.startswith('window') or item.startswith('roof') or item.startswith('ceiling') or item.startswith('floor'):
            surfid = item.split(' ')[1]
            value = []
            vertex_number = len(item.split(' '))
            for i in range(2,vertex_number):
                key = item.split(' ')[i]
                value.append(key)
            surfaceVertexes[surfid] = value
        else:
            pass
    return surfaceVertexes
def getSurfData (data): #this module is for re-writting surface data into dictionaries
    Collection = defaultdict(dict)
    for itemdata in data:
        ListA = []
        if 'SURF' in itemdata:
            ListA = itemdata.split(':')
            surfID1 = (ListA[1].split('=')[1]).replace(' ','')
            surfID = 'SURFACE ' + surfID1
            for item in ListA:
                try:
                    if 'ADJACENT' in item:
                        key = 'BOUNDARY'
                        value = (item.split('=')[0]).replace(' ','') + ' to zone ' + (item.split('=')[1]).replace(' ','')
                    else:
                        key = (item.split('=')[0]).replace(' ','')
                        value = (item.split('=')[1]).replace(' ','')
                except: #the variable 'EXTERNAL' does not have '=', therefore needs to be treated differently
                    if 'EXTERNAL' in item:
                        key = 'BOUNDARY'
                        value = (item.split('=')[0]).replace(' ','')
                    else:
                        key = 'ADJ_FACE'
                        value = (item.split('=')[0]).replace(' ','')
                Collection[surfID][key] = value
    return Collection
#This module combines the surface data and vertexes together
def combineSurfVertex(SurfData, SurfVertex):
    for item in SurfData:    #Write SurfDataList info into a new library
        for item2 in SurfVertex:   #Merge Vertex info into the same library
            if item.split(' ')[1] == item2:
                surfvertex = ','.join(SurfVertex[item2])
                SurfData[item]['VERTEX'] = surfvertex
    return SurfData
#Chapter 2. This chapter executes the modules for building geometry
#for read the selected data section from Base.inf into ram
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
    #print '%s, %s, no match found!'%(startpattern,stoppattern)
if Reload == 1:
    #for getting all the zones within a model
    zone_names_paragraph = getDataParagraph("Z\so\sn\se\ss", "\sO\sr\si\se\sn\st\sa\st\si\so\sn\ss", dummy_data)
    zone_names_list = zone_names_paragraph[0].split(' ')
    zone_names_list.pop(0)
    #for getting rid of ';', if it is inside the zone list
    for item in zone_names_list:
        if item == '':
            location = zone_names_list.index(item)
            zone_names_list.pop(location)
    airnode_names_list = []
    indices = [i for i, x in enumerate(dummy_data) if "AIRNODE " in x]
    for item in indices:
        airnode_names_list.append(dummy_data[item].split()[1])
    #get the link between ZONE and AIRNODE names
    zone_dict = {}
    zone_names_array = []
    zone_number_array = []
    zone_num = 0
    for item in dummy_data:
        if "ZONE " in item:
            zone_num += 1
            zname = item.split()[1]
            zone_dict[zname] = []
            zone_names_array.append(zname)
            zone_number_array.append(zone_num)
        if "AIRNODE " in item:
            aname = item.split()[1]
            zone_dict[zname].append(aname)
    #for getting vertexes and building geometry data
    TypeDataGeo = []
    zone_paragraphs = defaultdict(dict)
    zone_combineSurfVertex = defaultdict(dict)
    airnode_paragraphs = defaultdict(dict)
    airnode_locations = {}
    vertex = {}
    shader_vertex = {}
    shaderVertexes = defaultdict()
#get daylight sensor points
def getDaylightPoints():
    global getDataParagraph
    global dummy_data
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
                    #print item1
                    point_name = item1.split(' ')[0] + ' ' + item1.split(' ')[1]
                    points = item1.split(' ')[2] + ' ' + item1.split(' ')[3] + ' ' + item1.split(' ')[4]
                    DaylightPoints[item][point_name] = points
            i += 2
    return DaylightPoints
#get comfort and gain sensor points
def getComfortGainPoints():
    global getDataParagraph
    global dummy_data
    ComfortPoints = defaultdict(dict)
    GainPoints = defaultdict(dict)
    zone_list  = []
    zone_positions = []
    f = getDataParagraph("_EXTENSION_GeoPositionGeometry_START_", "_EXTENSION_GeoPositionGeometry_END_", dummy_data)
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
            ComfortPoints[item] = {}
            GainPoints[item] = {}
            zone_start = zone_positions[i]
            zone_end = zone_positions[i+1]
            for item1 in f[zone_start:zone_end+1]:
                if item1.startswith('cgeopos'):
                    point_name = item1.split(' ')[0] + ' ' + item1.split(' ')[1]
                    points = [float(item1.split(' ')[2]),float(item1.split(' ')[3]),float(item1.split(' ')[4])]
                    ComfortPoints[item][point_name] = points
                if item1.startswith('ggeopos'):
                    point_name = item1.split(' ')[0] + ' ' + item1.split(' ')[1]
                    points = [float(item1.split(' ')[2]),float(item1.split(' ')[3]),float(item1.split(' ')[4])]
                    GainPoints[item][point_name] = points
            i += 2
    return (ComfortPoints, GainPoints)
#get Virtual Surfaces
def getVirtualSurfaces():
    global getDataParagraph
    global dummy_data
    VirtualSurfaces = defaultdict(dict)
    zone_list  = []
    zone_positions = []
    f = getDataParagraph("_EXTENSION_VirtualSurfaceGeometry_START_", "_EXTENSION_VirtualSurfaceGeometry_END_", dummy_data)
    if f != None:
        for item in f:
            if item.startswith('airnode'):
                zone_name = item.upper()
                zone_list.append(zone_name)
                zone_positions.append(f.index(item))
                zone_positions.append(f.index(item))
        last_item = f[-1]
        zone_positions.append(f.index(last_item))
        zone_positions = zone_positions[1:]
        i = 0
        for item in zone_list:
            VirtualSurfaces[item] = {}
            zone_start = zone_positions[i]
            zone_end = zone_positions[i+1]
            for item1 in f[zone_start:zone_end+1]:
                if item1.startswith('ceiling') or item1.startswith('floor') or item1.startswith('wall')  or item1.startswith('roof'):
                    point_name = item1.split(' ')[0] + ' ' + item1.split(' ')[1]
                    dummy = item1.split()
                    points = []
                    for ind, item5 in enumerate(dummy):
                        if ind > 1:
                            points.append(item5)
                    VirtualSurfaces[item][point_name] = points
            i += 2
    return (VirtualSurfaces)
#Getting the zone name of the Airnode
def getZoneOfAirnode(aname):
    global zone_dict
    for item in zone_dict:
        for subitem in zone_dict[item]:
            if subitem == aname:
                return item
#Getting all the zone names available
def processZoneSurfVertex():
    global zone_names_list
    global zone_dict
    global airnode_names_list
    global TypeDataGeo
    global zone_paragraphs
    global airnode_paragraphs
    global zone_combineSurfVertex
    global airnode_locations
    global getDataParagraph
    global makeVertexDict
    global vertex
    global vertexToSurface
    global getSurfData
    global combineSurfVertex
    #print airnode_names_list
    for ai,item in enumerate(airnode_names_list):
        #zone_index = airnode_names_list.index(item)
        try: #For all airnodes except the last one
            next_airnode = airnode_names_list[ai + 1]
            airnode_start = r"Z\so\sn\se\s+%s\s+/\s+A\s+i\s+r\s+n\s+o\s+d\s+e\s+%s"%(getZoneOfAirnode(item),item)
            #airnode_start = "Z o n e\s+\S+\s+/  A i r n o d e  %s"%item
            airnode_end = r"Z\so\sn\se\s+%s\s+/\s+A\s+i\s+r\s+n\s+o\s+d\s+e\s+%s"%(getZoneOfAirnode(next_airnode),next_airnode)
            #airnode_end = "Z o n e\s+\S+\s+/  A i r n o d e  %s"%next_airnode
            airnode_paragraph = getDataParagraph(airnode_start, airnode_end, dummy_data)
            if airnode_paragraph[0].startswith('ZONE'):
                zonedef = airnode_paragraph[0:3]
            else:
                airnode_paragraph.insert(0,zonedef[2])
                airnode_paragraph.insert(0,zonedef[1])
                airnode_paragraph.insert(0,zonedef[0])
            airnode_paragraphs['AIRNODE %s'%item] = airnode_paragraph
            airnode_locations['AIRNODE %s'%item] = []
            for i, item1 in enumerate(airnode_paragraph):
                if item1.startswith('AIRNODE'):
                    airnode_location = str(i) + ' ' + item1
                    airnode_locations['AIRNODE %s'%item].append(i)
            last_line_index = len(airnode_paragraph) -1
            airnode_locations['AIRNODE %s'%item].append(last_line_index)
        except: #for the last zone, or the only zone
            last_airnode = airnode_names_list[-1]
            airnode_start = r"Z\so\sn\se\s+%s\s+/\s+A\s+i\s+r\s+n\s+o\s+d\s+e\s+%s"%(getZoneOfAirnode(last_airnode),last_airnode)
            try:
                airnode_end = " CAPACITANCE"
                airnode_paragraph = getDataParagraph(airnode_start, airnode_end, dummy_data)
                if airnode_paragraph[0].startswith('ZONE'):
                    zonedef = airnode_paragraph[0:3]
                else:
                    airnode_paragraph.insert(0,zonedef[2])
                    airnode_paragraph.insert(0,zonedef[1])
                    airnode_paragraph.insert(0,zonedef[0])
                airnode_paragraphs['AIRNODE %s'%item] = airnode_paragraph
                airnode_locations['AIRNODE %s'%item] = []
                for i, item1 in enumerate(airnode_paragraph):
                    if item1.startswith('AIRNODE'):
                        #airnode_location = str(i) + ' ' + item1
                        airnode_locations['AIRNODE %s'%item].append(i)
                last_line_index = len(airnode_paragraph) -1
                airnode_locations['AIRNODE %s'%item].append(last_line_index)
            except:
                airnode_end = "CAPACITANCE"
                airnode_paragraph = getDataParagraph(airnode_start, airnode_end, dummy_data)
                #print airnode_paragraph
                if airnode_paragraph[0].startswith('ZONE'):
                    zonedef = airnode_paragraph[0:3]
                else:
                    airnode_paragraph.insert(0,zonedef[2])
                    airnode_paragraph.insert(0,zonedef[1])
                    airnode_paragraph.insert(0,zonedef[0])
                airnode_paragraphs['AIRNODE %s'%item] = airnode_paragraph
                airnode_locations['AIRNODE %s'%item] = []
                for i, item1 in enumerate(airnode_paragraph):
                    if item1.startswith('AIRNODE'):
                        #airnode_location = str(i) + ' ' + item1
                        airnode_locations['AIRNODE %s'%item].append(i)
                last_line_index = len(airnode_paragraph) -1
                airnode_locations['AIRNODE %s'%item].append(last_line_index)
    #print airnode_paragraphs
    f_paragraph1 = getDataParagraph("_EXTENSION_BuildingGeometry_START_", "_EXTENSION_BuildingGeometry_END_", dummy_data)
    for item in f_paragraph1:
        TypeDataGeo.append(item)
    vertex = makeVertexDict(TypeDataGeo)
    #Compile the surface and vertex info for all of the zones into one defaultdict
    for item in airnode_paragraphs:
        surfaceVertexes = vertexToSurface(vertex, TypeDataGeo, vertex)
        SurfaceData = getSurfData (airnode_paragraphs['%s'%item])
        combineSurfVertex1 = combineSurfVertex(SurfaceData, surfaceVertexes)
        zone_combineSurfVertex['%s'%item] = combineSurfVertex1
if Reload == 1:
    processZoneSurfVertex()
#Getting all the shader geometry
def getshaderGeo():
    global getDataParagraph
    global makeVertexDict
    global vertexToSurface
    global shader_vertex
    global shaderVertexes
    shader_paragraph =  getDataParagraph("_EXTENSION_ExternalShadingGeometry_START_", "_EXTENSION_ExternalShadingGeometry_END_", dummy_data)
    shader_vertex = makeVertexDict(shader_paragraph)
    for item in shader_paragraph:
        if item.startswith('shader'):
            surfid = 'SHADER ' + str(item.split(' ')[1])
            value = []
            vertex_number = len(item.split(' '))
            for i in range(2,vertex_number):
                key = item.split(' ')[i]
                value.append(key)
            shaderVertexes[surfid] = value
        else:
            pass
if Reload == 1:
    getshaderGeo()
    #combine vertex dict and shader_vertex dict together
    for item in shader_vertex:
        vertex[item] = shader_vertex[item]
#for getting the U-values of each wall construction, directly copied from CF's script for Geometry output in Lizard
uvalues = {}
def getUvalues():
    global dummy_data
    global uvalues
    UVALUE_REGEX=r'\s+WALL\s+\S+\s+U='
    patternuvalue = re.compile(UVALUE_REGEX, re.UNICODE)
    for line in dummy_data:
        for match in patternuvalue.findall(line):
            mu = re.search('WALL\s+(.+)\s+U=\s+(.+)\s+W/m2K', line)
            if mu is not None:
                if '_W1' in mu.group(1):
                    dummy = 1 / (1/float(mu.group(2)) - 0.17)
                elif '_W2' in mu.group(1):
                    uvalues[mu.group(1).split('_W2')[0]] = 1/( 1/ (1/ (1/float(mu.group(2)) - 0.17)) + 1/dummy + 0.17)
                else:
                    uvalues[mu.group(1).strip()] = float(mu.group(2))
if Reload == 1:
    getUvalues()
#Scripts for printing out the info about zones
#for item in zone_paragraphs:
    #print item
#for item in zone_combineSurfVertex:
#    print "x"*20
#    print item
#    for item1 in zone_combineSurfVertex['%s'%item]:
#        print ' ' + item1
#        for item2 in zone_combineSurfVertex['%s'%item]['%s'%item1]:
#            print '   ' + item2 + ' ' + zone_combineSurfVertex['%s'%item]['%s'%item1]['%s'%item2]
#Chapter 3. This chapter writes all of the base.inf into a single defaultdict structure
#for putting all of BaseInf data into 1 single dictionary
def BaseInfData(type_dict_name):
    global TypeDataFull
    datalist = defaultdict(dict)
    for item in TypeDataFull.values(): #for selecting all the sub data of the chosen material
        for a in item:
            if a.startswith('%s '%type_dict_name):
                i = item.index(a)+1
                try:
                    while item[i].startswith(' '):
                        singleData = item[i].split(':')
                        for item2 in singleData:
                            key = (item2.split('=')[0]).replace(' ','')
                            content = item2.split('=')[1]
                            datalist['%s'%a][key] = content
                        i += 1
                except:
                    pass
    return datalist
#for getting all of the Radiationmode data
def RadiationmodeData(input_data1, type_dict_name):
    datalist = defaultdict(dict)
    for item in input_data1: #for selecting all the sub data of the chosen material
        try:
            if item.startswith('%s' %type_dict_name):
                i = input_data1.index(item)+2
                singleData = input_data1[i].split(':')
                for item2 in singleData:
                    key = (item2.split('=')[0]).replace(' ','')
                    content = item2.split('=')[1]
                    datalist['%s'%item][key] = content
            i += 1
        except:
            pass
        return datalist['%s'%item]
if Reload == 1:
    #Put all the search start and finish in 1 dict
    SearchLimit = defaultdict(list)
    s = [('LAYER','L a y e r s'),('LAYER','I n p u t s'),('SCHEDULE','S c h e d u l e s'),('SCHEDULE','W a l l s|C O N S T R U C T I O N'),('WALL','W a l l s|C O N S T R U C T I O N'),('WALL','W i n d o w s'),('CONSTRUCTION','C O N S T R U C T I O N'),('CONSTRUCTION','W i n d o w s'),('WINDOW','W i n d o w s'),('WINDOW','D e f a u l t  G a i n s|G a i n s'),('GAIN','O t h e r  G a i n s|G a i n s'),('GAIN','C o m f o r t'),('COMFORT','C o m f o r t'),('COMFORT','I n f i l t r a t i o n'),('INFILTRATION','I n f i l t r a t i o n'),('INFILTRATION','V e n t i l a t i o n'),('VENTILATION','V e n t i l a t i o n'),('VENTILATION','C o o l i n g'),('COOLING','C o o l i n g'),('COOLING','H e a t i n g'),('HEATING','H e a t i n g'),('HEATING','Z o n e s')]
    for k, v in s:
        SearchLimit[k].append(v)
#Put all the base.inf data into 1 dictionary
TypeDataFull = {}
def AllinOne(limit):
    global TypeDataFull
    for item in limit:
        f_start = limit['%s'%item][0]
        f_finish = limit['%s'%item][1]
        f_start = re.sub('\s+',r'\s+',f_start)
        f_finish = re.sub('\s+',r'\s+',f_finish)
        full_paragraph = getDataParagraph('%s'%f_start, '%s'%f_finish, dummy_data)
        if full_paragraph != None:
            TypeDataFull['%s'%item] = full_paragraph
if Reload == 1:
    AllinOne(SearchLimit)
    #Generate the multi-level Baseinf dictionary
    BaseInf = defaultdict(dict)
    for item in TypeDataFull:
        BaseInf['%s'%item] = BaseInfData('%s' %item)
    #Append Shader Geometry into BaseInf
    BaseInf['SHADER'] = shaderVertexes
    #Append vertex into BaseInf
    BaseInf['VERTEX'] = vertex
    #Append Daylight sensor points into BaseInf
    BaseInf['DAYLIGHT_POINTS'] = getDaylightPoints()
    #Append Comfort and Gain sensor points into BaseInf
    BaseInf['COMFORT_POINTS'], BaseInf['GAIN_POINTS'] = getComfortGainPoints()
    #Append Virtual Surfaces into BaseInf
    BaseInf['VIRTUAL_SURFACES'] = getVirtualSurfaces()
#print BaseInf['VIRTUAL_SURFACES']
#Add each Radiationmode and Airnode subsection into BaseInf, plus airnode volume
def AddRadiationAirnode(airnode_content):
    global BaseInf
    global zone_combineSurfVertex
    global RadiationmodeData
    global airnode_locations
    global uvalues
    for item in airnode_content:
        i=0
        BaseInf['AIRNODE']['%s'%item] = {}
        for item1 in airnode_content['%s'%item]:
            if item1.startswith('ZONE'):
                BaseInf['AIRNODE']['%s'%item]['%s'%item1] = {}
                if 1 > 0:
                    for item2 in airnode_content['%s'%item]:
                        if item2.startswith('WALL') or item2.startswith('WINDOW') or item2.startswith('ROOF') or item2.startswith('CEILING') or item2.startswith('FLOOR'):
                            surface = (item2.split(':')[1]).replace(' ','')
                            surface_number = 'SURFACE ' + str(surface.split('=')[1])
                            #print surface_number
                            BaseInf['AIRNODE'][item][item1][surface_number] = zone_combineSurfVertex['%s'%item][surface_number]
                            #print item
                            #print item1
                            if bool(uvalues) == True:
                                if 'WALL' in BaseInf['AIRNODE'][item][item1][surface_number]:
                                    wall_name = BaseInf['AIRNODE'][item][item1][surface_number]['WALL']
                                    BaseInf['AIRNODE'][item][item1][surface_number]['U-VALUE'] = str(uvalues['%s'%wall_name])
                                else:
                                    pass
                            else:
                                pass
                        if 'VOLUME' in item2:
                            airnode_volume = (item2.split(':')[1]).replace(' ','')
                            volume_value = str(airnode_volume.split('=')[1]) + ' m3'
                            BaseInf['AIRNODE'][item][item1]['VOLUME'] = volume_value
                else:
                    pass
                i+=1
        BaseInf['RADIATIONMODE']['%s'%item] = RadiationmodeData(airnode_paragraphs['%s'%item],'ZONE')
if Reload == 1:
    AddRadiationAirnode(airnode_paragraphs)
#this functions uses the surface information to get a brep surface
def verticesToSurface(local_vertex):
    global vertex
    local_vertex = local_vertex.split(',')
    dummy = []
    for single_vertex in local_vertex:
        if single_vertex == '':
            pass
        else:
            single_vertex_3d = vertex[single_vertex].split(' ')
            single_vertex_3d1 = []
            for item3 in single_vertex_3d:
                single_vertex_3d1.append(float(item3))
            point = rc.Geometry.Point3d(single_vertex_3d1[0],single_vertex_3d1[1],single_vertex_3d1[2])
            dummy.append(point)
    dummy.append(dummy[0])
    polyline = rc.Geometry.Polyline(dummy)
    return rc.Geometry.Brep.CreatePlanarBreps(polyline.ToNurbsCurve())
#this functions uses the vertexno to get the surface vertices
def verticesnoToSurfaceVertices(local_vertex):
    global vertex
    local_vertex = local_vertex.split(',')
    dummy = []
    for single_vertex in local_vertex:
        if single_vertex == '':
            pass
        else:
            single_vertex_3d = vertex[single_vertex].split(' ')
            single_vertex_3d1 = []
            for item3 in single_vertex_3d:
                single_vertex_3d1.append(float(item3))
            point = [single_vertex_3d1[0],single_vertex_3d1[1],single_vertex_3d1[2]]
            dummy.append(point)
    #dummy.append(dummy[0])
    return dummy
#this functions is used to define the geometry information for Rhino
def getBreps():
    global BaseInf
    global rhino
    BaseInf['GEOMETRY'] = defaultdict()
    BaseInf['GEOMETRY']['SHADER'] = []
    BaseInf['GEOMETRY']['GEOPOS'] = []
    for key1 in BaseInf['AIRNODE']:
        for key2 in BaseInf['AIRNODE'][key1]:
            if key2 in BaseInf['GEOMETRY']:
                print key1 + key2
                pass
            else:
                BaseInf['GEOMETRY'][key2] = defaultdict()
                if rhino == 1:
                    BaseInf['GEOMETRY'][key2]['BREP'] = rc.Geometry.Brep()
                    BaseInf['GEOMETRY'][key2]['BREP'].UserDictionary.Set('ZONE', key2)
                    BaseInf['GEOMETRY'][key2]['BREP'].UserDictionary.Set('DATA', file_name_base)
        BaseInf['GEOMETRY'][key2][key1] = defaultdict()
        if rhino == 1:
            BaseInf['GEOMETRY'][key2][key1]['BREP'] = rc.Geometry.Brep()
            BaseInf['GEOMETRY'][key2][key1]['BREP'].UserDictionary.Set('AIRNODE', key1)
            BaseInf['GEOMETRY'][key2][key1]['BREP'].UserDictionary.Set('ZONE', key2)
            BaseInf['GEOMETRY'][key2][key1]['BREP'].UserDictionary.Set('VOLUME', BaseInf['AIRNODE'][key1][key2]['VOLUME'])
            BaseInf['GEOMETRY'][key2][key1]['BREP'].UserDictionary.Set('DATA', file_name_base)
        BaseInf['GEOMETRY'][key2][key1]['SURFACE'] = defaultdict()
    #print BaseInf['AIRNODE']
    for key1 in BaseInf['AIRNODE']:
        for key2 in BaseInf['AIRNODE'][key1]:
            for key3 in BaseInf['AIRNODE'][key1][key2]:
                if 'SURFACE' in key3:
                    dummy = key3.split()
                    #print dummy
                    local_vertex = BaseInf['AIRNODE'][key1][key2][key3]['VERTEX']
                    if rhino == 1:
                        if 1 > 0:
                        #try:
                            brep = verticesToSurface(local_vertex)[0]
                            brep.UserDictionary.Set('ZONE', key2)
                            brep.UserDictionary.Set('AIRNODE', key1)
                            brep.UserDictionary.Set('ID', dummy[1])
                            for zi, zname in enumerate(zone_names_array):
                                if zname == key2.split()[-1]:
                                    brep.UserDictionary.Set('ZNR', zone_number_array[zi])
                            #brep.UserDictionary.Set('ID', 19)
                            brep.UserDictionary.Set('DATA', file_name_base)
                            if 'ADJACENT' in BaseInf['AIRNODE'][key1][key2][key3]['BOUNDARY']:
                                brep.UserDictionary.Set('BOUNDARY', 'ADJACENT')
                            if 'WALL' in BaseInf['AIRNODE'][key1][key2][key3]:
                                brep.UserDictionary.Set('TYPE', 'WALL')
                            elif 'WINDOW' in BaseInf['AIRNODE'][key1][key2][key3]:
                                brep.UserDictionary.Set('TYPE', 'WINDOW')
                            elif 'CEILING' in BaseInf['AIRNODE'][key1][key2][key3]:
                                brep.UserDictionary.Set('TYPE', 'CEILING')
                            elif 'FLOOR' in BaseInf['AIRNODE'][key1][key2][key3]:
                                brep.UserDictionary.Set('TYPE', 'FLOOR')
                            elif 'ROOF' in BaseInf['AIRNODE'][key1][key2][key3]:
                                brep.UserDictionary.Set('TYPE', 'ROOF')
                            BaseInf['GEOMETRY'][key2][key1]['SURFACE'][dummy[1]] = brep
                            BaseInf['GEOMETRY'][key2][key1]['BREP'].Append(brep)
                            BaseInf['GEOMETRY'][key2]['BREP'].Append(brep)
                        #except:
                        #    pass
                    else:
                        BaseInf['GEOMETRY'][key2][key1]['SURFACE'][dummy[1]] = verticesnoToSurfaceVertices(local_vertex)
                        #print key2
                        #print key1
                        #print dummy[1]
                        #print verticesnoToSurfaceVertices(local_vertex)
    #get the virtual surfaces into the geometry
    for key1 in BaseInf['GEOMETRY']:
        for key2 in BaseInf['GEOMETRY'][key1]:
            for item in BaseInf['VIRTUAL_SURFACES']:
                dummy = re.sub('  ',' ',item)
                if key2 == dummy:
                    for item2 in BaseInf['VIRTUAL_SURFACES'][item]:
                        dummy = item2.split()
                        local_vertex = ','.join(str(x) for x in BaseInf['VIRTUAL_SURFACES'][item][item2])
                        if rhino == 1:
                            brep = verticesToSurface(local_vertex)[0]
                            brep.UserDictionary.Set('ZONE', key1)
                            brep.UserDictionary.Set('AIRNODE', key2)
                            #brep.UserDictionary.Set('ID', dummy[1])
                            brep.UserDictionary.Set('ID', 18)
                            brep.UserDictionary.Set('DATA', file_name_base)
                            brep.UserDictionary.Set('TYPE', 'VIRTUAL')
                            BaseInf['GEOMETRY'][key1][key2]['SURFACE'][dummy[1]] = brep
                            BaseInf['GEOMETRY'][key1][key2]['BREP'].Append(brep)
                            BaseInf['GEOMETRY'][key1]['BREP'].Append(brep)
                        else:
                            BaseInf['GEOMETRY'][key1][key2]['SURFACE'][dummy[1]] = verticesnoToSurfaceVertices(local_vertex)
    for key1 in BaseInf['SHADER']:
        dummy = key1.split()
        local_vertex = ','.join(str(x) for x in BaseInf['SHADER'][key1])
        if rhino == 1:
            try:
                brep = verticesToSurface(local_vertex)[0]
                brep.UserDictionary.Set('ID', dummy[1])
                brep.UserDictionary.Set('DATA', file_name_base)
                brep.UserDictionary.Set('TYPE', 'SHADER')
                BaseInf['GEOMETRY']['SHADER'].append(brep)
            except:
                pass
    for key1 in BaseInf['COMFORT_POINTS']:
        for key2 in BaseInf['COMFORT_POINTS'][key1]:
            dummy = key2.split()
            if rhino == 1:
                point = rc.Geometry.Point3d(BaseInf['COMFORT_POINTS'][key1][key2][0],BaseInf['COMFORT_POINTS'][key1][key2][1],BaseInf['COMFORT_POINTS'][key1][key2][2])
                sphere = rc.Geometry.Sphere(point,0.1)
                brep = rc.Geometry.Brep.CreateFromSphere(sphere)
                brep.UserDictionary.Set('ID', dummy[1])
                brep.UserDictionary.Set('ZONE', key1)
                brep.UserDictionary.Set('TYPE', 'CGEOPOS')
                BaseInf['GEOMETRY']['GEOPOS'].append(brep)
if Reload == 1:
    getBreps()
#for key in BaseInf['AIRNODE']:
#    for key2 in BaseInf['AIRNODE'][key]:
#        print '#################'
#        print BaseInf['AIRNODE'][key][key2]
"""
for item in BaseInf['AIRNODE']:
    print '+++'
    print item
    for item1 in BaseInf['AIRNODE'][item]:
        print '  ' + item1
        for item2 in BaseInf['AIRNODE'][item][item1]:
            print '        ' + item2
            for item3 in BaseInf['AIRNODE'][item][item1][item2]:
                print '                ' + item3
"""
#for item in BaseInf:
#    print BaseInf[item]
#chapter 4. getting summary info
def writeSummary():
    global BaseInf
    #4.1 getting all of the external walls and windows
    External_wall = []
    External_window = []
    for item in BaseInf['AIRNODE']:
        for item1 in BaseInf['AIRNODE']['%s'%item]:
            for item2 in BaseInf['AIRNODE']['%s'%item]['%s'%item1]:
                #Find external walls
                try:
                    if BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['BOUNDARY'] == 'EXTERNAL' and 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]:
                        externalWall = BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']
                        External_wall.append(externalWall)
                #Find external windows
                    if BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['BOUNDARY'] == 'EXTERNAL' and 'WINDOW' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]:
                        externalWindow = BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']
                        External_window.append(externalWindow)
                except:
                    pass
    BaseInf['SUMMARY']['EXTERNAL WALLS'] = External_wall
    BaseInf['SUMMARY']['EXTERNAL WINDOWS'] = External_window
    """
    print 'External walls: '
    print External_wall
    print 'External windows: '
    print External_window
    """
    #4.2 getting all of the orientations of wall and windows, and store them into separate dictionaries
    #Getting the Wall/Window ratio of each orientation as well
    north = {}
    north['WALL'] = []
    north['FLOOR'] = []
    north['CEILING'] = []
    north['WINDOW'] = []
    north_wall_area = 0.0
    north_window_area = 0.0
    south = {}
    south['WALL'] = []
    south['FLOOR'] = []
    south['CEILING'] = []
    south['WINDOW'] = []
    south_wall_area = 0.0
    south_window_area = 0.0
    east = {}
    east['WALL'] = []
    east['FLOOR'] = []
    east['CEILING'] = []
    east['WINDOW'] = []
    east_wall_area = 0.0
    east_window_area = 0.0
    west = {}
    west['WALL'] = []
    west['FLOOR'] = []
    west['CEILING'] = []
    west['WINDOW'] = []
    west_wall_area = 0.0
    west_window_area = 0.0
    for item in BaseInf['AIRNODE']:
        for item1 in BaseInf['AIRNODE']['%s'%item]:
            for item2 in BaseInf['AIRNODE']['%s'%item]['%s'%item1]:
                if 'ORI' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]:
                    orientation = str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['ORI'])
                    orientation_letter = orientation.split('_')[0]
                    orientation_value = int(orientation.split('_')[1])
                    verticality = int(orientation.split('_')[2])
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'N' and verticality == 90:
                        north['WALL'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        north_wall_area = north_wall_area + area
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'N' and verticality == 180:
                        north['FLOOR'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        north_wall_area = north_wall_area + area
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'N' and verticality == 0:
                        north['CEILING'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        north_wall_area = north_wall_area + area
                    if 'WINDOW' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'N':
                        north['WINDOW'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        north_window_area = north_window_area + area
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'S' and verticality == 90:
                        south['WALL'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        south_wall_area = south_wall_area + area
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'S' and verticality == 180:
                        south['FLOOR'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        south_wall_area = south_wall_area + area
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'S' and verticality == 0:
                        south['CEILING'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        south_wall_area = south_wall_area + area
                    if 'WINDOW' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'S':
                        south['WINDOW'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        south_window_area = south_window_area + area
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'E' and verticality == 90:
                        east['WALL'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        east_wall_area = east_wall_area + area
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'E' and verticality == 180:
                        east['FLOOR'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        east_wall_area = east_wall_area + area
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'E' and verticality == 0:
                        east['CEILING'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        east_wall_area = east_wall_area + area
                    if 'WINDOW' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'E':
                        east['WINDOW'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        east_window_area = east_window_area + area
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'W' and verticality == 90:
                        west['WALL'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        west_wall_area = west_wall_area + area
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'W' and verticality == 180:
                        west['FLOOR'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        west_wall_area = west_wall_area + area
                    if 'WALL' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'W' and verticality == 0:
                        west['CEILING'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        west_wall_area = west_wall_area + area
                    if 'WINDOW' in BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2] and orientation_letter == 'W':
                        west['WINDOW'].append(str(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['SURF']))
                        area = float(BaseInf['AIRNODE']['%s'%item]['%s'%item1]['%s'%item2]['AREA'])
                        west_window_area = west_window_area + area
    """
    #Print out the surfaces according to their orientation and type
    print 'NORTH'
    for item in north:
        print item
        print north['%s'%item]
    print ' '
    print 'SOUTH'
    for item in south:
        print item
        print south['%s'%item]
    print ' '
    print 'EAST'
    for item in east:
        print item
        print east['%s'%item]
    print ' '
    print 'WEST'
    for item in west:
        print item
        print west['%s'%item]
    print ' '
    """
    #Calculating the window/wall ratio
    try:
        north_window_wall_ratio = north_window_area / north_wall_area
    except:
        north_window_wall_ratio = 0.0
        pass
    try:
        south_window_wall_ratio = south_window_area / south_wall_area
    except:
        south_window_wall_ratio = 0.0
        pass
    try:
        east_window_wall_ratio = east_window_area / east_wall_area
    except:
        east_window_wall_ratio = 0.0
        pass
    try:
        west_window_wall_ratio = west_window_area / west_wall_area
    except:
        west_window_wall_ratio = 0.0
        pass
    """
    print north_wall_area, north_window_area
    print north_window_wall_ratio
    print south_wall_area, south_window_area
    print south_window_wall_ratio
    print east_wall_area, east_window_area
    print east_window_wall_ratio
    print west_wall_area, west_window_area
    print west_window_wall_ratio
    """
    #Put into BaseInf dict
    BaseInf['SUMMARY']['NORTH'] = north
    BaseInf['SUMMARY']['NORTH']['WINDOW/WALL RATIO'] = north_window_wall_ratio
    BaseInf['SUMMARY']['SOUTH'] = south
    BaseInf['SUMMARY']['SOUTH']['WINDOW/WALL RATIO'] = south_window_wall_ratio
    BaseInf['SUMMARY']['EAST'] = east
    BaseInf['SUMMARY']['EAST']['WINDOW/WALL RATIO'] = east_window_wall_ratio
    BaseInf['SUMMARY']['WEST'] = west
    BaseInf['SUMMARY']['WEST']['WINDOW/WALL RATIO'] = west_window_wall_ratio
if Reload == 2:
    writeSummary()
    #chapter 5. output in GH
    #5.1 Output the entire dictionary
    #for k, v in BaseInf.items():
    #    print k
    #    print v
    #5.2 Accessing the data dictionary with GH input
    TypeList = BaseInf['%s'%Type]
    if Type == 'AIRNODE':
        try:
            SelectedZone = BaseInf['AIRNODE']['%s'%Zone]
        except:
            pass
        try:
            SelectedCategory = BaseInf['AIRNODE']['%s'%Zone]['%s'%Category]
        except:
            pass
        try:
            SelectedData = BaseInf['AIRNODE']['%s'%Zone]['%s'%Category]['%s'%Data_key]
        except:
            pass
        try:
            AirnodeData = BaseInf['AIRNODE']['%s'%Zone]['%s'%Category]['%s'%Data_key]['%s'%AirnodeCategory]
        except:
            pass
        try:
            VertexValue = vertex['%s'%vertex_number]
        except:
            pass
    else:
        try:
            SelectedCategory = BaseInf['%s'%Type]['%s'%Category]
        except:
            pass
        try:
            SelectedData = BaseInf['%s'%Type]['%s'%Category]['%s'%Data_key]
        except:
            pass
        try:
            VertexValue = vertex['%s'%vertex_number]
        except:
            pass
    #chapter 6. write all the data in a .txt file which is easy to read for the users
#writting the content into a .txt
def WriteTxt():
    global file_name
    global BaseInf
    f1 = open(file_name,'w')
    for item in BaseInf:
        #Because Airnode chapter has a deeper structure, so it will be written differently
        """if item == 'AIRNODE':
            f1.write(item + '\n')
            for item1 in BaseInf['%s'%item]:
                f1.write('  ' + item1 + '\n')
                for item2 in BaseInf['%s'%item]['%s'%item1]:
                    f1.write('    ' + item2 + '\n')
                    f1.write('      ' + 'VOLUME: ' + BaseInf['%s'%item]['%s'%item1]['%s'%item2]['VOLUME'] + '\n')
                    for item3 in BaseInf['%s'%item]['%s'%item1]['%s'%item2]:
                        if item3 != 'VOLUME':
                            item3_value = str(BaseInf['%s'%item]['%s'%item1]['%s'%item2]['%s'%item3])
                            f1.write('      ' + item3 + ': ' + item3_value + '\n')
                    f1.write('\n')
            f1.write('---------------------------------------------------------------------\n' + '\n')
        """
        #For writting the Summary Chapter
        if item == 'SUMMARY':
            f1.write(item + '\n')
            f1.write('  ' + 'EXTERNAL WINDOWS' + '\n')
            f1.write('    ' + str(BaseInf['%s'%item]['EXTERNAL WINDOWS']) + '\n' + '\n')
            f1.write('  ' + 'EXTERNAL WALLS' + '\n')
            f1.write('    ' + str(BaseInf['%s'%item]['EXTERNAL WALLS']) + '\n' + '\n')
            for item1 in BaseInf['%s'%item]:
                if item1 != 'EXTERNAL WALLS' and item1 != 'EXTERNAL WINDOWS':
                    f1.write('  ' + item1 + '\n')
                    f1.write('    ' + 'WINDOW/WALL RATIO' + ': ' + str(BaseInf['%s'%item]['%s'%item1]['WINDOW/WALL RATIO']) + '\n')
                    for item2 in BaseInf['%s'%item]['%s'%item1]:
                        if item2 != 'WINDOW/WALL RATIO':
                            try:
                                f1.write('    ' + item2 + ': ' + str(BaseInf['%s'%item]['%s'%item1]['%s'%item2]) + '\n')
                            except:
                                f1.write('    ' + item2 + ': ' + '\n')
                                pass
                    f1.write('\n')
            f1.write('---------------------------------------------------------------------\n' + '\n')
        """
        #For writting the Shader Chapter
        if item == 'SHADER':
            f1.write(item + '\n')
            for item1 in BaseInf['%s'%item]:
                f1.write('  ' + item1 + ': ' + str(BaseInf['%s'%item]['%s'%item1]) + '\n')
            f1.write('---------------------------------------------------------------------\n' + '\n')
        #The other chapters will be written like this:
        if item != 'AIRNODE' and item != 'SUMMARY' and item != 'SHADER' and item != 'VERTEX' and item != 'DAYLIGHT_POINTS' and item != 'COMFORT_POINTS' and item != 'GAIN_POINTS' and item != 'GEOMETRY':
            f1.write(item + '\n')
            for item1 in BaseInf['%s'%item]:
                f1.write('  ' + item1 + '\n')
                for item2 in BaseInf['%s'%item]['%s'%item1]:
                    item2_value = str(BaseInf['%s'%item]['%s'%item1]['%s'%item2])
                    f1.write('    ' + item2 + ': ' + item2_value + '\n')
                f1.write('\n')
            f1.write('---------------------------------------------------------------------\n' + '\n')
        """
    f1.close()
if Reload == 1:
    if write_odt == 1:
        WriteTxt()
#chapter 7. Write Base.inf into a structured .odt document
def WriteOdt():
    global file_name_base
    global BaseInf_template
    global BaseInf
    global getDataParagraph
    f2 = open('%s'%BaseInf_template, 'r')
    dummy_data1 = f2.readlines()
    BaseInf_output = {}
    for k, v in BaseInf.items():#Output the entire dictionary
        BaseInf_template_section = getDataParagraph('@START_%s'%k, '@STOP_%s'%k, dummy_data1)
        try:
            BaseInf_template_section.remove('@START_%s'%k)
            BaseInf_template_section.remove('@STOP_%s'%k)
            BaseInf_output['%s'%k] = BaseInf_template_section
        except:
            pass
    BaseInf_item1 = []
    #BaseInf_item1_2 = []
    BaseInf_item2 = []
    BaseInf_item3 = []
    BaseInf_output_final = []
    template_name = '%s\\%s_report.txt'%(file_folder, file_name_base)
    f3 = open('%s'%template_name,'w')
    for item in BaseInf:
        #for writting the airnode chapter
        """
        if item == 'AIRNODE': #Write in the airnode_header_1: header for the whole airnode chapter
            BaseInf_template_header = getDataParagraph('@START_HEADER1_%s'%item, '@STOP_HEADER1_%s'%item, dummy_data1)
            BaseInf_template_header.remove('@START_HEADER1_%s'%item)
            BaseInf_template_header.remove('@STOP_HEADER1_%s'%item)
            BaseInf_output_final.append(BaseInf_template_header) 
            for item1 in BaseInf['%s'%item]: #Write in the airnode_header_2: header for each airnode zone
                BaseInf_template_header_zone = getDataParagraph('@START_HEADER_ZONE', '@STOP_HEADER_ZONE', dummy_data1)
                BaseInf_template_header_zone.remove('@START_HEADER_ZONE')
                BaseInf_template_header_zone.remove('@STOP_HEADER_ZONE')
                BaseInf_template_header_zone[0] = item1
                BaseInf_output_final.append(BaseInf_template_header_zone)
                for item2 in BaseInf['%s'%item]['%s'%item1]:
                    BaseInf_template_header2 = getDataParagraph('@START_HEADER2_AIRNODE', '@STOP_HEADER2_AIRNODE', dummy_data1)
                    BaseInf_template_header2.remove('@START_HEADER2_AIRNODE')
                    BaseInf_template_header2.remove('@STOP_HEADER2_AIRNODE')
                    BaseInf_template_header2[0] = item2
                    volume_line = BaseInf_template_header2[2].split('@')
                    volume_line.pop(-1)
                    volume_line.append(BaseInf['%s'%item]['%s'%item1]['%s'%item2]['VOLUME'])
                    volume_line = ''.join(volume_line)
                    BaseInf_template_header2.pop(-1)
                    BaseInf_template_header2.append(volume_line)
                    BaseInf_output_final.append(BaseInf_template_header2)
                    for item3 in BaseInf['%s'%item]['%s'%item1]['%s'%item2]:
                        if item3 != 'VOLUME':
                            BaseInf_output['%s'%item][0] = item3 #write the item name,in this case Surface Name
                            BaseInf_item = BaseInf_output['%s'%item][:]
                            for item4 in BaseInf['%s'%item]['%s'%item1]['%s'%item2]['%s'%item3]: 
                                for item5 in BaseInf_item:
                                    if item4 in item5 and '@' in item5: #write the item values, to avoid iterating over non-item value objects
                                        location = BaseInf_item.index(item5)
                                        item_data = item5.split('@')
                                        item_data[1] = BaseInf['%s'%item]['%s'%item1]['%s'%item2]['%s'%item3]['%s'%item4]
                                        item_data1 = ''.join(item_data)
                                        BaseInf_item[location] = item_data1
                                        BaseInf_item1 = BaseInf_item[:]
                                    for item6 in BaseInf_item1: #deleting the item values which were not updated
                                        if '@' in item6:
                                            location1 = BaseInf_item1.index(item6)  
                                            BaseInf_item1.pop(location1)
                            BaseInf_item1_2 = BaseInf_item1[:]
                            #print BaseInf_item1_2[0]
                            BaseInf_output_final.append(BaseInf_item1_2) #the results are compiled into a list
        """
        #for writting the SUMMARY chapter
        if item == 'SUMMARY':
            try:
                BaseInf_template_header = getDataParagraph('@START_HEADER_%s'%item, '@STOP_HEADER_%s'%item, dummy_data1)
                location1 = BaseInf_template_header.index('@EXTERNAL WALLS')
                external_walls = ', '.join(BaseInf['%s'%item]['EXTERNAL WALLS'])
                BaseInf_template_header[location1] = external_walls
                location2 = BaseInf_template_header.index('@EXTERNAL WINDOWS')
                external_windows = ', '.join(BaseInf['%s'%item]['EXTERNAL WINDOWS'])
                BaseInf_template_header[location2] = external_windows
                BaseInf_template_header.remove('@START_HEADER_%s'%item)
                BaseInf_template_header.remove('@STOP_HEADER_%s'%item)
                BaseInf_output_final.append(BaseInf_template_header)
            except:
                pass
            BaseInf_item =  BaseInf_output['%s'%item][:]
            for item1 in BaseInf['%s'%item]:
                if item1 != 'EXTERNAL WALLS' and item1 != 'EXTERNAL WINDOWS':
                    BaseInf_item1 = BaseInf_item[:]#When iterating changes in a list, please clone the list content, otherwise, the iteration will overwrite the previous result.
                    #Replacing the values which are present from Base.Inf
                    for item_orientation in BaseInf_item1:
                        if item_orientation == '@ORIENTATION':
                            location = BaseInf_item1.index(item_orientation)
                            BaseInf_item1[location] = item1
                    for item2 in BaseInf['%s'%item]['%s'%item1]:
                        for item3 in BaseInf_item1:
                            try:
                                if item2 == item3.split('@')[1]:
                                    location = BaseInf_item1.index(item3)
                                    item_data = item3.split('@')
                                    if type(BaseInf['%s'%item]['%s'%item1]['%s'%item2]) is list:
                                        actual_data = ', '.join(BaseInf['%s'%item]['%s'%item1]['%s'%item2])
                                    else:
                                        actual_data = str(BaseInf['%s'%item]['%s'%item1]['%s'%item2])
                                    item_data[1] = actual_data
                                    item_data = ''.join(item_data)
                                    #print item_data
                                    BaseInf_item1[location] = item_data
                                    BaseInf_item2 = BaseInf_item1[:]
                            except:
                                pass
                            #Deleting the values which are not present from Base.Inf and are not changed
                        for item4 in BaseInf_item2:
                            if '@' in item4:
                                location1 = BaseInf_item2.index(item4)
                                BaseInf_item2.pop(location1)
                                BaseInf_item3 = BaseInf_item2[:]
                            else:
                                BaseInf_item3 = BaseInf_item2[:]#if all the values are updated, the list is copied straight away
                        for item5 in BaseInf_item3:
                            if type(item5) is list: #join sub lists into a single string
                                location2 = BaseInf_item3.index(item5)
                                item_data1 = ', '.join(BaseInf_item3[location2])
                                BaseInf_item3[location2] = item_data1
                                BaseInf_item4 = BaseInf_item3[:]
                            else:
                                BaseInf_item4 = BaseInf_item3[:]#if no more sub lists, the item is copied straight away
                    BaseInf_output_final.append(BaseInf_item4)
        """
        if item == 'SHADER':
            try:
                BaseInf_template_header = getDataParagraph('@START_HEADER_%s'%item, '@STOP_HEADER_%s'%item, dummy_data1)
                BaseInf_template_header.remove('@START_HEADER_%s'%item)
                BaseInf_template_header.remove('@STOP_HEADER_%s'%item)
                BaseInf_output_final.append(BaseInf_template_header) 
            except:
                pass
            for item1 in BaseInf['%s'%item]:
                BaseInf_output['%s'%item][0] = item1
                BaseInf_item = BaseInf_output['%s'%item][:]
                for item3 in BaseInf_item:
                    if '@' in item3:
                        location = BaseInf_item.index(item3)
                        item_data = item3.split('@')
                        shader_data = ', '.join(BaseInf['%s'%item]['%s'%item1])
                        item_data[1] = shader_data
                        item_data = ''.join(item_data)
                        BaseInf_item[location] = item_data
                        BaseInf_item1 = BaseInf_item[:]
                        BaseInf_output_final.append(BaseInf_item1)
        """
        #for writting the other chapters
        if item != 'AIRNODE' and item != 'SUMMARY' and item != 'SHADER' and item != 'VERTEX' and item != 'DAYLIGHT_POINTS' and item != 'COMFORT_POINTS' and item != 'GAIN_POINTS' and item != 'GEOMETRY' and item != 'VIRTUAL_SURFACES':
            try:
                BaseInf_template_header = getDataParagraph('@START_HEADER_%s'%item, '@STOP_HEADER_%s'%item, dummy_data1)
                BaseInf_template_header.remove('@START_HEADER_%s'%item)
                BaseInf_template_header.remove('@STOP_HEADER_%s'%item)
                BaseInf_output_final.append(BaseInf_template_header)
            except:
                pass
            for item1 in BaseInf['%s'%item]:
                BaseInf_output['%s'%item][0] = item1
                BaseInf_item = BaseInf_output['%s'%item][:]#When iterating changes in a list, please clone the list content, otherwise, the iteration will overwrite the previous result.
                #Replacing the values which are present from Base.Inf
                for item2 in BaseInf['%s'%item]['%s'%item1]:
                    for item3 in BaseInf_item:
                        if item2 in item3:
                            location = BaseInf_item.index(item3)
                            item_data = item3.split('@')
                            item_data[1] = BaseInf['%s'%item]['%s'%item1]['%s'%item2]
                            ''.join(item_data)
                            BaseInf_item[location] = item_data
                            BaseInf_item1 = BaseInf_item[:]
                #Deleting the values which are not present from Base.Inf and are not changed
                        for item4 in BaseInf_item1:
                            if '@' in item4:
                                location1 = BaseInf_item1.index(item4)
                                BaseInf_item1.pop(location1)
                                BaseInf_item2 = BaseInf_item1[:]
                            else:
                                BaseInf_item2 = BaseInf_item1[:]#if all the values are updated, the list is copied straight away
                        for item5 in BaseInf_item2:
                            if type(item5) is list: #join sub lists into a single string
                                location2 = BaseInf_item2.index(item5)
                                item_data1 = ''.join(BaseInf_item2[location2])
                                BaseInf_item2[location2] = item_data1
                                BaseInf_item3 = BaseInf_item2[:]
                            else:
                                BaseInf_item3 = BaseInf_item2[:]#if no more sub lists, the item is copied straight away
                BaseInf_output_final.append(BaseInf_item3)
    #write the list into a preformated .txt file in order to transfer into a .odt
    for item in BaseInf_output_final:
        if len(item) == 2:#this is for writting the chapter title
            f3.write('\n\n')
            for item2 in item:
                f3.write('%s\n'%item2)
        else:
            for item2 in item:
                if type(item2) is list: #for writting airnode chapter info
                    for item3 in item2:
                        f3.write('%s\n'%item3)
                    f3.write('\n')
                else: #for writting other chapter info
                    f3.write('%s\n'%item2)
        f3.write('\n\n\n')
    f3.close()
if Reload == 1:
    if BaseInf_template == None:
        pass
    else:
        if write_odt == 1:
            WriteOdt()
        #Converting to .odt document
        #hide_shell = True
        #Popen("rst2odt.py %s\\%s_report.txt %s\\%s_report.odt"%(file_folder, file_name_base, file_folder, file_name_base), shell=hide_shell, stdin=None, stdout=None, stderr=None, close_fds=True)
def plotly3d(geometry):
    noaxis=dict(showbackground=False,
        showline=False,
        zeroline=False,
        showgrid=False,
        showticklabels=False,
        title=''
        )
    mesh=[]
    #minx = 0
    #maxx = 0
    #miny = 0
    #maxy = 0
    #minz = 0
    #maxz = 0
    for zone in geometry:
        for ai,airnode in enumerate(geometry[zone]):
            lgroup = 0
            amesh = []
            for id in geometry[zone][airnode]['SURFACE']:
                if 'SURFACE %s'%id in BaseInf['AIRNODE'][airnode][zone]:
                    pass
                else:
                    #virtual surfaces need to be integrated
                    continue
                x = []
                y = []
                z = []
                base = geometry[zone][airnode]['SURFACE'][id][0]
                vector1 = []
                vector2 = []
                direction = "z"
                for vi,vertex in enumerate(geometry[zone][airnode]['SURFACE'][id]):
                    x.append(float(vertex[0]))
                    y.append(float(vertex[1]))
                    z.append(float(vertex[2]))
                    if vi == 1 and vi > 0:
                        for ix, item in enumerate(base):
                            vector1.append(float(item) - float(vertex[ix]))
                    elif vi > 1:
                        if len(vector2) == 0:
                            for iy, item2 in enumerate(base):
                                vector2.append(float(vertex[iy]) - float(item2))
                            crosspr = np.cross(vector1, vector2)
                            for iz, item3 in enumerate(crosspr):
                                if item3 <> 0 and iz == 0:
                                    direction = "x"
                                if item3 <> 0 and iz == 1:
                                    direction = "y"
                                if item3 <> 0 and iz == 2:
                                    direction = "z"
                x.append(float(geometry[zone][airnode]['SURFACE'][id][0][0]))
                y.append(float(geometry[zone][airnode]['SURFACE'][id][0][1]))
                z.append(float(geometry[zone][airnode]['SURFACE'][id][0][2]))
                #minx = min(x) if min(x) < minx else minx
                #maxx = max(x) if max(x) > maxx else maxx
                #miny = min(y) if min(y) < miny else miny
                #maxy = max(y) if max(y) > maxy else maxy
                #minz = min(z) if min(z) < minz else minz
                #maxz = max(z) if max(z) > maxz else maxz
                bndcond = BaseInf['AIRNODE'][airnode][zone]['SURFACE %s'%id]['BOUNDARY']
                opacity = 0.9
                acolor = colorlines[ai]
                color = colordef['mediumseagreen']
                window = 0
                if direction == 'z':
                    sa = 2
                elif direction == 'y':
                    sa = 1
                else:
                    sa = 0
                if 'EXTERNAL' in bndcond:
                    color = colordef['mediumseagreen']
                if 'INPUT' in bndcond:
                    color = colordef['tomato']
                if 'WINDOW' in BaseInf['AIRNODE'][airnode][zone]['SURFACE %s'%id]:
                    color = colordef['blue']
                    acolor = color
                    opacity = 1
                    window = 1
                showlegend = False
                if lgroup == 0:
                    showlegend = True
                if window == 1:
                    mesh.append(go.Scatter3d(
                        x=x,
                        y=y,
                        z=z,
                        name= airnode,
                        legendgroup=airnode,
                        showlegend=showlegend,
                        line = dict(width=10,color=color),
                        mode='lines',))
                    amesh.append(go.Scatter3d(
                        x=x,
                        y=y,
                        z=z,
                        name = "ID=%s"%id,
                        line = dict(width=5,color=color),
                        mode='lines',))
                else:
                    mesh.append(go.Scatter3d(
                        x=x,
                        y=y,
                        z=z,
                        name= airnode,
                        legendgroup=airnode,
                        showlegend=showlegend,
                        surfaceaxis = sa,
                        surfacecolor=acolor,
                        line = dict(width=1,color='rgba(0,0,0,1)'),
                        mode='lines',))
                    amesh.append(go.Scatter3d(
                        x=x,
                        y=y,
                        z=z,
                        name = "ID=%s"%id,
                        surfaceaxis = sa,
                        surfacecolor=color,
                        line = dict(width=1,color='rgba(0,0,0,1)'),
                        mode='lines',))
                lgroup += 1
            #minxy = min(minx,miny)
            #maxxy = max(maxx,maxy)
            layout = dict(
                title = airnode,
                scene = dict(
                    aspectmode="data",
                    xaxis = dict(
                        showline=False,
                        zeroline=False ,
                        showgrid=False,
                        showticklabels=False,
                        showaxeslabels=False,
                        title='',
                        #range = [minxy-1, maxxy+1]
                        ),
                    yaxis = dict(
                        showline=False,
                        zeroline=False ,
                        showgrid=False,
                        showticklabels=False,
                        showaxeslabels=False,
                        title='',
                        #range = [minxy-1, maxxy+1]
                        ),
                    zaxis = dict(
                        showline=False,
                        zeroline=False ,
                        showgrid=False,
                        showticklabels=False,
                        showaxeslabels=False,
                        title='',
                        #range = [minz-1, minz+maxxy-minxy +1]
                        ),
                    #xaxis=noaxis,
                    #yaxis=noaxis,
                    #zaxis=noaxis,
                )
            )
            fig = dict( data=amesh, layout=layout )
            #plotly.offline.plot(fig, filename='%s.html'%airnode, show_link=False)
    #minxy = min(minx,miny)
    #maxxy = max(maxx,maxy)
    layout = dict(
        title = '3DModel',
        showlegend = True,
        legend = dict(
            orientation = 'h',
            #borderwidth = 5,
            ),
        scene = dict(
            aspectmode="data",
            xaxis = dict(
                showline=False,
                zeroline=False ,
                showgrid=False,
                showticklabels=False,
                title='',
                #range = [minxy-1, maxxy+1]
                ),
            yaxis = dict(
                showline=False,
                zeroline=False ,
                showgrid=False,
                showticklabels=False,
                title='',
                #range = [minxy-1, maxxy+1]
                ),
            zaxis = dict(
                showline=False,
                zeroline=False ,
                showgrid=False,
                showticklabels=False,
                title='',
                #range = [minz-1, minz+maxxy-minxy +1]
                ),
        )
    )
    fig = dict( data=mesh, layout=layout )
    #plotly.offline.plot(fig, filename='3dModel.html', show_link=False, image='svg', image_filename='test', auto_open=True, image_width=1600, image_height=1200)
    plotly.offline.plot(fig, filename='%s3dModel.html'%output_dir, show_link=False, auto_open=True, image_width=1600, image_height=1200)
    #plotly.plotly.image.get(fig)
"""
colordef['red'] = 'rgb(255, 0, 0)'
colordef['tomato'] = 'rgb(255, 99, 71)'
colordef['deeppink'] = 'rgb(255, 20, 147)'
colordef['brown'] = 'rgb(165, 42, 42)'
colordef['darkturquoise'] = 'rgb(0, 206, 209)'
colordef['blue'] = 'rgb(0, 0, 255)'
colordef['mediumseagreen'] = 'rgb(60, 179, 113)'
colordef['firebrick'] = 'rgb(178, 34, 34)'
colordef['salmon'] = 'rgb(250, 128, 114)'
colordef['yellow'] = 'rgb(255, 255, 0)'
colordef['gold'] = 'rgb(255, 215, 0)'
colordef['lightskyblue'] = 'rgb(135, 206, 250)'
colordef['darkslateblue'] = 'rgb(72, 61, 139)'
"""
def plotmpl3d(geometry):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    minx = 0
    maxx = 0
    miny = 0
    maxy = 0
    minz = 0
    maxz = 0
    for zone in geometry:
        for airnode in geometry[zone]:
            for id in geometry[zone][airnode]['SURFACE']:
                x = []
                y = []
                z = []
                verticescoll = []
                for vi,vertex in enumerate(geometry[zone][airnode]['SURFACE'][id]):
                    x.append(float(vertex[0]))
                    y.append(float(vertex[1]))
                    z.append(float(vertex[2]))
                    vertices = (x[-1],y[-1],z[-1])
                    verticescoll.append(vertices)
                verts= [verticescoll]
                PC = Poly3DCollection(verts, alpha = 0.5, color='brown')
                ax.add_collection3d(PC)
                minx = min(x) if min(x) < minx else minx
                maxx = max(x) if max(x) > maxx else maxx
                miny = min(y) if min(y) < miny else miny
                maxy = max(y) if max(y) > maxy else maxy
                minz = min(z) if min(z) < minz else minz
                maxz = max(z) if max(z) > maxz else maxz
    minxy = min(minx,miny)
    maxxy = max(maxx,maxy)
    ax.set_xlim((minxy-1, maxxy+1))
    ax.set_ylim((minxy-1, maxxy+1))
    ax.set_zlim((minz-1, minz+maxxy-minxy +1))
    plt.show()
if rhino == 0:
    pass
    plotly3d(BaseInf['GEOMETRY'])
    #plotmpl3d(BaseInf['GEOMETRY'])
#optional outputs
#TypeList
#SelectedZone
#SelectedCategory
#SelectedData
#AirnodeData
#VertexValue
#END part in order to extract information from the building description file
#for storing the database into sc environment for other scripts to retrieve
sc.sticky['%s'%file_name_base] = BaseInf
#Save the raw data as a list into sc.sticky for printer to retrieve
sc.sticky['%s_raw_data'%file_name_base] = dummy_data
#Save the original file directory for printer to retrieve
sc.sticky['%s_directory'%file_name_base] = file_folder
#Only pass out the key name for the other components to retrieve the database
#here the baking processes are starting
shadersurfaces = []
virtualsurfaces = []
window_ids          = []
comfortpts = []
external_walls      = DataTree[Object]()
boundary_walls      = DataTree[Object]()
identical_walls     = DataTree[Object]()
external_windows    = DataTree[Object]()
adjacent_walls      = DataTree[Object]()
adjacent_windows    = DataTree[Object]()
center_pts          = DataTree[Object]()
id_list             = DataTree[System.Object]()
construction_list   = DataTree[System.Object]()
uval_list           = DataTree[System.Object]()
shading_list        = DataTree[System.Object]()
daylight_points     = []
comfort_points      = []
gain_points         = []
Zone               = DataTree[Object]()
Zone_name = []
Airnode_name = []
airnode_names_list = []
zonearray = []
airnodearray = []
wallsurfaces = []
ceilingsurfaces = []
roofsurfaces = []
floorsurfaces = []
windowsurfaces = []
#Load the BaseInf Database
DatabaseName = Database_name
BaseInf = sc.sticky['%s'%DatabaseName]
#print BaseInf['GEOMETRY']['ZONE Z1']['BREP']
#for k, v in BaseInf.items():
#    print k
#    print v
class Model: #1 Model instance per Zone
    vertices=[]
    layer=[]
    def __init__(self, zone=0):
        self.Zone = ''
        self.Airnode = zone
        self.Aname = ''
        self.Floor = []
        self.FloorVertNo = []
        self.VerticesList  = []
        self.FloorVertices = []
        self.Wall = []
        self.Window = []
        self.Surfaces = []
        self.Daylight_Points = []
        self.Comfort_Points = []
        self.Gain_Points = []
class Construction: #1 Construction instance per Surface
    def __init__(self):
        self.Geometry       = []
        self.Id             = ''
        self.Name           = ''
        self.BoundaryCond   = ''
        self.Type           = ''
        self.Uvalue         = ''
        self.Center         = rc.Geometry.Point3d(0,0,0)
        self.Shading        = ''
#print BaseInf['AIRNODE']
vertex = BaseInf['VERTEX']
#This function generates a surface out of the building vertices
def verticesToSurface(local_vertex):
    global vertex
    #local_vertex = local_vertex.split(',')
    dummy = []
    for single_vertex in local_vertex:
        if single_vertex == '':
            pass
        else:
            single_vertex_3d = vertex[single_vertex].split(' ')
            single_vertex_3d1 = []
            for item3 in single_vertex_3d:
                single_vertex_3d1.append(float(item3))
            point = rc.Geometry.Point3d(single_vertex_3d1[0],single_vertex_3d1[1],single_vertex_3d1[2])
            dummy.append(point)
    dummy.append(dummy[0])
    polyline = rc.Geometry.Polyline(dummy)
    brep = rc.Geometry.Brep.CreatePlanarBreps(polyline.ToNurbsCurve())
    return brep[0]
#This function creates the building geometry from BaseInf database
def getgeometry():
    global BaseInf
    global zonearray
    global airnodearray
    global wallsurfaces
    global ceilingsurfaces
    global floorsurfaces
    global windowsurfaces
    global shadersurfaces
    global virtualsurfaces
    global Zone_name
    global Airnode_name
    global airnode_names_list
    vertex = BaseInf['VERTEX']
    zone_check = []
    for item in BaseInf['AIRNODE']:
        for zitem in BaseInf['AIRNODE'][item]:
            zonename = zitem
        Zone_name.append(zonename)
        Airnode_name.append(item)
        zonearray.append(Model('%s'%Airnode_name[-1]))
        zonearray[-1].Zone = zonename
        #make the daylight_points into geometry points
        try:
            daylight_points2 = []
            for item1 in BaseInf['DAYLIGHT_POINTS']['%s'%item]:
                data = BaseInf['DAYLIGHT_POINTS'][item][item1].split(' ')
                single_point_3d = []
                for single_point_1d in data:
                    single_point_3d.append(float(single_point_1d))
                daylight_point = rs.AddPoint(single_point_3d)
                daylight_points2.append(daylight_point)
            zonearray[-1].Daylight_Points = daylight_points2
        except:
            pass
        #make the comfort_points into geometry points
        try:
            if zonename in zone_check:
                pass
            else:
                dummy = zonename
                comfort_points2 = []
                for item1 in BaseInf['GEOMETRY']['GEOPOS']:
                    #data = BaseInf['COMFORT_POINTS'][dummy][item1]
                    dzone = item1.UserDictionary.TryGetValue('ZONE')[1]
                    dtype = item1.UserDictionary.TryGetValue('TYPE')[1]
                    if dzone == zonename and dtype == 'CGEOPOS':
                        #print item1
                        comfort_points2.append(item1)
                zonearray[-1].Comfort_Points = comfort_points2
        except:
            pass
        #make the gain_points into geometry points
        try:
            if zonename in zone_check:
                pass
            else:
                dummy = zonename
                gain_points2 = []
                for item1 in BaseInf['GAIN_POINTS']['%s'%dummy]:
                    data = BaseInf['GAIN_POINTS'][dummy][item1].split(' ')
                    single_point_3d = []
                    for single_point_1d in data:
                        single_point_3d.append(float(single_point_1d))
                    gain_point = rs.AddPoint(single_point_3d)
                    gain_points2.append(gain_point)
                zonearray[-1].Gain_Points = gain_points2
        except:
            pass
        for item1 in BaseInf['AIRNODE'][item]:
            for item2 in BaseInf['AIRNODE'][item][item1]:
                #create the wall surface geometries
                if item2 != 'VOLUME' and 'WALL' in BaseInf['AIRNODE'][item][item1][item2]:
                    id = BaseInf['AIRNODE'][item][item1][item2]['SURF']
                    #print BaseInf['GEOMETRY'][item1][item]
                    surface_brep = BaseInf['GEOMETRY'][item1][item]['SURFACE'][id]
                    wallsurfaces.append(surface_brep)
                    amass = rc.Geometry.AreaMassProperties.Compute(surface_brep)
                    zonearray[-1].Surfaces.append(Construction())
                    zonearray[-1].Surfaces[-1].Id = BaseInf['AIRNODE'][item][item1][item2]['SURF']
                    zonearray[-1].Surfaces[-1].Geometry = wallsurfaces[-1]
                    zonearray[-1].Surfaces[-1].Type = 'WALL'
                    zonearray[-1].Surfaces[-1].Name = BaseInf['AIRNODE'][item][item1][item2]['WALL']
                    zonearray[-1].Surfaces[-1].BoundaryCond = BaseInf['AIRNODE'][item][item1][item2]['BOUNDARY']
                    try:
                        zonearray[-1].Surfaces[-1].Uvalue = BaseInf['AIRNODE'][item][item1][item2]['U-VALUE']
                    except:
                        pass
                    zonearray[-1].Surfaces[-1].Center = amass.Centroid
                #create the roof surface geometries
                if item2 != 'VOLUME' and 'ROOF' in BaseInf['AIRNODE'][item][item1][item2]:
                    id = BaseInf['AIRNODE'][item][item1][item2]['SURF']
                    surface_brep = BaseInf['GEOMETRY'][item1][item]['SURFACE'][id]
                    roofsurfaces.append(surface_brep)
                    amass = rc.Geometry.AreaMassProperties.Compute(surface_brep)
                    zonearray[-1].Surfaces.append(Construction())
                    zonearray[-1].Surfaces[-1].Id = BaseInf['AIRNODE'][item][item1][item2]['SURF']
                    zonearray[-1].Surfaces[-1].Geometry = roofsurfaces[-1]
                    zonearray[-1].Surfaces[-1].Type = 'ROOF'
                    zonearray[-1].Surfaces[-1].Name = BaseInf['AIRNODE'][item][item1][item2]['ROOF']
                    zonearray[-1].Surfaces[-1].BoundaryCond = BaseInf['AIRNODE'][item][item1][item2]['BOUNDARY']
                    try:
                        zonearray[-1].Surfaces[-1].Uvalue = BaseInf['AIRNODE'][item][item1][item2]['U-VALUE']
                    except:
                        pass
                    zonearray[-1].Surfaces[-1].Center = amass.Centroid
                #create the ceiling surface geometries
                if item2 != 'VOLUME' and 'CEILING' in BaseInf['AIRNODE'][item][item1][item2]:
                    id = BaseInf['AIRNODE'][item][item1][item2]['SURF']
                    surface_brep = BaseInf['GEOMETRY'][item1][item]['SURFACE'][id]
                    ceilingsurfaces.append(surface_brep)
                    amass = rc.Geometry.AreaMassProperties.Compute(surface_brep)
                    zonearray[-1].Surfaces.append(Construction())
                    zonearray[-1].Surfaces[-1].Id = BaseInf['AIRNODE'][item][item1][item2]['SURF']
                    zonearray[-1].Surfaces[-1].Geometry = ceilingsurfaces[-1]
                    zonearray[-1].Surfaces[-1].Type = 'CEILING'
                    zonearray[-1].Surfaces[-1].Name = BaseInf['AIRNODE'][item][item1][item2]['CEILING']
                    zonearray[-1].Surfaces[-1].BoundaryCond = BaseInf['AIRNODE'][item][item1][item2]['BOUNDARY']
                    try:
                        zonearray[-1].Surfaces[-1].Uvalue = BaseInf['AIRNODE'][item][item1][item2]['U-VALUE']
                    except:
                        pass
                    zonearray[-1].Surfaces[-1].Center = amass.Centroid
                #create the floor surface geometries
                if item2 != 'VOLUME' and 'FLOOR' in BaseInf['AIRNODE'][item][item1][item2]:
                    id = BaseInf['AIRNODE'][item][item1][item2]['SURF']
                    surface_brep = BaseInf['GEOMETRY'][item1][item]['SURFACE'][id]
                    floorsurfaces.append(surface_brep)
                    amass = rc.Geometry.AreaMassProperties.Compute(surface_brep)
                    zonearray[-1].Surfaces.append(Construction())
                    zonearray[-1].Surfaces[-1].Id = BaseInf['AIRNODE'][item][item1][item2]['SURF']
                    zonearray[-1].Surfaces[-1].Geometry = floorsurfaces[-1]
                    zonearray[-1].Surfaces[-1].Type = 'FLOOR'
                    zonearray[-1].Surfaces[-1].Name = BaseInf['AIRNODE'][item][item1][item2]['FLOOR']
                    zonearray[-1].Surfaces[-1].BoundaryCond = BaseInf['AIRNODE'][item][item1][item2]['BOUNDARY']
                    try:
                        zonearray[-1].Surfaces[-1].Uvalue = BaseInf['AIRNODE'][item][item1][item2]['U-VALUE']
                    except:
                        pass
                    zonearray[-1].Surfaces[-1].Center = amass.Centroid
                #create the window surface geometries
                if item2 != 'VOLUME' and 'WINDOW' in BaseInf['AIRNODE'][item][item1][item2]:
                    id = BaseInf['AIRNODE'][item][item1][item2]['SURF']
                    surface_brep = BaseInf['GEOMETRY'][item1][item]['SURFACE'][id]
                    windowsurfaces.append(surface_brep)
                    amass = rc.Geometry.AreaMassProperties.Compute(surface_brep)
                    zonearray[-1].Surfaces.append(Construction())
                    zonearray[-1].Surfaces[-1].Id = BaseInf['AIRNODE'][item][item1][item2]['SURF']
                    zonearray[-1].Surfaces[-1].Geometry = windowsurfaces[-1]
                    zonearray[-1].Surfaces[-1].Type = 'WINDOW'
                    zonearray[-1].Surfaces[-1].Name = BaseInf['AIRNODE'][item][item1][item2]['WINDOW']
                    zonearray[-1].Surfaces[-1].BoundaryCond = BaseInf['AIRNODE'][item][item1][item2]['BOUNDARY']
                    zonearray[-1].Surfaces[-1].Center = amass.Centroid + surface_brep.Faces[0].NormalAt(0,0)
                    if 'ESHADE' in BaseInf['AIRNODE'][item][item1][item2]:
                        zonearray[-1].Surfaces[-1].Shading = 'ESHADE::' + BaseInf['AIRNODE'][item][item1][item2]['ESHADE']
                    if 'ISHADE' in BaseInf['AIRNODE'][item][item1][item2]:
                        zonearray[-1].Surfaces[-1].Shading = 'ISHADE::' + BaseInf['AIRNODE'][item][item1][item2]['ISHADE']
        zone_check.append(zonename)
    #create shader geometries
    for item in BaseInf['GEOMETRY']['SHADER']:
        shadersurfaces.append(item)
    #create virtual surfaces geometries
    for item in BaseInf['VIRTUAL_SURFACES']:
        for subitem in BaseInf['VIRTUAL_SURFACES'][item]:
            local_vertex = BaseInf['VIRTUAL_SURFACES'][item][subitem]
            brep = verticesToSurface(local_vertex)
            virtualsurfaces.append(brep)
getgeometry()
#This part is for outputting all the associated data in a GH tree structure
zonegeo = defaultdict()
solid = []
for i in range(len(zonearray)):
    #create the tree structure, each branch is 1 zone
    p = GH_Path(i)
    #zonevol = rc.Geometry.Brep()
    #for item in zonearray[i].Surfaces:
    #    zonevol.Append(item.Geometry)
    data = []
    for item in zonearray[i].Surfaces:
        if (item.Type == 'WALL' or item.Type == 'CEILING' or item.Type == 'ROOF' or item.Type == 'FLOOR') and item.BoundaryCond == 'EXTERNAL':
            data.append(item.Geometry)
            #data.append(item.Id)
    external_walls.AddRange(data, p)
    data = []
    for item in zonearray[i].Surfaces:
       if (item.Type == 'WALL' or item.Type == 'CEILING' or item.Type == 'ROOF' or item.Type == 'FLOOR') and item.BoundaryCond != 'EXTERNAL' and item.BoundaryCond != 'IDENTICAL' and 'ADJACENT' not in item.BoundaryCond:
           data.append(rs.coercebrep(item.Geometry))
           #data.append(item.Id)
    boundary_walls.AddRange(data, p)
    data = []
    for item in zonearray[i].Surfaces:
       if (item.Type == 'WALL' or item.Type == 'CEILING' or item.Type == 'ROOF' or item.Type == 'FLOOR') and item.BoundaryCond == 'IDENTICAL':
           data.append(rs.coercebrep(item.Geometry))
           #data.append(item.Id)
    identical_walls.AddRange(data, p)
    data = []
    for item in zonearray[i].Surfaces:
       if (item.Type == 'WALL' or item.Type == 'CEILING' or item.Type == 'ROOF' or item.Type == 'FLOOR') and 'ADJACENT' in item.BoundaryCond:
           data.append(rs.coercebrep(item.Geometry))
           #data.append(item.Id)
    adjacent_walls.AddRange(data, p)
    data = []
    for item in zonearray[i].Surfaces:
       if item.Type == 'WINDOW' and item.BoundaryCond == 'EXTERNAL':
           data.append(rs.coercebrep(item.Geometry))
           #data.append(item.Id)
    external_windows.AddRange(data, p)
    data = []
    for item in zonearray[i].Surfaces:
       if item.Type == 'WINDOW' and 'ADJACENT' in item.BoundaryCond:
           data.append(rs.coercebrep(item.Geometry))
           #data.append(item.Id)
    adjacent_windows.AddRange(data, p)
    data = []
    for item in zonearray[i].Daylight_Points:
        data.append(item)
    daylight_points.extend(data)
    data = []
    for item in zonearray[i].Comfort_Points:
        data.append(item)
    comfort_points.extend(data)
    data = []
    for item in zonearray[i].Gain_Points:
        data.append(item)
    gain_points.extend(data)
    points = []
    idlist = []
    constrlist = []
    uvallist = []
    shdlist = []
    solid.append(rc.Geometry.Brep())
    origin = rc.Geometry.Point3d(0,0,0)
    airnodescalefactor = AirnodeScale
    surfacecalefactor = SurfaceScale
    scl = rc.Geometry.Transform.Scale(origin,airnodescalefactor)
    for item in external_walls.Branch(i):
        solid[i].Append(item)
    for item in boundary_walls.Branch(i):
        solid[i].Append(item)
    for item in identical_walls.Branch(i):
        solid[i].Append(item)
    for item in adjacent_walls.Branch(i):
        solid[i].Append(item)
    volprop = rc.Geometry.VolumeMassProperties.Compute(solid[i])
    acenter = volprop.Centroid
    line = rc.Geometry.Line(origin, acenter)
    oldto = line.To
    line.Transform(scl)
    newto = line.To
    vec = newto - oldto
    movevect = rc.Geometry.Vector3d(vec)
    scl2 = rc.Geometry.Transform.Scale(acenter,surfacecalefactor)
    for item in zonearray[i].Surfaces:
        if item.Type == 'WINDOW':
            window_ids.append(item.Id)
        points.append(item.Center)
        newpoint = rc.Geometry.Point3d.Add(points[-1],movevect)
        scenter = newpoint
        line = rc.Geometry.Line(acenter, scenter)
        oldto = line.To
        line.Transform(scl2)
        newto = line.To
        vec2 = newto - oldto
        movevect2 = rc.Geometry.Vector3d(vec2)
        newpoint = rc.Geometry.Point3d.Add(newpoint,movevect2)
        points[-1] = newpoint
        idlist.append(item.Id)
        constrlist.append(item.Name)
        shdlist.append(item.Shading)
        if item.Uvalue == '':
            if item.Type == 'WINDOW':
                uvallist.append('window')
            else:
                uvallist.append('not defined')
        else:
            uvallist.append(item.Uvalue)
    center_pts.AddRange(points, p)
    id_list.AddRange(idlist, p)
    construction_list.AddRange(constrlist, p)
    uval_list.AddRange(uvallist, p)
    shading_list.AddRange(shdlist, p)
    if zonearray[i].Zone in zonegeo:
        pass
    else:
        zonegeo[zonearray[i].Zone] = rc.Geometry.Brep()
    #combine information in one brep
    abstol = sc.doc.ModelAbsoluteTolerance
    dummysurfaces = []
    for item in zonearray[i].Surfaces:
        #dummysurfaces.append(rs.coercebrep(item.Geometry))
        zonegeo[zonearray[i].Zone].Append(rs.coercebrep(item.Geometry))
    #zonegeo[zonearray[i].Zone] = rc.Geometry.Brep.CreateSolid(dummysurfaces, abstol)
for i,name in enumerate(zonegeo):
    data = zonegeo[name]
    data.UserDictionary.Set('NAME', name)
    data.UserDictionary.Set('ZONE', name)
    data.UserDictionary.Set('DATA', '%s'%DatabaseName)
    data.UserDictionary.Set('TYPE', 'ZONE')
    p = GH_Path(i)
    Zone.AddRange([data], p)
#Zone.UserDictionary.Set("ZONES", 'TEST')
#from here on the bake geometry starts
sc.doc = rc.RhinoDoc.ActiveDoc
def bake_Points(daylight_points,comfort_points,gain_points):
    if len(daylight_points) == 0 and len(comfort_points) == 0 and len(gain_points) == 0:
        pass
    else:
        layertable = sc.doc.Layers
        layerindex = layertable.Find('TRNLizard_Sensor_Points',True)
        if layerindex > 0:
            found_objects = rs.ObjectsByLayer('TRNLizard_Sensor_Points')
            rs.DeleteObjects(found_objects)
        else:
            rs.AddLayer('TRNLizard_Sensor_Points')
    if len(daylight_points) == 0:
        pass
    else:
        layertable = sc.doc.Layers
        layerindex = layertable.Find('DAYLIGHT POINTS',True)
        if layerindex > 0:
            found_objects = rs.ObjectsByLayer('DAYLIGHT POINTS')
            rs.DeleteObjects(found_objects)
        else:
            rs.AddLayer('DAYLIGHT POINTS', parent = 'TRNLizard_Sensor_Points')
            rs.LayerColor('DAYLIGHT POINTS',(234,239,46))
            layer_colour = rs.LayerColor('DAYLIGHT POINTS')
            layer_material = rs.AddMaterialToLayer('DAYLIGHT POINTS')
            rs.MaterialColor(layer_material,layer_colour)
        for item in daylight_points:
            point = sc.doc.Objects.Add(item)
            point_guid = str(point)
            point_guid = point_guid.split('[')[-1]
            point_guid = point_guid.split(']')[0]
            rs.ObjectLayer('%s'%point_guid,'DAYLIGHT POINTS')
            rs.ObjectColorSource('%s'%point_guid,0)
            object_colour = rs.ObjectColor('%s'%point_guid)
            object_material = rs.AddMaterialToObject('%s'%point_guid)
            rs.MaterialColor(object_material,object_colour)
    if len(comfort_points) == 0:
        pass
    else:
        layertable = sc.doc.Layers
        layerindex = layertable.Find('COMFORT POINTS',True)
        if layerindex > 0:
            found_objects = rs.ObjectsByLayer('COMFORT POINTS')
            rs.DeleteObjects(found_objects)
        else:
            rs.AddLayer('COMFORT POINTS', parent = 'TRNLizard_Sensor_Points')
            rs.LayerColor('COMFORT POINTS',(0,225,0))
            layer_colour = rs.LayerColor('COMFORT POINTS')
            layer_material = rs.AddMaterialToLayer('COMFORT POINTS')
            rs.MaterialColor(layer_material,layer_colour)
        for item in comfort_points:
            point = sc.doc.Objects.Add(item)
            point_guid = str(point)
            point_guid = point_guid.split('[')[-1]
            point_guid = point_guid.split(']')[0]
            rs.ObjectLayer('%s'%point_guid,'COMFORT POINTS')
            rs.ObjectColorSource('%s'%point_guid,0)
            object_colour = rs.ObjectColor('%s'%point_guid)
            object_material = rs.AddMaterialToObject('%s'%point_guid)
            rs.MaterialColor(object_material,object_colour)
    if len(gain_points) == 0:
        pass
    else:
        layertable = sc.doc.Layers
        layerindex = layertable.Find('GAIN POINTS',True)
        if layerindex > 0:
            found_objects = rs.ObjectsByLayer('GAIN POINTS')
            rs.DeleteObjects(found_objects)
        else:
            rs.AddLayer('GAIN POINTS', parent = 'TRNLizard_Sensor_Points')
            rs.LayerColor('GAIN POINTS',(232,20,0))
            layer_colour = rs.LayerColor('GAIN POINTS')
            layer_material = rs.AddMaterialToLayer('GAIN POINTS')
            rs.MaterialColor(layer_material,layer_colour)
        for item in daylight_points:
            point = sc.doc.Objects.Add(item)
            #point = rs.AddSphere(item,0.2)
            point_guid = str(point)
            point_guid = point_guid.split('[')[-1]
            point_guid = point_guid.split(']')[0]
            rs.ObjectLayer('%s'%point_guid,'GAIN POINTS')
            rs.ObjectColorSource('%s'%point_guid,0)
            object_colour = rs.ObjectColor('%s'%point_guid)
            object_material = rs.AddMaterialToObject('%s'%point_guid)
            rs.MaterialColor(object_material,object_colour)
def delete_Points(daylight_points,comfort_points,gain_points):
    global Zone_name
    global Airnode_name
    layerindex = layertable.Find('DAYLIGHT POINTS',True)
    if layerindex > 0:
        found_objects = rs.ObjectsByLayer('DAYLIGHT POINTS')
        rs.DeleteObjects(found_objects)
        rs.DeleteLayer('DAYLIGHT POINTS')
    layerindex = layertable.Find('COMFORT POINTS',True)
    if layerindex > 0:
        found_objects = rs.ObjectsByLayer('COMFORT POINTS')
        rs.DeleteObjects(found_objects)
        rs.DeleteLayer('COMFORT POINTS')
    layerindex = layertable.Find('GAIN POINTS',True)
    if layerindex > 0:
        found_objects = rs.ObjectsByLayer('GAIN POINTS')
        rs.DeleteObjects(found_objects)
        rs.DeleteLayer('GAIN POINTS')
    layerindex = layertable.Find('TRNLizard_Sensor_Points',True)
    if layerindex > 0:
        found_objects = rs.ObjectsByLayer('TRNLizard_Sensor_Points')
        rs.DeleteObjects(found_objects)
        rs.DeleteLayer('TRNLizard_Sensor_Points')
def bake_Shader(shadersurfaces):
    layertable = sc.doc.Layers
    layerindex = layertable.Find('SHADER',True)
    if layerindex > 0:
        found_objects = rs.ObjectsByLayer('SHADER')
        rs.DeleteObjects(found_objects)
    else:
        rs.AddLayer('SHADER', parent = 'TRNLizard_Final_Geometry')
        rs.LayerColor('SHADER',(0,0,0))
        layer_colour = rs.LayerColor('SHADER')
        layer_material = rs.AddMaterialToLayer('SHADER')
        rs.MaterialColor(layer_material,layer_colour)
    for item in shadersurfaces:
        #surface = rs.AddPlanarSrf(item.Edges)
        surface = sc.doc.Objects.Add(item)
        surface_guid = str(surface)
        surface_guid = surface_guid.split('[')[-1]
        surface_guid = surface_guid.split(']')[0]
        rs.ObjectLayer('%s'%surface_guid,'SHADER')
        rs.ObjectColorSource('%s'%surface_guid,0)
        object_colour = rs.ObjectColor('%s'%surface_guid)
        object_material = rs.AddMaterialToObject('%s'%surface_guid)
        rs.MaterialColor(object_material,object_colour)
def delete_shader(shadersurfaces):
    layertable = sc.doc.Layers
    layerindex = layertable.Find('SHADER',True)
    if layerindex > 0:
        found_objects = rs.ObjectsByLayer('SHADER')
        rs.DeleteObjects(found_objects)
        rs.DeleteLayer('SHADER')
def bake_Virtual(virtualsurfaces):
    layertable = rs.LayerNames()
    found_virtual = 0
    for ix,item in enumerate(layertable):
        if 'TRNLizard' in item and 'VIRTUAL' in item:
            found_objects = rs.ObjectsByLayer('%s'%item)
            rs.DeleteObjects(found_objects)
            found_virtual = 1
    #layerindex = layertable.Find('VIRTUAL',True)
    if found_virtual == 0 and len(virtualsurfaces) > 0:
        rs.AddLayer('VIRTUAL', parent = 'TRNLizard_Final_Geometry')
        rs.LayerColor('VIRTUAL',(0,0,0))
        layer_colour = rs.LayerColor('VIRTUAL')
        layer_material = rs.AddMaterialToLayer('VIRTUAL')
        rs.MaterialColor(layer_material,layer_colour)
    for item in virtualsurfaces:
        surface = rs.AddPlanarSrf(item.Edges)
        surface_guid = str(surface)
        surface_guid = surface_guid.split('[')[-1]
        surface_guid = surface_guid.split(']')[0]
        rs.ObjectLayer('%s'%surface_guid,'VIRTUAL')
        rs.ObjectColorSource('%s'%surface_guid,0)
        object_colour = rs.ObjectColor('%s'%surface_guid)
        object_material = rs.AddMaterialToObject('%s'%surface_guid)
        rs.MaterialColor(object_material,object_colour)
def delete_virtual(virtualsurfaces):
    layertable = rs.LayerNames()
    for ix,item in enumerate(layertable):
        if 'TRNLizard' in item and 'VIRTUAL' in item:
            found_objects = rs.ObjectsByLayer('%s'%item)
            rs.DeleteObjects(found_objects)
            rs.DeleteLayer('%s'%item)
def bake_building(external_walls,boundary_walls,identical_walls,external_windows,adjacent_walls,adjacent_windows):
    global Zone_name
    global Airnode_name
    branch_num = external_walls.BranchCount
    centerpts = []
    solid = []
    origin = rc.Geometry.Point3d(0,0,0)
    airnodescalefactor = AirnodeScale
    surfacecalefactor = SurfaceScale
    scl = rc.Geometry.Transform.Scale(origin,airnodescalefactor)
    for i in range(0,branch_num):
        solid.append(rc.Geometry.Brep())
        layertable = sc.doc.Layers
        layercoll = rs.LayerNames()
        mainlayer = 'TRNLizard_Final_Geometry'
        zone_name = Zone_name[i].replace(' ', '_')
        zonelayer = mainlayer + '::' + zone_name
        if zonelayer in layercoll:
            found_objects = rs.ObjectsByLayer('%s'%zonelayer)
            rs.DeleteObjects(found_objects)
        else:
            rs.AddLayer('%s'%zonelayer)
        airnode_name = Airnode_name[i].replace(' ', '_')
        airnodelayer = zonelayer + '::' + airnode_name
        if airnodelayer in layercoll:
            found_objects = rs.ObjectsByLayer('%s'%airnodelayer)
            rs.DeleteObjects(found_objects)
        else:
            rs.AddLayer('%s'%airnodelayer)
        wallnames = ['EXT_WALL','BOUNDARY_WALL','IDT_WALL'  ,'EXT_WINDOW','ADJ_WALL' ,'ADJ_WINDOW' ]
        colours   = [(41,105,0),(232,20,0)     ,(234,239,46),(0,100,225),(225,134,49),(110,186,225)]
        for item in external_walls.Branch(i):
            solid[i].Append(item)
        for item in boundary_walls.Branch(i):
            solid[i].Append(item)
        for item in identical_walls.Branch(i):
            solid[i].Append(item)
        for item in adjacent_walls.Branch(i):
            solid[i].Append(item)
        volprop = rc.Geometry.VolumeMassProperties.Compute(solid[i])
        acenter = volprop.Centroid
        line = rc.Geometry.Line(origin, acenter)
        oldto = line.To
        line.Transform(scl)
        newto = line.To
        vec = newto - oldto
        movevect = rc.Geometry.Vector3d(vec)
        scl2 = rc.Geometry.Transform.Scale(acenter,surfacecalefactor)
        for ix,xitem in enumerate(wallnames):
            walllayer = airnodelayer + '::' + xitem
            if walllayer in layercoll:
                found_objects = rs.ObjectsByLayer('%s'%walllayer)
                rs.DeleteObjects(found_objects)
            else:
                rs.AddLayer('%s'%walllayer)
                rs.LayerColor('%s'%walllayer,colours[ix])
                layer_colour = rs.LayerColor('%s'%walllayer)
                layer_material = rs.AddMaterialToLayer('%s'%walllayer)
                rs.MaterialColor(layer_material,layer_colour)
            if xitem == 'EXT_WALL':
                for item in external_walls.Branch(i):
                    item.Translate(movevect)
                    amass = rc.Geometry.AreaMassProperties.Compute(item)
                    scenter = amass.Centroid
                    line = rc.Geometry.Line(acenter, scenter)
                    oldto = line.To
                    line.Transform(scl2)
                    newto = line.To
                    vec2 = newto - oldto
                    movevect2 = rc.Geometry.Vector3d(vec2)
                    item.Translate(movevect2)
                    surface = sc.doc.Objects.Add(item)
                    surface_guid = str(surface)
                    surface_guid = surface_guid.split('[')[-1]
                    surface_guid = surface_guid.split(']')[0]
                    rs.ObjectLayer('%s'%surface_guid,'%s'%walllayer)
                    rs.ObjectColorSource('%s'%surface_guid,0)
                    object_colour = rs.ObjectColor('%s'%surface_guid)
                    object_material = rs.AddMaterialToObject('%s'%surface_guid)
                    rs.MaterialColor(object_material,object_colour)
            if xitem == 'BOUNDARY_WALL':
                for item in boundary_walls.Branch(i):
                    item.Translate(movevect)
                    amass = rc.Geometry.AreaMassProperties.Compute(item)
                    scenter = amass.Centroid
                    line = rc.Geometry.Line(acenter, scenter)
                    oldto = line.To
                    line.Transform(scl2)
                    newto = line.To
                    vec2 = newto - oldto
                    movevect2 = rc.Geometry.Vector3d(vec2)
                    item.Translate(movevect2)
                    surface = sc.doc.Objects.Add(item)
                    surface_guid = str(surface)
                    surface_guid = surface_guid.split('[')[-1]
                    surface_guid = surface_guid.split(']')[0]
                    rs.ObjectLayer('%s'%surface_guid,'%s'%walllayer)
                    rs.ObjectColorSource('%s'%surface_guid,0)
                    object_colour = rs.ObjectColor('%s'%surface_guid)
                    object_material = rs.AddMaterialToObject('%s'%surface_guid)
                    rs.MaterialColor(object_material,object_colour)
            if xitem == 'IDT_WALL':
                for item in identical_walls.Branch(i):
                    item.Translate(movevect)
                    amass = rc.Geometry.AreaMassProperties.Compute(item)
                    scenter = amass.Centroid
                    line = rc.Geometry.Line(acenter, scenter)
                    oldto = line.To
                    line.Transform(scl2)
                    newto = line.To
                    vec2 = newto - oldto
                    movevect2 = rc.Geometry.Vector3d(vec2)
                    item.Translate(movevect2)
                    surface = sc.doc.Objects.Add(item)
                    surface_guid = str(surface)
                    surface_guid = surface_guid.split('[')[-1]
                    surface_guid = surface_guid.split(']')[0]
                    rs.ObjectLayer('%s'%surface_guid,'%s'%walllayer)
                    rs.ObjectColorSource('%s'%surface_guid,0)
                    object_colour = rs.ObjectColor('%s'%surface_guid)
                    object_material = rs.AddMaterialToObject('%s'%surface_guid)
                    rs.MaterialColor(object_material,object_colour)
            if xitem == 'EXT_WINDOW':
                for item in external_windows.Branch(i):
                    item.Translate(movevect)
                    amass = rc.Geometry.AreaMassProperties.Compute(item)
                    scenter = amass.Centroid
                    line = rc.Geometry.Line(acenter, scenter)
                    oldto = line.To
                    line.Transform(scl2)
                    newto = line.To
                    if surfacecalefactor > 1 and CutOutWindow == False:
                        newto = newto + item.Surfaces[0].NormalAt(0,0)
                    vec2 = newto - oldto
                    movevect2 = rc.Geometry.Vector3d(vec2)
                    item.Translate(movevect2)
                    surface = sc.doc.Objects.Add(item)
                    surface_guid = str(surface)
                    surface_guid = surface_guid.split('[')[-1]
                    surface_guid = surface_guid.split(']')[0]
                    rs.ObjectLayer('%s'%surface_guid,'%s'%walllayer)
                    rs.ObjectColorSource('%s'%surface_guid,0)
                    object_colour = rs.ObjectColor('%s'%surface_guid)
                    object_material = rs.AddMaterialToObject('%s'%surface_guid)
                    rs.MaterialColor(object_material,object_colour)
                    rs.MaterialTransparency(object_material,0.6)
            if xitem == 'ADJ_WALL':
                for item in adjacent_walls.Branch(i):
                    item.Translate(movevect)
                    amass = rc.Geometry.AreaMassProperties.Compute(item)
                    scenter = amass.Centroid
                    line = rc.Geometry.Line(acenter, scenter)
                    oldto = line.To
                    line.Transform(scl2)
                    newto = line.To
                    vec2 = newto - oldto
                    movevect2 = rc.Geometry.Vector3d(vec2)
                    item.Translate(movevect2)
                    surface = sc.doc.Objects.Add(item)
                    surface_guid = str(surface)
                    surface_guid = surface_guid.split('[')[-1]
                    surface_guid = surface_guid.split(']')[0]
                    rs.ObjectLayer('%s'%surface_guid,'%s'%walllayer)
                    rs.ObjectColorSource('%s'%surface_guid,0)
                    object_colour = rs.ObjectColor('%s'%surface_guid)
                    object_material = rs.AddMaterialToObject('%s'%surface_guid)
                    rs.MaterialColor(object_material,object_colour)
            if xitem == 'ADJ_WINDOW':
                for item in adjacent_windows.Branch(i):
                    item.Translate(movevect)
                    amass = rc.Geometry.AreaMassProperties.Compute(item)
                    scenter = amass.Centroid
                    line = rc.Geometry.Line(acenter, scenter)
                    oldto = line.To
                    line.Transform(scl2)
                    newto = line.To
                    if surfacecalefactor > 1 and CutOutWindow == False:
                        newto = newto + item.Surfaces[0].NormalAt(0,0)
                    vec2 = newto - oldto
                    movevect2 = rc.Geometry.Vector3d(vec2)
                    item.Translate(movevect2)
                    surface = sc.doc.Objects.Add(item)
                    surface_guid = str(surface)
                    surface_guid = surface_guid.split('[')[-1]
                    surface_guid = surface_guid.split(']')[0]
                    rs.ObjectLayer('%s'%surface_guid,'%s'%walllayer)
                    rs.ObjectColorSource('%s'%surface_guid,0)
                    object_colour = rs.ObjectColor('%s'%surface_guid)
                    object_material = rs.AddMaterialToObject('%s'%surface_guid)
                    rs.MaterialColor(object_material,object_colour)
                    rs.MaterialTransparency(object_material,0.6)
def window_cut_out():
    global Zone_name
    global Airnode_name
    for i,airnode_name in enumerate(Airnode_name):
        layercoll = rs.LayerNames()
        mainlayer = 'TRNLizard_Final_Geometry'
        layertable = sc.doc.Layers
        zone_name = Zone_name[i].replace(' ', '_')
        zonelayer = mainlayer + '::' + zone_name
        airnode_name = Airnode_name[i].replace(' ', '_')
        airnodelayer = zonelayer + '::' + airnode_name
        ext_wall_objects = []
        ext_window_objects = []
        extwalllayer = '%sEXT_WALL'%(airnodelayer + '::')
        extwinlayer = '%sEXT_WINDOW'%(airnodelayer + '::')
        adjwalllayer = '%sADJ_WALL'%(airnodelayer + '::')
        adjwinlayer = '%sADJ_WINDOW'%(airnodelayer + '::')
        ext_wall_objects.extend(rs.ObjectsByLayer(extwalllayer))
        ext_window_objects.extend(rs.ObjectsByLayer(extwinlayer))
        if len(ext_window_objects) > 0:
            ext_cut_out_walls = rs.BooleanDifference(ext_wall_objects,ext_window_objects)
            if extwalllayer in layercoll and ext_cut_out_walls is not None:
                found_objects = rs.ObjectsByLayer(extwalllayer)
                rs.DeleteObjects(found_objects)
                for item in ext_cut_out_walls:
                    rs.ObjectLayer('%s'%item,extwalllayer)
                    rs.ObjectColorSource('%s'%item,0)
                    object_colour = rs.ObjectColor('%s'%item)
                    object_material = rs.AddMaterialToObject('%s'%item)
                    rs.MaterialColor(object_material,object_colour)
        for item in external_windows.Branch(i):
            surface = rs.AddPlanarSrf(item.Edges)
            surface_guid = str(surface)
            surface_guid = surface_guid.split('[')[-1]
            surface_guid = surface_guid.split(']')[0]
            rs.ObjectLayer('%s'%surface_guid,extwinlayer)
            rs.ObjectColorSource('%s'%surface_guid,0)
            object_colour = rs.ObjectColor('%s'%surface_guid)
            object_material = rs.AddMaterialToObject('%s'%surface_guid)
            rs.MaterialColor(object_material,object_colour)
            rs.MaterialTransparency(object_material,0.6)
        adj_window_list = rs.ObjectsByLayer(adjwinlayer)
        if len(adj_window_list) == 0:
            pass
        else:
            adj_wall_objects = []
            adj_window_objects = []
            adj_wall_objects.extend(rs.ObjectsByLayer(adjwalllayer))
            adj_window_objects.extend(rs.ObjectsByLayer(adjwinlayer))
            adj_cut_out_walls = rs.BooleanDifference(adj_wall_objects,adj_window_objects)
            layerindex = layertable.Find(adjwalllayer,True)
            if layerindex > 0:
                found_objects = rs.ObjectsByLayer(adjwalllayer)
                rs.DeleteObjects(found_objects)
            for item in adj_cut_out_walls:
                rs.ObjectLayer('%s'%item,adjwalllayer)
                rs.ObjectColorSource('%s'%item,0)
                object_colour = rs.ObjectColor('%s'%item)
                object_material = rs.AddMaterialToObject('%s'%item)
                rs.MaterialColor(object_material,object_colour)
            for item in adjacent_windows.Branch(i):
                surface = rs.AddPlanarSrf(item.Edges)
                surface_guid = str(surface)
                surface_guid = surface_guid.split('[')[-1]
                surface_guid = surface_guid.split(']')[0]
                rs.ObjectLayer('%s'%surface_guid,adjwinlayer)
                rs.ObjectColorSource('%s'%surface_guid,0)
                object_colour = rs.ObjectColor('%s'%surface_guid)
                object_material = rs.AddMaterialToObject('%s'%surface_guid)
                rs.MaterialColor(object_material,object_colour)
                rs.MaterialTransparency(object_material,0.6)
def delete_building(external_walls,boundary_walls,identical_walls,external_windows,adjacent_walls,adjacent_windows):
    global Zone_name
    global Airnode_name
    branch_num = external_walls.BranchCount
    for i in range(0,branch_num):
        layercoll = rs.LayerNames()
        mainlayer = 'TRNLizard_Final_Geometry'
        layertable = sc.doc.Layers
        zone_name = Zone_name[i].replace(' ', '_')
        zonelayer = mainlayer + '::' + zone_name
        airnode_name = Airnode_name[i].replace(' ', '_')
        airnodelayer = zonelayer + '::' + airnode_name
        wallnames = ['EXT_WALL','BOUNDARY_WALL','IDT_WALL'  ,'EXT_WINDOW','ADJ_WALL' ,'ADJ_WINDOW' ]
        colours   = [(41,105,0),(232,20,0)     ,(234,239,46),(0,100,225),(225,134,49),(110,186,225)]
        for ix,xitem in enumerate(wallnames):
            walllayer = airnodelayer + '::' + xitem
            if walllayer in layercoll:
                found_objects = rs.ObjectsByLayer('%s'%walllayer)
                rs.DeleteObjects(found_objects)
                rs.DeleteLayer('%s'%walllayer)
        if (zonelayer) in layercoll:
            found_objects = rs.ObjectsByLayer('%s'%(zonelayer))
            rs.DeleteObjects(found_objects)
            rs.DeleteLayer('%s'%(zonelayer))
rs.EnableRedraw(False)
layertable = sc.doc.Layers
layerindex = layertable.Find("TRNLizard_Final_Geometry",True)
if layerindex > 0:
    found_objects = rs.ObjectsByLayer('TRNLizard_Final_Geometry')
    rs.DeleteObjects(found_objects)
    rs.DeleteLayer('TRNLizard_Final_Geometry')
rs.AddLayer('TRNLizard_Final_Geometry')
if BakePoints == True:
    bake_Points(daylight_points,comfort_points,gain_points)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
else:
    delete_Points(daylight_points,comfort_points,gain_points)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
if BakeShader == True:
    bake_Shader(shadersurfaces)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
else:
    delete_shader(shadersurfaces)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
if BakeVirtual == True:
    bake_Virtual(virtualsurfaces)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
else:
    delete_virtual(virtualsurfaces)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
if BakeBuilding == True:
    bake_building(external_walls,boundary_walls,identical_walls,external_windows,adjacent_walls,adjacent_windows)
    if CutOutWindow == True:
        window_cut_out()
if BakeBuilding == False:
    delete_building(external_walls,boundary_walls,identical_walls,external_windows,adjacent_walls,adjacent_windows)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
rs.EnableRedraw(False)
sc.doc = ghdoc
#starting from here the tags are printed
zone_names_list = Airnode_name
sc.doc = rc.RhinoDoc.ActiveDoc
def bake_text(text_data,text_type, colour):
    global center_pts
    global zone_names_list
    layertable = sc.doc.Layers
    layerindex = layertable.Find('%s'%text_type,True)
    if layerindex > 0:
        found_objects = rs.ObjectsByLayer('%s'%text_type)
        rs.DeleteObjects(found_objects)
    else:
        rs.AddLayer('%s'%text_type, parent = 'TRNLizard_Tags')
    branch_num = text_data.BranchCount
    for i in range(0,branch_num):
        zone_name = zone_names_list[i].replace(' ', '_')
        layertable = sc.doc.Layers
        layerindex = layertable.Find('%s_%s'%(zone_name, text_type),True)
        if layerindex > 0:
            found_objects = rs.ObjectsByLayer('%s_%s'%(zone_name, text_type))
            rs.DeleteObjects(found_objects)
        else:
            rs.AddLayer('%s_%s'%(zone_name, text_type), parent = '%s'%text_type)
            rs.LayerColor('%s_%s'%(zone_name, text_type), colour)
            layer_colour = rs.LayerColor('%s_%s'%(zone_name, text_type))
            layer_material = rs.AddMaterialToLayer('%s_%s'%(zone_name, text_type))
            rs.MaterialColor(layer_material,layer_colour)
        for text, text_location in zip(text_data.Branch(i), center_pts.Branch(i)):
            if text == '':
                pass
            else:
                item = rs.AddTextDot('%s'%text, text_location)
                rs.ObjectLayer('%s'%item,'%s_%s'%(zone_name, text_type))
                rs.ObjectColorSource('%s'%item,0)
                object_colour = rs.ObjectColor('%s'%item)
                object_material = rs.AddMaterialToObject('%s'%item)
                rs.MaterialColor(object_material,object_colour)
def delete_text(text_data,text_type):
    global center_pts
    global zone_names_list
    branch_num = text_data.BranchCount
    for i in range(0,branch_num):
        zone_name = zone_names_list[i].replace(' ', '_')
        layertable = sc.doc.Layers
        layerindex = layertable.Find('%s_%s'%(zone_name, text_type),True)
        if layerindex > 0:
            found_objects = rs.ObjectsByLayer('%s_%s'%(zone_name, text_type))
            rs.DeleteObjects(found_objects)
            rs.DeleteLayer('%s_%s'%(zone_name, text_type))
    layerindex = layertable.Find('%s'%text_type,True)
    if layerindex > 0:
        found_objects = rs.ObjectsByLayer('%s'%text_type)
        rs.DeleteObjects(found_objects)
        rs.DeleteLayer('%s'%text_type)
# @OC START
#Additional functions to bake the points names at the points location
def bake_points_names(points_dict,point_type,colour):
    points_dict2 = {}
    for k,v in points_dict.items():
        for k1,v1 in points_dict[k].items():
            point = rc.Geometry.Point3d(v1[0],v1[1],v1[2])
            points_dict2[k1] = point
    if len(points_dict2.keys()) != 0:
        layertable = sc.doc.Layers
        layerindex = layertable.Find('TRNLizard_Tags::%s_Pt_Names' %point_type,True)
        if layerindex > 0:
            found_objects = rs.ObjectsByLayer('TRNLizard_Tags::%s_Pt_Names' %point_type)
            rs.DeleteObjects(found_objects)
        else:
            rs.AddLayer('TRNLizard_Tags::%s_Pt_Names' %point_type)
            rs.LayerColor('TRNLizard_Tags::%s_Pt_Names' %point_type, colour)
            layer_colour = rs.LayerColor('TRNLizard_Tags::%s_Pt_Names' %point_type)
            layer_material = rs.AddMaterialToLayer('TRNLizard_Tags::%s_Pt_Names' %point_type)
            rs.MaterialColor(layer_material,layer_colour)
        for name,location in points_dict2.items():
            name = PointNamePrefix + name.split(' ')[-1]
            item = rs.AddTextDot(name,location)
            rs.ObjectLayer(item,'TRNLizard_Tags::%s_Pt_Names' %point_type)
            rs.ObjectColorSource(item,0)
            object_colour = rs.ObjectColor(item)
            object_material = rs.AddMaterialToObject(item)
            rs.MaterialColor(object_material,object_colour)
def delete_points_names(point_type):
    layertable = sc.doc.Layers
    layerindex = layertable.Find('%s_Pt_Names' %point_type,True)
    if layerindex > 0:
        found_objects = rs.ObjectsByLayer('%s_Pt_Names' %point_type)
        rs.DeleteObjects(found_objects)
        rs.DeleteLayer('%s_Pt_Names' %point_type)
# @OC END
rs.EnableRedraw(False)
layertable = sc.doc.Layers
layerindex = layertable.Find("TRNLizard_Tags",True)
if layerindex > 0:
    found_objects = rs.ObjectsByLayer('TRNLizard_Tags')
    rs.DeleteObjects(found_objects)
    rs.DeleteLayer('TRNLizard_Tags')
rs.AddLayer('TRNLizard_Tags')
layertable = sc.doc.Layers
layerindex = layertable.Find("TRNLizard_Tags",True)
# @OC START
if "ShowPointNames" in locals():
    pass
else:
    ShowPointNames = False
if ShowPointNames == True:
    Daylight_colour = (234,239,46)
    bake_points_names(BaseInf['DAYLIGHT_POINTS'],'Daylight', Daylight_colour)
    Comfort_colour = (0,225,0)
    bake_points_names(BaseInf['COMFORT_POINTS'],'Comfort', Comfort_colour)
    Gain_colour = (232,20,0)
    bake_points_names(BaseInf['GAIN_POINTS'],'Gain', Gain_colour)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
else:
    delete_points_names('Daylight')
    delete_points_names('Comfort')
    delete_points_names('Gain')
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
# @OC END
if ShowSurfaceID == True:
    colour = (225,0,0)
    bake_text(id_list,'ID', colour)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
else:
    delete_text(id_list,'ID')
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
if ShowConstruction == True:
    colour = (0,0,0)
    bake_text(construction_list,'CONSTRUCTION',colour)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
else:
    delete_text(construction_list,'CONSTRUCTION')
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
if ShowUVal == True:
    colour = (126,0,158)
    bake_text(uval_list,'UVAL',colour)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
else:
    delete_text(uval_list,'UVAL')
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
if ShowShading == True:
    colour = (126,100,158)
    bake_text(shading_list,'SHD',colour)
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
else:
    delete_text(shading_list,'SHD')
    #rs.EnableRedraw(True)
    #rs.EnableRedraw(False)
rs.EnableRedraw(True)
sc.doc = ghdoc
