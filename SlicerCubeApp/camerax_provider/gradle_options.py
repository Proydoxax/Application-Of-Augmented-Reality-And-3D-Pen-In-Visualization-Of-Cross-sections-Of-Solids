#
# Add gradle options for CameraX
#
from pythonforandroid.recipe import info
from os.path import dirname, join, exists

def before_apk_build(toolchain):
    unprocessed_args = toolchain.args.unknown_args

    if '--enable-androidx' not in unprocessed_args:
        unprocessed_args.append('--enable-androidx')
        info('Camerax Provider: Add android.enable_androidx = True')

    if 'CAMERA' not in unprocessed_args:
        unprocessed_args.append('--permission')
        unprocessed_args.append('CAMERA')
        info('Camerax Provider: Add android.permissions = CAMERA')

    if 'RECORD_AUDIO' not in unprocessed_args:
        unprocessed_args.append('--permission')
        unprocessed_args.append('RECORD_AUDIO')
        info('Camerax Provider: Add android.permissions = RECORD_AUDIO')

    required_depends = [
        'androidx.camera:camera-core:1.2.1',
        'androidx.camera:camera-camera2:1.2.1',
        'androidx.camera:camera-lifecycle:1.2.1',
        'androidx.lifecycle:lifecycle-process:2.5.1',
        'androidx.core:core:1.9.0'
    ]

    existing_depends = []
    read_next = False
    for ua in unprocessed_args:
        if read_next:
            existing_depends.append(ua)
            read_next = False
        if ua == '--depend':
            read_next = True

    message = False
    for rd in required_depends:
        name, version = rd.rsplit(':', 1)
        found = False
        for ed in existing_depends:
            if name in ed:
                found = True
                break
        if not found:
            unprocessed_args.append('--depend')
            unprocessed_args.append(f'{name}:{version}')
            message = True

    if message:
        info('Camerax Provider: Add android.gradle_dependencies required for CameraX')

    camerax_java = join(dirname(__file__), 'camerax_src')
    if exists(camerax_java):
        unprocessed_args.append('--add-source')
        unprocessed_args.append(camerax_java)
        info('Camerax Provider: Add android.add_src = ./camerax_provider/camerax_src')