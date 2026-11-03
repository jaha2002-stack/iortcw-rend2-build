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
import tempfile
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
        # Distinct shader surfaces can belong to the same physical fixture.
        # Keep targets farther apart than two 128-unit owner-association radii.
        if any(math.dist(target, view["anchor"]) <= 256 for view in views):
            continue
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
            view["camera_cluster"] = world.leaf(view["eye"])[0]
            # Paint both the view cluster and the flame-side cluster using the
            # real maplighting commands. Keep the probe in empty, visible BSP.
            toward_eye = [view["eye"][k] - target[k] for k in range(3)]
            norm = math.sqrt(sum(v * v for v in toward_eye))
            probe = None
            for offset in (24, 40, 64):
                point = [target[k] + toward_eye[k] * offset / norm for k in range(3)]
                hit = world.trace(point, target)
                if not world.solid(point) and not (hit and hit.get("fraction", 0) < .99):
                    probe = point
                    break
            view["baked_probe"] = probe if probe is not None else view["eye"]
            view["flame_probe_cluster"] = world.leaf(view["baked_probe"])[0]
            views.append(view)
        if len(views) == limit:
            break
    if len(views) < 2:
        raise RuntimeError(f"Only {len(views)} independently visible BSP flame cameras")
    return views, hashlib.sha256(data).hexdigest()


