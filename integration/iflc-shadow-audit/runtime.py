#!/usr/bin/env python3
"""Capture one frozen Crypt1 source for the isolated IFLC shadow audit.

The source must already contain the camera helpers and test-only renderer hooks.
This script does not instrument or build it. Screenshots are diagnostic evidence;
causal interpretation and hard state verification belong to the separate verifier.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import zipfile

REPO = next((p for p in Path(__file__).resolve().parents
             if (p / "testlab/scripts/rc4_requested_views.py").is_file()),
            Path(__file__).resolve().parent.parent / "iflc-repo")
sys.path.insert(0, str(REPO / "testlab/scripts"))
from rc4_assault_camera import World


def discover(retail, limit=3, metadata_path=None):
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
    if metadata_path is not None:
        entities = []
        fields = ("classname", "origin", "target", "targetname", "_color", "color", "light", "style", "noise", "spawnflags")
        classes = {"dlight", "light", "lightJunior", "corona", "target_speaker"}
        for ordinal, entity in enumerate(world.entities):
            try:
                origin = list(map(float, entity.get("origin", "").split()))
                distances = {str(v["surface"]): math.dist(origin, v["anchor"]) for v in views} if len(origin) == 3 else {}
            except ValueError:
                distances = {}
            if ordinal in (288, 289, 290, 291, 292) or (entity.get("classname") in classes and distances and min(distances.values()) <= 384):
                entities.append({"ordinal_zero_based": ordinal, "fields": {k: entity[k] for k in fields if k in entity}, "distance_to_flame": distances})
        selected_surfaces = []
        for index in (2992, 2968, 442, 9499):
            surface = surfaces[index]
            verts = vertices[surface[3]:surface[3] + surface[4]]
            selected_surfaces.append({"surface": index, "shader": world.shaders[surface[0]][0].split(b"\0")[0].decode("latin1"),
                                      "centroid": [sum(v[k] for v in verts) / len(verts) for k in range(3)],
                                      "bounds": [[min(v[k] for v in verts) for k in range(3)], [max(v[k] for v in verts) for k in range(3)]]})
        metadata_path.write_text(json.dumps({"entity_ordinal_convention": "Zero-based parsed BSP entity order; compare native291 origin before using it as identity evidence.",
                                             "entities": entities, "surfaces": selected_surfaces,
                                             "note": "Limited derived metadata only; no retail BSP, textures or meshes exported."}, indent=2) + "\n")
    return views, hashlib.sha256(data).hexdigest()


def build_scenario(view):
    """Exact causal matrix. Bit masks change receiver contribution, not ownership."""
    matrix = [
        # Reference reproduces the user's settings; all remaining frames have volume=0.
        ("production_reference_volume1", 0, 3, 1, .2, 1),
        ("baseline_direct0_volume0", 0, 0, 0, .2, 1),
        ("direct3_flags0", 0, 3, 0, .2, 1),
        ("optin_world_bypass", 1, 3, 0, .2, 1),
        ("optin_ordinary_bypass", 2, 3, 0, .2, 1),
        ("optin_both_shadows_bypass", 3, 3, 0, .2, 1),
        ("native291_direct_off", 4, 3, 0, .2, 1),
        ("optin_direct_off", 8, 3, 0, .2, 1),
        ("both_direct_off", 12, 3, 0, .2, 1),
        ("optin_off_native291_shadows_bypass", 56, 3, 0, .2, 1),
        ("all_direct_off", 64, 3, 0, .2, 1),
        ("direct3_flags0_restored", 0, 3, 0, .2, 1),
        ("baked0_optin_both_shadows_bypass", 3, 3, 0, 0, 1),
        ("baked0_optin_receiver_off", 8, 3, 0, 0, 1),
        ("baked0_both_receivers_off", 12, 3, 0, 0, 1),
        ("baked0_all_direct_off", 64, 3, 0, 0, 1),
        ("final_baked02_direct3_restore", 0, 3, 0, .2, 1),
    ]
    commands = ["set con_notifytime -1", "set cg_draw2D 0", "set cg_drawGun 0",
                "set cg_bobup 0", "set cg_bobpitch 0", "set cg_bobroll 0",
                "set r_autoExposure 0", "set r_forceAutoExposure 0",
                "set r_forceSunPause 1", "god", "notarget", "wait 18",
                f"echo IFLC_TEST_BEGIN {view['name']}", "set dw_proofShot 0",
                "set dw_proofFreeze 0", "set r_iflcShadowAudit 0", "set r_dwFireLightControl 0",
                "set r_mapLightingLearn 1", "set r_mapLightingLearnShow 0",
                "set r_mapLightingProfileEnable 0", "maplight_clear_memory confirm",
                "maplight_zone_new IFLC_runtime",
                "proofView " + " ".join(f"{v:.6f}" for v in view["baked_probe"] + view["angles"]),
                "wait 12", f"echo IFLC_BAKE {view['name']} flame_probe",
                "maplight_add_cluster", "maplight_status",
                "proofView " + " ".join(f"{v:.6f}" for v in view["eye"] + view["angles"]),
                "wait 35", f"echo IFLC_BAKE {view['name']} camera", "maplight_add_cluster",
                "maplight_baked 0.2", "maplight_status", "maplight_list",
                # Inspect only: never add/reassign a receiver during the causal sequence.
                "maplight_surface_inspect", "set dw_proofFreeze 1", "wait 12",
                "dw_fl_reload", "dw_fl_select", "dw_fl_next", "wait 2"]
    shots = []
    for variant, flags, direct, volume, baked, enabled in matrix:
        index = len(shots) + 1
        name = f"iflc_shadow_{index:02d}"
        commands += ["set dw_proofShot 0", "set r_dwFireLightControl 1",
                     f"set r_iflcShadowAudit {flags}", f"dw_fl_set enabled {enabled}",
                     f"dw_fl_set direct {direct}", "dw_fl_set radius 1",
                     f"dw_fl_set volume {volume}",
                     f"maplight_baked {baked:g}", "wait 12",
                     f"echo IFLC_SHADOW_STATE shot={index} flags={flags} direct={direct} volume={volume} baked={baked:g} enabled={enabled}",
                     f"echo IFLC_STATE {view['name']} {variant}",
                     "dw_fl_info", "maplight_list", "maplight_status",
                     # New shot ID is published only after the state has warmed up.
                     f"set dw_proofShot {index}", "wait 5", f"screenshot {name}", "wait 2"]
        shots.append({"id": index, "name": name, "variant": variant, "view": view["name"],
                      "flags": flags, "direct": direct, "volume": volume, "baked": baked,
                      "enabled": enabled, "radius": 1, "master": 1, "color_override": 0,
                      "role": "production_reference" if volume == 1 else "causal_control"})
    commands += ["set dw_proofShot 0", "set r_iflcShadowAudit 0",
                 "set dw_proofFreeze 0", "echo IFLC_SHADOW_AUDIT_RUNTIME_COMPLETE", "quit"]
    return commands, shots


def capture(source, retail, out):
    from PIL import Image, ImageDraw
    out.mkdir(parents=True, exist_ok=True)
    all_views, bsp_sha = discover(retail, limit=3, metadata_path=out / "CRYPT1_NEARBY_SOURCE_METADATA.json")
    view = all_views[0]
    views = [view]
    (out / "CRYPT1_IFLC_SHADOW_CAMERAS.json").write_text(json.dumps({"bsp_sha256": bsp_sha, "views": views}, indent=2) + "\n")
    # A fresh home is required: a failed earlier capture must not supply a
    # saved profile to the diagnostic baseline.
    runtime = Path(tempfile.mkdtemp(prefix="iflc-shadow-runtime-", dir=out.parent)).resolve()
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
    commands, shots = build_scenario(view)
    scenario = "IFLC_SHADOW_AUDIT_TEST.cfg"
    (main / scenario).write_text("\n".join(commands) + "\n")
    shutil.copy2(main / scenario, out / scenario)
    setup = ["set r_mode -1", "set r_customwidth 960", "set r_customheight 540", "set r_fullscreen 0",
             "set r_renderer rend2", "set cl_renderer rend2", "set r_hdr 1", "set r_postProcess 1",
             "set r_bloom 1", "set r_bloomMode 2", "set r_dwCas 1", "set r_dwA2C 1",
             "set r_ssgi 1", "set r_forceSun 1", "set r_sunShadows 1", "set r_dlightMode 2",
             "set r_dlightShadowMaxLights 3", "set r_dlightWorldContainment 2",
             "set r_volumetricSun 1", "set r_volumetricLocal 1", "set r_volumetricFire 1",
             # These four production settings enable the existing stable fixture
             # path; defaults select legacy v0.6 with no volume-only BSP sources.
             "set r_volumetricFireV07Mode 2", "set r_volumetricFireSourceMode 2",
             "set r_volumetricFireMaxActive 8", "set r_volumetricFireMode 2",
             "set r_volumetricFireSamples 40", "set r_iflcShadowAudit 0",
             "set r_volumetricFireDiag 1", "set r_volumetricFireResidencyDiag 1",
             "set r_ext_framebuffer_multisample 4", "set r_cameraExposure 1",
             "set r_autoExposure 0", "set r_forceAutoExposure 0", "set r_dwFireLightControl 0",
             "set s_initsound 0", "set r_swapInterval 0", "set fixedtime 100", "set con_notifytime -1"]
    (main / "IFLC_SHADOW_SETUP.cfg").write_text("\n".join(setup) + "\n")
    shutil.copy2(main / "IFLC_SHADOW_SETUP.cfg", out / "IFLC_SHADOW_SETUP.cfg")
    home = runtime / "home"
    home.mkdir(exist_ok=True)
    exe = next(p for p in runtime.iterdir() if p.name.startswith("iowolfsp") and p.is_file())
    exe.chmod(0o755)
    args = ["xvfb-run", "-a", "-s", "-screen 0 1280x720x24", str(exe), "+safe",
            "+set", "fs_basepath", str(runtime), "+set", "fs_homepath", str(home),
            "+set", "com_introplayed", "1", "+set", "com_recommendedSet", "1", "+set", "logfile", "2",
            "+set", "dw_proofAutomation", "1", "+set", "r_renderer", "rend2", "+set", "cl_renderer", "rend2",
            "+exec", "IFLC_SHADOW_SETUP.cfg", "+vid_restart", "+set", "dw_proofScenario", scenario, "+spdevmap", "crypt1"]
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
    if not text:
        text = (out / "stdout.log").read_text(errors="replace")
    images = set()
    for s in shots:
        found = list(home.rglob(s["name"] + ".tga"))
        if len(found) == 1:
            im = Image.open(found[0]).convert("RGB")
            im.save(out / (s["name"] + ".png"))
            images.add(s["name"])
    selected = [s for s in shots if s["name"] in images]
    board = Image.new("RGB", (480 * 3, 310 * max(1, math.ceil(len(selected) / 3))), (20, 20, 24))
    draw = ImageDraw.Draw(board)
    for j, shot in enumerate(selected):
        im = Image.open(out / (shot["name"] + ".png")).convert("RGB")
        im.thumbnail((480, 270))
        x, y = j % 3 * 480, j // 3 * 310
        draw.text((x + 8, y + 3), f"{shot['id']:02d} {shot['variant']}", fill="white")
        draw.text((x + 8, y + 18),
                  f"mask={shot['flags']} direct={shot['direct']} volume={shot['volume']} baked={shot['baked']} enabled={shot['enabled']}",
                  fill="white")
        board.paste(im, (x, y + 40))
    board.save(out / "IFLC_SHADOW_AUDIT_CONTACT_SHEET.png")
    manifest = {"base_run": 41408153237, "shots": shots, "view": view,
                "bsp_sha256": bsp_sha, "exit": rc, "ready": "PROOF_READY" in text,
                "complete": "IFLC_SHADOW_AUDIT_RUNTIME_COMPLETE" in text,
                "requested_screenshots": len(shots), "captured_screenshots": len(images),
                "renderer_instrumented": True, "visual_acceptance": "PENDING_IMAGE_REVIEW",
                "state_verification": "DELEGATED_TO_SEPARATE_VERIFIER",
                "flag_semantics": {"1": "selected opt-in world visibility bypass",
                    "2": "selected opt-in ordinary shadow bypass",
                    "4": "native291 direct receiver gain zero",
                    "8": "selected opt-in direct receiver gain zero",
                    "16": "native291 world visibility bypass",
                    "32": "native291 ordinary shadow bypass",
                    "64": "all dlight direct receiver gain zero"},
                "limitations": ["Reference frame 1 has volume=1; every causal frame has volume=0.",
                    "Native291 is a nearby candidate, not an established authored owner of this flame.",
                    "Mask bits suppress receiver contribution without deleting lights or changing ownership/allocations.",
                    "Client camera/time are frozen; wall-clock residency and GPU temporal history may still vary.",
                    "MapLighting changes only the existing zone scale; scene-dependent SSGI may respond indirectly.",
                    "Cluster assignment alone does not prove coverage of the small wall spot.",
                    "No pixel metric or screenshot count establishes visual acceptance or a shadow cause."]}
    (out / "IFLC_SHADOW_AUDIT_CAPTURE.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: manifest[k] for k in ("exit", "ready", "complete", "requested_screenshots", "captured_screenshots")}, indent=2), flush=True)
    assert rc == 0 and manifest["ready"] and manifest["complete"] and len(images) == len(shots), "Incomplete shadow-audit capture"
    print("IFLC_SHADOW_AUDIT_CAPTURE_COMPLETE_PENDING_VERIFICATION_AND_IMAGE_REVIEW", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("capture")
    p.add_argument("source", type=Path)
    p.add_argument("retail", type=Path)
    p.add_argument("output", type=Path)
    a = ap.parse_args()
    capture(a.source.resolve(), a.retail.resolve(), a.output.resolve())
