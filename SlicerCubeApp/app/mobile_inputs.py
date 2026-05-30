from kivy.uix.textinput import TextInput
from kivy.utils import platform

class PopupEditTextInput(TextInput):
    def __init__(self, open_popup_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.open_popup_callback = open_popup_callback

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and platform == "android":
            if self.open_popup_callback:
                self.open_popup_callback()
            return True
        return super().on_touch_down(touch)