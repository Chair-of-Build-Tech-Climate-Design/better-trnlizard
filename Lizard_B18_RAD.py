"""
GhPython provides a Python script component

Args:
    RadFile (str): Script variable Python
        Access: item
        Required: False
    PtsFile (str): Script input PtsFile.
        Access: item
        Required: False

Returns:
    Surfaces (object): Script output Surfaces.
        Access: item
    Windows (object): Script output Windows.
        Access: item
    Shader (object): Script output Shader.
        Access: item
    Other (object): Script output Other.
        Access: item
    Points (object): Script output Points.
        Access: item
"""
version='2.1.2'
import rhinoscriptsyntax as rs
import re
from collections import defaultdict
import Rhino as rc
import os
#160120 CFF changed that *.pts is automatically read from the same folder as the rad file
if RadFile:
    f = open(RadFile, 'r')
    data = {}
    id = 0
    for lines in f.readlines():
        dummy = lines
        m = re.search('\s*(-?\d+.\d+)\s+(-?\d+.\d+)\s+(-?\d+.\d+)', lines)
        m2 = re.search('\S+\s+\S+\s+\S+', lines)
        if '#-' in lines  and ('Surface' in lines or 'Shader' in lines):
            #print lines
            dummy = dummy.rstrip()
            dummy = re.sub('#--','',dummy)
            dummy = re.sub(' ','',dummy)
            id = int(dummy.split('=')[1])
            data[id] = defaultdict()
            data[id]['type'] = dummy.split('=')[0]
            data[id]['vertices'] = []
            #print id
        #elif '#-' in lines  and ('Surface' not in lines or 'Shader' not in lines):
        #    print lines
        #    dummy = dummy.rstrip()
        #    dummy = re.sub('#--','',dummy)
        #    dummy = re.sub(' ','',dummy)
        #    key, value = dummy.split('=')
        #    print value
        #    data[id][key] = value
        #    data[id]['vertices'] = []
        elif m:
            data[id]['vertices'].append([m.group(1),m.group(2),m.group(3)])
        #elif m2 and '#' not in lines:
        #    print id
        #    id +=1
        #    data[id] = defaultdict()
        #    data[id]['vertices'] = []
        #    data[id]['type'] = 'RAD'
    Surfaces = []
    Windows  = []
    Shader   = []
    Other    = []
    for key in data:
        vertices    = data[key]['vertices']
        if len(vertices) > 0:
            try:
                vertices.append(vertices[0])
                dummy       = rs.AddPolyline(vertices)
                face        = rs.AddPlanarSrf(dummy)
                if data[key]['type']    == 'SurfaceID':
                    Surfaces.append(dummy)
                elif data[key]['type']  == 'WindowSurfaceID':
                    Windows.append(dummy)
                elif data[key]['type']  == 'ShaderID':
                    Shader.append(dummy)
                else:
                    Other.append(dummy)
            except:
                pass
if PtsFile:
    pass
else:
    if RadFile:
        PtsFile = re.sub('.rad','.pts',RadFile)
        PtsFile    = PtsFile if os.path.isfile(PtsFile) else None
        if PtsFile is None:
            PtsFile = re.sub('.rad','_S.xyz',RadFile)
            PtsFile    = PtsFile if os.path.isfile(PtsFile) else None
if PtsFile:
    f = open(PtsFile, 'r')
    Points = []
    for lines in f.readlines():
        dummy = lines
        dummy = dummy.rstrip()
        dummy = dummy.split()
        Points.append(rs.AddPoint(float(dummy[0]),float(dummy[1]),float(dummy[2])))
