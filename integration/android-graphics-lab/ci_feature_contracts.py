#!/usr/bin/env python3
"""Pre-build contracts; fail before re-downloading Android SDK or compiling."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[2]
read=lambda p:(root/p).read_text()
native=read("integration/android-graphics-lab/patch_lab_bridge.py")
android=read("integration/android-rend2-v0-1/apply_android_rend2_v0_1.py")
arm=read("integration/android-rend2-v0-1/build_android_apk_bootstrap.sh")
emu=read("integration/android-rend2-v0-1/build_android_apk_x86_64_ci.sh")
driver=read("integration/android-graphics-lab/ci_scene_driver.py")
ui=read("integration/android-graphics-lab/inject_java.py")
assert re.search(r"clc\.state\s*!=\s*CA_ACTIVE",native)
assert "dw_android_ci_observe_gameview" in native
assert "GRAPHICS_LAB_CI_GAMEVIEW=PASS" in native
assert "GRAPHICS_LAB_CMD_DISPATCH=" in native
assert "DARKWOLF_ANDROID_MAP_AUTOSTART_ARMED=PASS" in android
assert "DARKWOLF_ANDROID_UI_BRIEFING_AUTOSTART=PASS" in android
assert "DW_ANDROID_BRIEFING_ARROW_AUTOSTART_V01" in android
assert "patch_android_briefing_ui(sp / \"ui\" / \"ui_main.c\")" in android
assert android.count('trap_Cvar_Set( "g_playerstart", "1" )')==1
assert 'Cvar_Set( "dw_android_briefing_autostart_pending", "1" )' in android
assert 'trap_Cvar_Set( "dw_android_briefing_autostart_pending", "0" )' in android
assert "DARKWOLF_ANDROID_BRIEFING_SENT_TO_UI=PASS" in android
assert "dw_android_auto_playerstart" in android
assert "KEYCODE_ENTER" not in driver and '"keyevent","66"' not in driver
assert "MAP_AUTOSTART_WITHOUT_ENTER=PASS" in driver
assert "GRAPHICS LAB" in ui and "nativeLabCvars()" in ui
assert all(k in ui for k in ["spdevmap ","noclip","cg_fov","setviewpos ","vid_restart"])
for source in [arm,emu]:
    assert '"+set", "dw_android_auto_playerstart", "1"' in source
    for n in ["r_dlightMode","r_forceSun","r_dwCas","r_dwA2C","r_dwLut",
              "r_ssgi","r_bloom","r_hdr","r_toneMap","r_sunShadows",
              "r_volumetricSun","r_volumetricLocal"]:
        assert '"+set", "'+n+'", "' in source,n
print("GRAPHICS_LAB_SOURCE_CONTRACTS=PASS")

assert "DARKWOLF_ANDROID_UI_BRIEFING_AUTOSTART=PASS" in driver
assert "DARKWOLF_ANDROID_UI_BRIEFING_AUTOSTART=PASS" in read("integration/android-graphics-lab/ci_ui_probe.py")

# Device-sized Android EGL drawable instead of legacy corner viewport.
fullscreen = read("integration/android-graphics-lab/patch_fullscreen.py")
assert "DARKWOLF_ANDROID_FULLSCREEN_DRAWABLE=PASS" in fullscreen
assert "SDL_GL_GetDrawableSize" in fullscreen
assert "SDL_WINDOW_FULLSCREEN_DESKTOP" in fullscreen
assert "labQueryCvar(k);" in ui
assert "private void labQueryCvar(String name)" in ui

# Android 11 CI assets must not depend on /sdcard/Android via ADB.
assert "retailRoot = homeRoot;" in emu
wf = read(".github/workflows/ANDROID_GRAPHICS_LAB_V01.yml")
assert 'dest="files/DarkWolfRTCW/main"' in wf
assert 'adb exec-in' in wf
assert 'manifest=".android-rend2-work/lab-assets/pk3-files.txt"' in wf
assert 'mapfile -t pk3_names < "$manifest"' in wf
assert 'test "$transferred" -eq "${#pk3_names[@]}"' in wf
assert 'for name in pak0.pk3 sp_pak1.pk3 sp_pak2.pk3' not in wf
assert 'adb shell run-as "$pkg" mkdir -p "$dest"' in wf
assert 'dest="/sdcard/Android/data/org.darkwolf.rend2/files/DarkWolfRTCW/main"' not in wf

# Fix the actual broken mobile controls at usercmd construction, not via
# delayed console +forward/-forward which can miss taps between frames.
touch = read("integration/android-graphics-lab/patch_touch_input.py")
assert "DARKWOLF_ANDROID_DIRECT_WASD_V01" in touch
assert "CL_AndroidApplyTouchInput(&cmd)" in touch
assert "nativeQueueLookDelta" in touch
assert "androidMoveTapMask" in touch
assert "drawDirection(canvas, wRect" in touch
assert "case DW_ACT_FORWARD:" in touch
assert "GRAPHICS_LAB_DIRECT_TOUCH_SELFTEST=PASS" in touch
assert "CONTROLS / COMMAND HELP" in ui
for source in [arm,emu]:
    assert 'patch_touch_input.py" --java "$PROJECT"' in source
wf = read(".github/workflows/ANDROID_GRAPHICS_LAB_V01.yml")
assert 'patch_touch_input.py --native .android-rend2-work/source' in wf

# Native Android diagnosis and explicit stock stopcam during noclip.
nav = read("integration/android-graphics-lab/patch_navigation_diag.py")
assert "GRAPHICS_LAB_NAVIGATION_DIAGNOSTICS_SELFTEST=PASS" in nav
assert "DW_ANDROID_LAB_NOCLIP_CINEMATIC_STOP_V01" in nav
assert "DARKWOLF_ANDROID_NAVIGATION_DIAGNOSTICS_V01" in nav
assert "nativeLabInputStatus" in nav
assert "INPUT & COMMAND MONITOR (toggle)" in ui
for source in [arm,emu]:
    assert 'patch_navigation_diag.py" --java "$PROJECT"' in source
    assert '"+set", "dw_android_camera_noclip", "1"' in source
assert 'patch_navigation_diag.py --native .android-rend2-work/source' in wf
