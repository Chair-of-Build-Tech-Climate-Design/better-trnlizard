"""
GhPython provides a Python script component

Args:
    Crit0 (object): Script variable Shading_Control
        Access: item
        Required: False
    Crit1 (object): Script input Crit1.
        Access: item
        Required: False
    Crit2 (object): Script input Crit2.
        Access: item
        Required: False
    Crit3 (object): Script input Crit3.
        Access: item
        Required: False
    Shd2 (object): Script input Shd2.
        Access: item
        Required: False
    Shd3 (object): Script input Shd3.
        Access: item
        Required: False
    Shd4 (object): Script input Shd4.
        Access: item
        Required: False
    Shd5 (object): Script input Shd5.
        Access: item
        Required: False
    Shd6 (object): Script input Shd6.
        Access: item
        Required: False
    Shd7 (object): Script input Shd7.
        Access: item
        Required: False
    Shd8 (object): Script input Shd8.
        Access: item
        Required: False
    Shd9 (object): Script input Shd9.
        Access: item
        Required: False

Returns:
    Control (object): Script output Control.
        Access: item
"""
ghenv.Component.Name = "Lizard_Shading_Control"
ghenv.Component.NickName = 'Shading_Control'
ghenv.Component.Message = 'VER 2.1.2\n2019'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Construction"
version='2.1.2'
class SHDCONTROL():
    def __init__(self):
        self.Crit0 = Crit0
        self.Crit1 = Crit1
        self.Crit2 = Crit2
        self.Crit3 = Crit3
        self.State2 = Shd2
        self.State3 = Shd3
        self.State4 = Shd4
        self.State5 = Shd5
        self.State6 = Shd6
        self.State7 = Shd7
        self.State8 = Shd8
        self.State9 = Shd9
Control = SHDCONTROL()
