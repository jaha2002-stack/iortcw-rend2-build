#!/usr/bin/env python3
"""DarkWolf Hybrid Relight V2 Stage 1: read-only compiled-BSP safety inventory.

This is NOT a light solver. The files it creates contain provenance and
permission masks only. They cannot reconstruct indirect lighting from retail
8-bit lightmaps and must not be used as a replacement for source-tagged baking.

No original game geometry, texture, lightmap RGB pixels or executable is
written. All outputs are compact derived metadata and optional binary masks.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

import bsp

SCHEMA = 'darkwolf.hybrid-relight.v2.bsp-preflight.v1'
PINNED_RUN = 41019985033
PINNED_COMMIT = 'c653433e1b0a29b2f43f29a240b96a8192acb617'


def require(value, msg):
    if not value:
        raise bsp.BspError(msg)


def retained_source_candidates(world):
    """BSP entity candidates, NOT matched tagged bake source IDs.

    The compiler may have stripped/reordered entities; these are *not* proof
    that source .map indices, shader emissives or bounce attribution match.
    """
    out = []
    for idx, ent in enumerate(world.entities):
        classname = ent.get('classname', '')
        if not classname.lower().startswith('light'):
            continue
        payload = json.dumps(ent, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        source_hash = hashlib.sha256(payload.encode()).hexdigest()
        out.append({
            'candidate_id': 'bsp-%s-%05d-%s' %
                (Path(world.name).stem.lower(), idx, source_hash[:16]),
            'entity_index': idx,
            'entity_signature_sha256': source_hash,
            'classname': classname,
            'origin': ent.get('origin'),
            'color': ent.get('_color'),
            'light': ent.get('light'),
            'targetname': ent.get('targetname'),
            'source_bake_identity_verified': False,
            'eligible_for_direct_light_subtraction': False,
        })
    return out


def _mark(buffer, rect):
    x,y,w,h = rect
    for row in range(y,y+h):
        i = row*bsp.ATLAS_SIDE+x
        buffer[i:i+w] = b'\xff'*w


def atlas_ownership(world, return_masks=False):
    """Summarize lightmap texel ownership without reading or changing RGB.

    Any overlap between an opaque candidate and a protected/non-selected
    surface is treated as blocked. This gate is geometric conservatism;
    analysis of ownership is not evidence of sufficient lighting to relight.
    """
    n = world.num_lightmaps
    side_sq = bsp.ATLAS_SIDE**2
    candidate = [bytearray(side_sq) for _ in range(n)]
    blocked = [bytearray(side_sq) for _ in range(n)]
    stats = [Counter() for _ in range(n)]
    for surf in world.surfaces:
        i = surf['lightmap_id']
        if i < 0 or surf['surface_type'] == bsp.MST_FLARE:
            continue
        if surf['classification'] == 'opaque-candidate':
            _mark(candidate[i], surf['rect'])
            stats[i]['opaque_candidate_surfaces'] += 1
        else:
            _mark(blocked[i], surf['rect'])
            stats[i]['blocked_surfaces'] += 1
            if surf['shader'].lower().find('water') >= 0 or surf['classification'] == 'protected-content':
                stats[i]['water_or_other_protected_contents_surfaces'] += 1
    mask_dict = {} if return_masks else None
    atlases = []
    for i in range(n):
        c, b = candidate[i], blocked[i]
        safe = bytes(255 if cv and not b[k] else 0 for k,cv in enumerate(c))
        candidates = c.count(255)
        blocked_count = b.count(255)
        safe_count = safe.count(255)
        info = {'lightmap_index':i,
                'opaque_candidate_surfaces':stats[i]['opaque_candidate_surfaces'],
                'blocked_surfaces':stats[i]['blocked_surfaces'],
                'water_or_other_protected_contents_surfaces': stats[i]['water_or_other_protected_contents_surfaces'],
                'candidate_texels':candidates, 'blocked_texels':blocked_count,
                'safe_texels':safe_count,
                'overlap_clipped_texels':candidates-safe_count,
                'safe_mask_sha256':bsp.sha_bytes(safe),
                'tagged_bake_availability':'UNAVAILABLE_UNTIL_SOURCE_TAGGED_REBAKE'}
        require(info['safe_texels'] + info['overlap_clipped_texels'] == candidates,
                'internal atlas clipping invariant broken')
        atlases.append(info)
        if return_masks:
            mask_dict[i] = b'P5\n128 128\n255\n'+safe
    return atlases, mask_dict


def map_policy(world, include_registry=True, include_atlases=True):
    inventory = world.summary()
    registry = retained_source_candidates(world)
    a, _ = atlas_ownership(world)
    safe = sum(x['safe_texels'] for x in a)
    total = sum(x['candidate_texels'] for x in a)
    protected_names = Counter(s['shader'] for s in world.surfaces
                              if s['classification'].startswith('protected')
                              and 'water' in s['shader'].lower())
    result = {
        'schema':SCHEMA,'base_run':PINNED_RUN,'base_commit':PINNED_COMMIT,
        'map_name':Path(world.name).stem.lower(),
        'bsp_sha256':world.sha256,'atlas_layout_sha256':world.atlas_layout_sha256,
        'ibsp_version':47,'compiled_map_only':True,
        'lightmap_count':world.num_lightmaps,
        'surface_count':len(world.surfaces),
        'surface_types':inventory['surface_types'],
        'surface_classes':inventory['surface_classes'],
        'embedded_light_candidates':len(registry),
        'safe_candidate_texels':safe,
        'candidate_texels':total,
        'overlap_blocked_texels':total-safe,
        'protected_water_shader_counts':dict(sorted(protected_names.items())),
        'status':'PREFLIGHT_ONLY_NO_BAKED_LIGHT_REMOVAL',
        'blocked_steps':['original .map absent',
                         'no verified source-tagged direct/indirect exporter',
                         'no per-light source attribution',
                         'no runtime relit-lightmap import'],
        'guardrails':{
            'preserve_water_sky_fog_transparency':True,
            'not_a_relight_result':True,
            'legacy_maplighting_profiles_not_migrated':True,
            'original_bsp_not_modified':True,
            'source_registry_requires_editor_map_match':True}
    }
    if include_registry:
        result['unverified_bsp_light_entity_candidates'] = registry
    if include_atlases:
        result['atlas_ownership'] = a
    return result


def audit_all(original, out, only=None):
    require(original.is_file(), 'input PK3/ZIP missing')
    require(not out.exists(), 'output already exists, refusing overwrite')
    out.mkdir(parents=True)
    try:
        with zipfile.ZipFile(original) as pack:
            members = [x for x in pack.infolist() if re.fullmatch('maps/[a-zA-Z0-9_-]+\\.bsp',x.filename,re.I)]
            source_map_count = sum(bool(re.fullmatch(r'maps/[a-zA-Z0-9_-]+\.map', x.filename, re.I)) for x in pack.infolist())
            require(0 < len(members) <= bsp.MAX_PK3_MAPS, 'no recognized BSPs or too many')
            members.sort(key=lambda x:x.filename.lower())
            inventory=[]
            for entry in members:
                stem=Path(entry.filename).stem.lower()
                if only is not None and stem not in only:
                    continue
                require(entry.file_size <= bsp.MAX_BSP_SIZE, 'BSP larger than safe bound')
                world=bsp.BSP(pack.read(entry),entry.filename)
                details=map_policy(world)
                (out/(stem+'_PREFLIGHT.json')).write_text(json.dumps(details,indent=2,sort_keys=True)+'\n',encoding='utf-8')
                slim={k:v for k,v in details.items() if k not in ('unverified_bsp_light_entity_candidates','atlas_ownership')}
                inventory.append(slim)
        require(inventory,'selected map not found in archive')
        report={'schema':SCHEMA,'archive_sha256':bsp.sha_file(original),
                'source_map_available':source_map_count > 0,
                'base_run':PINNED_RUN,'base_commit':PINNED_COMMIT,
                'map_count':len(inventory), 'maps':inventory,
                'proprietary_game_assets_embedded':False,
                'renderer_binary_modified':False}
        (out/'ALL_MAPS_INVENTORY.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        return report
    except Exception:
        # Preserve non-destructive audit semantics: a failed analysis must not
        # leave results that can be mistaken for a complete or accepted audit.
        import shutil
        shutil.rmtree(out,ignore_errors=True)
        raise


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path)
    p.add_argument('--out',type=Path,required=True,help='new output directory (will not overwrite)')
    p.add_argument('--only',nargs='*',help='optional map names (e.g. norway escape1)')
    args=p.parse_args(argv)
    try:
        result=audit_all(args.archive,args.out,{
            x.lower() for x in args.only} if args.only else None)
        print(json.dumps({'status':'HYBRID_RELIGHT_V2_RETAIL_BSP_PREFLIGHT_PASS',
                          'base_run':result['base_run'],
                          'map_count':result['map_count'],
                          'output':str(args.out)},indent=2))
    except (bsp.BspError, zipfile.BadZipFile, OSError, ValueError) as e:
        p.exit(2,'HYBRID_RELIGHT_V2_PREFLIGHT_REJECTED: %s\n'%e)
    return 0

if __name__=='__main__':
    sys.exit(main())
