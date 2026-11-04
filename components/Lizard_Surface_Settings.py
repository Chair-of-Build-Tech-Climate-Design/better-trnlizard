"""
Define the parameters of one building surface type.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
Modified by Junfeng Xiao, 2026.
-

Args:
    Construction (object): define surface construction (refer to Wall Type Library). Empty = keep the value of the surface; a surface without one is an error before the simulation
        Access: item
        Required: False
    Category (object): define boundary conditions of surface. Empty = keep the value of the surface; if it has none, adjacent where another room faces it, otherwise what FallbackBoundary of Lizard_Component gives. AUTOMATIC = back to that rule. GROUND = BOUNDARY with BoundaryTemperature Tsoil
        Access: item
        Required: False
    --------------------- Boundary
    BoundaryTemperature (str): use if category = boundary and if boundary temp. is not identical
        Access: item
        Required: False
    ---------------------- Adjacent
    FrontBack (str): use if category = adjacent in order to define which part of the wall is front or back
        Access: item
        Required: False

Returns:
    out (object): Log Information!!!
        Access: item
    Settings (object): connect to corresponding airnode / - / HINT: Press shift key in order to connect  / multiple outputs to one input node
        Access: item
"""

import Grasshopper.Kernel as gh
version='2.2.1'
ghenv.Component.Name = "Lizard_Surface_Settings"
ghenv.Component.NickName = 'Surface Settings'
ghenv.Component.Message = 'VER 2.2.1\n2020'

class SurfaceDefinition:
    def __init__(self):
        self.Boundarycond = Category #Options are EXTERNAL, ADJACENT, BOUNDARY
        self.Construction = Construction #Set wall type according to library
        self.Boundarytemp = BoundaryTemperature
        self.Frontback = FrontBack #Options are FRONT or BACK
    def __repr__(self):
        """Class representation."""
        return "{0}:{1}:{2}".format('Settings:Surface',self.Construction,self.Boundarycond)
Settings = SurfaceDefinition()
if Settings.Boundarycond == 'GROUND':
    if Settings.Boundarytemp and Settings.Boundarytemp != 'Tsoil':
        ghenv.Component.AddRuntimeMessage(gh.GH_RuntimeMessageLevel.Error, "GROUND means BoundaryTemperature Tsoil: use BOUNDARY for %s"%Settings.Boundarytemp)
    Settings.Boundarycond = 'BOUNDARY'
    Settings.Boundarytemp = 'Tsoil'
if "InternalWallGain" in locals():
    Settings.Wagain = InternalWallGain
if "ExternalWallGain" in locals():
    Settings.Wagaino = ExternalWallGain
