"""
GhPython provides a Python script component

Args:
    Brep (Brep): Script variable Python
        Access: list
        Required: False
    RadMaterial (object): Script input RadMaterial.
        Access: item
        Required: False

Returns:
    AddDaylightGeometry (object): Script output AddDaylightGeometry.
        Access: item
"""
import Rhino as rc
version='2.2.1'
for bitem in Brep:
    bitem.UserDictionary.Set("MAT", RadMaterial)
AddDaylightGeometry = Brep
