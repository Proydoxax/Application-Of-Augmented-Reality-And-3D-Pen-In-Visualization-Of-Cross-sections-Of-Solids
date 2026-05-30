import json
import traceback
from kivy.utils import platform


def androidAutoclass():
    # noinspection PyUnresolvedReferences
    from jnius import autoclass

    return autoclass


class ARBridge:
    def __init__(self):
        self.session_active = False
        self.last_error = ""

    def isAvailable(self) -> bool:
        if platform != "android":
            return False

        # noinspection PyBroadException
        try:
            autoclass = androidAutoclass()

            python_activity_class = autoclass("org.kivy.android.PythonActivity")
            ar_core_apk_class = autoclass("com.google.ar.core.ArCoreApk")

            activity = python_activity_class.mActivity
            availability = ar_core_apk_class.getInstance().checkAvailability(activity)
            return bool(availability is not None and availability.isSupported())
        except Exception:
            self.last_error = traceback.format_exc()
            return False

    def startSession(self) -> bool:
        self.session_active = True
        return True

    def stopSession(self):
        self.session_active = False

    def showCubeOnPlane(self, cube_data: dict) -> bool:
        if platform != "android":
            self.last_error = f"Not Android. Kivy platform={platform!r}."
            return False

        # noinspection PyBroadException
        try:
            autoclass = androidAutoclass()

            python_activity_class = autoclass("org.kivy.android.PythonActivity")
            intent_class = autoclass("android.content.Intent")
            java_string = autoclass("java.lang.String")
            activity = python_activity_class.mActivity
            intent = intent_class()
            intent.setClassName(activity.getPackageName(), java_string("org.kivy.ar.ArPlaneActivity"))

            payload = json.dumps(cube_data or {})
            intent.putExtra(java_string("cube_payload_json"), java_string(payload))

            activity.startActivity(intent)
            self.session_active = True
            self.last_error = ""
            return True
        except Exception:
            self.session_active = False
            self.last_error = traceback.format_exc()
            return False