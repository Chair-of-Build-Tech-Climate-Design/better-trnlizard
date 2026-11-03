"""
This defines the plotter settings.
-
TRNLizard 
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    Title (object): String that defines the chart title
        Access: item
        Required: True
    Xlabel (object): Script variable Python
        Access: item
        Required: True
    Ylabel (object): Script variable PlotSettings
        Access: item
        Required: True
    Ystart (object): Script variable PlotSettings
        Access: item
        Required: True
    Ystop (object): Script variable PlotSettings
        Access: item
        Required: True
    Ydticks (object): Script variable PlotSettings
        Access: item
        Required: True
    Xstart (object): Script variable PlotSettings
        Access: item
        Required: True
    Xstop (object): Script variable PlotSettings
        Access: item
        Required: True
    Xdticks (object): Script variable PlotSettings
        Access: item
        Required: True
    Data (object): Script variable PlotSettings
        Access: list
        Required: True
    Type (object): Script variable PlotSettings
        Access: item
        Required: True
    Comfort (object): Script variable PlotSettings
        Access: item
        Required: True
    Fill (object): Script variable PlotSettings
        Access: item
        Required: True
    Image (object): Script variable PlotSettings
        Access: item
        Required: True
    Width (object): Script variable PlotSettings
        Access: item
        Required: True

Returns:
    out (object): Information
        Access: item
    Settings_ (object): Chart settings need to be linked to the plotter component
        Access: item
"""
ghenv.Component.Name = "Lizard_Plot_Settings"
ghenv.Component.NickName = 'PlotSettings'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "5 | Tools"
from collections import defaultdict
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
error = ghenv.Component.RuntimeMessageLevel.Error
warning = ghenv.Component.RuntimeMessageLevel.Warning
class Settings:
    def __init__(self):
        self.Title = "r' '"
        self.Subtitle = "r' '"
        self.Xlabel  = "r' '"
        self.Ylabel = "r' '"
        self.Xdata = [[]]
        self.Xstart = 0
        self.Xstop = 168
        self.Xdticks = 1000
        self.Ydata = []
        self.Ystart = -10
        self.Ystop = 40
        self.Ydticks = 10
        self.Titlesize = 24
        self.Fontsize = 14
        self.Fill = "r'none'" #options are e.g. 'tozeroy' or 'none'
        self.Comfort = "r'none'" #options are e.g. 'none' or 'D15251NA' or 'D4108RESC' or 'DIN15251ENADII' or 'DIN15251ENADIIEL'
        self.Width = 150
        self.Height = 500
        self.Image = "r'none'" #options are e.g. 'svg' or 'none' or 'png'
        self.Opacity = 0.8
        self.Carray = [10,20,26,32]
        self.Annotation = 1
Settings_ = Settings()
if Title != None:
    Settings_.Title = "r'{0}'".format(Title)
if Xlabel != None:
    Settings_.Xlabel = "r'{0}'".format(Xlabel)
if Ylabel != None:
    Settings_.Ylabel = "r'{0}'".format(Ylabel)
if Ystart != None:
    Settings_.Ystart = Ystart
if Ystop != None:
    Settings_.Ystop = Ystop
if Ydticks != None:
    Settings_.Ydticks = Ydticks
if Xstart != None:
    Settings_.Xstart = Xstart
if Xstop != None:
    Settings_.Xstop = Xstop
if Xdticks != None:
    Settings_.Xdticks = Xdticks
if Data != None:
    Settings_.Xdata = r"["
    Settings_.Ydata = r"["
    for ix,item in enumerate(Data):
        for sy,subyitem in enumerate(item.Ydata):
            Settings_.Ydata += r"'{0}'".format(subyitem)
            if ix <= len(Data)-1 and sy == len(item.Ydata)-1:
                pass
            else:
                Settings_.Ydata += r","
        for sx,subxitem in enumerate(item.Xdata):
            Settings_.Xdata += r"'{0}'".format(subxitem)
            if ix <= len(Data)-1 and sx == len(item.Xdata)-1:
                pass
            else:
                Settings_.Xdata += r","
    Settings_.Xdata += r"]"
    Settings_.Ydata += r"]"
if Type != None:
    Settings_.Type = "r'{0}'".format(Type)
    if Type == 'SEQUENCE' or Type == 'LOAD':
        if Settings_.Xstart < 0:
            ghenv.Component.AddRuntimeMessage(error, 'The minimum allowed value for the x-Axis is 0!')
        if Settings_.Xstop > 8760:
            ghenv.Component.AddRuntimeMessage(error, 'The maximum allowed value for the x-Axis is 8760 or the number of actual simulated hours!')
if Comfort != None:
    Settings_.Comfort = "r'{0}'".format(Comfort)
if Fill != None:
    Settings_.Fill = "r'{0}'".format(Fill)
if Image != None:
    Settings_.Image = "r'{0}'".format(Image)
if Width != None:
    Settings_.Width = Width
