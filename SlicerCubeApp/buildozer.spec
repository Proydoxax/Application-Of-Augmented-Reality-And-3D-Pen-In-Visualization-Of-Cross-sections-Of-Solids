[app]

title = SlicerCube AR
package.name = myapp
package.domain = org.test

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,java,ttf,otf
version = 0.1

requirements = python3,kivy,pillow,pyjnius,numpy,opencv,camera4kivy,gestures4kivy
orientation = portrait
fullscreen = 0

osx.python_version = 3
osx.kivy_version = 2.2.0

android.permissions = CAMERA
android.api = 33
android.minapi = 24

android.add_src = %(source.dir)s/android_src
android.add_activities = org.kivy.ar.ArPlaneActivity

android.gradle_dependencies = com.google.ar:core:1.31.0, com.gorisse.thomas.sceneform:sceneform:1.23.0, androidx.fragment:fragment:1.6.2, org.jetbrains.kotlin:kotlin-stdlib:1.8.20, org.jetbrains.kotlin:kotlin-stdlib-jdk7:1.8.20, org.jetbrains.kotlin:kotlin-stdlib-jdk8:1.8.20

android.enable_androidx = True
android.add_compile_options = "sourceCompatibility = 1.8", "targetCompatibility = 1.8"

android.meta_data = com.google.ar.core=optional

android.copy_libs = 1
android.archs = arm64-v8a
android.allow_backup = True

android.debug_artifact = apk

p4a.hook = camerax_provider/gradle_options.py

ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.10.0
ios.codesign.allowed = false

icon.filename = %(source.dir)s/app/logo/APPlogo.png
presplash.filename = %(source.dir)s/app/logo/APPlogo.png


[buildozer]

log_level = 2
warn_on_root = 1
