"""
Load results from thermal and daylight simulation.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    Variants (object): Simulation output files
        Access: list
        Required: True
    FocusAirnode (object): Selecting focused airnode to post-process result
        Access: item
        Required: True

Returns:
    out (object): 
        Access: item
    Building (object): *.b18 filepath
        Access: item
    BuildingInfo (object): Script output building_info.
        Access: item
    Temperature (object): temperature *.prn filepath
        Access: item
    Power (object): power *.prn filepath
        Access: item
    Additional (object): Script variable Output_Files
        Access: item
    PlotPath (object): path to folder contain results plots *.html
        Access: item
    FocusAirnode (object): Airnode name
        Access: item
    VariantName (object): Variant name
        Access: item
"""
version='2.2.1'
ghenv.Component.Name = "Lizard_Output_Files"
ghenv.Component.NickName = 'Output_Files'
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "3 | Components"
import re
import scriptcontext as sc
import os
import ghpythonlib.components as ghcomp
import rhinoscriptsyntax as rs
if len(Variants) > 0:
    variant = Variants
else:
    variant = sc.sticky[sc.doc.Path]['Variant']
if FocusAirnode:
    aname = FocusAirnode
elif sc.sticky[sc.doc.Path].has_key('focusairnode'):
    aname = sc.sticky[sc.doc.Path]['focusairnode']
else:
    aname = ''
variantname = ''
for item in variant:
    dummy = re.sub('\n','',item)
    storage = dummy.split('\t')
    shortname = storage[1]
    variantname = storage[2]
    #results_folder = re.sub('Model','Results',storage[3])
    results_folder = storage[3] + 'Results\\'
    System        = storage[3] + storage[1] + '.d18'
    System        = System if os.path.isfile(System) else None
    Building        = storage[3] + storage[1] + '.b18'
    Building        = Building if os.path.isfile(Building) else None
    BuildingInfo   = storage[3] + storage[1] + '.inf'
    BuildingInfo   = BuildingInfo if os.path.isfile(BuildingInfo) else None
    BuildingRad    = storage[3] + storage[1] + '.rad'
    BuildingRad    = BuildingRad if os.path.isfile(BuildingRad) else None
    Temperature     = results_folder + 'temp_1h_{0}.prn'.format(aname)
    Temperature     = Temperature if os.path.isfile(Temperature) else None
    Power           = results_folder + 'p_spec_1h_{0}.prn'.format(aname)
    Power           = Power if os.path.isfile(Power) else None
    Additional           = results_folder + 'addoutput_1h.prn'.format(aname)
    Additional           = Additional if os.path.isfile(Additional) else None
    DaylightGrid   = results_folder + storage[1] + '.grid'
    DaylightGrid   = DaylightGrid if os.path.isfile(DaylightGrid) else None
    DaylightIllGrid  = results_folder + storage[1] + '.ill_grid'
    DaylightIllGrid  = DaylightIllGrid if os.path.isfile(DaylightIllGrid) else None
    DaylightFactor    = results_folder + storage[1] + '.df'
    DaylightFactor    = DaylightFactor if os.path.isfile(DaylightFactor) else None
    DaylightIlluminance = results_folder + storage[1] + '_SHD.ill'
    DaylightIlluminance = DaylightIlluminance if os.path.isfile(DaylightIlluminance) else None
    DaylightPoints   = storage[3] + storage[1] + '_S.xyz'
    DaylightPoints = DaylightPoints if os.path.isfile(DaylightPoints) else None
    PlotPath = results_folder
    VariantName = variantname
surfaces = []
column = []
results = []
outputnames = []
sumdata = []
output = {}
pointssummary = []
if DaylightGrid != None:
    def readdatafile():
        f = open(DaylightGrid, 'r')
        lines=f.readlines()
        for i in range(len(lines)):
            if re.search('^\s+-?\d+',lines[i]) is not None:
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
                            dummypoint = ghcomp.ConstructPoint(point[0],point[1],point[2])
                            pointscoll.append(dummypoint)
                            point = []
                    #print surfacecoll
                    pointstest.append(pointscoll)
                pointssummary.append(pointstest)
                #print pointscoll
        f.close()
    # 1 read data file from the printer file
    readdatafile()
    daylight_mesh = []
    for item in range(len(pointssummary)):
        surfaces = []
        for subitem in pointssummary[item]:
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
        daylight_mesh.append(joined_surfaces)
