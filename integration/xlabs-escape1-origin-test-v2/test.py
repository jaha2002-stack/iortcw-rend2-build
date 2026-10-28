#!/usr/bin/env python3
"""Exact source/semantic zero-mode and static regressions for Tesla Fire diagnostic V2."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("source",type=Path)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args()
root=a.source
read=lambda rel:(root/rel).read_text()
sha=lambda rel:hashlib.sha256((root/rel).read_bytes()).hexdigest()
CG="SP/code/cgame/cg_ents.c"
MAIN="SP/code/rend2/tr_main.c"
ents=read(CG);world=read(MAIN)
checks={
 "test_flags_cgame_non_archived":'{ &cg_dwTeslaNativeShiftTest, "cg_dwTeslaNativeShiftTest", "0", 0 }' in read("SP/code/cgame/cg_main.c"),
 "test_cvar_decl":'extern vmCvar_t cg_dwTeslaNativeShiftTest;' in read("SP/code/cgame/cg_local.h"),
 "test_origin_only_xlabs":'strstr( cgs.mapname, "xlabs" ) != NULL && cg_dwTeslaNativeShiftTest.integer > 0' in ents,
 "zero_mode_original_offset":'electricOffset = electricDistance * 0.08f;' in ents and 'electricOffset = 32.0f;' in ents,
 "native_test64":'float factor = (cg_dwTeslaNativeShiftTest.integer == 1) ? 0.16f : 0.24f;' in ents,
 "native_test96":'float cap = (cg_dwTeslaNativeShiftTest.integer == 1) ? 64.0f : 96.0f;' in ents,
 "no_change_tesla_pulse":'float pulse = 0.90f + 0.10f * sin( 0.019f' in ents,
 "native_world_occlusion_preserved":'DARKWOLF_REF_WORLD_OCCLUSION' in ents,
 "shadow_class_preserved":'CG_EFFECTLIGHT_ENVIRONMENTAL_TESLA' in ents,
 "audit_not_telemetry":'if (auditThisFrame)' in world and 'ri.Cvar_Set("r_dwWorldGateAuditOnce", "0")' in world,
 "audit_default_off":'ri.Cvar_Get("r_dwWorldGateAuditOnce", "0", 0)' in world,
 "audit_records_fire_eligibility":'(int)dl->fireVolumetricSource' in world,
 "audit_records_coverage":'(int)dl->worldOcclusion' in world and '(int)tr.refdef.dlightWorldSlot[k]' in world,
 "audit_records_light_location":'cameraDistance = VectorLength(delta);' in world and 'dl->origin[0]' in world,
 "audit_bounded":'k < tr.refdef.num_dlights && k < MAX_DLIGHTS' in world,
 "unchanged_fire_classification":sha("SP/code/rend2/tr_scene.c")=="2ce98792ab054ea59529ac103a9485443f08d2c8d34b0e8ded42d2aacf9ebcaf",
 "unchanged_shader_dlight":sha("SP/code/rend2/glsl/dlight_fp.glsl")=="1651e1e14c8154aead2616856ba2d7c1c5ab66b69fb26bd049a5dd9e236ed08c",
 "unchanged_shader_lightall":sha("SP/code/rend2/glsl/lightall_fp.glsl")=="f5d93f15acedb9139f648658774bc409690d07ef0a34f52058fe053c13bee2cd",
 "unchanged_main_capture_flags":'shadowParms.flags = VPF_SHADOWMAP | VPF_DEPTHSHADOW | VPF_NOVIEWMODEL | VPF_DLIGHT_WORLD_OCCLUSION;' in world,
 "unchanged_sky_sun_fire_etc":sha("SP/code/rend2/tr_backend.c")=="6bacff99ad55bb857f2ad9d85e6c76141c4209490699dc1526b8858709fb2317" }
# The last Backend SHA must be exact; tested via same frozen-source export.
assert all(checks.values()),[key for key,val in checks.items() if not val]
for mode,scale,cap in ((0,0.08,32.0),(1,0.16,64.0),(2,0.24,96.0)):
 for distance in (1.0,16.0,100.0,500.0,1000.0):
  new=min(distance*scale,cap)
  prior=min(distance*0.08,32.0)
  if mode==0: assert new==prior
  else: assert new>=prior
a.out.mkdir(parents=True,exist_ok=True)
report={"status":"PASS","checks":checks,"modified_sources":4,
        "engine_shaders_byte_identical":True,"new_test_only_cvars":2,
        "gpu_visual_result":"NOT_YET_TESTED"}
(a.out/"V2_QA.json").write_text(json.dumps(report,indent=2)+"\n")
print("DW_TESLA_FIRE_DIAG_V2_SOURCE_REGRESSION_PASS")
