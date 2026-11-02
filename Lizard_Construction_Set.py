"""
Default constructions by the kind of surface. Lizard_System gives them to the surfaces that have no construction once the adjacency is
solved, so one wall that is split into an outer and an inner part gets a construction for each part.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Connect Set to the input ConstructionSet of Lizard_Multizone for the whole building, or of Lizard_Thermal_Airnode for one room. The
airnode comes first, slot by slot: an empty slot is looked up in the set of the model. A construction in Lizard_Surface_Settings always
wins. Windows and active layers need that explicit construction: a set does not fill them.

Args:
    ExteriorWall (str): wall with outside air
        Access: item
        Required: False
    InteriorWall (str): wall towards another airnode, or BOUNDARY
        Access: item
        Required: False
    Roof (str): ceiling or roof with outside air
        Access: item
        Required: False
    InteriorCeiling (str): ceiling towards another airnode, or BOUNDARY. Mirror of InteriorFloor, or empty if that one is symmetric
        Access: item
        Required: False
    InteriorFloor (str): floor towards another airnode, or BOUNDARY with the air temperature of the room itself (an unmodelled neighbour below)
        Access: item
        Required: False
    GroundFloor (str): floor with any other BOUNDARY, for example the ground
        Access: item
        Required: False
    ExposedFloor (str): floor with outside air
        Access: item
        Required: False

Returns:
    out (object): Log Information!!!
        Access: item
    Set (object): connect to ConstructionSet of Lizard_Multizone or Lizard_Thermal_Airnode
        Access: item
"""
import scriptcontext as sc
import Grasshopper.Kernel as gh
version = '1.0.0'
ghenv.Component.Name = "Lizard_Construction_Set"
ghenv.Component.NickName = 'Construction Set'
ghenv.Component.Message = 'VER %s'%version
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "0 | Project"
err = gh.GH_RuntimeMessageLevel.Error
class ConstructionSet:
    def __init__(self):
        self.ExteriorWall = ExteriorWall
        self.InteriorWall = InteriorWall
        self.Roof = Roof
        self.InteriorCeiling = InteriorCeiling
        self.InteriorFloor = InteriorFloor
        self.GroundFloor = GroundFloor
        self.ExposedFloor = ExposedFloor
    def __repr__(self):
        """Class representation."""
        return "{0}:{1}".format('Settings:ConstructionSet',self.ExteriorWall)
Set = ConstructionSet()
known = [wall_item.Name for wall_item in sc.sticky[sc.doc.Path]["library"].Walls]
for slot, name in sorted(vars(Set).items()):
    if name and name not in known:
        ghenv.Component.AddRuntimeMessage(err, "{0}: construction {1} not found in the library!".format(slot, name))