def inspect_command_evidence(text, views, shots):
    """Validate commands and cameras separately from visual acceptance."""
    records, proof, baked = {}, {}, {}
    current = None
    bake = None
    for line in text.splitlines():
        if "IFLC_TEST_BEGIN " in line:
            current = None
            bake = None
        match = re.search(r"IFLC_STATE (\S+) (\S+)", line)
        if match:
            current = records.setdefault((match[1], match[2]), {"view": match[1], "variant": match[2]})
            bake = None
        match = re.search(r"IFLC_BAKE (\S+) (\S+)", line)
        if match:
            bake = baked.setdefault((match[1], match[2]), {"view": match[1], "phase": match[2]})
            current = None
        match = re.search(r"IFLC: map=crypt1 bsp=([0-9a-f]+) key=(\S+) route=(\S+) anchor=\(([^)]+)\)", line)
        if match and current is not None:
            current.update(bsp=match[1], key=match[2], route=match[3], anchor=[float(v) for v in match[4].split()])
        match = re.search(r"IFLC: editable=(\S+) realDlights=(\d+) baseRadius=([\d.]+) currentRadius=([\d.]+) worldContainment=(\d+)", line)
        if match and current is not None:
            current.update(editable=match[1], real_dlights=int(match[2]), base_radius=float(match[3]),
                           current_radius=float(match[4]), containment=int(match[5]))
        match = re.search(r"IFLC: direct=([\d.]+) radius=([\d.]+) volume=([\d.]+) enabled=(\d+) colorOverride=(\d+) master=(\d+) profile=(\S+)", line)
        if match and current is not None:
            current.update(direct=float(match[1]), radius=float(match[2]), volume=float(match[3]),
                           enabled=int(match[4]), master=int(match[6]), profile=match[7])
        match = re.search(r"IFLC: direct bridge blocked=(\d+)", line)
        if match and current is not None:
            current["bridge_blocked"] = int(match[1])
        match = re.search(r"PROOF_VIEW shot=(\d+) time=(\d+) eye=([\d.,-]+) forward=([\d.,-]+)", line)
        if match:
            proof[int(match[1])] = {"time": int(match[2]), "eye": [float(v) for v in match[3].split(",")],
                                    "forward": [float(v) for v in match[4].split(",")]}
        match = re.search(r"MAPLIGHT_LEARN status .* cluster=(-?\d+) .*clusterLM=(\d+)", line)
        if match and bake is not None:
            bake.update(actual_cluster=int(match[1]), lightmapped_surfaces_in_cluster=int(match[2]))
        match = re.search(r"MAPLIGHT_LEARN: add_cluster changed=(\d+) activeZone=(\d+) cluster=(-?\d+)", line)
        if match and bake is not None:
            bake.update(added_surfaces=int(match[1]), active_zone=int(match[2]), assigned_cluster=int(match[3]))
        match = re.search(r"zone=\d+ name=IFLC_runtime mode=(\S+) baked=([\d.]+) surfaces=(\d+)", line)
        if match and bake is not None:
            bake.update(mode=match[1], baked_scale=float(match[2]), assigned_surfaces=int(match[3]))

    expected = {
        "empty_off": (1, 1, 1, 0), "empty_off_repeat": (1, 1, 1, 0), "empty_on": (1, 1, 1, 1),
        "direct_0": (0, 1, 1, 1), "direct_3": (3, 1, 1, 1), "direct_0_repeat": (0, 1, 1, 1),
        "volume_0": (1, 1, 0, 1), "volume_3": (1, 1, 3, 1), "volume_0_repeat": (1, 1, 0, 1),
        "saved": (1.75, 1.25, .8, 1), "mutated": (.5, 1.25, .8, 1), "reload": (1.75, 1.25, .8, 1),
        "reset": (1, 1, 1, 1), "off_restored": (1, 1, 1, 0), "off_restored_repeat": (1, 1, 1, 0),
    }
    faults, cameras = [], []
    for view in views:
        states = [records.get((view["name"], shot["variant"]), {}) for shot in shots if shot["view"] == view["name"]]
        keys = {state.get("key") for state in states}
        if None in keys or len(keys) != 1:
            faults.append(f"{view['name']}: missing or changing selected owner")
        for state in states:
            variant = state.get("variant", "missing")
            wanted = expected.get(variant)
            if not wanted or any(abs(state.get(field, -999) - value) > .001 for field, value in zip(("direct", "radius", "volume", "master"), wanted)):
                faults.append(f"{view['name']}/{variant}: requested parameter state not confirmed")
            if state.get("editable") != "YES":
                faults.append(f"{view['name']}/{variant}: physical source is not editable")
            if variant.startswith(("direct_", "volume_")) or variant in ("saved", "mutated", "reload"):
                if state.get("real_dlights") != 1 or state.get("bridge_blocked"):
                    faults.append(f"{view['name']}/{variant}: no unique active direct emitter")
            if variant in ("saved", "reload") and state.get("profile") != "SAVED":
                faults.append(f"{view['name']}/{variant}: persistence result unconfirmed")
            if variant.startswith(("empty_", "off_restored")) or variant == "reset":
                if state.get("profile") != "BASELINE":
                    faults.append(f"{view['name']}/{variant}: empty profile not confirmed")
            if "anchor" in state and math.dist(state["anchor"], view["anchor"]) > 129:
                faults.append(f"{view['name']}/{variant}: selected owner too far from aimed flame")
        snapshots = [proof.get(shot["id"]) for shot in shots if shot["view"] == view["name"]]
        present = [p for p in snapshots if p is not None]
        fixed_time = len({p["time"] for p in present}) == 1
        max_eye_drift = max((math.dist(p["eye"], present[0]["eye"]) for p in present), default=None)
        max_direction_drift = max((math.dist(p["forward"], present[0]["forward"]) for p in present), default=None)
        target_error = max((math.dist(p["eye"], view["eye"]) for p in present), default=None)
        camera_ok = (bool(present) and len(present) == len(snapshots) and fixed_time
                     and max_eye_drift < .05 and max_direction_drift < .0001 and target_error < 1)
        cameras.append({"view": view["name"], "confirmed": camera_ok, "fixed_client_time": fixed_time,
                        "max_eye_drift_units": max_eye_drift, "max_forward_drift": max_direction_drift,
                        "max_requested_eye_error_units": target_error})
        if not camera_ok:
            faults.append(f"{view['name']}: frozen camera/time evidence incomplete or changed")
        for phase, cluster in (("camera", view["camera_cluster"]), ("flame_probe", view["flame_probe_cluster"])):
            record = baked.get((view["name"], phase), {})
            if record.get("actual_cluster") != cluster or record.get("assigned_cluster") != cluster or record.get("active_zone", 0) <= 0:
                faults.append(f"{view['name']}: maplighting {phase} cluster coverage unconfirmed")
        record = baked.get((view["name"], "camera"), {})
        if record.get("mode") != "custom" or abs(record.get("baked_scale", -1) - .2) > .001 or record.get("assigned_surfaces", 0) <= 0:
            faults.append(f"{view['name']}: 20-percent baked zone not confirmed")
    distinct = {state.get("key") for (view, variant), state in records.items() if variant == "direct_0" and state.get("key")}
    if len(distinct) < 2:
        faults.append("Fewer than two independently selected physical sources in direct-test states")
    return {"faults": faults, "states": list(records.values()), "camera_checks": cameras,
            "maplighting": list(baked.values()), "independent_source_keys": sorted(distinct)}


