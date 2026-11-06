#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,subprocess,zipfile

OUT=Path("dist"); OUT.mkdir(exist_ok=True)
EV=Path("evidence"); EV.mkdir(exist_ok=True)
sha=lambda b: hashlib.sha256(b).hexdigest()

BASE_RUN=42198541106
BASE_ARTIFACT=13494035208
TEST_RUN=42213574949
TEST_ARTIFACT=13499009635
TEST_COMMIT="34cf998df54d131884132030e495799375bed588"
EXPECTED_BASE_DLL="57da8388945f3f7e9e874d8cd19b886a6e4685ac0457390f8028f176efdfa002"
EXPECTED_TESTED_DLL="0b2ff0b28bbf69ff0df73417866eb330eb204c10b5be5fb0835b98f26797cc2d"

def gh_artifact(artifact_id,path):
    with path.open("wb") as f:
        subprocess.run(
            ["gh","api",f"repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/{artifact_id}/zip"],
            stdout=f,check=True
        )

def inner_zip(wrapper,needle):
    with zipfile.ZipFile(wrapper) as z:
        candidates=[n for n in z.namelist() if n.endswith(".zip") and needle in n]
        assert len(candidates)==1,(wrapper,candidates)
        return z.read(candidates[0])

def entries_from_zip(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        roots={n.split("/",1)[0] for n in z.namelist() if "/" in n}
        assert len(roots)==1,roots
        root=next(iter(roots))
        return root,{n.split("/",1)[1]:z.read(n) for n in z.namelist() if not n.endswith("/")}

base_wrap=EV/"base_42198541106_artifact.zip"
test_wrap=EV/"tested_42213574949_artifact.zip"
gh_artifact(BASE_ARTIFACT,base_wrap)
gh_artifact(TEST_ARTIFACT,test_wrap)

base_raw=inner_zip(base_wrap,"Clean_Production_FireVol_Final")
tested_raw=inner_zip(test_wrap,"ComponentPick_From_42198541106_Win64_TEST")
base_root,base=entries_from_zip(base_raw)
tested_root,tested=entries_from_zip(tested_raw)

assert "renderer_sp_rend2_x64.dll" in base
assert "renderer_sp_rend2_x64.dll" in tested
base_dll=base["renderer_sp_rend2_x64.dll"]
tested_dll=tested["renderer_sp_rend2_x64.dll"]
assert sha(base_dll)==EXPECTED_BASE_DLL,(sha(base_dll),EXPECTED_BASE_DLL)
assert sha(tested_dll)==EXPECTED_TESTED_DLL,(sha(tested_dll),EXPECTED_TESTED_DLL)

# The production binary must be the exact DLL the user visually accepted.
for marker in (
    b"dw_el_select",
    b"dw_el_self_pick",
    b"r_dwElectricLightControl",
    b"ELSS V1.1:",
    b"ownBodyTriangles=",
    b"bound exact compact body surface",
    b"protected surface",
    b"FIREVOL_CLEAN_PRODUCTION",
):
    assert marker in tested_dll,marker
for forbidden in (
    b"ELSS11_TEST_",
    b"dw_el_v11_test_",
    b"ELSS_TEST_",
    b"dw_el_test_",
):
    assert forbidden not in tested_dll,forbidden

# Confirm the tested package itself declares the requested base.
status=json.loads(tested["ELSS_V11_BUILD_STATUS.json"].decode("utf-8"))
assert status["base_run"]==BASE_RUN,status
assert status["base_commit"]=="5ba3e923803674c9acee71600412720a0eeaf81e",status

entries=base.copy()
entries["renderer_sp_rend2_x64.dll"]=tested_dll

readme="""DarkWolf Clean Production Release - ELSS V1.1 Component Pick REFINED
Base: GitHub Run #42198541106 (Clean Production FireVol Final)
Accepted ELSS test: GitHub Run #42213574949

This release uses the exact renderer_sp_rend2_x64.dll binary visually accepted
by the user on Church fixture:107.

Production delta over #42198541106:
- ELSS V1.1 Component Pick.
- Exact compact-housing fallback for a protected/shared BSP surface hit.
- ELSS V1.0.1 restart persistence remains preserved.
- Existing DW_ELSS 1 profiles are readable; new saves use DW_ELSS 2.
- IFLC V1.5 Universal, FireVol Clean Production, Crypt1 Slot6 reanchor,
  Direct light, Local Volumetric and the existing shadow-slot policy are preserved.

No test hooks or test commands are present in the renderer DLL.
No diagnostic cvars are enabled by this package.
No TEST cfg is added.

ELSS workflow remains:
  /r_dwElectricLightControl 1
  /dw_el_select
  /dw_el_self_pick
  /dw_el_set selfshadow 0
  /dw_el_save

Profiles:
  electricshadows/<map>.elss
"""
entries["README_ELSS_V11_COMPONENT_PICK_REFINED_PRODUCTION.txt"]=readme.replace("\n","\r\n").encode("utf-8-sig")

manifest={
    "status":"CLEAN_PRODUCTION",
    "version":"ELSS_V1.1_COMPONENT_PICK_REFINED",
    "base_run":BASE_RUN,
    "base_commit":"5ba3e923803674c9acee71600412720a0eeaf81e",
    "accepted_test_run":TEST_RUN,
    "accepted_test_commit":TEST_COMMIT,
    "accepted_renderer_sha256":sha(tested_dll),
    "user_visual_pass":"Church fixture:107 own-body self-shadow successfully disabled",
    "inherits_elss_v101_persistence":True,
    "profile_read":["DW_ELSS 1","DW_ELSS 2"],
    "profile_write":"DW_ELSS 2",
    "firevol_clean_production_preserved":True,
    "crypt1_slot6_reanchor_preserved":True,
    "iflc_v15u_preserved":True,
    "shadow_slot_policy_preserved":True,
    "direct_light_preserved":True,
    "local_volumetric_preserved":True,
    "other_casters_preserved":True,
    "test_hooks_present":False,
    "diagnostic_defaults_changed":False,
    "package_run":os.environ.get("GITHUB_RUN_ID"),
    "package_commit":os.environ.get("GITHUB_SHA"),
}
entries["ELSS_V11_CLEAN_PRODUCTION_STATUS.json"]=(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n").encode("utf-8")

# Replace package checksum manifest only; inherited payload stays byte-identical.
entries.pop("SHA256SUMS.txt",None)
entries["SHA256SUMS.txt"]="".join(
    sha(b)+"  "+name+"\n" for name,b in sorted(entries.items())
).encode("ascii")

# Strict inheritance proof: everything from #42198541106 is byte-identical
# except renderer and the regenerated checksum file.
changed=[]
for name,b in base.items():
    if name in ("renderer_sp_rend2_x64.dll","SHA256SUMS.txt"):
        continue
    assert entries[name]==b,name
for name in sorted(set(entries)|set(base)):
    if base.get(name)!=entries.get(name):
        changed.append(name)
assert changed==[
    "ELSS_V11_CLEAN_PRODUCTION_STATUS.json",
    "README_ELSS_V11_COMPONENT_PICK_REFINED_PRODUCTION.txt",
    "SHA256SUMS.txt",
    "renderer_sp_rend2_x64.dll",
],changed

root="DarkWolf_Clean_Production_ELSS_V1.1_ComponentPick_REFINED_From_42198541106_Win64"
target=OUT/(root+".zip")
with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,b in sorted(entries.items()):
        z.writestr(root+"/"+name,b)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None

proof={
    "package":str(target),
    "package_sha256":sha(target.read_bytes()),
    "renderer_sha256":sha(tested_dll),
    "base_renderer_sha256":sha(base_dll),
    "base_run":BASE_RUN,
    "accepted_test_run":TEST_RUN,
    "tested_artifact_wrapper_sha256":sha(test_wrap.read_bytes()),
    "changed_vs_base":changed,
    "base_file_count":len(base),
    "production_file_count":len(entries),
}
(EV/"CLEAN_PRODUCTION_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n")
(OUT/"SHA256SUMS.txt").write_text(
    proof["package_sha256"]+"  "+target.name+"\n"+
    proof["renderer_sha256"]+"  renderer_sp_rend2_x64.dll\n"
)
print(json.dumps(proof,indent=2))
