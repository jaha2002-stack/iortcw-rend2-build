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
