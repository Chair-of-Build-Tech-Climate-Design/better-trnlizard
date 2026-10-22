"""
GhPython provides a Python script component

Args:
    DaylightGeometry (Brep): Script input DaylightGeometry.
        Access: list
        Required: False
    DaylightMaterial (str): Script input DaylightMaterial.
        Access: item
        Required: False
    ShadingFractionExtA (object): Script input ShadingFractionExtA.
        Access: item
        Required: False
    ShadingFractionIntA (object): Script input ShadingFractionIntA.
        Access: item
        Required: False
    ShadingFractionExtB (object): Script input ShadingFractionExtB.
        Access: item
        Required: False
    ShadingFractionIntB (object): Script input ShadingFractionIntB.
        Access: item
        Required: False

Returns:
    Shader (object): Script output Shader.
        Access: item
    Geometry (object): Script output Geometry.
        Access: item
"""
ghenv.Component.Name = "Lizard_Operable_Shading"
ghenv.Component.NickName = 'Operable_Shading'
ghenv.Component.Message = 'VER 2.1.2\n2019'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Construction"
version='2.1.2'
dlgeo = DaylightGeometry
dlmat = DaylightMaterial
class SHADING():
    def __init__(self):
        self.Dlgeo = ''
        self.Dlmat = ''
        self.Ishadeglazingcovera = ShadingFractionIntA/100
        self.Eshadeglazingcovera = ShadingFractionExtA/100
        self.Ishadeglazingcoverb = ShadingFractionIntB/100
        self.Eshadeglazingcoverb = ShadingFractionExtB/100
Shader = SHADING()
Shader.Dlgeo = dlgeo
Shader.Dlmat = dlmat
Geometry = dlgeo
