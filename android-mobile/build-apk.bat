@echo off
setlocal
cd /d "%~dp0"
where gradle >nul 2>nul
if errorlevel 1 (
  echo Gradle 8.9 was not found. Install Gradle or open this folder in Android Studio.
  exit /b 1
)
if "%ANDROID_HOME%"=="" if "%ANDROID_SDK_ROOT%"=="" (
  echo Android SDK not found. Set ANDROID_HOME or ANDROID_SDK_ROOT.
  exit /b 1
)
gradle --no-daemon clean assembleDebug
if errorlevel 1 exit /b 1
echo APK: app\build\outputs\apk\debug\app-debug.apk
