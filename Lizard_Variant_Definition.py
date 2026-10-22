"""
GhPython provides a Python script component

Args:
    slider (object): Script variable Python
        Access: item
        Required: False

Returns:
    VarName (object): Script output VarName.
        Access: item
    Desc (object): Script output Desc.
        Access: item
    Variants (object): Script output Variants.
        Access: item
"""
version='2.2.1'
class Variants():
    def __init__(self):
        self.ExtWalls = "EWL_L"
        self.VarName = "V0"
        self.WindowRatio = 0.5
    def __repr__(self):
        return "Variants"
Variants = Variants()
setattr(Variants,'dummy',1)
print dir(Variants)
if slider == 0:
    pass
elif slider == 1:
    Variants.WindowRatio = 0.6
Desc = "VAR" + str(int(slider) )
VarName = "VAR" + str(int(slider) )
#VarName = "V%s_%s"%(str(int(slider)),Variants.ExtWalls)
Variants.VarName = VarName
