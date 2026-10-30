#!/usr/bin/env python3
"""Exact RTCW flare handling and optional user-owned real-game fixture.

CI always runs the synthetic cases. User-owned original BSP assets are never
committed or downloaded by the public workflow; a local audit can opt in via
DW_RTCW_ORIGINAL_MAPS_ZIP environment variable.
"""
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import bsp
import policy


def make_test_bsp(extra_surface, invalid_other=False):
    shader=b'textures/stone/wall\0'.ljust(64,b'\0')+struct.pack('<ii',0,0)
    water=b'textures/liquids/water_norway\0'.ljust(64,b'\0')+struct.pack('<ii',0,32)
    def surface(shader_id,kind,y,rect=True):
        fields=[shader_id,-1,kind,0,4,0,6,0,0,y,128,64 if rect else 0]
        return struct.pack('<12i12f2i',*fields,*([0.0]*12),0,0)
    lumps=[b'']*17
    lumps[0] = b'{"classname" "worldspawn"}\n{"classname" "light" "origin" "0 0 32"}\n\0'
    lumps[1] = shader+water
    lumps[13] = (surface(0,1,0)+surface(1,1,64)+extra_surface)
    lumps[14] = b'\x40\x40\x40'*(128*128)
    out=bytearray(b'IBSP'+struct.pack('<i',47))
    start=8+17*8
    tail=bytearray()
    for b in lumps:
        out+=struct.pack('<ii',start,len(b));start+=len(b);tail+=b
    out+=tail
    return bytes(out)


def flare_surface():
    # The original RTCW retail maps write 0 as the flare lightmapNum even
    # though the flare rectangle is entirely empty.
    vals=[0,0,4,0,0,0,0,0,0,0,0,0]
    return struct.pack('<12i12f2i',*vals,*([0.0]*12),0,0)


class RetailFlareSafetyTests(unittest.TestCase):
    def test_retail_flare_zero_rect_is_valid_and_protected(self):
        world=bsp.BSP(make_test_bsp(flare_surface()),'norway.bsp')
        self.assertEqual(world.surfaces[2]['classification'],'protected-flare')
        self.assertEqual(world.summary()['surface_types']['flare'],1)
        mask,metadata=world.build_mask(0,[0])
        self.assertEqual(metadata['eligible_texels'],8192)
        self.assertEqual(mask.count(255),8192)
        with self.assertRaisesRegex(bsp.BspError,'fail-closed'):
            world.build_mask(0,[2])

    def test_planar_zero_rect_is_still_rejected(self):
        broken=bytearray(make_test_bsp(flare_surface()))
        off,_=struct.unpack_from('<ii',broken,8+13*8)
        # Planar second surface lightmap height -> 0
        struct.pack_into('<i',broken,off+104+44,0)
        with self.assertRaisesRegex(bsp.BspError,'invalid surface lightmap rectangle'):
            bsp.BSP(bytes(broken),'norway.bsp')

    def test_fail_closed_water_ownership(self):
        world=bsp.BSP(make_test_bsp(flare_surface()),'norway.bsp')
        atlases,masks=policy.atlas_ownership(world,return_masks=True)
        self.assertEqual(atlases[0]['safe_texels'],8192)
        self.assertEqual(atlases[0]['blocked_texels'],8192)
        self.assertEqual(masks[0].count(255),8192)
        doc=policy.map_policy(world)
        self.assertFalse(doc['unverified_bsp_light_entity_candidates'][0]['eligible_for_direct_light_subtraction'])
        self.assertEqual(doc['protected_water_shader_counts'],{'textures/liquids/water_norway':1})

    def test_overlapping_water_texel_wins_over_opaque_surface(self):
        data=bytearray(make_test_bsp(flare_surface()))
        off,_=struct.unpack_from('<ii',data,8+13*8)
        # Water is forced onto the EXACT same 128x64 texels as selected stone.
        # A single shared texel must be excluded; changing both violates policy.
        struct.pack_into('<i',data,off+104+9*4,0)
        world=bsp.BSP(bytes(data),'norway.bsp')
        atlas,_=policy.atlas_ownership(world)
        self.assertEqual(atlas[0]['candidate_texels'],8192)
        self.assertEqual(atlas[0]['overlap_clipped_texels'],8192)
        self.assertEqual(atlas[0]['safe_texels'],0)
        mask,meta=world.build_mask(0,[0])
        self.assertEqual(mask.count(255),0)
        self.assertEqual(meta['clipped_overlapping_texels'],8192)

    def test_source_candidates_not_promoted_without_tagged_bake(self):
        world=bsp.BSP(make_test_bsp(flare_surface()),'norway.bsp')
        a=policy.retained_source_candidates(world)
        b=policy.retained_source_candidates(world)
        self.assertEqual(a,b)
        self.assertEqual(len(a),1)
        self.assertFalse(a[0]['eligible_for_direct_light_subtraction'])
        self.assertTrue(a[0]['candidate_id'].startswith('bsp-norway-'))

    def test_no_editor_source_is_not_misrepresented(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            original=root/'retail.zip'
            with zipfile.ZipFile(original,'w') as z:
                z.writestr('maps/norway.bsp',make_test_bsp(flare_surface()))
            output=root/'out'
            doc=policy.audit_all(original,output)
            self.assertFalse(doc['source_map_available'])
            self.assertEqual(doc['map_count'],1)
            self.assertTrue((output/'norway_PREFLIGHT.json').is_file())
            self.assertEqual(json.loads((output/'norway_PREFLIGHT.json').read_text())['status'],
                             'PREFLIGHT_ONLY_NO_BAKED_LIGHT_REMOVAL')
            with self.assertRaisesRegex(bsp.BspError,'already exists'):
                policy.audit_all(original,output)

    def test_optional_original_32_map_retail_regression(self):
        path=os.environ.get('DW_RTCW_ORIGINAL_MAPS_ZIP')
        if not path:
            self.skipTest('user-owned original maps are not committed to CI')
        with zipfile.ZipFile(path) as pack:
            names=[x.filename for x in pack.infolist() if x.filename.lower().endswith('.bsp')]
            self.assertEqual(len(names),32)
            expected={'norway':(8972,92,79,55,226),
                      'escape1':(15321,42,665,7,None),
                      'factory':(9077,20,240,208,None)}
            for entry in names:
                world=bsp.BSP(pack.read(entry),entry)
                self.assertGreater(world.num_lightmaps,0)
                self.assertGreater(len(world.surfaces),0)
                if Path(entry).stem in expected:
                    surfs,lightmaps,lights,fl,water=expected[Path(entry).stem]
                    self.assertEqual((len(world.surfaces),world.num_lightmaps,
                                      len(bsp.light_sources(world.entities)),
                                      world.summary()['surface_types'].get('flare',0)),
                                      (surfs,lightmaps,lights,fl))
                    if water is not None:
                        self.assertEqual(sum(s['shader']=='textures/liquids/water_norway'
                                             for s in world.surfaces),water)
                        self.assertTrue(all(s['classification']!='opaque-candidate'
                                             for s in world.surfaces if 'water_norway' in s['shader']))

if __name__ == '__main__':
    unittest.main(verbosity=2)
