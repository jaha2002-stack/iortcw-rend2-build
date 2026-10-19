#!/usr/bin/env python3
"""Targeted stage-3 proof with a real animated RTCW player mesh and two animation frames.

Only test-harness client camera distance changes; the renderer stays byte-for-byte
identical to the four-profile RC4+CSM+texture-fidelity candidate.
No protected game asset bytes are exported.
"""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageStat
import json
import struct
import re
import sys
import zipfile

import run_stage_ab as ab

BASE_INSTRUMENT = ab.photo.instrument
MODEL_SELECTION = None
OUT = None


def instrument_close_model(root):
    BASE_INSTRUMENT(root)
    path = root / "SP/code/cgame/cg_view.c"
    txt = path.read_text()
    original = "VectorMA( cg.refdef.vieworg, 100, cg.refdef.viewaxis[0], cg.testModelEntity.origin );"
    changed = r'''
    // Test-only authored RTCW material proof; cvar set by isolated runner.
    {
        char skinPath[MAX_QPATH];
        trap_Cvar_VariableStringBuffer("dw_proofSkin", skinPath, sizeof(skinPath));
        cg.testModelEntity.customSkin = trap_R_RegisterSkin(skinPath);
        CG_Printf("PROOF_CHARACTER_SKIN requested=%s handle=%d\n",
                  skinPath, cg.testModelEntity.customSkin);
        if (!cg.testModelEntity.customSkin) {
            cg.testModelEntity.hModel = 0;
            return;
        }
    }
    VectorMA( cg.refdef.vieworg, 120, cg.refdef.viewaxis[0], cg.testModelEntity.origin );
    // Keep complete standing character (with feet origin) in central viewport.
    cg.testModelEntity.origin[2] -= 32;
    '''
    if txt.count(original) != 1:
        raise RuntimeError("Fail closed: unexpected RTCW testmodel camera anchor")
    path.write_text(txt.replace(original, changed))
    print("PROOF_CHARACTER_CLOSEUP: test-only model distance 120 units, z=-32; required skin; renderer unchanged", flush=True)


def animated_player_mesh(retail):
    """Select a real full-body skeletal MDS player, with its authored skin."""
    global MODEL_SELECTION
    if MODEL_SELECTION:
        return MODEL_SELECTION["path"]
    paths = {}
    for pk3 in sorted(retail.glob("*.pk3")):
        with zipfile.ZipFile(pk3) as z:
            for info in z.infolist():
                lower = info.filename.lower()
                if lower.startswith("models/players/") and not info.is_dir():
                    # Later PK3s override names in the native VFS.
                    paths[lower] = (pk3, info.filename, info.file_size)
    candidates = []
    for low, (pk3, original, size) in paths.items():
        if not low.endswith("/body.mds") or size < 40000:
            continue
        with zipfile.ZipFile(pk3) as z, z.open(original) as handle:
            header = handle.read(84)
        if len(header) != 84 or header[:4] != b"MDSW":
            continue
        version = struct.unpack_from("<i", header, 4)[0]
        frames = struct.unpack_from("<i", header, 80)[0]
        if version != 4 or not 1 < frames < 10000:
            continue
        folder = low.rsplit("/", 1)[0]
        skins = [(p, paths[p][2]) for p in paths if p.startswith(folder + "/body_")
                 and p.endswith(".skin") and paths[p][2] > 10]
        if not skins:
            continue
        skins.sort(key=lambda pair: ("default" not in pair[0],
                                    "original" not in pair[0], -pair[1], pair[0]))
        name = folder.rsplit("/", 1)[-1]
        priority = ["infantryss", "officerss", "blackguard", "eliteguard",
                    "soldier", "mechanic", "murphy", "partisan", "higgs", "jack"]
        rank = next((i for i,v in enumerate(priority) if v in name), len(priority))
        candidates.append({"path": original, "frames": frames, "bytes": size,
                           "skin": paths[skins[0][0]][1], "skin_bytes":skins[0][1],
                           "body_mesh": True, "format":"mds",
                           "skin_variants":len(skins), "human_character_rank":rank})
    candidates.sort(key=lambda x:(x["human_character_rank"],
                                   -min(x["bytes"],2000000),x["path"].lower()))
    info = {"selected": candidates[0] if candidates else None,
            "full_body_mds_with_skin_count":len(candidates),
            "candidate_models": candidates[:35],
            "selection_method":"validated MDSW v4 body.mds + body_*.skin from retail PK3 filenames; nonmatching models excluded",
            "protected_assets_embedded":False}
    (OUT/"MODEL_DISCOVERY.json").write_text(json.dumps(info,indent=2)+"\n")
    if not candidates:
        raise RuntimeError("No skinned full-body animated MDS candidate in RTCW retail; see MODEL_DISCOVERY.json")
    MODEL_SELECTION=candidates[0]
    print("PROOF_CHARACTER_SELECTED", MODEL_SELECTION,flush=True)
    return MODEL_SELECTION["path"]


