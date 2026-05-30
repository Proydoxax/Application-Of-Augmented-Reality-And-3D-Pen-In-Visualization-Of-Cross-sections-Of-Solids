from kivy.clock import Clock

from .constants import IS_ANDROID


def requestCameraPermission(callback):
    if not IS_ANDROID:
        Clock.schedule_once(lambda _dt: callback(False), 0)
        return

    try:
        # noinspection PyUnresolvedReferences
        from android.permissions import request_permissions, check_permission, Permission
    except Exception:
        Clock.schedule_once(lambda _dt: callback(False), 0)
        return

    try:
        if check_permission(Permission.CAMERA):
            Clock.schedule_once(lambda _dt: callback(True), 0)
            return
    except Exception:
        pass

    def permissionCallback(_permissions, grant_results):
        granted = bool(grant_results) and all(grant_results)
        Clock.schedule_once(lambda _dt: callback(granted), 0)

    try:
        request_permissions([Permission.CAMERA], permissionCallback)
    except Exception:
        Clock.schedule_once(lambda _dt: callback(False), 0)
