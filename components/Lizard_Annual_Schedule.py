"""
Define the weekly schedule profile.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    name (object): annual schedule name
        Access: item
        Required: False
    January (float): link monthly input information
        Access: item
        Required: False
    February (float): link daily input information
        Access: item
        Required: False
    March (float): link monthly input information
        Access: item
        Required: False
    April (float): link monthly input information
        Access: item
        Required: False
    May (float): link monthly input information
        Access: item
        Required: False
    June (float): link monthly input information
        Access: item
        Required: False
    July (float): link monthly input information
        Access: item
        Required: False
    August (float): link monthly input information
        Access: item
        Required: False
    September (float): link monthly input information
        Access: item
        Required: False
    October (float): link monthly input information
        Access: item
        Required: False
    November (float): link monthly input information
        Access: item
        Required: False
    December (float): link monthly input information
        Access: item
        Required: False

Returns:
    Annual_Schedule (object): link to the library component
        Access: item
    Monthly_View (object): Script output hour_view.
        Access: item
"""
version='2.2.1'
ghenv.Component.Name        = "Lizard_Annual_Schedule"
ghenv.Component.NickName    = 'Annual Schedule'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category    = "TRNLizard"
ghenv.Component.SubCategory = "5 | Tools"
import rhinoscriptsyntax as rs
import re
import scriptcontext
import ghpythonlib.components as ghcomp
class Annualschedule:
    def __init__(self):
        self.Name = name
        self.Annual = 1
        self.January = January
        self.February = February
        self.March = March
        self.April = April
        self.May = May
        self.June = June
        self.July = July
        self.August = August
        self.September = September
        self.October = October
        self.November = November
        self.December = December
Annual_Schedule = Annualschedule()
Monthly_View = [0]
Monthly_View.append(January)
Monthly_View.append(January)
Monthly_View.append(February)
Monthly_View.append(February)
Monthly_View.append(March)
Monthly_View.append(March)
Monthly_View.append(April)
Monthly_View.append(April)
Monthly_View.append(May)
Monthly_View.append(May)
Monthly_View.append(June)
Monthly_View.append(June)
Monthly_View.append(July)
Monthly_View.append(July)
Monthly_View.append(August)
Monthly_View.append(August)
Monthly_View.append(September)
Monthly_View.append(September)
Monthly_View.append(October)
Monthly_View.append(October)
Monthly_View.append(November)
Monthly_View.append(November)
Monthly_View.append(December)
Monthly_View.append(December)
