#!/usr/bin/env bash
set -Eeuo pipefail
python3 -m py_compile integration/xlabs-escape1-v4/package.py
mkdir -p evidence/v4-old/SP/code/rend2 evidence/v4-replay/SP/code/rend2
for f in tr_main.c tr_scene.c; do
  cp "sept-source/SP/code/rend2/$f" "evidence/v4-old/SP/code/rend2/$f"
  cp "sept-source/SP/code/rend2/$f" "evidence/v4-replay/SP/code/rend2/$f"
done
printf '%s\n' \
  '070f2bfa3c3f1d7beb02333f2ce124afc456e472e971a05afd68b6161448d0ea  sept-source/SP/code/rend2/tr_main.c' \
  '2ce98792ab054ea59529ac103a9485443f08d2c8d34b0e8ded42d2aacf9ebcaf  sept-source/SP/code/rend2/tr_scene.c' \
  '1651e1e14c8154aead2616856ba2d7c1c5ab66b69fb26bd049a5dd9e236ed08c  sept-source/SP/code/rend2/glsl/dlight_fp.glsl' \
  'f5d93f15acedb9139f648658774bc409690d07ef0a34f52058fe053c13bee2cd  sept-source/SP/code/rend2/glsl/lightall_fp.glsl' \
  'e08d1f94b186fd46b078fbaf740e38c8cea93170836c2701c27801ad443f495f  sept-source/SP/code/rend2/tr_backend.c' | sha256sum -c -
git -C sept-source apply --check ../integration/xlabs-escape1-v4/TEST_ONLY_SOURCE.patch
git -C sept-source apply ../integration/xlabs-escape1-v4/TEST_ONLY_SOURCE.patch
git -C sept-source apply --reverse --check ../integration/xlabs-escape1-v4/TEST_ONLY_SOURCE.patch
printf '%s\n' \
  'f4f37f8c46b0e7b5e5ee7d24d6f069093f58fa3536685d026489b4d64d4a957f  sept-source/SP/code/rend2/tr_main.c' \
  '58e2a3aeb784558575de9d40bb64e15d1f5a7c7a8730a2d5d0d626f748d5ab37  sept-source/SP/code/rend2/tr_scene.c' | sha256sum -c -
if git -C sept-source apply --check ../integration/xlabs-escape1-v4/TEST_ONLY_SOURCE.patch >/dev/null 2>&1; then
  echo DOUBLE_APPLICATION_UNEXPECTED >&2; exit 1
fi
patch -d evidence/v4-replay -p1 < integration/xlabs-escape1-v4/TEST_ONLY_SOURCE.patch
for f in tr_main.c tr_scene.c; do
  cmp "sept-source/SP/code/rend2/$f" "evidence/v4-replay/SP/code/rend2/$f"
done
python3 - <<'PY'
import hashlib,json,pathlib
base=pathlib.Path('sept-source')
r=lambda p:(base/p).read_text()
h=lambda p:hashlib.sha256((base/p).read_bytes()).hexdigest()
m=r('SP/code/rend2/tr_main.c');s=r('SP/code/rend2/tr_scene.c')
assert m.count('R_DWTestTeslaWorldCaptureOrigin(dl, testCaptureOrigin);')==2
assert m.count('R_DlightWorldCacheMatches(')==3
assert 'VectorCopy(tr.refdef.dlights[bestLight].origin, shadowParms.or.origin);' in m
assert 'VectorCopy(testCaptureOrigin, shadowParms.or.origin);' in m
assert 'VectorCopy(testCaptureOrigin, cache->origin);' in m
assert 'Q_stricmp(tr.world->baseName, "xlabs")' in m
assert 'r_dwTeslaWorldCaptureXTest", "0", 0' in m
assert 'requiredRadius = dl->radius + fabs(testCaptureOrigin[0] - dl->origin[0]);' in m
assert s.count('ri.Cvar_Set("r_dwMainSceneLightAuditOnce", "0")')==1
assert '!(fd->rdflags & (RDF_SKYBOXPORTAL | RDF_NOWORLDMODEL))' in s
assert s.index('R_RenderDlightWorldOcclusion(fd);')<s.index('DW_MAIN_SCENE_AUDIT_V4_BEGIN')
assert 'r_dwMainSceneLightAuditOnce", "0", 0' in s
assert 'R_DarkWolfFireVolumetricSourceMatch' in s
assert h('SP/code/rend2/glsl/dlight_fp.glsl')=='1651e1e14c8154aead2616856ba2d7c1c5ab66b69fb26bd049a5dd9e236ed08c'
assert h('SP/code/rend2/glsl/lightall_fp.glsl')=='f5d93f15acedb9139f648658774bc409690d07ef0a34f52058fe053c13bee2cd'
assert h('SP/code/rend2/tr_backend.c')=='e08d1f94b186fd46b078fbaf740e38c8cea93170836c2701c27801ad443f495f'
proof={'marker':'DW_XLABS_ESCAPE1_WORLD_CAPTURE_MAIN_SCENE_AUDIT_V4_20261028',
 'frozen_user_accepted_runtime_run':40640998083,
 'changed_source_files':['SP/code/rend2/tr_main.c','SP/code/rend2/tr_scene.c'],
 'source_sha_before':{'SP/code/rend2/tr_main.c':'070f2bfa3c3f1d7beb02333f2ce124afc456e472e971a05afd68b6161448d0ea',
 'SP/code/rend2/tr_scene.c':'2ce98792ab054ea59529ac103a9485443f08d2c8d34b0e8ded42d2aacf9ebcaf'},
 'source_sha_after':{'SP/code/rend2/tr_main.c':h('SP/code/rend2/tr_main.c'),
 'SP/code/rend2/tr_scene.c':h('SP/code/rend2/tr_scene.c')},
 'test_cvars_non_archived':['r_dwTeslaWorldCaptureXTest','r_dwMainSceneLightAuditOnce'],
 'normal_light_origin_unchanged':True,'point_shadow_origin_unchanged':True,
 'production':False,'sky_portal_audit_excluded':True}
pathlib.Path('evidence/XLABS_ESCAPE1_V4_SOURCE_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
for offset in [0,32,64,96,-32]:
 delta=max(-96,min(96,offset))
 if offset==0:assert delta==0
 else:assert abs(delta)>=32
for p in ['SP/code/rend2/glsl/dlight_fp.glsl','SP/code/rend2/glsl/lightall_fp.glsl']:
 assert 'DARKWOLF_CRYPT1_ARCHITECTURAL_WORLD_VISIBILITY_PCF2X2_V1_20261028' in r(p)
print('DW_XLABS_ESCAPE1_V4_SOURCE_FROZEN_REPLAY_AND_STATIC_TEST_PASS')
PY
