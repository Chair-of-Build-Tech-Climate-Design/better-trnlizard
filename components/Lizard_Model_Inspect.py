"""
Shows what Lizard_System would make of the surfaces, without writing anything: the final boundary conditions after adjacency, with the
split surfaces and the constructions from the sets. It also works when the model has errors, so the surfaces in question can be seen.
-
TRNLizard
Copyright (c) 2026 Junfeng Xiao
All Rights Reserved.
-

For colours in the viewport connect Preview and Colours to a Custom Preview component (Geometry and Material) and switch off the preview
of this component. GeneralSettings of Lizard_System are not applied here. Errors of components upstream are listed under Problems: Lizard_System
would stop on them, and the surfaces shown may be incomplete.

Args:
    Multizone (object): connect the output of Lizard_Multizone
        Access: item
        Required: True
    Standalone (bool): True = each airnode on its own, as PrintSingleSimFiles of Lizard_System does. Not connected = False
        Access: item
        Required: False

Returns:
    out (object): Log Information!!!
        Access: item
    External (object): surfaces with outside air, one branch per airnode in the order of Airnodes
        Access: tree
    Adjacent (object): surfaces with a partner in another airnode
        Access: tree
    Boundary (object): surfaces with a given boundary temperature, for example the ground
        Access: tree
    Mirror (object): BOUNDARY surfaces with the air temperature of their own airnode: an unmodelled neighbour
        Access: tree
    Window (object): windows
        Access: tree
    Other (object): virtual surfaces and other categories
        Access: tree
    Unresolved (object): surfaces without a final boundary condition or without their partner
        Access: tree
    Airnodes (str): names of the airnodes, one per branch of the groups
        Access: list
    Table (str): one tab-separated line per surface after a header line, with the surface it was split from and its construction
        Access: list
    Summary (str): number and area of the surfaces per group
        Access: list
    Problems (str): errors, warnings and what the construction sets filled
        Access: list
    ProblemSurfaces (Brep): the surfaces of the errors and warnings
        Access: list
    Preview (Brep): all surfaces for a Custom Preview, windows slightly in front of their wall
        Access: list
    Colours (object): the colour of each surface of Preview, by group
        Access: list
"""
import operator
import scriptcontext as sc
import Grasshopper.Kernel as gh
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path
from System.Drawing import Color
version = '1.0.0'
ghenv.Component.Name = "Lizard_Model_Inspect"
ghenv.Component.NickName = 'Model Inspect'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "0 | Project"
w = gh.GH_RuntimeMessageLevel.Warning
err = gh.GH_RuntimeMessageLevel.Error
WINDOW_OFFSET = 0.01    # m, in front of the wall in the preview
if Multizone:
    if "Standalone" not in locals():
        Standalone = False
    shared = sc.sticky[sc.doc.Path]
    airnodes = shared["ZONECOLL"]().callFromZones(Multizone.airnode)
    airnodes.sort(key=operator.attrgetter("Name"))
    report = shared["inspectModel"](airnodes, shared["library"], Multizone.autoadjacency, Multizone.gaptolerance, bool(Standalone), Multizone.constructionset)
    Airnodes = report['airnodes']
    Table = shared["inspectTable"](report['rows'])
    Summary = report['summary']
    Preview = []
    Colours = []
    trees = {}
    for group in shared["INSPECT_GROUPS"]:
        tree = DataTree[object]()
        red, green, blue = shared["INSPECT_COLOURS"][group]
        for index, branch in enumerate(report['groups'][group]):
            tree.EnsurePath(GH_Path(index))
            for item in branch:
                tree.Add(item.Faces, GH_Path(index))
                brep = item.Faces
                if group == 'Window':
                    brep = brep.DuplicateBrep()
                    brep.Translate(item.Normalvector * WINDOW_OFFSET)
                Preview.append(brep)
                Colours.append(Color.FromArgb(red, green, blue))
        trees[group] = tree
    External = trees['External']
    Adjacent = trees['Adjacent']
    Boundary = trees['Boundary']
    Mirror = trees['Mirror']
    Window = trees['Window']
    Other = trees['Other']
    Unresolved = trees['Unresolved']
    Problems = []
    ProblemSurfaces = []
    counts = {'error': 0, 'warning': 0}
    for message in shared["upstreamErrors"](ghenv.Component, err):
        message = "Upstream error, {0}".format(message)
        Problems.append('ERROR: {0}'.format(message))
        counts['error'] += 1
        ghenv.Component.AddRuntimeMessage(err, message)
    for issue in report['issues']:
        Problems.append('{0}: {1}'.format(issue['level'].upper(), issue['message']))
        if issue['level'] == 'info':
            continue
        counts[issue['level']] += 1
        ghenv.Component.AddRuntimeMessage(err if issue['level'] == 'error' else w, issue['message'])
        for item in issue['surfaces']:
            if item.Faces not in ProblemSurfaces:
                ProblemSurfaces.append(item.Faces)
    ghenv.Component.Message = '{0} error(s)\n{1} warning(s)'.format(counts['error'], counts['warning'])
