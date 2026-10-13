#!/usr/bin/env python3
"""Read-only escape1 furnace perimeter capture using a TestLab-only native Linux binary.

The probe camera is injected only into a diagnostic build. No retail pk3 or protected
asset is copied into the public evidence directory.
"""
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from PIL import Image, ImageStat

source, retail, output = [Path(x).resolve() for x in sys.argv[1:4]]
label = sys.argv[4] if len(sys.argv) >= 5 else "after"
output.mkdir(parents=True, exist_ok=True)
root = Path(__file__).resolve().parents[1] / "optimized-v4-4-6"
build = source / "SP/build/release-linux-x86_64"
executables = sorted(list(build.glob("iowolfsp.*")) + list(build.glob("ioWolfSP.*")))
assert executables, f"Linux ioWolfSP executable missing in {build}"
exe = executables[0]
runtime = Path.cwd() / ("private-runtime-stove-scout-" + label)
assert not runtime.exists()
(runtime / "main").mkdir(parents=True)
for p in build.iterdir():
    if p.is_file():
        shutil.copy2(p, runtime / p.name)
for p in (build / "main").glob("*.so"):
    shutil.copy2(p, runtime / "main" / p.name)
retail_paks = sorted(p for p in retail.iterdir() if p.is_file() and p.suffix.lower() == ".pk3")
assert any(p.name.lower() == "pak0.pk3" for p in retail_paks)
for p in retail_paks:
    (runtime / "main" / p.name.lower()).symlink_to(p)
shutil.copy2(root / "payload/Main/darkwolf_ignition_rc_v0_6.pk3",
             runtime / "main/darkwolf_ignition_rc_v0_6.pk3")
shutil.copy2(root / "PRODUCTION_HIGH_QUALITY.cfg",
             runtime / "main/PRODUCTION_HIGH_QUALITY.cfg")
# Verified opaque exterior wall x=-1152, ground z=-128, courtyard cluster 1154.
# 112 BSP units ~ 2.84m from wall; camera faces its base and adjacent ground.
origin = (-1226.,602.,-64.)
camera = (-1040.,602.,-70.)
target = (-1152.,602.,-128.)
yaw = 180.0
pitch = -math.degrees(math.atan2(target[2]-camera[2], math.hypot(target[0]-camera[0],target[1]-camera[1])))
cameras = [dict(i=i,xyz=camera,angles=(pitch,yaw,0.),radius=112.,
                frame_sequence=i,goal='wall_and_ground',target=target) for i in range(20)]
assert len({tuple(q['xyz']) for q in cameras}) == 1
assert len({tuple(q['angles']) for q in cameras}) == 1

scenario = ["set developer 1", "set cg_draw2D 0", "set cg_drawGun 0",
            "echo STOVE_SCOUT_BEGIN map=escape1 model=furnace.md3",
            "wait 30"]
for cam in cameras:
    i = cam["i"]
    scenario += [f"echo STOVE_SCOUT_POSITION index={i:02d}",
                 "dw_testView " + " ".join(f"{x:.3f}" for x in (*cam["xyz"], *cam["angles"])),
                 "wait 1", f"dw_testViewState {i}",
                 f"set r_testlabCaptureIndex {i}", "wait 3",
                 f"screenshot {label}_{i:02d}", "wait 1"]
scenario += ["echo STOVE_SCOUT_COMPLETE", "wait 10", "quit"]
(runtime / "main" / "TESTLAB_STOVE_SCOUT.cfg").write_text("\n".join(scenario) + "\n")
(output / "scout-camera-manifest.json").write_text(
    json.dumps(dict(model="models/mapobjects/furniture/furnace.md3",
                    model_origin=origin, map="escape1", cameras=cameras,
                    software_renderer="Mesa llvmpipe", source_variant=label, camera=camera, target=target,
                    shot_interval="one engine rendered frame (not calibrated milliseconds)"), indent=2) + "\n")
home = runtime / "home"
home.mkdir()
cmd = [str(runtime / exe.name),
       "+set", "fs_basepath", str(runtime), "+set", "fs_homepath", str(home),
       "+safe", "+set", "com_introplayed", "1", "+set", "com_recommendedSet", "1",
       "+set", "logfile", "2", "+set", "dw_testAutomation", "1",
       "+set", "r_renderer", "rend2", "+set", "cl_renderer", "rend2",
       "+exec", "PRODUCTION_HIGH_QUALITY.cfg",
       "+set", "r_mode", "-1", "+set", "r_customwidth", "640",
       "+set", "r_customheight", "480", "+set", "r_fullscreen", "0",
       "+set", "s_initsound", "0", "+vid_restart",
       "+set", "dw_testlabSmokeCapture", "escape1-stove-" + label,
       "+set", "dw_testlabScenario", "TESTLAB_STOVE_SCOUT.cfg",
       "+spdevmap", "escape1"]
started = time.monotonic()
with (output / "stdout.log").open("w") as fh:
    proc = subprocess.Popen(["xvfb-run", "-a", *cmd], stdout=fh,
                            stderr=subprocess.STDOUT, start_new_session=True,
                            env={**os.environ, "LIBGL_ALWAYS_SOFTWARE": "1"})
    try:
        return_code = proc.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        return_code = 124
console_files = sorted(home.rglob("*console*.log"))
console_text = "\n".join(p.read_text(errors="replace") for p in console_files)
if console_files:
    (output / "qconsole.log").write_text(console_text)
(output / "screenshots").mkdir()
shots = sorted(home.rglob("*.tga"))
records = []
for shot in shots:
    img = Image.open(shot).convert("RGB")
    out_path = output / "screenshots" / (shot.stem + ".png")
    img.save(out_path)
    val = ImageStat.Stat(img).mean
    records.append(dict(name=out_path.name, size=img.size,
                        mean_rgb=[round(x, 2) for x in val],
                        fraction_dark=round(sum(max(x) < 8 for x in img.getdata()) /
                                            (img.width * img.height), 4),
                        sha256=hashlib.sha256(out_path.read_bytes()).hexdigest()))
result = dict(map="escape1", label=label, return_code=return_code,
              elapsed_seconds=round(time.monotonic() - started, 2),
              frames=len(records), target_frames=len(cameras),
              render_ready="TESTLAB_CAPTURE_READY frames=" in console_text,
              gameplay_started="TESTLAB_GAMEPLAY_START requested=1" in console_text,
              camera_command_proof_count=console_text.count("TESTLAB_VIEW "),
              screenshots=records)
result["status"] = ("PASS" if return_code == 0 and len(records) == len(cameras)
                    and result["render_ready"] and result["gameplay_started"]
                    and result["camera_command_proof_count"] >= len(cameras) else "FAIL")
(output / "scout-results.json").write_text(json.dumps(result, indent=2) + "\n")
print("STOVE_SCOUT_SUMMARY " + json.dumps({k: v for k, v in result.items() if k != "screenshots"}))
if result["status"] != "PASS":
    raise SystemExit("STOVE_SCOUT_FAIL: see stdout.log, qconsole.log, scout-results.json")
