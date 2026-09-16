"""
This defines the plotter settings.
-
TRNLizard 
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    Output (object): Script variable PlotData
        Access: item
        Required: True
    Label (object): Script variable PlotData
        Access: item
        Required: True
    Color (object): Script variable PlotData
        Access: item
        Required: True

Returns:
    out (object): Information
        Access: item
    Output_ (object): Chart settings need to be linked to the plotter component
        Access: item
"""
ghenv.Component.Name = "Lizard_Plot_Data_Settings"
ghenv.Component.NickName = 'PlotDataSet'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "2 | Extras"
class Info:
    def __init__(self):
        self.Output = r''
        self.Label = r''
        self.Color = r'none'
Output_ = Info()
if Output:
    Output_.Output = r'%s'%(Output)
if Label:
    Output_.Label = r'%s'%(Label)
if Color:
    Output_.Color = r'rgb(%s;%s;%s)'%(Color.R, Color.G, Color.B)
