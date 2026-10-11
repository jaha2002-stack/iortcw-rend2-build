#!/usr/bin/env python3
"""Factory tunnel SSGI A/B. Read real spawn state and retail BSP light origins.
Creates equal-camera screenshots for SSGI OFF, ON, requested mode1 and control mode2.
Never treats a speculative lamp origin or a screenshot filename as a gameplay PASS.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import struct
import zipfile
from pathlib import Path

def spawn_from_log(path: Path):
    text = path.read_text(errors="replace")
    m = re.search(r"TESTLAB_VIEW_STATE index=800 origin=([-+0-9.eE,]+) angles=([-+0-9.eE,]+)", text)
    if not m:
        raise SystemExit("FACTORY_PROBE_FAILED: TESTLAB_VIEW_STATE index=800 absent")
    return tuple(map(float, m.group(1).split(","))), tuple(map(float, m.group(2).split(",")))

def bsp_entities(main: Path):
    for pk3 in sorted(main.glob("*")):
        if pk3.suffix.lower() != ".pk3":
            continue
        with zipfile.ZipFile(pk3) as z:
            matches = [n for n in z.namelist() if n.lower() == "maps/factory.bsp"]
            if not matches:
                continue
            bsp = z.read(matches[0])
            if len(bsp) < 16 or bsp[:4] != b"IBSP":
                raise SystemExit("FACTORY_BSP_FAILED: invalid IBSP")
            off, length = struct.unpack_from("<ii", bsp, 8)
            if off < 0 or length <= 0 or off + length > len(bsp):
                raise SystemExit("FACTORY_BSP_FAILED: entity lump outside file")
            text = bsp[off:off + length].decode("latin-1", errors="replace")
            rows = []
            for number, match in enumerate(re.finditer(r"\{([^{}]*)\}", text, re.S)):
                d = dict(re.findall(r'"([^"]+)"\s*"([^"]*)"', match.group(1)))
                classname = d.get("classname", "").lower()
                if "light" not in classname or classname.startswith("target_"):
                    continue
                coords = d.get("origin", "").replace(",", " ").split()
                if len(coords) != 3:
                    continue
                try:
                    xyz = tuple(float(x) for x in coords)
                except ValueError:
                    continue
                rows.append({"entity": number, "class": classname, "origin": xyz, "targetname": d.get("targetname", "")})
            print("FACTORY_BSP_FOUND", pk3.name, "entities", len(rows))
            return rows
    raise SystemExit("FACTORY_BSP_NOT_FOUND: maps/factory.bsp absent from protected assets")

def candidate_lamps(spawn, entities, limit=2):
    x, y, z = spawn
    rows = []
    for e in entities:
        lx, ly, lz = e["origin"]
        planar = math.hypot(lx - x, ly - y)
        height = lz - (z + 52)
        if planar > 800 or height < -32 or height > 280:
            continue
        # Lamps above the starting tunnel are prioritized; don't presume all lights are visible.
        score = planar + abs(height - 75) * 0.45
        rows.append((score, e, planar, height))
    rows.sort(key=lambda t: t[0])
    return [dict(e, distanceXY=round(dist, 1), heightAboveEye=round(h, 1))
            for _, e, dist, h in rows[:limit]]

def view_toward(origin, target):
    x, y, z = origin
    tx, ty, tz = target
    dx, dy, dz = tx - x, ty - y, tz - (z + 52.0)
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = -math.degrees(math.atan2(dz, max(math.hypot(dx, dy), 0.001)))
    return pitch, yaw

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--main", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()
    origin, angles = spawn_from_log(args.log)
    lamps = candidate_lamps(origin, bsp_entities(args.main))
    manifest = {"schema": 1, "map": "factory", "spawn_origin": origin, "spawn_angles": angles,
                "lighting_candidates": lamps, "screenshots": [], "verified_lamp_visual": False,
                "notes": "BSP light entity coordinates are candidate aim points, not optical/visibility confirmation."}
    # VISUAL CALIBRATION V2: the earlier BSP light targets were off screen.
    # Scan three stable directions centered on the actual tunnel axis. BSP light
    # entity coordinates are retained for provenance but are not assumed visible.
    entries = [
        (f"tunnel_axis_{i:02d}", origin, (-18.0, yaw), None)
        for i, yaw in enumerate((-24.0, 0.0, 24.0))
    ]
    manifest["status"] = "PENDING_TUNNEL_AXIS_VISUAL_REVIEW"
    manifest["notes"] = (
        "Scan along Factory spawn tunnel using yaw -24/0/+24. "
        "Camera orientation is calibrated from the two real pilot screenshots; "
        "visual lamp presence must be verified before accepting any SSGI fix."
    )
    lines = [
        "set developer 1", "set logfile 2",
        "set cg_draw2D 0", "set cg_drawGun 0", "set con_notifytime 0",
        "set r_staticPromoteMaxLights 32", "set r_dlightShadowMaxLights 3",
        "set r_ssgiTrace 1",
        "echo FACTORY_SSGI_REAL_GAMEPLAY_CAPTURE_BEGIN",
    ]
    cases = [
        ("off", ["set r_ssgi 0", "set r_ssgiResolveMode 0", "set r_ssgiRadius 32"]),
        ("on", ["set r_ssgi 1", "set r_ssgiBrightSourceFix 2", "set r_ssgiResolveMode 0", "set r_ssgiRadius 32"]),
        ("requested", ["set r_ssgi 1", "set r_ssgiBrightSourceFix 2", "set r_ssgiResolveMode 1", "set r_ssgiRadius 16"]),
        ("bilateral", ["set r_ssgi 1", "set r_ssgiBrightSourceFix 2", "set r_ssgiResolveMode 2", "set r_ssgiRadius 16"]),
    ]
    for idx, (entry_name, pos, (pitch, yaw), eid) in enumerate(entries):
        px, py, pz = pos
        lines += [
            f"echo FACTORY_VIEW_BEGIN index={idx} name={entry_name} lampEntity={eid}",
            f"dw_testView {px:.3f} {py:.3f} {pz:.3f} {pitch:.3f} {yaw:.3f} 0",
            "wait 10",
            f"dw_testViewState {idx}",
            "wait 4",
        ]
        for case, cv in cases:
            lines += cv
            lines += ["wait 12", f"echo FACTORY_CAPTURE_READY view={idx} case={case}"]
            shot = f"factory_ssgi_{idx:02d}_{case}"
            lines += [f"screenshot {shot}", "wait 5"]
            manifest["screenshots"].append({"name": shot + ".tga", "case": case,
                                            "view": idx, "target_entity": eid,
                                            "eye_target_pitch": round(pitch, 3),
                                            "yaw": round(yaw, 3)})
        lines += [f"echo FACTORY_VIEW_DONE index={idx}", "wait 5"]
    lines += ["echo FACTORY_SSGI_REAL_GAMEPLAY_CAPTURE_COMPLETE", "wait 5", "quit"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n")
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print("FACTORY_CAPTURE_CFG_GENERATED views=", len(entries),
          "cases=", len(cases), "expected_tga=", len(manifest["screenshots"]),
          "target_lamps=", len(lamps))
    print("FACTORY_SPAWN", origin, angles)
    for item in lamps:
        print("FACTORY_LAMP_CANDIDATE", item)

if __name__ == "__main__":
    main()
