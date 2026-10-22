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
command -v timeout >/dev/null

adb_bounded() {
  local sec="$1"; shift
  timeout --signal=TERM --kill-after=3s "${sec}s" adb "$@"
}

diagnostics() {
  local rc="$1"
  echo "A6_CI_EMULATOR_BOOTSTRAP_FAILED=${rc}" >&2
  timeout 8s adb devices -l > "$OUT/adb-devices-failure.txt" 2>&1 || true
  timeout 12s adb logcat -d -v threadtime > "$OUT/logcat-failure.txt" 2>&1 || true
  tail -n 70 "$OUT/logcat-failure.txt" 2>/dev/null || true
}
trap 'rc=$?; if [ "$rc" -ne 0 ]; then diagnostics "$rc"; fi' EXIT

echo "A6_BOOTSTRAP_PHASE=ADB_READY"
adb_bounded 30 wait-for-device
adb_bounded 12 shell getprop ro.product.cpu.abi | tr -d '\r' | tee "$OUT/device-abi.txt"
adb_bounded 12 shell getprop ro.build.version.sdk | tr -d '\r' | tee "$OUT/device-api.txt"
grep -Fxq x86_64 "$OUT/device-abi.txt"

echo "A6_BOOTSTRAP_PHASE=INSTALL"
adb_bounded 100 install -r "$APK" | tee "$OUT/adb-install.txt"
grep -Fq Success "$OUT/adb-install.txt"
adb_bounded 12 logcat -c

# Android 30 emulator may hang on ActivityManager '-W', especially when the
# host renderControl decoder fatals. Do not block waiting for activity return.
echo "A6_BOOTSTRAP_PHASE=ACTIVITY_START_NONBLOCKING"
start_rc=0
adb_bounded 20 shell am start -n "$PKG/$ACTIVITY" > "$OUT/am-start.txt" 2>&1 || start_rc=$?
echo "A6_BOOTSTRAP_AM_START_RC=$start_rc"
cat "$OUT/am-start.txt"
if [ "$start_rc" -ne 0 ]; then
  echo "A6_ACTIVITY_START_FAILED=$start_rc" >&2
  exit "$start_rc"
fi

echo "A6_BOOTSTRAP_PHASE=JNI_MARKER_WAIT"
marker=0
for i in $(seq 1 30); do
  if adb_bounded 12 logcat -d -v threadtime > "$OUT/logcat.txt" 2>"$OUT/logcat-err.txt"; then
    if grep -Fq 'A5_HOME=' "$OUT/logcat.txt" &&
       grep -Fq 'A5_RETAIL_BASE=' "$OUT/logcat.txt" &&
       grep -Fq 'A5_RETAIL_MAIN=' "$OUT/logcat.txt"; then
      marker=1
      break
    fi
  fi
  sleep 1
done
test "$marker" -eq 1 || {
  echo "A6_BOOTSTRAP_A5_JNI_MARKERS_ABSENT=YES" >&2
  exit 1
}

adb_bounded 15 exec-out screencap -p > "$OUT/bootstrap-frame.png" || true
adb_bounded 15 shell dumpsys package "$PKG" > "$OUT/package.txt" || true
adb_bounded 12 shell pidof "$PKG" > "$OUT/pid.txt" || true

grep -E "DarkWolfRTCW|A5_HOME=|A5_RETAIL_BASE=|A5_RETAIL_MAIN=|SDL|UnsatisfiedLinkError|dlopen failed|Fatal signal|FATAL EXCEPTION|FS_Startup|pak0|Couldn.t load|couldn.t load" \
  "$OUT/logcat.txt" > "$OUT/high-signal-log.txt" || true

grep -Fq 'A5_HOME=' "$OUT/high-signal-log.txt"
grep -Fq 'A5_RETAIL_BASE=' "$OUT/high-signal-log.txt"
grep -Fq 'A5_RETAIL_MAIN=' "$OUT/high-signal-log.txt"
! grep -Eq 'UnsatisfiedLinkError|Fatal signal|FATAL EXCEPTION' "$OUT/high-signal-log.txt"

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
