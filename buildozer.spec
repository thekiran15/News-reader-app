[app]

# (str) Title of your application
title = News Reader

# (str) Package name
package.name = newsreader

# (str) Package domain (needed for android/ios packaging)
package.domain = org.yourname

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json

# (str) Application versioning (method 1)
version = 0.1

# (list) Application requirements
# Kivy pinned to 2.2.1 (predates the meson-python build switch that breaks
# under p4a's pip dry-run check). KivyMD 1.2.0 is compatible with it.
requirements = python3,kivy==2.2.1,kivymd==1.2.0,requests,pillow,certifi,urllib3,chardet,idna,pyjnius,android

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
android.accept_sdk_license = True

# (list) Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (list) The Android archs to build for
android.archs = arm64-v8a

# (bool) Keep the app data (history file) across updates
android.allow_backup = True

# (str) python-for-android fork to use
#p4a.fork = kivy

# (str) python-for-android specific commit to use, defaults to HEAD
# Pinned to the last stable tagged release. The current p4a master/develop
# branch has a confirmed-broken kivy recipe (pip dry-run check fails for
# every kivy version since no PyPI wheel exists for android). This tag
# predates that bug and is confirmed working.
# See: https://github.com/kivy/python-for-android/issues/3342
p4a.commit = v2024.01.21

# (str) The directory in which python-for-android should look for
# your own build recipes (if any)
p4a.local_recipes = ./p4a-recipes

# (str) Bootstrap to use for android builds
p4a.bootstrap = sdl2

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
