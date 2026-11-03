"""
Define the weekly schedule profile.
-
TRNLizard 
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    Name (object): weekly schedule name
        Access: item
        Required: True
    Monday (object): link daily input information
        Access: item
        Required: True
    Tuesday (object): link daily input information
        Access: item
        Required: True
    Wednesday (object): link daily input information
        Access: item
        Required: True
    Thursday (object): link daily input information
        Access: item
        Required: True
    Friday (object): link daily input information
        Access: item
        Required: True
    Saturday (object): link daily input information
        Access: item
        Required: True
    Sunday (object): link daily input information
        Access: item
        Required: True

Returns:
    out (object): The execution information, as output and error streams
        Access: item
    Schedule (object): link to the library component
        Access: item
    Hour_View (object): Script output hour_view.
        Access: item
"""
version='2.2.1'
ghenv.Component.Name        = "Lizard_Weekly_Schedule"
ghenv.Component.NickName    = 'Weekly Schedule'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category    = "TRNLizard"
ghenv.Component.SubCategory = "5 | Tools"
import rhinoscriptsyntax as rs
import re
import scriptcontext
import ghpythonlib.components as ghcomp
class Weekschedule:
    def __init__(self):
        self.Name = Name
        self.Days = '1 2 3 4 5 6 7'
        self.Hourly = ''
        self.Daysarray = []
        self.Hoursarray = []
        self.Valuesarray = []
tab = ' '
weekarray = [Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday]
Schedule = Weekschedule()
Hour_View = []
for item in weekarray:
    Schedule.Hourly = Schedule.Hourly + item.Name + tab
    Schedule.Daysarray.append(item.Name)
    Schedule.Hoursarray.append(item.Hours)
    Schedule.Valuesarray.append(item.Values)
    Hour_View.extend(item.Data)
