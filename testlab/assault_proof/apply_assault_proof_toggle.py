#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "source")
p=root/"SP/code/rend2/tr_backend.c"
if not p.is_file():
    raise SystemExit(f"missing {p}")
s=p.read_text(encoding="utf-8")
mark="DARKWOLF_ASSAULT_PROOF_AA_TOGGLE_V1"
if mark in s:
    print("Assault proof AA toggle already applied")
    raise SystemExit(0)

# TestLab-only A/B switch around the already validated v4.4.3 production path.
# 0 = exact v4.4.2 composite fallback, 1 = v4.4.3 coverage-aware reconstruction.
sun_old='''\tif (tr.volumetricFullresFbo && tr.volumetricLocalUpscaleShader.program)\n\t{\n'''
sun_new='''\t// DARKWOLF_ASSAULT_PROOF_AA_TOGGLE_V1\n\tif (ri.Cvar_VariableIntegerValue("r_assaultProofVolumetricAA") != 0 &&\n\t\ttr.volumetricFullresFbo && tr.volumetricLocalUpscaleShader.program)\n\t{\n'''
if s.count(sun_old) != 1:
    raise SystemExit(f"Sun production branch count={s.count(sun_old)}")
s=s.replace(sun_old,sun_new,1)

local_old='''\t\tif (tr.volumetricFullresFbo && tr.volumetricLocalUpscaleShader.program &&\n\t\t\t((mode >= 1 && mode <= 3) || reconstructionMode > 0))\n'''
local_new='''\t\tif (ri.Cvar_VariableIntegerValue("r_assaultProofVolumetricAA") != 0 &&\n\t\t\ttr.volumetricFullresFbo && tr.volumetricLocalUpscaleShader.program &&\n\t\t\t((mode >= 1 && mode <= 3) || reconstructionMode > 0))\n'''
if s.count(local_old)!=1:
    raise SystemExit(f"Local production branch count={s.count(local_old)}")
s=s.replace(local_old,local_new,1)

p.write_text(s,encoding="utf-8",newline="\n")
print("DARKWOLF_ASSAULT_PROOF_AA_TOGGLE_V1 applied")
