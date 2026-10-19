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
    changed = "VectorMA( cg.refdef.vieworg, 55, cg.refdef.viewaxis[0], cg.testModelEntity.origin );"
    if txt.count(original) != 1:
        raise RuntimeError("Fail closed: unexpected RTCW testmodel camera anchor")
    path.write_text(txt.replace(original, changed))
    print("PROOF_CHARACTER_CLOSEUP: test-only model distance 55 game units; renderer unchanged", flush=True)


def animated_player_mesh(retail):
    global MODEL_SELECTION
    if MODEL_SELECTION:
        return MODEL_SELECTION["path"]
    catalogue = []
    for pk3 in sorted(retail.glob("*.pk3")):
        with zipfile.ZipFile(pk3) as z:
            for info in z.infolist():
                name = info.filename
                low = name.lower()
                if not low.startswith("models/players/") or not low.endswith((".md3", ".mdc")):
                    continue
                if "lod" in Path(low).stem or info.file_size < 16000:
                    continue
                with z.open(info) as handle:
                    head = handle.read(84)
                if len(head) < 80 or head[:4] not in (b"IDP3", b"IDPC"):
                    continue
                frames = struct.unpack_from("<i", head, 76)[0]
                if frames < 1 or frames > 2000:
                    continue
                stem = Path(low).stem
                is_body = any(term in stem for term in ("body", "torso", "upper", "legs", "lower"))
                entry = {"path": name, "frames": frames, "bytes": info.file_size,
                         "body_mesh": is_body, "format": low.rsplit(".", 1)[-1]}
                catalogue.append(entry)
    if not catalogue:
        raise RuntimeError("No parseable player MD3/MDC models found in RTCW retail inputs")
    preferred = [x for x in catalogue if x["frames"] > 1]
    preferred.sort(key=lambda x: (not x["body_mesh"], -min(x["bytes"], 2000000),
                                  -x["frames"], x["path"].lower()))
    result = {"selected":preferred[0] if preferred else None,
              "candidate_count":len(catalogue), "animated_count":len(preferred),
              "top_candidates":preferred[:30],
              "static_model_examples":catalogue[:12]}
    (OUT / "MODEL_DISCOVERY.json").write_text(json.dumps(result, indent=2) + "\n")
    if not preferred:
        raise RuntimeError("Player meshes exist but NONE have >1 animation frame; see model discovery")
    MODEL_SELECTION = preferred[0]
    print("PROOF_CHARACTER_SELECTED", MODEL_SELECTION, flush=True)
    return MODEL_SELECTION["path"]


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
        "test_model_distance_units":55, "renderer_source_changes_for_closeup":False,
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
    ab.main()
    analyze_character(OUT)


if __name__ == "__main__":
    main()
