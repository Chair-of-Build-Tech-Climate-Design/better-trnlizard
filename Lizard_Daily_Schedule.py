"""
Define the daily schedule profile.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    Name (object): daily schedule name
        Access: item
        Required: True
    Hours_Domains (object): define the occupation times
        Access: list
        Required: True

Returns:
    out (object): The execution information, as output and error streams
        Access: item
    Daily_Schedule (object): link to the weekly schedule
        Access: item
    Hour_View (object): Script output hour_view.
        Access: item
"""
version='2.2.1'
ghenv.Component.Name = "Lizard_Daily_Schedule"
ghenv.Component.NickName = 'Daily Schedule'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "2 | Extras"
import re
import scriptcontext
import Grasshopper.Kernel as gh
w = gh.GH_RuntimeMessageLevel.Warning
err = gh.GH_RuntimeMessageLevel.Error
#ghenv.Component.AddRuntimeMessage(err, "Capillary heating definition in the Construction is not correct!")
tab = ' '
class Schedule:
    def __init__(self):
        self.Name   = Name
        self.Type   = 'daily'
        self.Hours  = ''
        self.Values = ''
        self.Data = []
Daily_Schedule = Schedule()
hour_array = []
scheduledict = {}
starttime = []
stoptime = []
values = []
#startdict = {}
#stopdict = {}
if Hours_Domains:
    for l, litem in enumerate(Hours_Domains):
        Hours_Domains_split = str(litem)
        new_hours_domain,new_hours_domain_value = Hours_Domains_split.split(";",1)
        new_hours_domain_value = float(new_hours_domain_value)
        start_hours_domain,end_hours_domain = new_hours_domain.split(' to ')
        if ':' in start_hours_domain:
            s1,s2 = start_hours_domain.split(':')
            start_hours_domain = float(s1) + float(s2)/60
        if ':' in end_hours_domain:
            e1,e2 = end_hours_domain.split(':')
            end_hours_domain = float(e1) + float(e2)/60
        start_hours_domain = float(start_hours_domain)
        end_hours_domain = float(end_hours_domain)
        for i,item in enumerate(values):
            if start_hours_domain == starttime[i] or end_hours_domain == stoptime[i]:
                print "error overlapping definition found1"
            elif start_hours_domain > starttime[i] and start_hours_domain < stoptime[i] or end_hours_domain > starttime[i] and end_hours_domain < stoptime[i]:
                print "error overlapping definition found2"
            else:
                pass
        scheduledict[start_hours_domain] = new_hours_domain_value
        if end_hours_domain in scheduledict:
            pass
        elif end_hours_domain == 24:
            scheduledict[end_hours_domain] = scheduledict[start_hours_domain]
        else:
            scheduledict[end_hours_domain] = 0
        starttime.append(start_hours_domain)
        stoptime.append(end_hours_domain)
        values.append(new_hours_domain_value)
Hour_View = []
#add first and last value if they don't exist
if 0 in scheduledict:
    pass
else:
    scheduledict[0] = 0
if 24 in scheduledict:
    pass
else:
    scheduledict[24] = 0
for key in sorted(scheduledict.iterkeys()):
    Daily_Schedule.Hours = Daily_Schedule.Hours + str(key) + tab
    Daily_Schedule.Values = Daily_Schedule.Values + str(scheduledict[key]) + tab
    Hour_View.append("%s %s"%(key,scheduledict[key]))
#Hour_View = []
#for i in range(0,24):
#    print i
#    print Hour_View
#    if i in scheduledict:
#        Hour_View.append(scheduledict[i])
#    else:
#        Hour_View.append(Hour_View[-1])
Daily_Schedule.Data = Hour_View
