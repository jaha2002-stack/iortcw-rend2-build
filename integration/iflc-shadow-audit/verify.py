#!/usr/bin/env python3
"""Verify causal controls and measure original screenshots; no visual PASS."""
import argparse
import json
import math
from pathlib import Path
import re


def verify(out):
    from PIL import Image
    import numpy as np
    capture = json.loads((out / "IFLC_SHADOW_AUDIT_CAPTURE.json").read_text())
    logs = sorted(out.glob("console-*.log"))
    text = "\n".join(p.read_text(errors="replace") for p in logs)
    shots, view = capture["shots"], capture["view"]
    states, proof, cvars, hooks = {}, {}, {}, {}
    current = None
    for line in text.splitlines():
        match = re.search(r"IFLC_STATE (\S+) (\S+)", line)
        if match:
            current = states.setdefault(match[2], {"view": match[1]})
        match = re.search(r"IFLC: map=crypt1 bsp=([0-9a-f]+) key=(\S+) route=(\S+) anchor=\(([^)]+)\)", line)
        if match and current is not None:
            current.update(bsp=match[1], key=match[2], route=match[3], anchor=list(map(float, match[4].split())))
        match = re.search(r"IFLC: editable=(\S+) realDlights=(\d+) baseRadius=([\d.]+) currentRadius=([\d.]+) worldContainment=(\d+)", line)
        if match and current is not None:
            current.update(editable=match[1], real_dlights=int(match[2]), base_radius=float(match[3]), radius_world=float(match[4]), containment=int(match[5]))
        match = re.search(r"IFLC: direct=([\d.]+) radius=([\d.]+) volume=([\d.]+) enabled=(\d+) colorOverride=(\d+) master=(\d+)", line)
        if match and current is not None:
            current.update(direct=float(match[1]), radius_gain=float(match[2]), volume=float(match[3]), enabled=int(match[4]), master=int(match[6]))
        match = re.search(r"zone=1 name=IFLC_runtime mode=(\S+) baked=([\d.]+) surfaces=(\d+)", line)
        if match and current is not None:
            current.update(baked=float(match[2]), baked_surfaces=int(match[3]))
        match = re.search(r"PROOF_VIEW shot=(\d+) time=(\d+) eye=([\d.,-]+) forward=([\d.,-]+)", line)
        if match:
            proof[int(match[1])] = {"time": int(match[2]), "eye": list(map(float, match[3].split(","))), "forward": list(map(float, match[4].split(",")))}
            current = None
        match = re.search(r"PROOF_CVAR shot=(\d+) name=(\S+) value=(\S+)", line)
        if match:
            cvars.setdefault(int(match[1]), {})[match[2]] = match[3]
        match = re.search(r"IFLC_SHADOW_AUDIT (.+)", line)
        if match:
            fields = dict(re.findall(r"(\w+)=([^\s]+)", match[1]))
            if "shot" in fields and "kind" in fields:
                hooks.setdefault(int(fields["shot"]), {})[fields["kind"]] = fields
    faults, records, images = [], [], {}
    expected_origins = {"optin": [-224.5, 1544.5, 552.0], "native291": [-152.0, 1668.0, 636.0]}
    expected_cvars = {"r_ssgi": 1, "r_volumetricSun": 1, "r_volumetricLocal": 1,
                      "r_volumetricFire": 1, "r_volumetricFireV07Mode": 2,
                      "r_volumetricFireSourceMode": 2, "r_volumetricFireMode": 2,
                      "r_volumetricFireMaxActive": 8, "r_volumetricFireSamples": 40,
                      "r_dlightShadowMaxLights": 3, "r_dlightWorldContainment": 2,
                      "r_dlightShadowStrength": .88, "r_dwFireLightControl": 1,
                      "r_ext_framebuffer_multisample": 4, "r_hdr": 1, "r_postProcess": 1,
                      "r_mapLightingLearn": 1, "cg_drawGun": 0}
    native_colors, native_radii = set(), set()
    for shot in shots:
        label, index = shot["variant"], shot["id"]
        state = states.get(label, {})
        camera = proof.get(index, {})
        control = cvars.get(index, {})
        received = hooks.get(index, {})
        def require(condition, detail):
            if not condition:
                faults.append(f"shot {index} {label}: {detail}")
        require(state.get("bsp") == "dffbf243" and state.get("key") == "surface:2992:711b28d1:6de6bac8" and state.get("route") == "VOLUME_ONLY", "selected source identity")
        require(state.get("real_dlights") == 1 and state.get("containment") == 1 and state.get("enabled") == 1 and state.get("master") == 1, "active single opt-in with containment")
        require(state.get("base_radius") == 205 and state.get("radius_world") == 205 and state.get("radius_gain") == 1, "fixed physical radius")
        require(state.get("direct") == shot["direct"] and state.get("volume") == shot["volume"], "direct/volume controls")
        require(state.get("baked") == shot["baked"] and state.get("baked_surfaces", 0) > 0, "MapLighting zone scale")
        require("eye" in camera and math.dist(camera["eye"], view["eye"]) < .002, "camera eye")
        pitch, yaw = map(math.radians, view["angles"][:2])
        forward = [math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), -math.sin(pitch)]
        require("forward" in camera and math.dist(camera["forward"], forward) < .002, "camera direction")
        for name, value in {**expected_cvars, "r_iflcShadowAudit": shot["flags"]}.items():
            try:
                valid = abs(float(control.get(name, "nan")) - value) < .0001
            except ValueError:
                valid = False
            require(valid, f"cvar {name}={value}")
        for kind, origin in expected_origins.items():
            hook = received.get(kind, {})
            require(bool(hook), f"missing actual receiver draw for {kind}")
            if not hook:
                continue
            flags = shot["flags"]
            zero = bool(flags & 64 or flags & (8 if kind == "optin" else 4))
            require(int(hook["flags"]) == flags and float(hook["gain"]) == (0 if zero else 1), f"{kind} actual RGB gain")
            require(int(hook["worldBypass"]) == bool(flags & (1 if kind == "optin" else 16)), f"{kind} world bypass")
            require(int(hook["ordinaryBypass"]) == bool(flags & (2 if kind == "optin" else 32)), f"{kind} ordinary bypass")
            require(math.dist(list(map(float, hook["origin"].split(","))), origin) < .002, f"{kind} physical origin")
            if kind == "optin":
                require(float(hook["radius"]) == 205 and int(hook["sourceWorld"]) == 1 and int(hook["worldSlot"]) >= 0, "opt-in original world capture available")
                require(math.dist(list(map(float, hook["color"].split(","))), [shot["direct"] * v for v in (1, .52, .16)]) < .00002, "opt-in struct RGB unchanged by diagnostic mask")
            else:
                require(int(hook["nativeOrdinal"]) == 291, "native ordinal")
                native_colors.add(hook["color"])
                native_radii.add(hook["radius"])
        path = out / (shot["name"] + ".png")
        require(path.is_file(), "original screenshot missing")
        if path.is_file():
            array = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
            require(array.shape == (540, 960, 3), "capture dimensions")
            images[index] = array
        records.append({"shot": shot, "state": state, "camera": camera, "cvars": control, "receiver_hooks": received})
    if len({v.get("time") for v in proof.values()}) != 1:
        faults.append("Client time is not frozen across the full matrix")
    if len(native_colors) != 1 or len(native_radii) != 1:
        faults.append("Native291 structure RGB/radius not invariant across the matrix")
    scans = re.findall(r"FIREVOL07_SCAN map=crypt1 variant=C_RENDERED_MULTI .*?selected=(\d+) rendered=(\d+)", text)
    if not any(int(a) > 0 and int(b) > 0 for a, b in scans):
        faults.append("No production FireVol render confirmation")
    for field in ("ready", "complete"):
        if not capture.get(field):
            faults.append("Capture did not report " + field)
    if capture.get("exit") != 0 or len(images) != len(shots):
        faults.append("Incomplete process/screenshots")

    rois = {"small_spot_and_near_fixture": [430, 399, 552, 471],
            "large_shadow_left_wing": [350, 390, 405, 450],
            "large_shadow_below_spot": [350, 490, 430, 530],
            "lit_wall_reference": [560, 350, 650, 450]}
    pairs, seen = [], set()
    def compare(a, b, purpose):
        if not a or not b or a["id"] not in images or b["id"] not in images:
            return
        key = (a["id"], b["id"])
        if key in seen:
            return
        seen.add(key)
        delta = np.abs(images[a["id"]] - images[b["id"]])
        def metrics(d):
            return {"changed_pixels": int(np.any(d > 0, axis=2).sum()),
                    "pixels_above_2": int(np.any(d > 2, axis=2).sum()),
                    "mean_abs_rgb": float(d.mean()), "max_abs_rgb": int(d.max())}
        pairs.append({"a": a["variant"], "b": b["variant"], "purpose": purpose,
                      "full_frame": metrics(delta),
                      "rois": {name: metrics(delta[y0:y1, x0:x1]) for name, (x0, y0, x1, y1) in rois.items()}})
    def find(flags, baked=.2, direct=3, volume=0):
        return next((s for s in shots if all(s[k] == v for k, v in {"flags": flags, "baked": baked, "direct": direct, "volume": volume}.items())), None)
    for flags, purpose in ((1, "Opt-in world visibility"), (2, "Opt-in ordinary visibility"),
                           (3, "Both opt-in visibility paths"), (4, "Native291 receiver contribution"),
                           (8, "Opt-in receiver contribution"), (12, "Both target receiver contributions")):
        compare(find(0), find(flags), purpose)
    compare(find(8), find(56), "Native291 both shadow paths; opt-in receiver off")
    compare(find(8), find(64), "Other Direct receivers with opt-in receiver off")
    for flags in (0, 3, 8, 12, 64):
        compare(find(flags), find(flags, baked=0), "Lightmap contribution with fixed receiver controls")
    groups = {}
    for shot in shots:
        key = tuple(shot[k] for k in ("flags", "baked", "direct", "volume"))
        if key in groups:
            compare(groups[key], shot, "Repeated controls: temporal/restore drift")
        else:
            groups[key] = shot
    points = {"large_left": [385, 400], "large_below": [400, 500], "small_center": [450, 440], "lit_wall": [580, 400]}
    pixels = {shot["variant"]: {name: images[shot["id"]][y, x].tolist() for name, (x, y) in points.items()}
              for shot in shots if shot["id"] in images}
    report = {"status": "CONTROLS_VERIFIED_PENDING_VISUAL_CAUSAL_REVIEW" if not faults else "CONTROL_VERIFICATION_FAILED",
              "environment": "Linux Mesa llvmpipe real retail Crypt1, native diagnostic instrumentation",
              "visual_acceptance": "NOT_ASSESSED_BY_THIS_SCRIPT", "faults": faults,
              "records": records, "firevol_scan_count": len(scans), "roi_coordinates_xyxy": rois,
              "comparisons": pairs, "pixel_points_xy": points, "pixel_samples_rgb": pixels,
              "limitations": ["Receiver hook logs the first draw after the warmed state gets its shot id, not the screenshot frame.",
                              "RGB0 and bypass do not remove lights or change capture/selection; model aggregate lighting remains.",
                              "Bypass request is meaningful only when the corresponding original capture is available.",
                              "SSGI settings stay enabled; its result can respond to changed scene color.",
                              "A dark image at baked0 does not prove the small mark is baked. Review the illuminated baked0/both-bypass pair and ROI coverage.",
                              "Pixels are measurement evidence, not an automatic judgment of shadow correctness."]}
    (out / "IFLC_SHADOW_AUDIT_VERIFICATION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "frames": len(images), "faults": faults}, indent=2), flush=True)
    assert not faults, "Diagnostic controls not verified"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    verify(args.output.resolve())
