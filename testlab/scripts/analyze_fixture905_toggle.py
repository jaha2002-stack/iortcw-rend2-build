#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: analyze_fixture905_toggle.py LOG OUT")

lines = Path(sys.argv[1]).read_text(errors="replace").splitlines()

begin_re = re.compile(r"TESTLAB_CAPTURE_BEGIN index=(\d+)")
done_re = re.compile(r"TESTLAB_CAPTURE_DONE index=(\d+)")
marker_re = re.compile(
    r"TESTLAB_SHADOW_ELIGIBILITY map=escape1 fixture=905 capture=(-?\d+) exclude905=([01])"
)
direct_re = re.compile(
    r"SPR_FIXV1_FRAME map=escape1 entity=905\b.*sourceRoute=promoted\b.*addedDlightIndex=(-?\d+)"
)
group_re = re.compile(r"USLRD_SHADOW_GROUP slot=\d+ group=(\d+)\b")
phase_re = re.compile(
    r"TESTLAB_TABLE_PHASE label=(front|side) budget=3 exclude905=([01]) repeat=([01]) "
    r"capture=(\d+) state=(BEGIN|READY|DONE)"
)

captures = {
    idx: {
        "capture": idx,
        "markers": [],
        "direct905_indices": [],
        "shadow_groups": [],
        "phases": [],
    }
    for idx in range(120, 128)
}

current = None
for line in lines:
    m = begin_re.search(line)
    if m:
        current = int(m.group(1))

    m = marker_re.search(line)
    if m:
        idx = int(m.group(1))
        if idx in captures:
            captures[idx]["markers"].append(int(m.group(2)))

    m = phase_re.search(line)
    if m:
        idx = int(m.group(4))
        if idx in captures:
            captures[idx]["phases"].append(
                {
                    "label": m.group(1),
                    "exclude905": int(m.group(2)),
                    "repeat": int(m.group(3)),
                    "state": m.group(5),
                }
            )

    if current in captures:
        m = direct_re.search(line)
        if m:
            captures[current]["direct905_indices"].append(int(m.group(1)))
        m = group_re.search(line)
        if m:
            captures[current]["shadow_groups"].append(int(m.group(1)))

    m = done_re.search(line)
    if m and current == int(m.group(1)):
        current = None

expected = {
    120: ("front", 0, 0),
    121: ("front", 1, 0),
    122: ("front", 0, 1),
    123: ("front", 1, 1),
    124: ("side", 0, 0),
    125: ("side", 1, 0),
    126: ("side", 0, 1),
    127: ("side", 1, 1),
}

failures = []
rows = []
for idx in range(120, 128):
    row = captures[idx]
    label, exclude905, repeat = expected[idx]
    marker_ok = exclude905 in row["markers"]
    direct_ok = any(x >= 0 for x in row["direct905_indices"])
    group905_present = 905 in row["shadow_groups"]
    group918_present = 918 in row["shadow_groups"]
    phase_states = {
        p["state"]
        for p in row["phases"]
        if p["label"] == label
        and p["exclude905"] == exclude905
        and p["repeat"] == repeat
    }
    phase_ok = {"BEGIN", "READY", "DONE"}.issubset(phase_states)
    shadow_gate_ok = (group905_present if exclude905 == 0 else not group905_present)

    if not marker_ok:
        failures.append(f"capture {idx}: missing exclude905={exclude905} eligibility marker")
    if not direct_ok:
        failures.append(f"capture {idx}: fixture 905 direct dlight disappeared")
    if not group918_present:
        failures.append(f"capture {idx}: retained fixture 918 shadow group missing")
    if not shadow_gate_ok:
        failures.append(
            f"capture {idx}: fixture 905 shadow group gate mismatch "
            f"(exclude905={exclude905}, group905_present={group905_present})"
        )
    if not phase_ok:
        failures.append(f"capture {idx}: incomplete deterministic A/B phase markers")

    rows.append(
        {
            "capture": idx,
            "view": label,
            "repeat": repeat,
            "exclude905": exclude905,
            "marker_ok": marker_ok,
            "direct905_present": direct_ok,
            "group905_present": group905_present,
            "group918_present": group918_present,
            "phase_ok": phase_ok,
            "shadow_groups": sorted(set(row["shadow_groups"])),
        }
    )

result = {
    "schema": 2,
    "test": "escape1_fixture905_shadow_only_ab",
    "production_shadow_budget": 3,
    "captures": rows,
    "failures": failures,
    "status": "PASS" if not failures else "FAIL",
}
Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
if failures:
    raise SystemExit(1)
