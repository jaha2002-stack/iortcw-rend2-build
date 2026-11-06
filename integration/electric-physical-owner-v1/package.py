#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,subprocess,zipfile

EV=Path('evidence');OUT=Path('dist')
EV.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()

BASE_RUN=42217883095
BASE_ARTIFACT=13502112057
BASE_COMMIT='0ef4fc401daff30c230ccb8226a8029fb0a3519f'
EXPECTED_BASE_DLL='0b2ff0b28bbf69ff0df73417866eb330eb204c10b5be5fb0835b98f26797cc2d'

wrap=EV/'base_42217883095_artifact.zip'
with wrap.open('wb') as f:
    subprocess.run(['gh','api',f'repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/{BASE_ARTIFACT}/zip'],stdout=f,check=True)
with zipfile.ZipFile(wrap) as z:
    inners=[n for n in z.namelist() if n.endswith('.zip') and 'Clean_Production_ELSS_V1.1_ComponentPick_REFINED' in n]
    assert len(inners)==1,inners
    raw=z.read(inners[0])
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None
    roots={n.split('/',1)[0] for n in z.namelist() if '/' in n}
    assert len(roots)==1,roots
    base={n.split('/',1)[1]:z.read(n) for n in z.namelist() if not n.endswith('/')}

base_dll=base['renderer_sp_rend2_x64.dll']
assert sha(base_dll)==EXPECTED_BASE_DLL,(sha(base_dll),EXPECTED_BASE_DLL)
dlls=list(Path('source/SP/build').rglob('renderer_sp_rend2_x64.dll'))
assert len(dlls)==1,dlls
dll=dlls[0].read_bytes()
for marker in (
    b'r_dwElectricPhysicalOwner',
    b'r_dwElectricPhysicalOwnerDiag',
    b'EPO_V1_SUMMARY',
    b'EPOA_SUMMARY',
    b'dw_el_self_pick',
    b'FIREVOL_CLEAN_PRODUCTION',
):
    assert marker in dll,marker

entries=base.copy()
entries['renderer_sp_rend2_x64.dll']=dll

entries['Main/DW_ELECTRIC_PHYSICAL_OWNER_V1_ON_TEST.cfg']=(
'// Electric Physical Owner V1 - Shadow + LocalVol ownership only\r\n'
'seta r_dwElectricPhysicalOwner "1"\r\n'
'seta r_dwElectricPhysicalOwnerDiag "0"\r\n'
'seta r_dwElectricOwnerAudit "0"\r\n'
).encode('ascii')

entries['Main/DW_ELECTRIC_PHYSICAL_OWNER_V1_OFF_TEST.cfg']=(
'// Baseline A/B: disable only new explicit owner association.\r\n'
'// Legacy production 16-unit grouping remains active exactly as before.\r\n'
'seta r_dwElectricPhysicalOwner "0"\r\n'
'seta r_dwElectricPhysicalOwnerDiag "0"\r\n'
'seta r_dwElectricOwnerAudit "0"\r\n'
).encode('ascii')

entries['Main/DW_ELECTRIC_PHYSICAL_OWNER_V1_AUDIT_TEST.cfg']=(
'// Optional verbose ownership telemetry; rendering policy is V1 ON.\r\n'
'seta r_dwElectricPhysicalOwner "1"\r\n'
'seta r_dwElectricPhysicalOwnerDiag "2"\r\n'
'seta r_dwElectricOwnerAudit "3"\r\n'
'seta r_dwElectricOwnerAuditIntervalMs "1000"\r\n'
'seta r_dwElectricOwnerAuditNearRadius "96"\r\n'
).encode('ascii')

