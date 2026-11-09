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
    subprocess.run([
        'gh','api',
        f'repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/{BASE_ARTIFACT}/zip'
    ],stdout=f,check=True)

with zipfile.ZipFile(wrap) as z:
    inners=[n for n in z.namelist()
            if n.endswith('.zip') and
            'Clean_Production_ELSS_V1.1_ComponentPick_REFINED' in n]
    assert len(inners)==1,inners
    raw=z.read(inners[0])

with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None
    base={n.split('/',1)[1]:z.read(n)
          for n in z.namelist() if '/' in n and not n.endswith('/')}

base_dll=base['renderer_sp_rend2_x64.dll']
assert sha(base_dll)==EXPECTED_BASE_DLL

dlls=list(Path('source/SP/build').rglob('renderer_sp_rend2_x64.dll'))
assert len(dlls)==1,dlls
dll=dlls[0].read_bytes()

for marker in (
    b'r_dwElectricPhysicalOwner',
    b'r_dwEscape1PhysicalDlightOwnerResidency',
    b'r_dwEscape1ExternalNativeReserve',
    b'EDR12_SUMMARY',
    b'EDRA_SUMMARY',
    b'dw_el_self_pick',
):
    assert marker in dll,marker

# Withdrawn V1.1 must not be part of the new renderer.
assert b'EDRF_SUMMARY' not in dll
assert b'r_dwEscape1StableDlightResidency' not in dll

entries=base.copy()
entries['renderer_sp_rend2_x64.dll']=dll

entries['Main/DW_ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_ON_TEST.cfg']=(
'// Escape1 Physical DLight Owner Residency V1.2 ON\r\n'
'seta r_dwElectricPhysicalOwner "1"\r\n'
'seta r_dwEscape1PhysicalDlightOwnerResidency "1"\r\n'
'seta r_dwEscape1ExternalNativeReserve "9"\r\n'
'seta r_dwEscape1PhysicalDlightOwnerDiag "0"\r\n'
'seta r_dwEscape1DlightResidencyAudit "0"\r\n'
).encode('ascii')

entries['Main/DW_ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_OFF_TEST.cfg']=(
'// A/B baseline: production all-accepted overflow ordering\r\n'
'seta r_dwElectricPhysicalOwner "1"\r\n'
'seta r_dwEscape1PhysicalDlightOwnerResidency "0"\r\n'
'seta r_dwEscape1PhysicalDlightOwnerDiag "0"\r\n'
'seta r_dwEscape1DlightResidencyAudit "0"\r\n'
).encode('ascii')

entries['Main/DW_ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_AUDIT_TEST.cfg']=(
'// Escape1 Physical DLight Owner V1.2 + detailed telemetry\r\n'
'seta r_dwElectricPhysicalOwner "1"\r\n'
'seta r_dwEscape1PhysicalDlightOwnerResidency "1"\r\n'
'seta r_dwEscape1ExternalNativeReserve "9"\r\n'
'seta r_dwEscape1PhysicalDlightOwnerDiag "1"\r\n'
'seta r_dwEscape1DlightResidencyAudit "1"\r\n'
'seta r_dwEscape1DlightResidencyAuditIntervalMs "100"\r\n'
).encode('ascii')

readme='''DarkWolf Escape1 Physical DLight Owner Residency V1.2 - Win64 TEST
Base: Clean Production Run #42217883095 + Electric Physical Owner V1.

Why V1.1 was withdrawn
----------------------
The real PC audit proved total sceneNative can reach 11, not 9. More importantly,
accepted fixtures 851 and 298 can switch between native and promoted delivery.
V1.1 stabilized promoted slots, not physical owners, so a route change could still
open/close a slot and make a neighbouring room lamp (notably fixture 745) toggle.

What V1.2 changes
-----------------
Only on Escape1 and only during DLight overflow:

1. Capacity is assigned to PHYSICAL StaticPromote owners, not to a particular
   native/promoted delivery route.
2. Accepted native-route owners are subtracted from the promoted budget.
   Therefore one owner changing native <-> promoted does not donate a temporary
   slot to another lamp.
3. External native pressure is calculated as:
      sceneNative - acceptedNativeRoutes
   The user's real log showed sceneNative up to 11 with up to two accepted native
   routes, so the external native high-water remains 9 and the stable physical
   owner budget is 32 - 9 = 23.
4. Selection under overflow prefers FORCE ON, then SURFACE_VISIBLE / PVS-connected /
   physical / grace-held owners, then native-capable latent owners, then ordinary
   latent owners. Existing retention/grace is preserved.
5. The whole guard-room group 740-745 is audited.

Explicitly NOT changed
----------------------
- MAX_DLIGHTS remains 32.
- Direct color, radius, brightness and source intensity are untouched.
- StaticPromote user blocks/learn files are untouched.
- IFLC, ELSS, FireVol, point-shadow policy and LocalVol quality are untouched.
- Other maps use the production path.
- Electric Physical Owner V1 remains included.

Commands
--------
ON:    /exec DW_ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_ON_TEST.cfg
OFF:   /exec DW_ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_OFF_TEST.cfg
AUDIT: /exec DW_ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_AUDIT_TEST.cfg

This is a TEST release, not Clean Production.
'''

entries['README_ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_TEST.txt']=(
    readme.replace('\n','\r\n').encode('utf-8-sig'))

status={
 'status':'TEST_CANDIDATE',
 'version':'ESCAPE1_PHYSICAL_DLIGHT_OWNER_RESIDENCY_V12',
 'base_run':BASE_RUN,
 'base_commit':BASE_COMMIT,
 'build_run':os.environ.get('GITHUB_RUN_ID'),
 'commit':os.environ.get('GITHUB_SHA'),
 'renderer_sha256':sha(dll),
 'base_renderer_sha256':sha(base_dll),
 'map_scope':'escape1',
 'external_native_reserve':9,
 'stable_physical_owner_budget':23,
 'owner_identity_route_independent':True,
 'accepted_native_routes_subtract_from_promoted_budget':True,
 'direct_energy_mutated':False,
 'max_dlights_changed':False,
 'other_maps_changed':False,
 'withdraws_escape1_residency_v11':True,
 'inherits_electric_physical_owner_v1':True,
}
entries['ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_TEST_STATUS.json']=(
    json.dumps(status,indent=2)+'\n').encode()

entries.pop('SHA256SUMS.txt',None)
entries['SHA256SUMS.txt']=''.join(
    sha(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode('ascii')

root='DarkWolf_Escape1_Physical_DLight_Owner_Residency_V1.2_From_42217883095_Win64_TEST'
target=OUT/(root+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for n,b in sorted(entries.items()):
        z.writestr(root+'/'+n,b)

with zipfile.ZipFile(target) as z:
    assert z.testzip() is None

proof={
 'package':str(target),
 'package_sha256':sha(target.read_bytes()),
 'renderer_sha256':sha(dll),
 'base_renderer_sha256':sha(base_dll),
}
(EV/'EDR12_PACKAGE_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
(OUT/'SHA256SUMS.txt').write_text(
    proof['package_sha256']+'  '+target.name+'\n'+
    proof['renderer_sha256']+'  renderer_sp_rend2_x64.dll\n')
print(json.dumps(proof,indent=2))
