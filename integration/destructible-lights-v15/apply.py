#!/usr/bin/env python3
from pathlib import Path
import sys

src=Path(sys.argv[1] if len(sys.argv)>1 else "source")
code=src/"SP"/"code"
g=code/"game"/"g_destructible_lights_v1.inc"
c=code/"cgame"/"cg_ents.c"

for p in (g,c):
    if not p.exists():
        raise SystemExit(f"missing {p}")

gt=g.read_text()
ct=c.read_text()

# V1.4 used density as a 32-bit magic field. In RTCW network protocol density
# is NETF(...,10), so the magic was truncated in snapshots and cgame never saw it.
# Move the discriminator to effect3Time, which is transmitted as full 32 bits.
repls=[
    ("e->s.density = DW_DLV14_SWITCH_MAGIC;", "e->s.density = 0;\n    e->s.effect3Time = DW_DLV14_SWITCH_MAGIC;"),
    ("e->s.density=DW_DLV14_LAMP_MAGIC;", "e->s.density=0;\n    e->s.effect3Time=DW_DLV14_LAMP_MAGIC;"),
]
for a,b in repls:
    if a not in gt:
        raise SystemExit("game marker anchor missing: "+a)
    gt=gt.replace(a,b)

if "if (s1->density == DW_DLV14_SWITCH_MAGIC)" not in ct:
    raise SystemExit("cgame switch marker anchor missing")
ct=ct.replace("if (s1->density == DW_DLV14_SWITCH_MAGIC)",
              "if (s1->effect3Time == DW_DLV14_SWITCH_MAGIC)")

if "if (s1->density == DW_DLV14_LAMP_MAGIC)" not in ct:
    raise SystemExit("cgame lamp marker anchor missing")
ct=ct.replace("if (s1->density == DW_DLV14_LAMP_MAGIC)",
              "if (s1->effect3Time == DW_DLV14_LAMP_MAGIC)")

# Add one-time proof prints for actual snapshot receipt, not just model registration.
old="""    if (s1->effect3Time == DW_DLV14_SWITCH_MAGIC) {
        qhandle_t h = CG_DLV14_GetSwitchModel(s1->effect1Time, s1->effect2Time ? 1 : 0);
"""
new="""    if (s1->effect3Time == DW_DLV14_SWITCH_MAGIC) {
        static qboolean printedSwitchSnapshot;
        qhandle_t h;
        if (!printedSwitchSnapshot) {
            printedSwitchSnapshot=qtrue;
            CG_Printf("DW_DLV15 SWITCH_SNAPSHOT ent=%d type=%d state=%d origin=(%.1f %.1f %.1f)\\n",
                s1->number,s1->effect1Time,s1->effect2Time,
                cent->lerpOrigin[0],cent->lerpOrigin[1],cent->lerpOrigin[2]);
        }
        h = CG_DLV14_GetSwitchModel(s1->effect1Time, s1->effect2Time ? 1 : 0);
"""
if old not in ct:
    raise SystemExit("switch custom block anchor missing")
ct=ct.replace(old,new,1)

old="""    if (s1->effect3Time == DW_DLV14_LAMP_MAGIC) {
        /*
"""
new="""    if (s1->effect3Time == DW_DLV14_LAMP_MAGIC) {
        static qboolean printedLampSnapshot;
        if (!printedLampSnapshot) {
            printedLampSnapshot=qtrue;
            CG_Printf("DW_DLV15 LAMP_SNAPSHOT ent=%d type=%d state=%d origin=(%.1f %.1f %.1f)\\n",
                s1->number,s1->effect1Time,s1->effect2Time,
                cent->lerpOrigin[0],cent->lerpOrigin[1],cent->lerpOrigin[2]);
        }
        /*
"""
if old not in ct:
    raise SystemExit("lamp custom block anchor missing")
ct=ct.replace(old,new,1)

g.write_text(gt)
c.write_text(ct)
print("DW_DESTRUCTIBLE_LIGHTS_V15_NETWORK_VISUAL_APPLY_PASS")
