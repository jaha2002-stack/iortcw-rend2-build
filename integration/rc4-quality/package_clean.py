#!/usr/bin/env python3
"""Package one rebuilt renderer with byte-identical approved baseline payload."""
from pathlib import Path, PurePosixPath
import hashlib, io, json, os, struct, zipfile
BASE_RUN=38733120730
BASE_TREE='c652eaed9cbcf1df4eb7d7d5187b9bea63dce60b'
BASE_ARCHIVE_SHA='b45a2d5f443f05fcb41a54ffde61c3781ee050bd99daba4bbe2512476977578a'
MARKERS=(b'AB_SCENE',b'AB_LIGHT',b'AB_MAP_USE',b'dw_abFreeze',b'dw_abReference',b'__asan_',b'__ubsan_',b'TESTLAB_CAPTURE_READY',b'QUALITY_FLOAT_CAPTURE',b'r_qualityDump')
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
    out=Path('dist');out.mkdir(exist_ok=True)
    archive=Path('base-clean.zip').read_bytes();assert digest(archive)==BASE_ARCHIVE_SHA
    with zipfile.ZipFile(io.BytesIO(archive)) as outer:
        names=[n for n in outer.namelist() if n.endswith('.zip')];assert len(names)==1
        with zipfile.ZipFile(io.BytesIO(outer.read(names[0]))) as z:
            assert z.testzip() is None
            files={}
            for entry in z.infolist():
                if entry.is_dir():continue
                path=PurePosixPath(entry.filename);assert not path.is_absolute() and '..' not in path.parts and len(path.parts)>1
                rel='/'.join(path.parts[1:]);assert rel not in files
                files[rel]=z.read(entry)
    target='renderer_sp_rend2_x64.dll';old_renderer=digest(files[target])
    renderer=Path('source/SP/build/release-mingw32-x86_64')/target
    binary=renderer.read_bytes();assert binary[:2]==b'MZ'
    pe=struct.unpack_from('<I',binary,60)[0];assert binary[pe:pe+4]==b'PE\0\0' and struct.unpack_from('<H',binary,pe+4)[0]==0x8664
    for marker in MARKERS:assert marker not in binary,('diagnostic marker',marker)
    assert b'no-independent-depth' in binary, 'Shared SSGI depth fix missing'
    assert b'addReconstructionTap' in binary and b'coverageAA' in binary, 'Tested reconstruction shader missing'
    assert digest(binary)!=old_renderer,'Renderer unexpectedly identical to baseline'
    retained={k:digest(v) for k,v in files.items() if k!=target}
    original_provenance=json.loads(files['docs/BUILD_PROVENANCE.json'])
    files[target]=binary
    source_tree=Path('evidence/quality-source-tree.txt').read_text().strip()
    prov={'status':'CLEAN_WIN64_CANDIDATE_NOT_VISUALLY_ACCEPTED',
          'base_run':BASE_RUN,'base_source_tree':BASE_TREE,'source_tree':source_tree,
          'builder_commit':os.getenv('GITHUB_SHA'),'run_id':os.getenv('GITHUB_RUN_ID'),
          'changed_binary':{target:{'before':old_renderer,'after':digest(binary)}},
          'all_other_baseline_files_byte_identical':retained,
          'parent_provenance':original_provenance,
          'production_telemetry_added':False,'new_test_cvars':False,'retail_assets_included':False,
          'windows_game_runtime':'NOT_RUN','corrected_factory_gameplay_ab':'NOT_RUN',
          'gaming_gpu_performance':'NOT_MEASURED','shader_and_synthetic_tests':'Separate evidence; not game acceptance'}
    newdocs={
      'QUALITY_PROVENANCE.json':(json.dumps(prov,indent=2)+'\n').encode(),
      'QUALITY_INSTALL.txt':b'''DarkWolf v4.4.6 RC4 - SSGI / Volumetric Quality candidate

This is a clean Windows x64 SP candidate, not a visually accepted final release.
Baseline: Actions run 38733120730. Only the renderer DLL is replaced.
All other baseline EXE, DLL, CFG, BAT and approved PK3 files are byte-identical.
No retail game maps/textures are distributed. No diagnostic instrumentation.

Install into a SEPARATE copy of the working RTCW installation. Keep the baseline.
Copy the candidate contents into that copy and run RUN_DARKWOLF_OPTIMIZED_CLEAN.bat.
No new effect-disabling or quality-reducing CVars are required.

Implemented changes:
- SSGI retains authored surface-emission identity in its existing rejection mask.
- SSGI reuses an independently produced depth snapshot.
- Volumetric reconstruction aligns inverted low-resolution color with scene depth.
- Producer/reconstruction depth-grid ties use the same canonical texel.
- Coverage AA remains inside depth-validated reconstruction cells.

Validation limits:
The corrected candidate has NOT been captured at the actual Factory tunnel lamps
or verified on a gaming GPU. Do not interpret synthetic tests or compilation as
proof of final visual acceptance, compatibility on every GPU, or unchanged FPS.
The mask-based SSGI change still needs actual authored-material coverage checked.

The docs/BUILD_PROVENANCE.json and docs/SHA256SUMS.txt retained from the parent
package describe the BASELINE, not the replacement renderer. The authoritative
new package records are QUALITY_PROVENANCE.json and QUALITY_SHA256SUMS.txt.
Complete changed source and the minimal patch are supplied as separate artifacts.
'''}
    assert not set(newdocs)&set(files)
    files.update(newdocs)
    for name,data in files.items():
        if name in retained:assert digest(data)==retained[name]
    files['QUALITY_SHA256SUMS.txt']=''.join(f'{digest(v)}  {k}\n' for k,v in sorted(files.items())).encode()
    name='DarkWolf-v446-RC4-Quality-Candidate-Win64-SP';zpath=out/(name+'.zip')
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
        for rel,data in sorted(files.items()):
            info=zipfile.ZipInfo(name+'/'+rel,date_time=(2026,10,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,data)
    with zipfile.ZipFile(zpath) as z:assert z.testzip() is None
    (out/(name+'.zip.sha256')).write_text(digest(zpath.read_bytes())+'  '+zpath.name+'\n')
    (out/'QUALITY_PROVENANCE.json').write_bytes(newdocs['QUALITY_PROVENANCE.json'])
    print('CLEAN_PACKAGE_OK',digest(zpath.read_bytes()),'retained_baseline_files',len(retained))
if __name__=='__main__':main()