readme='''DarkWolf Electric Physical Owner V1 - Shadow + LocalVol - Win64 TEST
Base: GitHub Run #42217883095 Clean Production ELSS V1.1 REFINED.

Purpose
-------
First corrective stage after Electric Physical Owner Audit.
Direct lighting is intentionally NOT deduplicated in this version.

What V1 changes
---------------
- Adds explicit map-local physicalElectricOwnerId metadata.
- Real promoted electric lights obtain an owner only through the existing
  unambiguous Electric Fixture geometry matcher.
- A synthetic may inherit that owner only from a delivered real promoted light,
  within 48 units, with compatible base radius/color, and only when no competing
  owner is close enough to make the association ambiguous.
- Point-shadow grouping uses equal physicalElectricOwnerId before falling back
  to the existing production 16-unit proximity grouping.
- Local Volumetric grouping uses the same owner rule and the same fallback.
- Shared point-shadow capture keeps the resolved electric fixture identity so
  ELSS own-body suppression remains available for the group.

Explicitly unchanged
--------------------
- Direct DLight count, origin, radius, color, brightness and energy.
- StaticPromote residency/budget/selection and learned/synthetic files.
- IFLC settings/profiles and FireVol ownership.
- ELSS profiles/component-pick behavior.
- Existing production 16-unit grouping remains the fallback when owner is
  unresolved or the new feature is disabled.
- r_dlightShadowMaxLights and all LocalVol quality settings are unchanged.

A/B
---
ON:    /exec DW_ELECTRIC_PHYSICAL_OWNER_V1_ON_TEST.cfg
OFF:   /exec DW_ELECTRIC_PHYSICAL_OWNER_V1_OFF_TEST.cfg
AUDIT: /exec DW_ELECTRIC_PHYSICAL_OWNER_V1_AUDIT_TEST.cfg

For PC performance testing, compare the same camera position and scene with
ON vs OFF. OFF disables only the new explicit owner association; it does not
disable the older production grouping.

This is a TEST release, not Clean Production.
'''
entries['README_ELECTRIC_PHYSICAL_OWNER_V1_TEST.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')

status={
 'status':'TEST_CANDIDATE',
 'version':'ELECTRIC_PHYSICAL_OWNER_V1_SHADOW_LOCALVOL',
 'base_run':BASE_RUN,
 'base_commit':BASE_COMMIT,
 'build_run':os.environ.get('GITHUB_RUN_ID'),
 'commit':os.environ.get('GITHUB_SHA'),
 'renderer_sha256':sha(dll),
 'base_renderer_sha256':sha(base_dll),
 'default_enabled':True,
 'direct_light_mutated':False,
 'staticpromote_residency_mutated':False,
 'point_shadow_owner_changed':True,
 'localvol_owner_changed':True,
 'iflc_profile_mutated':False,
 'elss_profile_mutated':False,
 'legacy_grouping_fallback_preserved':True,
 'synthetic_inherit_max_distance':48.0,
 'ambiguity_margin':16.0,
 'windows_gpu_fps':'USER_TEST_REQUIRED'
}
entries['ELECTRIC_PHYSICAL_OWNER_V1_TEST_STATUS.json']=(json.dumps(status,indent=2)+'\n').encode()
entries.pop('SHA256SUMS.txt',None)
entries['SHA256SUMS.txt']=''.join(sha(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode('ascii')

changed=[n for n in sorted(set(entries)|set(base)) if entries.get(n)!=base.get(n)]
expected=[
 'ELECTRIC_PHYSICAL_OWNER_V1_TEST_STATUS.json',
 'Main/DW_ELECTRIC_PHYSICAL_OWNER_V1_AUDIT_TEST.cfg',
 'Main/DW_ELECTRIC_PHYSICAL_OWNER_V1_OFF_TEST.cfg',
 'Main/DW_ELECTRIC_PHYSICAL_OWNER_V1_ON_TEST.cfg',
 'README_ELECTRIC_PHYSICAL_OWNER_V1_TEST.txt',
 'SHA256SUMS.txt',
 'renderer_sp_rend2_x64.dll'
]
assert changed==expected,changed

root='DarkWolf_Electric_Physical_Owner_V1_Shadow_LocalVol_From_42217883095_Win64_TEST'
target=OUT/(root+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for n,b in sorted(entries.items()):
        z.writestr(root+'/'+n,b)
with zipfile.ZipFile(target) as z:assert z.testzip() is None

proof={
 'package':str(target),'package_sha256':sha(target.read_bytes()),
 'renderer_sha256':sha(dll),'base_renderer_sha256':sha(base_dll),
 'changed_vs_base':changed,'base_run':BASE_RUN
}
(EV/'EPO_V1_PACKAGE_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
(OUT/'SHA256SUMS.txt').write_text(
 proof['package_sha256']+'  '+target.name+'\n'+proof['renderer_sha256']+'  renderer_sp_rend2_x64.dll\n')
print(json.dumps(proof,indent=2))