def capture(source, retail, out):
    from PIL import Image, ImageDraw
    import numpy as np
    out.mkdir(parents=True, exist_ok=True)
    views, bsp_sha = discover(retail)
    (out / "CRYPT1_IFLC_CAMERAS.json").write_text(json.dumps({"bsp_sha256": bsp_sha, "views": views}, indent=2) + "\n")
    # A fresh home is required: a failed earlier capture must not supply a
    # saved profile to the purported empty-profile baseline.
    runtime = Path(tempfile.mkdtemp(prefix="iflc-runtime-", dir=out.parent)).resolve()
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
                         f"set dw_proofShot {index}", "wait 5", f"screenshot {name}", "wait 2"])
        shots.append({"id": index, "view": view["name"], "variant": variant, "name": name})

    for view in views:
        commands += [f"echo IFLC_TEST_BEGIN {view['name']}", "set dw_proofFreeze 0",
                     "set r_dwFireLightControl 0", "set r_mapLightingLearn 1",
                     "set r_mapLightingLearnShow 0", "set r_mapLightingProfileEnable 0",
                     "maplight_clear_memory", "maplight_zone_new IFLC_runtime",
                     "proofView " + " ".join(f"{v:.6f}" for v in view["baked_probe"] + view["angles"]),
                     "wait 12", f"echo IFLC_BAKE {view['name']} flame_probe", "maplight_add_cluster", "maplight_status",
                     "proofView " + " ".join(f"{v:.6f}" for v in view["eye"] + view["angles"]),
                     "wait 35", f"echo IFLC_BAKE {view['name']} camera", "maplight_add_cluster",
                     "maplight_baked 0.2", "maplight_status", "maplight_list",
                     "set dw_proofFreeze 1", "wait 12", "dw_fl_reload", "dw_fl_select", "dw_fl_next", "wait 2"]
        shot(view, "empty_off")
        commands += ["wait 5"]
        shot(view, "empty_off_repeat")
        commands += ["set r_dwFireLightControl 1", "wait 8"]
        shot(view, "empty_on")
        # 'enabled' refuses existing native/promoted owners; that is the expected guard.
        commands += ["dw_fl_set enabled 1", "dw_fl_set direct 0", "dw_fl_set radius 1", "dw_fl_set volume 1", "wait 8"]
        shot(view, "direct_0")
        commands += ["dw_fl_set direct 3", "wait 8"]
        shot(view, "direct_3")
        commands += ["dw_fl_set direct 0", "wait 8"]
        shot(view, "direct_0_repeat")
        commands += ["dw_fl_set direct 1", "dw_fl_set volume 0", "wait 8"]
        shot(view, "volume_0")
        commands += ["dw_fl_set volume 3", "wait 8"]
        shot(view, "volume_3")
        commands += ["dw_fl_set volume 0", "wait 8"]
        shot(view, "volume_0_repeat")
        commands += ["dw_fl_set direct 1.75", "dw_fl_set radius 1.25", "dw_fl_set volume 0.8",
                     "dw_fl_save", "wait 8"]
        shot(view, "saved")
        commands += ["dw_fl_set direct 0.5", "wait 8"]
        shot(view, "mutated")
        commands += ["dw_fl_reload", "wait 8"]
        shot(view, "reload")
        commands += ["dw_fl_reset", "dw_fl_save", "wait 8"]
        shot(view, "reset")
        commands += ["set r_dwFireLightControl 0", "wait 8"]
        shot(view, "off_restored")
        commands += ["wait 5"]
        shot(view, "off_restored_repeat")
    commands += ["maplight_clear_memory", "set r_mapLightingLearn 0", "set dw_proofFreeze 0", "echo IFLC_CRYPT1_RUNTIME_COMPLETE", "quit"]
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
    command_evidence = inspect_command_evidence(text, views, shots)
    changes = []
    effects, parity = [], []
    pairs = [("empty_off", "empty_on"), ("direct_0", "direct_3"), ("volume_0", "volume_3"),
             ("empty_off", "reset"), ("empty_off", "off_restored"), ("saved", "reload"),
             ("empty_off", "empty_off_repeat"), ("direct_0", "direct_0_repeat"),
             ("volume_0", "volume_0_repeat"), ("off_restored", "off_restored_repeat")]
    for view in views:
        prefix = f"iflc_{view['name']}_"

        def delta(a, b):
            if prefix + a not in images or prefix + b not in images:
                return None
            return np.abs(images[prefix + a] - images[prefix + b])

        for a, b in pairs:
            d = delta(a, b)
            if d is not None:
                changes.append({"view": view["name"], "a": a, "b": b,
                                "changed_pixels": int(np.any(d > 0, axis=2).sum()),
                                "mean_abs_rgb": float(d.mean()), "max_abs_rgb": int(d.max())})
        for kind in ("direct", "volume"):
            effect = delta(kind + "_0", kind + "_3")
            drift = delta(kind + "_0", kind + "_0_repeat")
            if effect is None or drift is None:
                continue
            effect_mean, drift_mean = float(effect.mean()), float(drift.mean())
            stronger = np.any(effect > drift + 2, axis=2)
            clear = effect_mean > max(.05, drift_mean * 2) and int(stronger.sum()) > 50
            effects.append({"view": view["name"], "control": kind,
                            "comparison": [kind + "_0", kind + "_3", kind + "_0_repeat"],
                            "effect_mean_abs_rgb": effect_mean, "repeat_drift_mean_abs_rgb": drift_mean,
                            "effect_to_drift_ratio_floor_0_02": effect_mean / max(.02, drift_mean),
                            "pixels_above_repeat_drift_plus_2": int(stronger.sum()),
                            "evidence_flag": "CLEAR_DIFFERENCE_ABOVE_REPEAT_DRIFT" if clear else "NEEDS_IMAGE_REVIEW_DRIFT_OR_WEAK_RESPONSE"})
        early_drift = delta("empty_off", "empty_off_repeat")
        late_drift = delta("off_restored", "off_restored_repeat")
        if early_drift is not None and late_drift is not None:
            drift = np.maximum(early_drift, late_drift)
            drift_mean = float(drift.mean())
            for a, b in (("empty_off", "empty_on"), ("empty_off", "reset"),
                         ("empty_off", "off_restored"), ("saved", "reload")):
                d = delta(a, b)
                if d is None:
                    continue
                mean = float(d.mean())
                parity.append({"view": view["name"], "a": a, "b": b,
                               "mean_abs_rgb": mean, "off_repeat_drift_envelope_mean_abs_rgb": drift_mean,
                               "pixels_above_repeat_drift_plus_2": int(np.any(d > drift + 2, axis=2).sum()),
                               "evidence_flag": "WITHIN_OFF_REPEAT_DRIFT_ENVELOPE" if mean <= max(.05, drift_mean * 2) else "NEEDS_IMAGE_REVIEW_RESTORE_OR_TEMPORAL_DRIFT"})
        selected = [s for s in shots if s["view"] == view["name"] and s["name"] in images]
        board = Image.new("RGB", (480 * 3, 298 * max(1, math.ceil(len(selected) / 3))), (20, 20, 24))
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
              "command_behavior_verified": not command_evidence["faults"], "command_evidence": command_evidence,
              "effect_vs_repeat_drift": effects, "parity_vs_repeat_drift": parity,
              "pixel_evidence_limitations": "Client time and camera are frozen; wall-clock FireVol residency and GPU temporal history can still change. Pixel flags are triage evidence only. Inspect images for direct/volume independence and restoration before visual acceptance.",
              "camera_and_cvar_proof": [line for line in text.splitlines() if "PROOF_VIEW" in line or "PROOF_CVAR" in line]}
    (out / "IFLC_RUNTIME_REPORT.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("exit", "ready", "complete", "captured_screenshots", "selected_identities")}, indent=2), flush=True)
    assert rc == 0 and report["ready"] and report["complete"] and len(images) == len(shots), "Incomplete real-game capture"
    assert not command_evidence["faults"], "Unconfirmed runtime behavior: " + "; ".join(command_evidence["faults"])
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
