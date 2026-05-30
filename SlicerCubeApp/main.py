from kivy.app import App
from kivy.core.window import Window
from app.root_widget import RootWidget

class SlicerCubeAR(App):
    title = "SlicerCubeAR"

    def build(self):
        Window.clearcolor = (0, 0, 0, 1)
        return RootWidget()

if __name__ == "__main__":
    SlicerCubeAR().run()
