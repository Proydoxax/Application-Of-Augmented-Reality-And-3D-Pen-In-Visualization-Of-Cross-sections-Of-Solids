import os

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.utils import platform
from kivy.metrics import dp, sp
from kivy.graphics import Color, Line, Rectangle

from .cube_widget import CubeWidget
from .constants import ROW_HEIGHT, TEXT_HEIGHT, registerVigaFont
from .mobile_inputs import PopupEditTextInput
from .popups import openQrEditPopup as openTextEditPopup
from .popups import showMessagePopup as showInfoPopup


class RootWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.app_font_name = registerVigaFont()

        self.camera_permission_pending = False
        self.camera_popup = None

        self.ar_bridge = None
        self.latest_cube_payload = None
        self.shift_hold_event = None
        self.shift_hold_direction = 0
        self.shift_hold_elapsed = 0.0

        self.logo_path = os.path.join(os.path.dirname(__file__), "logo", "APPlogo.png")

        self.cube = CubeWidget(size_hint=(1, 1))
        self.add_widget(self.cube)

        row_h = ROW_HEIGHT
        text_h = TEXT_HEIGHT

        self.controls_root = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=row_h * 5 + text_h,
            padding=dp(6),
            spacing=dp(4),
        )
        self.add_widget(self.controls_root)

        self.edge_controls = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=row_h,
            padding=(0, dp(2)),
            spacing=dp(4),
        )
        self.controls_root.add_widget(self.edge_controls)

        self.btn_cancel = Button(text="X", font_size=sp(14))
        self.btn_cancel.bind(on_press=self.onCancelEdge)
        self.edge_controls.add_widget(self.btn_cancel)

        self.btn_left = Button(text="<", font_size=sp(16))
        self.btn_left.bind(on_press=self.onShiftLeft)
        self.btn_left.bind(state=self.onShiftLeftState)
        self.edge_controls.add_widget(self.btn_left)

        self.edge_value = TextInput(
            text="0.50",
            multiline=False,
            input_filter="float",
            size_hint_x=1.2,
            font_size=sp(14),
        )
        self.edge_value.bind(text=self.onEdgeValueText)
        self.edge_controls.add_widget(self.edge_value)

        self.btn_right = Button(text=">", font_size=sp(16))
        self.btn_right.bind(on_press=self.onShiftRight)
        self.btn_right.bind(state=self.onShiftRightState)
        self.edge_controls.add_widget(self.btn_right)

        self.btn_ok = Button(text="OK", font_size=sp(14))
        self.btn_ok.bind(on_press=self.onConfirmEdge)
        self.edge_controls.add_widget(self.btn_ok)

        self.showEdgeControls(False)

        undo_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=row_h,
            spacing=dp(4),
        )
        self.controls_root.add_widget(undo_row)

        self.btn_erase_mode = Button(text="POINT ERASE MODE", font_size=sp(10), disabled=True)
        self.btn_erase_mode.bind(on_press=self.onTogglePointEraseMode)
        undo_row.add_widget(self.btn_erase_mode)

        self.btn_remove_point = Button(text="ERASE POINT", font_size=sp(10), disabled=True)
        self.btn_remove_point.bind(on_press=self.onRemoveSelectedPoint)
        undo_row.add_widget(self.btn_remove_point)

        self.btn_undo = Button(text="UNDO LAST POINT", font_size=sp(10), disabled=True)
        self.btn_undo.bind(on_press=self.onUndoLastPoint)
        undo_row.add_widget(self.btn_undo)

        action_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=row_h,
            spacing=dp(4),
        )
        self.controls_root.add_widget(action_row)

        self.btn_camera = Button(text="SCAN TEMPLATE", font_size=sp(13))
        self.btn_camera.bind(on_press=self.onOpenCameraScan)
        self.styleActionButton(self.btn_camera)
        action_row.add_widget(self.btn_camera)

        self.btn_split = Button(text="SPLIT", font_size=sp(13), disabled=True)
        self.btn_split.bind(on_press=self.onToggleSplit)
        self.styleActionButton(self.btn_split)
        action_row.add_widget(self.btn_split)

        self.btn_ar_mode = Button(text="AR MODE", font_size=sp(13), disabled=True)
        self.btn_ar_mode.bind(on_press=self.onOpenArMode)
        self.styleActionButton(self.btn_ar_mode)
        action_row.add_widget(self.btn_ar_mode)

        toggle_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=row_h,
            spacing=dp(4),
        )
        self.controls_root.add_widget(toggle_row)

        self.btn_net = Button(text="2D NET", font_size=sp(11))
        self.btn_net.bind(on_press=self.onToggleNetView)
        toggle_row.add_widget(self.btn_net)

        self.btn_faces = Button(text="FACES", font_size=sp(13))
        self.btn_faces.bind(on_press=self.onToggleFaces)
        toggle_row.add_widget(self.btn_faces)

        self.btn_edges = Button(text="EDGES", font_size=sp(13))
        self.btn_edges.bind(on_press=self.onToggleEdges)
        toggle_row.add_widget(self.btn_edges)

        self.btn_coords = Button(text="T LABELS", font_size=sp(13))
        self.btn_coords.bind(on_press=self.onToggleCoords)
        toggle_row.add_widget(self.btn_coords)

        load_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=row_h,
            spacing=dp(4),
        )
        self.controls_root.add_widget(load_row)

        self.btn_load = Button(text="LOAD TEXT", font_size=sp(13))
        self.btn_load.bind(on_press=self.onLoadQrText)
        load_row.add_widget(self.btn_load)

        self.ar_status = Label(text="AR: scan the blueprint first.", halign="left", valign="middle")
        self.ar_status.bind(size=lambda *_: setattr(self.ar_status, "text_size", self.ar_status.size))

        qr_container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=text_h,
        )
        self.controls_root.add_widget(qr_container)

        self.qr_input = PopupEditTextInput(
            open_popup_callback=self.openQrEditPopup,
            hint_text="face, edge, t per line (e.g. 1, 2, 0.5)",
            multiline=True,
            size_hint=(1, 1),
            font_size=sp(13),
        )
        qr_container.add_widget(self.qr_input)

        self.applyAppTextStyle(self)
        self.updateArPayloadFromCube()


    def applyAppTextStyle(self, widget):
        if self.app_font_name and hasattr(widget, "font_name"):
            try:
                widget.font_name = self.app_font_name
            except Exception:
                pass
        if isinstance(widget, Button):
            widget.text = str(widget.text).upper()
        for child in getattr(widget, "children", []):
            self.applyAppTextStyle(child)

    def styleActionButton(self, button):
        button.background_normal = ""
        button.background_down = ""
        try:
            button.background_disabled_normal = ""
        except Exception:
            pass
        button.background_color = (0, 0, 0, 0)
        button.color = (1, 1, 1, 1)
        button.disabled_color = (0.70, 0.70, 0.70, 1)

        border_color = (0x25 / 255.0, 0x0E / 255.0, 0x5C / 255.0, 1.0)
        enabled_fill = (0.0, 0.0, 0.0, 1.0)
        disabled_fill = (0.22, 0.22, 0.22, 1.0)

        def redraw(*_):
            button.canvas.before.clear()
            button.canvas.after.clear()
            fill = disabled_fill if button.disabled else enabled_fill
            with button.canvas.before:
                Color(*fill)
                Rectangle(pos=button.pos, size=button.size)
            with button.canvas.after:
                Color(*border_color)
                Line(rectangle=(button.x, button.y, button.width, button.height), width=dp(1.3))

        button.bind(pos=redraw, size=redraw, disabled=redraw, state=redraw)
        redraw()

    def getArBridge(self):
        if self.ar_bridge is None:
            from .ar_bridge import ARBridge
            self.ar_bridge = ARBridge()
        return self.ar_bridge

    def updateArPayloadFromCube(self):
        split_caps = []
        if hasattr(self.cube, "buildSplitCapPayload"):
            try:
                split_caps = self.cube.buildSplitCapPayload()
            except Exception:
                split_caps = []

        if hasattr(self.cube, "dedupedIntersectionList"):
            intersections = self.cube.dedupedIntersectionList()
        else:
            intersections = self.cube.intersections

        self.latest_cube_payload = {
            "intersections": [dict(dot) for dot in intersections],
            "text": self.qr_input.text.strip(),
            "split_requested": bool(getattr(self.cube, "split_mode", False)),
            "split_caps": split_caps,
        }

        has_points = bool(intersections)
        split = bool(getattr(self.cube, "split_mode", False))
        erase_mode = bool(getattr(self.cube, "point_erase_mode", False))
        editing_dot = getattr(self.cube, "mode", "") == "edge"
        scan_view = bool(getattr(self.cube, "scan_verification_mode", False))
        net_view = bool(getattr(self.cube, "net_2d_mode", False))
        invalid_placement = (
            bool(self.cube.hasInvalidPlacementWarning())
            if hasattr(self.cube, "hasInvalidPlacementWarning")
            else False
        )
        valid_split, validation_msg = self.cube.validateSplitDefinition() if has_points else (False, "Scan the blueprint first.")
        is_ready = has_points and valid_split

        if hasattr(self, "btn_undo"):
            self.btn_undo.disabled = (not has_points) or split or editing_dot

        if hasattr(self, "btn_erase_mode"):
            self.btn_erase_mode.disabled = (not has_points) or split
            self.btn_erase_mode.text = "EXIT ERASE MODE" if erase_mode else "POINT ERASE MODE"

        if hasattr(self.cube, "selectedErasePointCount"):
            selected_erase_point_count = self.cube.selectedErasePointCount()
        else:
            selected_erase_point_count = 1 if getattr(self.cube, "erase_candidate_index", None) is not None else 0
        if hasattr(self, "btn_remove_point"):
            self.btn_remove_point.text = "ERASE POINTS" if selected_erase_point_count > 1 else "ERASE POINT"
            self.btn_remove_point.disabled = (not erase_mode) or (selected_erase_point_count <= 0)
        if hasattr(self, "btn_coords"):
            self.btn_coords.disabled = (not has_points) or invalid_placement

        if hasattr(self, "btn_split"):
            self.btn_split.text = "UNSPLIT" if split else "SPLIT"
            self.btn_split.disabled = erase_mode or net_view or not (valid_split or split)

        if hasattr(self, "btn_camera"):
            self.btn_camera.disabled = platform != "android" or erase_mode or editing_dot
        if hasattr(self, "btn_load"):
            self.btn_load.disabled = erase_mode or editing_dot
        if hasattr(self, "btn_faces"):
            self.btn_faces.disabled = split or editing_dot
        if hasattr(self, "btn_edges"):
            self.btn_edges.disabled = split or editing_dot
        if hasattr(self, "btn_net"):
            if scan_view:
                self.btn_net.text = "CONFIRM SCAN"
            elif net_view:
                self.btn_net.text = "CUBE VIEW"
            else:
                self.btn_net.text = "2D NET"
            self.btn_net.disabled = split or editing_dot

        ar_disabled = erase_mode or net_view or not is_ready
        if platform == "android":
            self.btn_ar_mode.disabled = ar_disabled

            if erase_mode:
                self.ar_status.text = "Erase mode active."
            elif net_view:
                self.ar_status.text = "Return to cube view before AR mode."
            elif not has_points:
                self.ar_status.text = "AR: scan the blueprint first."
            elif not valid_split:
                self.ar_status.text = f"Invalid dots: {validation_msg}"
            else:
                self.ar_status.text = "ARCore: ready. Tap AR mode, scan a table, then tap to place."
            return

        self.btn_ar_mode.disabled = True

        if erase_mode:
            self.ar_status.text = "Erase mode active."
        elif net_view:
            self.ar_status.text = "Return to cube view before AR mode."
        elif not has_points:
            self.ar_status.text = "AR: scan the blueprint first."
        elif not valid_split:
            self.ar_status.text = f"Invalid dots: {validation_msg}"
        else:
            self.ar_status.text = "ARCore mode is available in Android builds."

    def onToggleSplit(self, _instance):
        if getattr(self.cube, "point_erase_mode", False) or getattr(self.cube, "net_2d_mode", False):
            return
        self.cube.toggleSplitMode()
        self.updateArPayloadFromCube()

    def syncTextFromCube(self):
        if hasattr(self.cube, "formatIntersectionsAsText"):
            self.qr_input.text = self.cube.formatIntersectionsAsText()

    def onUndoLastPoint(self, _instance):
        if getattr(self.cube, "mode", "") == "edge" or getattr(self.cube, "split_mode", False):
            return
        if hasattr(self.cube, "undoLastPoint") and self.cube.undoLastPoint():
            self.syncTextFromCube()
            self.updateArPayloadFromCube()

    def onTogglePointEraseMode(self, _instance):
        enabled = not bool(getattr(self.cube, "point_erase_mode", False))
        if hasattr(self.cube, "setPointEraseMode"):
            self.cube.setPointEraseMode(enabled)
        self.showEdgeControls(False)
        self.syncTextFromCube()
        self.updateArPayloadFromCube()

    def onPointEraseSelectionChanged(self):
        self.updateArPayloadFromCube()

    def onRemoveSelectedPoint(self, _instance):
        if hasattr(self.cube, "removeSelectedErasePoint") and self.cube.removeSelectedErasePoint():
            self.syncTextFromCube()
        self.updateArPayloadFromCube()

    def onFinishScanVerification(self, _instance):
        if getattr(self.cube, "split_mode", False):
            return
        if getattr(self.cube, "mode", "") == "edge":
            return
        if hasattr(self.cube, "exitScanVerificationMode"):
            self.cube.exitScanVerificationMode()
        self.showEdgeControls(False)
        self.syncTextFromCube()
        self.updateArPayloadFromCube()

    def onToggleNetView(self, instance):
        if getattr(self.cube, "scan_verification_mode", False):
            self.onFinishScanVerification(instance)
            return
        if getattr(self.cube, "split_mode", False):
            return
        if getattr(self.cube, "mode", "") == "edge":
            return
        if hasattr(self.cube, "toggleNet2dMode"):
            self.cube.toggleNet2dMode()
        self.showEdgeControls(False)
        self.syncTextFromCube()
        self.updateArPayloadFromCube()

    def onToggleEdges(self, _instance):
        if getattr(self.cube, "split_mode", False):
            return
        self.cube.show_edge_numbers = not self.cube.show_edge_numbers
        self.cube.updateCanvas()

    def onToggleFaces(self, _instance):
        if getattr(self.cube, "split_mode", False):
            return
        self.cube.show_face_numbers = not self.cube.show_face_numbers
        self.cube.updateCanvas()

    def onToggleCoords(self, _instance):
        if not self.cube.intersections:
            return
        self.cube.show_coord_labels = not self.cube.show_coord_labels
        self.cube.updateCanvas()
        self.updateArPayloadFromCube()

    def onLoadQrText(self, _instance):
        if getattr(self.cube, "point_erase_mode", False):
            return
        was_scan_view = bool(getattr(self.cube, "scan_verification_mode", False))
        self.cube.setIntersectionsFromString(self.qr_input.text)
        if was_scan_view and hasattr(self.cube, "enterScanVerificationMode"):
            self.cube.enterScanVerificationMode()
        self.updateArPayloadFromCube()

    def openQrEditPopup(self):
        def onApply(text):
            self.qr_input.text = text
            was_scan_view = bool(getattr(self.cube, "scan_verification_mode", False))
            self.cube.setIntersectionsFromString(self.qr_input.text)
            if was_scan_view and hasattr(self.cube, "enterScanVerificationMode"):
                self.cube.enterScanVerificationMode()
            self.updateArPayloadFromCube()

        openTextEditPopup(
            self.qr_input.text,
            onApply,
            title="EDIT DOTS",
            size_hint=(0.95, 0.42),
            pos_hint={"center_x": 0.5, "top": 0.98},
            font_size=sp(13),
            style_callback=self.applyAppTextStyle,
        )

    def onOpenCameraScan(self, _instance):
        if getattr(self.cube, "point_erase_mode", False):
            return
        if platform != "android":
            self.showMessagePopup("Camera scanning is available only in the Android app.")
            return
        if self.camera_permission_pending:
            return

        self.camera_permission_pending = True

        from .android_camera import requestCameraPermission
        requestCameraPermission(self.afterCameraPermission)

    def afterCameraPermission(self, granted: bool):
        self.app_font_name = registerVigaFont()

        self.camera_permission_pending = False

        if not granted:
            self.showMessagePopup("Camera permission is needed to scan.")
            return

        self.closeCameraPopup()

        try:
            from .camera_screen import CameraPopup
            self.camera_popup = CameraPopup(
                on_result=self.onCameraResult,
                on_validate=self.validateCameraResult,
            )
            self.camera_popup.open()
        except Exception:
            import traceback
            self.showMessagePopup(traceback.format_exc())

    def validateCameraResult(self, result: dict) -> bool:
        text = result.get("text", "").strip()
        if not text:
            return False

        old_intersections = [dict(dot) for dot in self.cube.intersections]
        try:
            parsed = self.cube.parseIntersectionsFromString(text)
            if len(parsed) < 3:
                return False
            self.cube.intersections = parsed
            valid, _message = self.cube.validateSplitDefinition()
            return bool(valid)
        except Exception:
            return False
        finally:
            self.cube.intersections = old_intersections

    def onCameraResult(self, result: dict):
        text = result.get("text", "").strip()
        if not text:
            self.showMessagePopup("No cube dots were found.")
            return False

        if not self.validateCameraResult(result):
            return False

        self.qr_input.text = text
        self.cube.setIntersectionsFromString(text)
        if hasattr(self.cube, "enterScanVerificationMode"):
            self.cube.enterScanVerificationMode()
        self.syncTextFromCube()
        self.updateArPayloadFromCube()
        self.closeCameraPopup()
        return True

    def onOpenArMode(self, *_):
        if getattr(self.cube, "point_erase_mode", False) or getattr(self.cube, "net_2d_mode", False):
            return
        if not self.latest_cube_payload or not self.latest_cube_payload.get("intersections"):
            self.showMessagePopup("Scan the blueprint first so the cube can be created for AR mode.")
            return

        if platform == "android":
            bridge = self.getArBridge()
            if not bridge.isAvailable():
                self.showMessagePopup("This device does not report ARCore support. AR mode cannot start.")
                return

            ok = bridge.showCubeOnPlane(self.latest_cube_payload)
            if not ok:
                self.showMessagePopup("Failed to launch native AR mode.")
            return

        self.showMessagePopup("ARCore mode is available only in the Android app.")

    def closeCameraPopup(self):
        if self.camera_popup is not None:
            self.camera_popup.dismiss()
            self.camera_popup = None

    def showMessagePopup(self, text):
        showInfoPopup(
            text,
            title="INFO",
            font_name=self.app_font_name,
            size_hint=(0.7, 0.4),
        )

    def enterFaceView(self, face_index):
        if getattr(self.cube, "split_mode", False) or getattr(self.cube, "point_erase_mode", False):
            return
        self.showEdgeControls(False)
        self.cube.enterFaceViewMode(face_index)

    def onScanSuggestionAdded(self):
        self.syncTextFromCube()
        self.updateArPayloadFromCube()

    def enterEdgeEdit(self, edge_index, touch_pos=None):
        if getattr(self.cube, "point_erase_mode", False):
            return
        self.cube.enterEdgeEditModeNew(edge_index, touch_pos)
        self.edge_value.text = f"{self.cube.current_t:.2f}"
        self.showEdgeControls(True)

    def enterEdgeEditForPoint(self, dot_index):
        if getattr(self.cube, "point_erase_mode", False):
            return
        self.cube.enterEdgeEditModeExisting(dot_index)
        self.edge_value.text = f"{self.cube.current_t:.2f}"
        self.showEdgeControls(True)

    def cancelEdit(self):
        self.showEdgeControls(False)
        self.cube.exitToCube()

    def showEdgeControls(self, show: bool):
        if not show:
            self.stopShiftHold()
        self.edge_controls.disabled = not show
        self.edge_controls.opacity = 1 if show else 0
        if hasattr(self, "btn_undo"):
            self.btn_undo.disabled = show or not bool(self.cube.intersections) or getattr(self.cube, "split_mode", False)
        if hasattr(self, "btn_ar_mode"):
            self.updateArPayloadFromCube()

    def onEdgeValueText(self, _instance, value):
        if getattr(self.cube, "mode", "") != "edge":
            return
        try:
            self.cube.setCurrentEdgeT(float(value))
        except Exception:
            return

    def onEdgeEditorTChanged(self, t_value):
        try:
            self.edge_value.text = f"{float(t_value):.2f}"
        except Exception:
            pass

    def shiftEdgeValue(self, direction, amount=0.01):
        if self.cube.mode == "edge":
            self.cube.shiftCurrentEdgeT(float(direction) * float(amount))
            self.edge_value.text = f"{self.cube.current_t:.2f}"

    def onShiftLeft(self, _instance):
        self.shiftEdgeValue(-1, 0.01)

    def onShiftRight(self, _instance):
        self.shiftEdgeValue(1, 0.01)

    def onShiftLeftState(self, _instance, value):
        self.onShiftButtonState(value, -1)

    def onShiftRightState(self, _instance, value):
        self.onShiftButtonState(value, 1)

    def onShiftButtonState(self, value, direction):
        if value == "down":
            self.startShiftHold(direction)
        elif self.shift_hold_direction == direction:
            self.stopShiftHold()

    def startShiftHold(self, direction):
        self.stopShiftHold()
        self.shift_hold_direction = int(direction)
        self.shift_hold_elapsed = 0.0
        self.shift_hold_event = Clock.schedule_interval(self.repeatShiftHold, 1 / 30.0)

    def stopShiftHold(self):
        if self.shift_hold_event is not None:
            self.shift_hold_event.cancel()
        self.shift_hold_event = None
        self.shift_hold_direction = 0
        self.shift_hold_elapsed = 0.0

    def repeatShiftHold(self, dt):
        if getattr(self.cube, "mode", "") != "edge" or not self.shift_hold_direction:
            self.stopShiftHold()
            return False

        self.shift_hold_elapsed += float(dt)
        hold_delay = 0.28
        if self.shift_hold_elapsed < hold_delay:
            return True

        held = self.shift_hold_elapsed - hold_delay
        amount = 0.01 * min(1.0 + held * 2.4, 9.0)
        self.shiftEdgeValue(self.shift_hold_direction, amount)
        return True

    def onConfirmEdge(self, _instance):
        if self.cube.mode == "edge":
            try:
                val = float(self.edge_value.text)
                self.cube.setCurrentEdgeT(val)
            except ValueError:
                pass
            ok = self.cube.confirmEdgePoint()
            self.showEdgeControls(False)
            if ok:
                self.syncTextFromCube()
            self.updateArPayloadFromCube()

    def onCancelEdge(self, _instance):
        if self.cube.mode == "edge":
            self.cube.cancelEdgeEdit()
            self.showEdgeControls(False)
            self.updateArPayloadFromCube()
