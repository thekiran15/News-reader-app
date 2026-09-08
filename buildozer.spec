[app]

title = News Reader
package.name = newsreader
package.domain = org.yourname

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json

version = 0.1

requirements = python3,kivy==2.3.0,kivymd==1.2.0,requests,pillow,certifi,urllib3,chardet,idna,pyjnius,android

orientation = portrait
fullscreen = 0

android.accept_sdk_license = True

android.permissions = INTERNET,ACCESS_NETWORK_STATE

android.api = 34
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

# Keep the app data (history file) across updates
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