BASE_PREPARE_RUNTIME = ab.prepare_runtime


def prepare_runtime_with_skin(build, retail, out):
    runtime, main = BASE_PREPARE_RUNTIME(build, retail, out)
    assert MODEL_SELECTION and MODEL_SELECTION["skin"].endswith(".skin")
    cfg = main/"PRODUCTION_HIGH_QUALITY.cfg"
    with cfg.open("a") as handle:
        handle.write("\nset dw_proofSkin " + MODEL_SELECTION["skin"] + "\n")
    return runtime, main


def analyze_character(out):
    modes = tuple(ab.PROFILE)
    assert modes == ("BASE", "STAGE1", "STAGE2", "STAGE3")
    original = json.loads((out / "AB_REPORT.json").read_text())
    assert len(original["pairs"]) == 2
    assert MODEL_SELECTION and MODEL_SELECTION["frames"] > 1
    modelpath = MODEL_SELECTION["path"]
    canvas = Image.new("RGB", (480 * len(modes), 60 + 440 * 2), (16, 16, 16))
    draw = ImageDraw.Draw(canvas)
    checks = []
    for mi, mode in enumerate(modes):
        meta = json.loads((out / f"assault_{mode}-result.json").read_text())
        assert meta["exit"] == 0 and meta["ready"] and meta["complete"]
        assert meta["character_model_path"] == modelpath
        paths = [out / meta["character_images"][f"frame{frame}"] for frame in (0, 1)]
        assert all(path.exists() for path in paths)
        log=(out/f"assault_{mode}-console-0.log").read_text(errors="replace")
        proof=re.search(r"PROOF_CHARACTER_SKIN requested=([^ ]+) handle=(\d+)",log)
        if not proof or proof.group(1).lower()!=MODEL_SELECTION["skin"].lower() or int(proof.group(2))<=0:
            raise RuntimeError(f"{mode}: original RTCW skin not registered: {MODEL_SELECTION['skin']}")
        images = [Image.open(p).convert("RGB") for p in paths]
        assert images[0].size == images[1].size == (1280, 720)
        subject = (290, 120, 1000, 690)
        a, b = [im.crop(subject) for im in images]
        d = ImageChops.difference(a, b)
        count = sum(1 for pixel in d.getdata() if max(pixel) >= 12)
        checks.append({"mode": mode, "model": modelpath, "animation_frame_delta_pixels_ge_12": count,
                       "within_subject_roi":list(subject),
                       "mean_animation_rgb_delta":round(sum(ImageStat.Stat(d).mean)/3,4)})
        for fi, im in enumerate((a, b)):
            im.thumbnail((480, 395))
            x = mi * 480; y = fi * 440
            draw.text((x+9, y+8), f"{mode}: {Path(modelpath).name}, frame {fi}", fill="white")
            canvas.paste(im, (x, y+38))
    canvas.save(out / "DARKWOLF_CHARACTER_MODEL_4STAGES.png")
    original["character_proof"] = {
        "asset_path": modelpath, "source_frame_count":MODEL_SELECTION["frames"],
        "test_model_distance_units":120, "test_model_origin_z_adjust":-32,
        "skin_path":MODEL_SELECTION["skin"], "skin_registration_verified":True,
        "full_body_mds":True, "renderer_source_changes_for_closeup":False,
        "model_frame_checks": checks,
        "acceptance":"PENDING_USER_REVIEW_AND_REAL_GPU_FPS"
    }
    (out / "AB_REPORT.json").write_text(json.dumps(original, indent=2) + "\n")
    (out / "CHARACTER_PROOF_REPORT.json").write_text(
        json.dumps(original["character_proof"], indent=2) + "\n")
    print(json.dumps(original["character_proof"], indent=2), flush=True)
    # At least one frame change is necessary to call this an animation test.
    if not any(q["animation_frame_delta_pixels_ge_12"] > 100 for q in checks):
        raise RuntimeError("Animation frames captured but do not visibly differ; reject proof")
    assert (out / "DARKWOLF_CHARACTER_MODEL_4STAGES.png").is_file()


def main():
    global OUT
    if len(sys.argv) != 4:
        raise SystemExit("Usage: run_character_proof.py source retail_main evidence/real-game-character")
    OUT = Path(sys.argv[3]).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    ab.MAPS = ("assault",)
    ab.photo.instrument = instrument_close_model
    ab.discover_character_model = animated_player_mesh
    ab.prepare_runtime = prepare_runtime_with_skin
    animated_player_mesh(Path(sys.argv[2]).resolve())
    ab.main()
    analyze_character(OUT)


if __name__ == "__main__":
    main()
