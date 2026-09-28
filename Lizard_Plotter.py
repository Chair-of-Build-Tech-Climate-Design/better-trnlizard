"""
Generate Result Diagrams
-
TRNLizard 
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    Settings (object): Script variable Plot
        Access: list
        Required: True
    ScriptPath (object): Script variable Plot
        Access: item
        Required: True
    OutputFilePath (object): Script variable Plot
        Access: item
        Required: True
    Plot (object): 
        Access: item
        Required: True

Returns:
    out (object): 
        Access: item
"""
ghenv.Component.Name = "Lizard_Plotter"
ghenv.Component.NickName = 'Plot'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "2 | Extras"
import sys
from subprocess import Popen
import subprocess
import rhinoscriptsyntax as rs
import ctypes
import scriptcontext as sc
import os
import inspect
import subprocess
ctrlout = open(OutputFilePath.encode('string-escape') + 'control.txt', 'w')
counter = 0
for item in Settings:
    counter += 1
    dummy = item.__dict__
    ctrlout.write('#plot%s definition\n'%(counter))
    for key in dummy:
        try:
            dummy2 = dummy[key].__dict__
            for key2 in dummy2:
                ctrlout.write('plot%s.%s = %s\n'%(counter,key2,dummy2[key2]))
        except:
            ctrlout.write('plot%s.%s = %s\n'%(counter,key,dummy[key]))
ctrlout.close()
#This call is not wating and directly jumps back to rhino after executing the simulation
if Plot == 1:
    #proc = Popen( analysis_folder + 'plots.py ' + 'control.txt' , shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
    proc = Popen( ScriptPath + ' ' + 'control.txt' , shell=True, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=False, cwd=OutputFilePath.encode('string-escape'))
    mess, err = proc.communicate() #now wait
    print mess
    print err
    #dummy = err.split()
    #if len(err) > 0:
    #    print 'ERROR: %s'%dummy[-1]
    #else:
    #    print mess
        #print 'Execution completed successfully!'
#    proc1 = Popen( weatherconverter, shell=hide_shell, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=False)#
#    mess, err = proc1.communicate() #now wait
