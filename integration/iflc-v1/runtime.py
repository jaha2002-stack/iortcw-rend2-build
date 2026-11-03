#!/usr/bin/env python3
"""Real Crypt1 IFLC command/screenshot smoke test using licensed retail assets.

Camera helpers change only client/game/cgame in an isolated native tree.
The renderer being exercised is the actual IFLC candidate, without test hooks.
Screenshot capture and pixel deltas are evidence, not automatic visual acceptance.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys
import zipfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "testlab/scripts"))
import rc4_requested_views as camera
from rc4_assault_camera import World


def instrument(source):
    camera.instrument(source)


def discover(retail, limit=3):
    data = None
    for p in sorted(retail.iterdir()):
        if p.suffix.lower() != ".pk3":
            continue
        with zipfile.ZipFile(p) as z:
            for name in z.namelist():
                if name.lower() == "maps/crypt1.bsp":
                    data = z.read(name)
    if data is None:
        raise RuntimeError("Licensed Crypt1 BSP unavailable")
    world = World(data)

    def lump(i):
        offset, size = struct.unpack_from("<ii", data, 8 + i * 8)
        return data[offset:offset + size]

    vertices = list(struct.iter_unpack("<10f4B", lump(10)))
    surfaces = list(struct.iter_unpack("<12i12f2i", lump(13)))
    model = struct.unpack_from("<6f4i", lump(7))
    start_entities = [e for e in world.entities if e.get("classname") == "info_player_start"]
    start = list(map(float, start_entities[0]["origin"].split())) if start_entities else [0.0, 0.0, 0.0]
    anchors = []
    for index in range(model[6], model[6] + model[7]):
        surface = surfaces[index]
        name = world.shaders[surface[0]][0].split(b"\0")[0].decode("latin1")
        if not any(s in name.lower() for s in ("flame", "torch_ember")):
            continue
        if "flamethrower" in name.lower() or "fthrow_" in name.lower():
            continue
        verts = vertices[surface[3]:surface[3] + surface[4]]
        if not verts:
            continue
        center = [sum(v[k] for v in verts) / len(verts) for k in range(3)]
        if any(a["shader"] == name and math.dist(a["anchor"], center) <= 16 for a in anchors):
            continue
        anchors.append({"surface": index, "shader": name, "anchor": center})
    anchors.sort(key=lambda a: math.dist(a["anchor"], start))
    views = []
    for anchor in anchors:
        target = anchor["anchor"]
        candidates = []
        for distance in (160, 224, 112):
            for step in range(16):
                angle = step * 2 * math.pi / 16
                for dz in (-32, -64, 0):
                    eye = [target[0] + distance * math.cos(angle),
                           target[1] + distance * math.sin(angle), target[2] + dz]
                    if world.solid(eye):
                        continue
                    if any(world.solid([eye[0] + dx, eye[1] + dy, eye[2] + z])
                           for dx, dy, z in ((8, 0, 0), (-8, 0, 0), (0, 8, 0), (0, -8, 0), (0, 0, -24))):
                        continue
                    hit = world.trace(eye, target)
                    if hit and hit.get("fraction", 0) < 0.99:
                        continue
                    direction = [target[k] - eye[k] for k in range(3)]
                    pitch = -math.degrees(math.atan2(direction[2], math.hypot(direction[0], direction[1])))
                    yaw = math.degrees(math.atan2(direction[1], direction[0])) % 360
                    neighbors = sum(math.dist(a["anchor"], target) < 700 for a in anchors)
                    candidates.append((math.dist(eye, start) - neighbors * 24,
                                       {**anchor, "eye": eye, "angles": [pitch, yaw, 0.0],
                                        "bsp_camera_clear": True, "bsp_ray_clear": True}))
        if candidates:
            view = min(candidates, key=lambda x: x[0])[1]
            view["name"] = f"flame_{len(views) + 1}_surface_{anchor['surface']}"
            views.append(view)
        if len(views) == limit:
            break
    if len(views) < 2:
        raise RuntimeError(f"Only {len(views)} independently visible BSP flame cameras")
    return views, hashlib.sha256(data).hexdigest()


def capture(source, retail, out):
    from PIL import Image, ImageDraw
    import numpy as np
    out.mkdir(parents=True, exist_ok=True)
    views, bsp_sha = discover(retail)
    (out / "CRYPT1_IFLC_CAMERAS.json").write_text(json.dumps({"bsp_sha256": bsp_sha, "views": views}, indent=2) + "\n")
    runtime = (out.parent / "iflc-runtime").resolve()
    main = runtime / "main"
    main.mkdir(parents=True, exist_ok=True)
    build = source / "SP/build/release-linux-x86_64"
    for p in build.iterdir():
        if p.is_file():
            shutil.copy2(p, runtime / p.name)
    for p in (build / "main").glob("*.so"):
        shutil.copy2(p, main / p.name)
    for p in retail.iterdir():
        if p.suffix.lower() == ".pk3":
            target = main / p.name.lower()
            if not target.exists():
                target.symlink_to(p.resolve())
    commands = ["set con_notifytime -1", "set cg_draw2D 0", "set cg_drawGun 0", "set cg_bobup 0",
                "set cg_bobpitch 0", "set cg_bobroll 0", "set r_autoExposure 0", "set r_forceAutoExposure 0",
                "set r_forceSunPause 1", "god", "notarget", "wait 18"]
    shots = []

    def shot(view, variant):
        index = len(shots) + 1
        name = f"iflc_{view['name']}_{variant}"
        commands.extend([f"echo IFLC_STATE {view['name']} {variant}", "dw_fl_info",
                         f"set dw_proofShot {index}", "wait 8", f"screenshot {name}", "wait 3"])
        shots.append({"id": index, "view": view["name"], "variant": variant, "name": name})

    for view in views:
        commands += [f"echo IFLC_TEST_BEGIN {view['name']}", "set dw_proofFreeze 0",
                     "proofView " + " ".join(f"{v:.6f}" for v in view["eye"] + view["angles"]),
                     "wait 45", "set dw_proofFreeze 1", "wait 12", "set r_dwFireLightControl 0"]
        shot(view, "empty_off")
        commands += ["set r_dwFireLightControl 1", "wait 15", "dw_fl_select", "dw_fl_next", "wait 2"]
        shot(view, "empty_on")
        # 'enabled' refuses existing native/promoted owners; that is the expected guard.
        commands += ["dw_fl_set enabled 1", "dw_fl_set direct 0", "dw_fl_set radius 1", "dw_fl_set volume 1", "wait 15"]
        shot(view, "direct_0")
        commands += ["dw_fl_set direct 3", "wait 15"]
        shot(view, "direct_3")
        commands += ["dw_fl_set volume 0", "wait 15"]
        shot(view, "volume_0")
        commands += ["dw_fl_set volume 3", "wait 15"]
        shot(view, "volume_3")
        commands += ["dw_fl_set direct 1.75", "dw_fl_set radius 1.25", "dw_fl_set volume 0.8",
                     "dw_fl_save", "dw_fl_set direct 0.5", "dw_fl_reload", "wait 15"]
        shot(view, "reload")
        commands += ["dw_fl_reset", "dw_fl_save", "wait 15"]
        shot(view, "reset")
        commands += ["set r_dwFireLightControl 0", "wait 15"]
        shot(view, "off_restored")
    commands += ["set dw_proofFreeze 0", "echo IFLC_CRYPT1_RUNTIME_COMPLETE", "quit"]
    scenario = "IFLC_CRYPT1_TEST.cfg"
    (main / scenario).write_text("\n".join(commands) + "\n")
    shutil.copy2(main / scenario, out / scenario)
    setup = ["set r_mode -1", "set r_customwidth 960", "set r_customheight 540", "set r_fullscreen 0",
             "set r_renderer rend2", "set cl_renderer rend2", "set r_hdr 1", "set r_postProcess 1",
             "set r_bloom 1", "set r_bloomMode 2", "set r_dwCas 1", "set r_dwA2C 1",
             "set r_ssgi 1", "set r_forceSun 1", "set r_sunShadows 1", "set r_dlightMode 2",
             "set r_dlightShadowMaxLights 3", "set r_dlightWorldContainment 2",
             "set r_volumetricSun 1", "set r_volumetricLocal 1", "set r_volumetricFire 1",
             "set r_ext_framebuffer_multisample 4", "set r_cameraExposure 1",
             "set r_autoExposure 0", "set r_forceAutoExposure 0", "set r_dwFireLightControl 0",
             "set s_initsound 0", "set r_swapInterval 0", "set fixedtime 100", "set con_notifytime -1"]
    (main / "IFLC_SETUP.cfg").write_text("\n".join(setup) + "\n")
    shutil.copy2(main / "IFLC_SETUP.cfg", out / "IFLC_SETUP.cfg")
    home = runtime / "home"
    home.mkdir(exist_ok=True)
    exe = next(p for p in runtime.iterdir() if p.name.startswith("iowolfsp") and p.is_file())
    exe.chmod(0o755)
    args = ["xvfb-run", "-a", "-s", "-screen 0 1280x720x24", str(exe), "+safe",
            "+set", "fs_basepath", str(runtime), "+set", "fs_homepath", str(home),
            "+set", "com_introplayed", "1", "+set", "com_recommendedSet", "1", "+set", "logfile", "2",
            "+set", "dw_proofAutomation", "1", "+set", "r_renderer", "rend2", "+set", "cl_renderer", "rend2",
            "+exec", "IFLC_SETUP.cfg", "+vid_restart", "+set", "dw_proofScenario", scenario, "+spdevmap", "crypt1"]
    env = {k: v for k, v in os.environ.items()
           if not any(s in k.upper() for s in ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"))}
    env.update(LIBGL_ALWAYS_SOFTWARE="1", LP_NUM_THREADS="2", SDL_AUDIODRIVER="dummy")
    with (out / "stdout.log").open("w") as log:
        p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            rc = p.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            rc = 124
    logs = []
    for index, p in enumerate(sorted(home.rglob("*console*.log"))):
        shutil.copy2(p, out / f"console-{index}.log")
        logs.append(p.read_text(errors="replace"))
    text = "\n".join(logs)
    images = {}
    for s in shots:
        found = list(home.rglob(s["name"] + ".tga"))
        if len(found) == 1:
            im = Image.open(found[0]).convert("RGB")
            im.save(out / (s["name"] + ".png"))
            images[s["name"]] = np.asarray(im).astype(np.int16)
    identities = re.findall(r"IFLC: map=crypt1 bsp=([0-9a-f]+) key=(\S+) route=(\S+)", text)
    changes = []
    pairs = [("empty_off", "empty_on"), ("direct_0", "direct_3"), ("volume_0", "volume_3"),
             ("empty_off", "reset"), ("empty_off", "off_restored")]
    for view in views:
        prefix = f"iflc_{view['name']}_"
        for a, b in pairs:
            if prefix + a in images and prefix + b in images:
                d = np.abs(images[prefix + a] - images[prefix + b])
                changes.append({"view": view["name"], "a": a, "b": b,
                                "changed_pixels": int(np.any(d > 0, axis=2).sum()),
                                "mean_abs_rgb": float(d.mean()), "max_abs_rgb": int(d.max())})
        selected = [s for s in shots if s["view"] == view["name"] and s["name"] in images]
        board = Image.new("RGB", (480 * 3, 298 * 3), (20, 20, 24))
        draw = ImageDraw.Draw(board)
        for j, s in enumerate(selected):
            im = Image.open(out / (s["name"] + ".png")).convert("RGB")
            im.thumbnail((480, 270))
            x, y = j % 3 * 480, j // 3 * 298
            draw.text((x + 8, y + 6), s["variant"], fill="white")
            board.paste(im, (x, y + 28))
        board.save(out / (view["name"] + "_comparison.png"))
    for p in home.rglob("*.iflc"):
        shutil.copy2(p, out / ("saved_" + p.name))
    report = {"base_run": 41408153237, "environment": "Linux Mesa llvmpipe real RTCW retail Crypt1",
              "renderer_instrumented": False, "visual_acceptance": "PENDING_IMAGE_REVIEW",
              "exit": rc, "ready": "PROOF_READY" in text, "complete": "IFLC_CRYPT1_RUNTIME_COMPLETE" in text,
              "requested_screenshots": len(shots), "captured_screenshots": len(images),
              "selected_identities": sorted(set(identities)), "shots": shots, "pixel_changes": changes,
              "camera_and_cvar_proof": [line for line in text.splitlines() if "PROOF_VIEW" in line or "PROOF_CVAR" in line]}
    (out / "IFLC_RUNTIME_REPORT.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("exit", "ready", "complete", "captured_screenshots", "selected_identities")}, indent=2), flush=True)
    assert rc == 0 and report["ready"] and report["complete"] and len(images) == len(shots), "Incomplete real-game capture"
    assert len({i[1] for i in identities}) >= 2, "Fewer than two separately selected physical lights"
    assert any(c["a"] == "direct_0" and c["changed_pixels"] > 10 for c in changes), "No measured direct-light response"
    assert any(c["a"] == "volume_0" and c["changed_pixels"] > 10 for c in changes), "No measured FireVol response"
    print("IFLC_REAL_GAME_CAPTURE_COMPLETE_PENDING_VISUAL_REVIEW", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("instrument")
    p.add_argument("source", type=Path)
    p = sub.add_parser("capture")
    p.add_argument("source", type=Path)
    p.add_argument("retail", type=Path)
    p.add_argument("output", type=Path)
    a = ap.parse_args()
    if a.command == "instrument":
        instrument(a.source)
    else:
        capture(a.source.resolve(), a.retail.resolve(), a.output.resolve())
