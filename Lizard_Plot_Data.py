"""
This defines the plotter settings.
-
TRNLizard 
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    FilePath (object): String that defines the file to load results from
        Access: item
        Required: True
    ShortVariantName (object): Script variable PlotData
        Access: item
        Required: True
    AirnodeName (object): Script variable PlotData
        Access: item
        Required: True
    XOutput (object): Script variable PlotData
        Access: item
        Required: True
    YOutput (object): Script variable PlotData
        Access: list
        Required: True

Returns:
    out (object): Information
        Access: item
    Data_ (object): Chart settings need to be linked to the plotter component
        Access: item
"""
ghenv.Component.Name = "Lizard_Plot_Data"
ghenv.Component.NickName = 'PlotData'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "5 | Tools"
from collections import defaultdict
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import sys
reload(sys)
sys.setdefaultencoding('UTF-8')
class Data:
    def __init__(self):
        self.Xdata = []
        self.Ydata = []
ShortVariantName = ShortVariantName.encode('utf-8')
Data_ = Data()
if XOutput:
    for i in YOutput:
        Data_.Xdata.append(r'%s|%s|%s|%s'%(FilePath,ShortVariantName,AirnodeName,XOutput))
if YOutput:
    for item in YOutput:
        dtype = type(item)
        if 'instance' in '%s'%type(item):
            Data_.Ydata.append(r'%s|%s|%s|%s|%s|%s'%(FilePath,ShortVariantName,AirnodeName,item.Output,item.Label,item.Color))
        elif 'str' in '%s'%type(item):
            Data_.Ydata.append(r'%s|%s|%s|%s'%(FilePath,ShortVariantName,AirnodeName,item))
