#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "source")
p = root / "SP/code/rend2/tr_scene.c"
if not p.is_file():
    raise SystemExit(f"missing {p}")
s = p.read_text(encoding="utf-8")
mark = "DARKWOLF_ASSAULT_PROOF_SUN_PROBE_V1"
if mark in s:
    print("assault proof sun probe already applied")
    raise SystemExit(0)

old = '''\tVectorCopy(tr.sunDirection, tr.refdef.sunDir);\n'''
new = '''\t// DARKWOLF_ASSAULT_PROOF_SUN_PROBE_V1: isolated TestLab telemetry only.\n\t{\n\t\tstatic int assaultProofSunPrinted = 0;\n\t\tif (!assaultProofSunPrinted && tr.world)\n\t\t{\n\t\t\tri.Printf(PRINT_ALL,\n\t\t\t\t"ASSAULT_PROOF_SUN map=%s dir=%.7f,%.7f,%.7f light=%.3f,%.3f,%.3f\\n",\n\t\t\t\ttr.world->baseName,\n\t\t\t\ttr.sunDirection[0], tr.sunDirection[1], tr.sunDirection[2],\n\t\t\t\ttr.sunLight[0], tr.sunLight[1], tr.sunLight[2]);\n\t\t\tassaultProofSunPrinted = 1;\n\t\t}\n\t}\n\n\tVectorCopy(tr.sunDirection, tr.refdef.sunDir);\n'''
n = s.count(old)
if n != 1:
    raise SystemExit(f"sun probe anchor count={n}")
p.write_text(s.replace(old,new,1),encoding="utf-8",newline="\n")
print("DARKWOLF_ASSAULT_PROOF_SUN_PROBE_V1 applied")
