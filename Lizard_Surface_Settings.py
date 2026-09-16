"""
Define the parameters of one building surface type.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    Construction (object): define surface construction (refer to Wall Type Library)
        Access: item
        Required: True
    Category (object): define boundary conditions of surface
        Access: item
        Required: True
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
if "InternalWallGain" in locals():
    Settings.Wagain = InternalWallGain
if "ExternalWallGain" in locals():
    Settings.Wagaino = ExternalWallGain
