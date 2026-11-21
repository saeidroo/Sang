#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v gradle >/dev/null 2>&1 || { echo "Gradle 8.9 is required." >&2; exit 1; }
[[ -n "${ANDROID_HOME:-}${ANDROID_SDK_ROOT:-}" ]] || { echo "Android SDK not found." >&2; exit 1; }
gradle --no-daemon clean assembleDebug
echo "APK: app/build/outputs/apk/debug/app-debug.apk"
