#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("evidence")
OUT.mkdir(parents=True, exist_ok=True)

MAPS = ("swf", "rocket")
ASSET_TERMS = (
    "gas", "tank", "cylinder", "canister", "bottle", "radio", "rocket",
    "barrel", "alarm", "plane", "m109", "vehicle", "fuel", "oxygen",
)
VALUE_TERMS = (
    "rocket", "missile", "launch", "gas", "tank", "cylinder", "canister",
    "radio", "elevator", "lift", "barrel", "alarm", "explode", "explosive",
)
CLASS_TERMS = (
    "func_explosive", "target_effect", "script_mover", "misc_gamemodel",
    "props_", "alarm_box", "func_button", "target_relay", "target_script",
)


def parse_entities(blob: bytes):
    if len(blob) < 16 or blob[:4] != b"IBSP":
        raise RuntimeError("not an IBSP file")
    ent_ofs, ent_len = struct.unpack_from("<ii", blob, 8)
    raw = blob[ent_ofs:ent_ofs + ent_len].split(b"\0", 1)[0]
    text = raw.decode("latin1", errors="replace")
    entities = []
    for idx, block in enumerate(re.findall(r"\{(.*?)\}", text, flags=re.S)):
        pairs = re.findall(r'"([^"]*)"\s+"([^"]*)"', block)
        ent = {k: v for k, v in pairs}
        ent["__index"] = idx
        entities.append(ent)
    return text, entities


def interesting(ent):
    cls = ent.get("classname", "").lower()
    if any(t in cls for t in CLASS_TERMS):
        return True
    for key in ("model", "model2", "target", "targetname", "scriptname", "scriptName", "message"):
        val = ent.get(key, "").lower()
        if any(t in val for t in VALUE_TERMS):
            return True
    joined = " ".join(str(v).lower() for k, v in ent.items() if k != "__index")
    return any(t in joined for t in VALUE_TERMS)


pk3s = sorted([p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() == ".pk3"])
if not pk3s:
    raise SystemExit(f"ERROR: no pk3 files found under {ROOT}")

inventory = []
map_sources = {}
model_assets = []
script_candidates = []

for pk3 in pk3s:
    with zipfile.ZipFile(pk3) as zf:
        names = zf.namelist()
        lower = {n.lower(): n for n in names}
        inventory.append({"pk3": str(pk3), "files": len(names)})

        for mapname in MAPS:
            want = f"maps/{mapname}.bsp"
            if want in lower and mapname not in map_sources:
                actual = lower[want]
                blob = zf.read(actual)
                entity_text, entities = parse_entities(blob)
                map_sources[mapname] = {
                    "pk3": str(pk3),
                    "path": actual,
                    "entity_text": entity_text,
                    "entities": entities,
                }

        for n in names:
            ln = n.lower()
            if ln.endswith((".md3", ".mdc")) and any(t in ln for t in ASSET_TERMS):
                model_assets.append({"pk3": pk3.name, "path": n})
            if ln.endswith(".script") and ("swf" in ln or "rocket" in ln):
                try:
                    txt = zf.read(n).decode("latin1", errors="replace")
                except Exception:
                    continue
                script_candidates.append({"pk3": pk3.name, "path": n, "text": txt})

for mapname in MAPS:
    if mapname not in map_sources:
        raise SystemExit(f"ERROR: maps/{mapname}.bsp not found in retail pk3 set")

for mapname, data in map_sources.items():
    all_entities = data["entities"]
    filt = [e for e in all_entities if interesting(e)]
    (OUT / f"{mapname}-entities-all.json").write_text(
        json.dumps(all_entities, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT / f"{mapname}-entities-interesting.json").write_text(
        json.dumps(filt, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT / f"{mapname}-entity-lump.txt").write_text(data["entity_text"], encoding="latin1")

(OUT / "retail-model-assets.json").write_text(
    json.dumps(model_assets, indent=2, ensure_ascii=False), encoding="utf-8"
)
(OUT / "pk3-inventory.json").write_text(
    json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8"
)
for i, s in enumerate(script_candidates):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", s["path"])
    (OUT / f"script-{i:02d}-{safe}").write_text(s["text"], encoding="latin1")

summary = {
    "maps": {
        m: {
            "pk3": map_sources[m]["pk3"],
            "path": map_sources[m]["path"],
            "entity_count": len(map_sources[m]["entities"]),
            "interesting_count": sum(1 for e in map_sources[m]["entities"] if interesting(e)),
        }
        for m in MAPS
    },
    "model_asset_matches": len(model_assets),
    "script_candidates": [{"pk3": s["pk3"], "path": s["path"]} for s in script_candidates],
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
