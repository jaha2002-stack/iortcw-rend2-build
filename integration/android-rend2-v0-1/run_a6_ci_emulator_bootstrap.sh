#!/usr/bin/env bash
set -Eeuo pipefail

APK="${1:?usage: run_a6_ci_emulator_bootstrap.sh <x86_64-apk>}"
OUT="${2:-.android-rend2-work/a6-ci-emulator}"
PKG="org.darkwolf.rend2"
ACTIVITY="org.darkwolf.rend2.DarkWolfActivity"

rm -rf "$OUT"
mkdir -p "$OUT"

test -s "$APK"
command -v adb >/dev/null

adb wait-for-device
adb shell getprop ro.product.cpu.abi | tee "$OUT/device-abi.txt"
adb shell getprop ro.build.version.sdk | tee "$OUT/device-api.txt"
grep -Fxq x86_64 "$OUT/device-abi.txt"

adb install -r "$APK" | tee "$OUT/adb-install.txt"
adb logcat -c

set +e
adb shell am start -W -n "$PKG/$ACTIVITY" > "$OUT/am-start.txt" 2>&1
start_rc=$?
set -e

for _ in $(seq 1 20); do
  adb logcat -d -v threadtime > "$OUT/logcat.txt" || true
  if grep -Eq 'A5_HOME=|A5_RETAIL_BASE=|A5_RETAIL_MAIN=' "$OUT/logcat.txt"; then
    break
  fi
  sleep 1
done

adb exec-out screencap -p > "$OUT/bootstrap-frame.png" || true
adb shell dumpsys package "$PKG" > "$OUT/package.txt" || true
adb shell pidof "$PKG" > "$OUT/pid.txt" || true

grep -E 'DarkWolfRTCW|A5_HOME=|A5_RETAIL_BASE=|A5_RETAIL_MAIN=|SDL|UnsatisfiedLinkError|dlopen failed|Fatal signal|FATAL EXCEPTION|FS_Startup|pak0|Couldn't load|couldn.t load'   "$OUT/logcat.txt" > "$OUT/high-signal-log.txt" || true

grep -Fq 'A5_HOME=' "$OUT/high-signal-log.txt"
grep -Fq 'A5_RETAIL_BASE=' "$OUT/high-signal-log.txt"
grep -Fq 'A5_RETAIL_MAIN=' "$OUT/high-signal-log.txt"
! grep -Eq 'UnsatisfiedLinkError|dlopen failed|Fatal signal|FATAL EXCEPTION' "$OUT/high-signal-log.txt"

cat > "$OUT/A6_CI_BOOTSTRAP_AUDIT.txt" <<EOF
A6_CI_EMULATOR_BOOTSTRAP=PASS
PACKAGE=$PKG
ACTIVITY=$ACTIVITY
ABI=x86_64
AM_START_RC=$start_rc
A5_PATH_MARKERS=PASS
JNI_NATIVE_LOAD_FATAL=NONE
RETAIL_DATA=INTENTIONALLY_ABSENT
SCREENSHOT_CAPTURED=$(test -s "$OUT/bootstrap-frame.png" && echo YES || echo NO)
EOF
cat "$OUT/A6_CI_BOOTSTRAP_AUDIT.txt"
