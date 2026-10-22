"""
GhPython provides a Python script component

Args:
    Shader2 (object): Script variable Python
        Access: item
        Required: False
    Shader3 (object): Script input Shader3.
        Access: item
        Required: False
    Shader4 (object): Script input Shader4.
        Access: item
        Required: False
    Shader5 (object): Script input Shader5.
        Access: item
        Required: False
    Shader6 (object): Script input Shader6.
        Access: item
        Required: False
    Shader7 (object): Script input Shader7.
        Access: item
        Required: False
    Shader8 (object): Script input Shader8.
        Access: item
        Required: False
    Shader9 (object): Script input Shader9.
        Access: item
        Required: False
    Control (object): Script input Control.
        Access: item
        Required: False

Returns:
    ComplexShade (object): Script output ComplexShade.
        Access: item
"""
ghenv.Component.Name = "Lizard_Complex_Shader"
ghenv.Component.NickName = 'Complex_Shader'
ghenv.Component.Message = 'VER 2.1.2\n2019'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Construction"
version='2.1.2'
class CPLSHADE():
    def __init__(self):
        self.Shd2 = None
        self.Shd3 = None
        self.Shd4 = None
        self.Shd5 = None
        self.Ctrl = None
ComplexShade = CPLSHADE()
ComplexShade.Ctrl = Control
if 'Shader2' in locals():
    if Shader2 is not None:
        ComplexShade.Shd2 = Shader2
if 'Shader3' in locals():
    if Shader3 is not None:
        ComplexShade.Shd3 = Shader3
if 'Shader4' in locals():
    if Shader4 is not None:
        ComplexShade.Shd4 = Shader4
if 'Shader5' in locals():
    if Shader5 is not None:
        ComplexShade.Shd5 = Shader5
if 'Shader6' in locals():
    if Shader6 is not None:
        ComplexShade.Shd6 = Shader6
if 'Shader7' in locals():
    if Shader7 is not None:
        ComplexShade.Shd7 = Shader7
if 'Shader8' in locals():
    if Shader8 is not None:
        ComplexShade.Shd8 = Shader8
if 'Shader9' in locals():
    if Shader9 is not None:
        ComplexShade.Shd9 = Shader9
