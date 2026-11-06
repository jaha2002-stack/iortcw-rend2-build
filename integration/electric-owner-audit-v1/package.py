#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,subprocess,zipfile

EV=Path('evidence'); OUT=Path('dist')
EV.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()

BASE_RUN=42217883095
BASE_ARTIFACT=13502112057
BASE_COMMIT='0ef4fc401daff30c230ccb8226a8029fb0a3519f'

wrap=EV/'run42217883095_artifact.zip'
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

dlls=list(Path('source/SP/build').rglob('renderer_sp_rend2_x64.dll'))
assert len(dlls)==1,dlls
dll=dlls[0].read_bytes()
for m in (b'EPOA_SUMMARY',b'EPOA_GROUP',b'EPOA_NEAR',b'r_dwElectricOwnerAudit',
          b'dw_el_self_pick',b'FIREVOL_CLEAN_PRODUCTION'):
    assert m in dll,m

base_dll=base['renderer_sp_rend2_x64.dll']
entries=base.copy()
entries['renderer_sp_rend2_x64.dll']=dll

entries['Main/DW_ELECTRIC_OWNER_AUDIT_V1_ENABLE.cfg']=(
'// Electric Physical Owner Audit V1 - read only\r\n'
'seta r_dwElectricOwnerAudit "2"\r\n'
'seta r_dwElectricOwnerAuditIntervalMs "1000"\r\n'
'seta r_dwElectricOwnerAuditFocus "-1"\r\n'
'seta r_dwElectricOwnerAuditNearRadius "64"\r\n'
'seta r_staticPromoteUnifiedDiag "1"\r\n'
).encode('ascii')

entries['Main/DW_ELECTRIC_OWNER_AUDIT_V1_VERBOSE.cfg']=(
'// Verbose read-only collection\r\n'
'seta r_dwElectricOwnerAudit "3"\r\n'
'seta r_dwElectricOwnerAuditIntervalMs "750"\r\n'
'seta r_dwElectricOwnerAuditFocus "-1"\r\n'
'seta r_dwElectricOwnerAuditNearRadius "64"\r\n'
'seta r_staticPromoteUnifiedDiag "1"\r\n'
).encode('ascii')

readme='''DarkWolf Electric Physical Owner Audit V1 - Win64 DIAGNOSTIC
Base: GitHub Run #42217883095 (Clean Production ELSS V1.1 REFINED)

This is READ-ONLY instrumentation. It does not deduplicate, move, recolor,
resize, disable or reassign any light. Default r_dwElectricOwnerAudit is 0.

Recommended collection:
1. /exec DW_ELECTRIC_OWNER_AUDIT_V1_ENABLE.cfg
2. Reproduce a heavy lamp area for 20-30 seconds.
3. /condump EPOA_<map>.txt
4. For a suspicious fixture:
   /r_dwElectricOwnerAuditFocus <fixtureId>
   /r_dwElectricOwnerAudit 3
5. Reproduce again and condump a second log.
6. /r_dwElectricOwnerAudit 0

Telemetry:
EPOA_SUMMARY - Direct promoted/synthetic counts, shadow groups/slots,
               LocalVol groups/active groups, nearby synthetic pairs.
EPOA_GROUP   - current production 16-unit physical groups.
EPOA_MEMBER  - exact delivered dlight identity, origin, radius/color,
               shadow/localvol group and shadow slot.
EPOA_NEAR    - synthetic-related pairs inside 64 units and whether current
               production merges them for shadow and LocalVol.
EPOA_REG     - persistent registry details in verbose mode.

Safety contract:
Direct light unchanged.
Point-shadow grouping/selection/budget unchanged.
Local Volumetric rendering unchanged.
FireVol, IFLC, ELSS and GLSL unchanged.
No profile files are written by the audit.
'''
entries['README_ELECTRIC_OWNER_AUDIT_V1.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')

status={
 'status':'DIAGNOSTIC_READ_ONLY',
 'version':'ELECTRIC_PHYSICAL_OWNER_AUDIT_V1',
 'base_run':BASE_RUN,
 'base_commit':BASE_COMMIT,
 'build_run':os.environ.get('GITHUB_RUN_ID'),
 'commit':os.environ.get('GITHUB_SHA'),
 'renderer_sha256':sha(dll),
 'base_renderer_sha256':sha(base_dll),
 'default_enabled':False,
 'direct_light_mutation':False,
 'shadow_mutation':False,
 'local_volumetric_mutation':False,
 'firevol_mutation':False,
 'production_merge_radius_observed':16.0,
 'diagnostic_near_radius_default':64.0,
 'windows_gpu_fps':'USER_COLLECTION_REQUIRED'
}
entries['ELECTRIC_OWNER_AUDIT_V1_STATUS.json']=(json.dumps(status,indent=2)+'\n').encode()

entries.pop('SHA256SUMS.txt',None)
entries['SHA256SUMS.txt']=''.join(sha(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode('ascii')

changed=[n for n in sorted(set(entries)|set(base)) if entries.get(n)!=base.get(n)]
expected=[
 'ELECTRIC_OWNER_AUDIT_V1_STATUS.json',
 'Main/DW_ELECTRIC_OWNER_AUDIT_V1_ENABLE.cfg',
 'Main/DW_ELECTRIC_OWNER_AUDIT_V1_VERBOSE.cfg',
 'README_ELECTRIC_OWNER_AUDIT_V1.txt',
 'SHA256SUMS.txt',
 'renderer_sp_rend2_x64.dll'
]
assert changed==expected,changed

root='DarkWolf_Electric_Physical_Owner_Audit_V1_From_42217883095_Win64_DIAGNOSTIC'
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
 'changed_vs_base':changed
}
(EV/'EPOA_V1_PACKAGE_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
(OUT/'SHA256SUMS.txt').write_text(
 proof['package_sha256']+'  '+target.name+'\n'+
 proof['renderer_sha256']+'  renderer_sp_rend2_x64.dll\n'
)
print(json.dumps(proof,indent=2))
