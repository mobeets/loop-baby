
class Button:
    def __init__(self, name, button_number, interface):
        self.name = name
        self.button_number = button_number
        self.interface = interface

    def set_color(self, color):
        """
        color is str
        and can be either the color name, or a key to color_map
        """
        self.interface.set_color(self.button_number, color)
