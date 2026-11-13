#!/usr/bin/env python3
"""DarkWolf Fire Shadow Motion V1.2: undo unsafe V1.1 world-PCF ray dilation.

Apply on the exact successful V1.1 renderer source derived from Run #43189244002.
The native-fire movement and ordinary point shadow softness remain unchanged.
Only the two world-PCF GLSL implementations are modified.
"""
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1])/"SP/code/rend2"
evidence=Path(sys.argv[2] if len(sys.argv)>2 else "evidence")
evidence.mkdir(parents=True,exist_ok=True)
files={
 "glsl/dlight_fp.glsl":("901a00d83c0b2d2c6fe564653b62b9b1e8bf8c00808519825fa0f5af6b552920","bf16412aba8eb26a14cdd336cc4347d712ec83253b26821ae8348a3a047289f6"),
 "glsl/lightall_fp.glsl":("dbd27055bf161adc760c5b8da71f96b57d696f9ebf427ac396020494506e051e","2e94b61d96ec2049337b08c333466d69df853e1c4b07d599ea74c22441e7cb2e")
}
old="""    // FIRE_SHADOW_MOTION_V11: wider area-source footprint for one tagged
    // native Crypt1 fire. Existing -2.x Tesla/Fire PCF stays unchanged.
    float marker = 2.0;
    float spread = 1.0;
    if (u_DlightWorldOrigin.w < -3.25) { marker = 3.5; spread = 2.65; }
    else if (u_DlightWorldOrigin.w < -2.75) { marker = 3.0; spread = 2.10; }
    else if (u_DlightWorldOrigin.w < -2.25) { marker = 2.5; spread = 1.55; }
    float invRange = -u_DlightWorldOrigin.w - marker;"""
new="""    // FIRE_SHADOW_MOTION_V12: preserve the proven face-correct 4x4 tent PCF.
    // V1.1 enlarged sample directions by 1.55-2.65x on a 256px cubemap;
    // those rays crossed unrelated wall depth discontinuities, creating stripes.
    // Keep distinct markers for safe depth decoding but NEVER dilate samples.
    // Primary DLight PCF is still controlled by r_dwFireShadowSoftness.
    float marker = 2.0;
    if (u_DlightWorldOrigin.w < -3.25) marker = 3.5;
    else if (u_DlightWorldOrigin.w < -2.75) marker = 3.0;
    else if (u_DlightWorldOrigin.w < -2.25) marker = 2.5;
    float invRange = -u_DlightWorldOrigin.w - marker;"""
old2="""            vec2 softSample = samplePos + (unbounded - samplePos) * spread;
            vec2 texel = clamp(softSample, vec2(0.0), vec2(worldSize - 1.0));"""
new2="""            // FIRE_SHADOW_MOTION_V12: sample only the original 4x4 footprint.
            vec2 texel = clamp(unbounded, vec2(0.0), vec2(worldSize - 1.0));"""
proof={}
for rel,(expected,post) in files.items():
    p=root/rel
    raw=p.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    assert digest==expected,(rel,"WRONG_V11_SHADER_SOURCE",digest,expected)
    s=raw.decode("utf-8")
    assert s.count(old)==1,(rel,"PCF_MARKER_BLOCK_COUNT",s.count(old))
    assert s.count(old2)==1,(rel,"PCF_SAMPLE_BLOCK_COUNT",s.count(old2))
    updated=s.replace(old,new,1).replace(old2,new2,1)
    block=updated[updated.index("float DW_TeslaWorldCubeFacePcf4x4("):updated.index("float DlightWorldVisibility(")]
    assert "spread" not in block and "softSample" not in block,rel
    actual=hashlib.sha256(updated.encode("utf-8")).hexdigest()
    assert actual==post,(rel,"WRONG_EXPECTED_V12_SHA",actual,post)
    p.write_text(updated)
    proof[rel]={"sha_v11":digest,"sha_v12":actual}
(evidence/"FSM_V12_PCF_SCOPE_PROOF.json").write_text(json.dumps({
    "base_run":43189244002,"parent_run":43427599566,
    "scope":"two GLSL architectural PCF files only",
    "files":proof,"motion_unchanged":True,"ordinary_shadow_filter_unchanged":True,
    "global_lights_unchanged":True,"new_dlights":0,"visually_gpu_tested":False
},indent=2)+"\n")
print("DW_FSM_V12_FIXED_WORLD_PCF_4X4_TWO_SHADERS_PASS")
