from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.metrics import dp, sp


def showMessagePopup(text, title="Info", font_name=None, size_hint=(0.7, 0.4)):
    label = Label(text=text, halign="center", valign="middle")
    label.bind(size=lambda *_: setattr(label, "text_size", label.size))
    if font_name:
        label.font_name = font_name

    popup = Popup(
        title=title,
        content=label,
        size_hint=size_hint,
    )
    popup.open()
    return popup


def openQrEditPopup(current_text, onApply, title="Edit dots", size_hint=(0.95, 0.6), pos_hint=None, font_size=None, style_callback=None):
    content = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))

    edit_input = TextInput(
        text=current_text,
        multiline=True,
        size_hint=(1, 1),
        font_size=font_size or sp(13),
    )
    content.add_widget(edit_input)

    btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
    btn_cancel = Button(text="Cancel")
    btn_apply = Button(text="Apply")
    btn_row.add_widget(btn_cancel)
    btn_row.add_widget(btn_apply)
    content.add_widget(btn_row)

    popup = Popup(
        title=title,
        content=content,
        size_hint=size_hint,
    )
    if pos_hint is not None:
        popup.pos_hint = pos_hint

    def doCancel(*_):
        popup.dismiss()

    def doApply(*_):
        onApply(edit_input.text)
        popup.dismiss()

    if style_callback is not None:
        style_callback(content)

    btn_cancel.bind(on_press=doCancel)
    btn_apply.bind(on_press=doApply)

    popup.open()
    return popup
