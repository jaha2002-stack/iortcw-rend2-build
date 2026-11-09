#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,subprocess,zipfile

EV=Path('evidence');OUT=Path('dist');EV.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
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
    base={n.split('/',1)[1]:z.read(n) for n in z.namelist() if '/' in n and not n.endswith('/')}

base_dll=base['renderer_sp_rend2_x64.dll']; assert sha(base_dll)==EXPECTED_BASE_DLL
dlls=list(Path('source/SP/build').rglob('renderer_sp_rend2_x64.dll'));assert len(dlls)==1,dlls
dll=dlls[0].read_bytes()
for m in (b'r_dwElectricPhysicalOwner',b'r_dwEscape1StableDlightResidency',b'EDRF_SUMMARY',b'EDRA_SUMMARY',b'dw_el_self_pick'):
    assert m in dll,m

entries=base.copy(); entries['renderer_sp_rend2_x64.dll']=dll
entries['Main/DW_ESCAPE1_DLIGHT_RESIDENCY_V1_ON_TEST.cfg']=(
'// Escape1 Stable DLight Residency V1 ON\r\n'
'seta r_dwElectricPhysicalOwner "1"\r\n'
'seta r_dwEscape1StableDlightResidency "1"\r\n'
'seta r_dwEscape1DlightNativeReserve "9"\r\n'
'seta r_dwEscape1StableDlightResidencyDiag "0"\r\n'
'seta r_dwEscape1DlightResidencyAudit "0"\r\n'
).encode('ascii')
entries['Main/DW_ESCAPE1_DLIGHT_RESIDENCY_V1_OFF_TEST.cfg']=(
'// A/B baseline: restore previous all-accepted overflow ordering\r\n'
'seta r_dwElectricPhysicalOwner "1"\r\n'
'seta r_dwEscape1StableDlightResidency "0"\r\n'
'seta r_dwEscape1DlightNativeReserve "9"\r\n'
'seta r_dwEscape1StableDlightResidencyDiag "0"\r\n'
'seta r_dwEscape1DlightResidencyAudit "0"\r\n'
).encode('ascii')
entries['Main/DW_ESCAPE1_DLIGHT_RESIDENCY_V1_AUDIT_TEST.cfg']=(
'// Escape1 residency V1 + detailed slot telemetry\r\n'
'seta r_dwElectricPhysicalOwner "1"\r\n'
'seta r_dwEscape1StableDlightResidency "1"\r\n'
'seta r_dwEscape1DlightNativeReserve "9"\r\n'
'seta r_dwEscape1StableDlightResidencyDiag "1"\r\n'
'seta r_dwEscape1DlightResidencyAudit "1"\r\n'
'seta r_dwEscape1DlightResidencyAuditIntervalMs "100"\r\n'
).encode('ascii')

readme='''DarkWolf Escape1 Stable DLight Residency V1.1 - Win64 TEST
Base: Clean Production Run #42217883095 + Electric Physical Owner V1.

Problem proven by runtime audit
-------------------------------
Escape1 has 30 accepted promoted fixtures while native DLight count moves between
6 and 9. MAX_DLIGHTS is 32, therefore promoted headroom moves between 26 and 23.
The former ordering can repeatedly evict/re-add a boundary lamp as native DLight
count changes.

What this V1.1 changes
----------------------
Only on Escape1, and only when the accepted promoted set exceeds the stable budget:
1. Reserve 9 DLight slots for the proven native high-water occupancy (audit: 6..9).
   Promoted ownership therefore stays at 23 instead of oscillating 23..26.
2. FORCE ON fixtures remain absolute.
3. Ordinary fixtures keep existing StaticPromote priority. Inside the same priority,
   a map-space 260-unit coherence score keeps dense lamp groups together before
   isolated peers. Camera distance is never used.
4. The actual MAX_DLIGHTS limit remains 32. If native occupancy ever exceeds the
   reserve, actual hard headroom still wins safely.

Explicitly NOT changed
----------------------
- MAX_DLIGHTS remains 32.
- Direct light color, radius, brightness and source intensity are untouched.
- No StaticPromote user profile or learned file is changed.
- IFLC, ELSS, FireVol, point-shadow budget and LocalVol quality are unchanged.
- When accepted promoted lights fit inside the reserved budget, the old production
  selection path is used.
- Other maps use the old production path.
- The fix may intentionally leave 1-3 DLight slots unused when native occupancy is
  below 9; this is the reserve that prevents transient native lights from evicting
  promoted room lamps and can slightly reduce GPU work.

Commands
--------
ON:    /exec DW_ESCAPE1_DLIGHT_RESIDENCY_V1_ON_TEST.cfg
OFF:   /exec DW_ESCAPE1_DLIGHT_RESIDENCY_V1_OFF_TEST.cfg
AUDIT: /exec DW_ESCAPE1_DLIGHT_RESIDENCY_V1_AUDIT_TEST.cfg

This is a TEST release, not Clean Production.
'''
entries['README_ESCAPE1_DLIGHT_RESIDENCY_V1_TEST.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')
status={
 'status':'TEST_CANDIDATE','version':'ESCAPE1_DLIGHT_RESIDENCY_V1_1',
 'base_run':BASE_RUN,'base_commit':BASE_COMMIT,'build_run':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA'),
 'renderer_sha256':sha(dll),'base_renderer_sha256':sha(base_dll),
 'map_scope':'escape1','overflow_only':True,'native_reserve':9,'stable_promoted_budget':23,'direct_energy_mutated':False,'max_dlights_changed':False,
 'selection_identity_changed_under_overflow':True,'camera_distance_used':False,'coherence_radius':260.0,'other_maps_changed':False,
 'inherits_electric_physical_owner_v1':True
}
entries['ESCAPE1_DLIGHT_RESIDENCY_V1_TEST_STATUS.json']=(json.dumps(status,indent=2)+'\n').encode()
entries.pop('SHA256SUMS.txt',None)
entries['SHA256SUMS.txt']=''.join(sha(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode('ascii')
root='DarkWolf_Escape1_DLight_Residency_V1_From_42217883095_Win64_TEST'
target=OUT/(root+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for n,b in sorted(entries.items()): z.writestr(root+'/'+n,b)
with zipfile.ZipFile(target) as z: assert z.testzip() is None
proof={'package':str(target),'package_sha256':sha(target.read_bytes()),'renderer_sha256':sha(dll),'base_renderer_sha256':sha(base_dll)}
(EV/'EDRF_V1_PACKAGE_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
(OUT/'SHA256SUMS.txt').write_text(proof['package_sha256']+'  '+target.name+'\n'+proof['renderer_sha256']+'  renderer_sp_rend2_x64.dll\n')
print(json.dumps(proof,indent=2))
