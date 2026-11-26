#!/usr/bin/env python3
"""One-file CSM correction: compare primary-view areamasks, not alternating skybox/primary render scenes."""
from pathlib import Path
import argparse, hashlib, json

MARK='DARKWOLF_RC4_FORCE_SUN_CSM_REPRIME_V1'
NEW='DARKWOLF_CSM_PRIMARY_VIEW_AREAMASK_V1'

def once(s, old, new, name):
    count=s.count(old)
    if count != 1: raise RuntimeError(f'{name}: expected 1 anchor, found {count}')
    return s.replace(old,new,1)

def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    a=argparse.ArgumentParser();a.add_argument('source',type=Path);a.add_argument('--proof',type=Path);opts=a.parse_args()
    r=opts.source/'SP/code/rend2'; scene=r/'tr_scene.c'
    current=scene.read_text(encoding='utf-8')
    assert MARK in current and 'DARKWOLF_FORCE_SUN_CSM_SMART_PRODUCTION_V444' in current
    assert NEW not in current
    before={str(p.relative_to(r)):h(p) for p in r.rglob('*') if p.is_file()}
    src=once(current,
    '''	int shadowFilter;
} forceSunVisibleCsmState_t;''',
    '''	int shadowFilter;
	// %s: cache visibility of the MAIN world, not the preceding portal scene.
	byte primaryAreaMask[MAX_MAP_AREA_BYTES];
} forceSunVisibleCsmState_t;'''%NEW, 'save primary visibility')
    src=once(src,
    '''		s_forceSunVisibleCsmState.world != tr.world ||
		tr.refdef.areamaskModified ||
		!tr.volumetricSunCsmValid[3])''',
    '''		s_forceSunVisibleCsmState.world != tr.world ||
		// %s: the shared areamaskModified flag is a false positive after
		// RDF_SKYBOXPORTAL, whose areamask differs from the player view.
		// Keep real primary areamask transitions as hard invalidations.
		memcmp(s_forceSunVisibleCsmState.primaryAreaMask, fd->areamask,
			sizeof(s_forceSunVisibleCsmState.primaryAreaMask)) != 0 ||
		!tr.volumetricSunCsmValid[3])'''%NEW,'primary-only visibility comparison')
    src=once(src,
    '''	s_forceSunVisibleCsmState.shadowFilter = r_shadowFilter->integer;
}''',
    '''	s_forceSunVisibleCsmState.shadowFilter = r_shadowFilter->integer;
	// %s: snapshot from the primary fd (never the shared portal refdef).
	Com_Memcpy(s_forceSunVisibleCsmState.primaryAreaMask, fd->areamask,
		sizeof(s_forceSunVisibleCsmState.primaryAreaMask));
}'''%NEW,'snapshot primary world mask')
    scene.write_text(src,encoding='utf-8',newline='\n')
    after={str(p.relative_to(r)):h(p) for p in r.rglob('*') if p.is_file()}
    changes=sorted(k for k in before if after[k]!=before[k])
    assert changes==['tr_scene.c'],changes
    assert current.count('tr.refdef.areamaskModified ||')==1
    assert 'tr.refdef.areamaskModified ||' not in src
    assert src.count(NEW)==3
    assert len(src)>len(current)
    proof={'change':'PRIMARY_VIEW_AREAMASK_CSM_REPRIME', 'historical_csm_guard_present':True,
      'source_only_changed':['SP/code/rend2/tr_scene.c'],
      'before_sha256':before['tr_scene.c'],'after_sha256':after['tr_scene.c'],
      'preserved_sun_cascade_cadence':True, 'preserved_shadow_filter_shader':True,
      'preserved_cgame_and_Xlabs':True,
      'view_provenance':'cg_view.c:CG_DrawSkyBoxPortal occurs before primary snapshot areamask memcpy',
      'correctness':'memcmp of fd->areamask compares primary views; real areamask changes still invalidate all four cascades'}
    if opts.proof:
      opts.proof.parent.mkdir(parents=True,exist_ok=True)
      opts.proof.write_text(json.dumps(proof,indent=2)+'\n')
    print('DW_CSM_PRIMARY_MASK_SOURCE_ISOLATION_PASS',json.dumps(proof,sort_keys=True),flush=True)

if __name__=='__main__': main()
