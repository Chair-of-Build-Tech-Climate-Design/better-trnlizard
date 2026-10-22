"""
GhPython provides a Python script component

Args:
    Variants (object): Script variable Python
        Access: item
        Required: False

Returns:
    VarName (object): Script output VarName.
        Access: item
    ExtWalls (object): Script output ExtWalls.
        Access: item
    WindowRatio (object): Script output WindowRatio.
        Access: item
"""
import Grasshopper as gh
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path
from System import Object
import System
import re
version='2.2.1'
#if you are adding information to the Variants CLASS
#then you just have to add the Attribute name here as output to get the value
definitions =  [a for a in dir(Variants) if not a.startswith('__') and not callable(getattr(Variants,a))]
newvar = locals()
outarray = []
for item in definitions:
    newvar[item] = getattr(Variants,item)
    outarray.append(item)
newoutputs = []
existingoutputs = []
for item in ghenv.Component.Params.Output:
    existingoutputs.append(item.Name)
for item in outarray:
    search = 0
    for subitem in existingoutputs:
        if item in subitem:
            search = 1
    if search == 0:
        newoutputs.append(item)
def addOutputParam(outputIndex,name,newvar):
    param = gh.Kernel.Parameters.Param_String()
    outputName = name
    param.NickName = outputName
    param.Name = outputName
    param.Description = "description of output parameter %s" % outputName
    param.Access = gh.Kernel.GH_ParamAccess.item
    p = GH_Path(0)
    param.AddVolatileData(p,0,newvar[name])
    test = ghenv.Component.Params.Output.Count
    ghenv.Component.Params.RegisterOutputParam(param, test)
Update = False
if Update == True and len(newoutputs) > 0:
    for ix,item in enumerate(newoutputs):
        addOutputParam(ix,item,newvar)
ghenv.Component.Params.OnParametersChanged()
