#!/usr/bin/env python3
"""Synthetic-only tests. Never embed or modify proprietary RTCW game assets."""
import array
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bsp
import relight


def shader(name, flags=0, content=0):
    raw = name.encode('ascii')
    assert len(raw) < 64
    return struct.pack('<64sii',raw,flags,content)


def surface(shader_num, y, height=64):
    fields = [shader_num, -1, 1, 0, 4, 0, 6, 0, 0, y, 128, height]
    return struct.pack('<12i12f2i', *fields, *([0.0]*12), 0, 0)


def make_bsp(path, bad_version=False):
    lumps = [b''] * 17
    lumps[0] = (b'{"classname" "worldspawn"}\n'
                b'{"classname" "light" "origin" "3 4 5" "light" "250"}\n\0')
    lumps[1] = shader('textures/stone/wall')+shader('textures/liquids/water',content=32)
    lumps[13] = surface(0, 0) + surface(1, 64)
    lumps[14] = bytes([90,90,90]) * (128*128)
    header = bytearray(b'IBSP' + struct.pack('<i', 46 if bad_version else 47))
    body = bytearray()
    offset = 8+17*8
    for item in lumps:
        header += struct.pack('<ii', offset, len(item))
        body += item
        offset += len(item)
    payload=bytes(header+body)
    path.write_bytes(payload)
    return payload


def make_pfm(path, value_fn):
    with path.open('wb') as f:
        f.write(b'PF\n128 128\n-1.0\n')
        for bottom_y in range(128):
            out=array.array('f')
            for x in range(128):
                v=value_fn(x,bottom_y)
                out.extend([v,v,v])
            if sys.byteorder != 'little':out.byteswap()
            f.write(out.tobytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HybridV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base/'input'
        self.root.mkdir()
        self.bsp_path = self.root/'norway.bsp'
        make_bsp(self.bsp_path)
        self.bsp = bsp.BSP(self.bsp_path.read_bytes(), self.bsp_path.name)
        self.map_path=self.root/'norway.map'
        self.map_path.write_text('''{
"classname" "worldspawn"
{ ( 0 0 0 ) ( 0 10 0 ) ( 0 10 10 ) textures/stone/wall 0 0 0 1 1 }
}
{
"classname" "light"
"origin" "3 4 5"
"light" "250"
}
''',encoding='utf-8')
        self.eligible_mask, self.mask_meta = self.bsp.build_mask(0,[0])
        (self.root/'eligible.pgm').write_bytes(b'P5\n128 128\n255\n'+self.eligible_mask)
        # Bottom PFM row = underwater, upper PFM row = wall.
        make_pfm(self.root/'full.pfm', lambda x,y: 0.6 if y < 64 else 0.9)
        make_pfm(self.root/'indirect.pfm', lambda x,y: 0.3)
        make_pfm(self.root/'keep.pfm', lambda x,y: 0.2)
        make_pfm(self.root/'light_01.pfm', lambda x,y: 0.1 if y < 64 else 0.4)
        source_id=relight.parse_map(self.map_path)['map_light_candidates'][0]['source_id']
        files=['norway.bsp','norway.map','eligible.pgm','full.pfm','indirect.pfm','keep.pfm','light_01.pfm']
        self.manifest={'schema': relight.SCHEMA, 'base_run':relight.BASE_RUN,
                       'base_commit':relight.BASE_COMMIT, 'map_name':'norway',
                       'atlas_layout_sha256':self.bsp.atlas_layout_sha256,
                       'source_map':'norway.map','source_bsp':'norway.bsp',
                       'file_sha256':{f:sha(self.root/f) for f in files},
                       'compiler':{'tagged_direct_indirect':True,
                                   'same_radiosity_solution':True,
                                   'color_space':'linear-rgb','output_units':'irradiance',
                                   'build_id':'synthetic-ci-fixture-NOT-production'},
                       'source_registry':[{'id':source_id,'kind':'map-light'}],
                       'atlases':[{'id':'atlas000','lightmap_index':0,'selected_surface_ids':[0],
                                   'full':'full.pfm','indirect':'indirect.pfm',
                                   'unselected_direct':'keep.pfm','eligible_mask':'eligible.pgm',
                                   'selected_direct':[{'source_id':source_id,
                                                       'remove_fraction':1.0,'file':'light_01.pfm'}]}]}
        self.manifest_path=self.root/'manifest.json'
        self.save_manifest()

    def save_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest,indent=2),encoding='utf8')

    def test_bsp_audit_and_water_protection(self):
        audit=self.bsp.summary()
        self.assertEqual(audit['lightmap_count'],1)
        self.assertEqual(audit['embedded_light_entity_count'],1)
        self.assertEqual(audit['surface_classes']['protected-content'],1)
        self.assertEqual(self.mask_meta['eligible_texels'],128*64)
        self.assertEqual(self.eligible_mask.count(255),128*64)
        with self.assertRaisesRegex(bsp.BspError,'fail-closed'):
            self.bsp.build_mask(0,[1])

    def test_read_original_pk3_bsp_entries(self):
        archive=self.base/'original-maps.pk3'
        with zipfile.ZipFile(archive,'w') as z:
            z.write(self.bsp_path,'maps/norway.bsp')
            z.writestr('scripts/common.shader','non-map')
        r=bsp.audit_archive(archive)
        self.assertEqual(r['map_count'],1)
        self.assertEqual(r['maps'][0]['bsp_sha256'],self.bsp.sha256)
        self.assertFalse(r['source_map_available'])

    def test_accept_tagged_bake_and_preserve_water(self):
        output=self.base/'output'
        report=relight.compose(self.manifest_path,output)
        self.assertEqual(report['status'],'TAGGED_BAKE_PARITY_PASS')
        out=relight.PFM(output/'norway_atlas000_relit.pfm')
        self.addCleanup(out.close)
        self.assertAlmostEqual(out.row(0)[0],0.6,places=5)  # water unchanged
        self.assertAlmostEqual(out.row(127)[0],0.5,places=5) # wall direct removed
        self.assertEqual(report['atlases'][0]['eligible_texels'],8192)
        self.assertEqual(report['map_source_audit']['entity_count'],2)

    def test_check_only_writes_nothing(self):
        output=self.base/'not-written'
        r=relight.compose(self.manifest_path,output,check_only=True)
        self.assertEqual(r['status'],'TAGGED_BAKE_PARITY_PASS')
        self.assertFalse(output.exists())

    def test_parity_mismatch_fails_without_partial(self):
        make_pfm(self.root/'full.pfm',lambda x,y: 0.7 if y<64 else 0.9)
        self.manifest['file_sha256']['full.pfm']=sha(self.root/'full.pfm')
        self.save_manifest()
        out=self.base/'should_not_exist'
        with self.assertRaisesRegex(relight.RelightError,'decomposition differs'):
            relight.compose(self.manifest_path,out)
        self.assertFalse(out.exists())

    def test_hash_corruption_fails(self):
        (self.root/'light_01.pfm').write_bytes(b'broken')
        with self.assertRaisesRegex(relight.RelightError,'SHA256 mismatch'):
            relight.compose(self.manifest_path,self.base/'out')

    def test_mask_corruption_fails(self):
        data=bytearray((self.root/'eligible.pgm').read_bytes())
        data[-1]=255  # a water texel must not be eligible
        (self.root/'eligible.pgm').write_bytes(data)
        self.manifest['file_sha256']['eligible.pgm']=sha(self.root/'eligible.pgm')
        self.save_manifest()
        with self.assertRaisesRegex(relight.RelightError,'eligible mask'):
            relight.compose(self.manifest_path,self.base/'out')

    def test_missing_map_source_fails(self):
        self.map_path.unlink()
        with self.assertRaisesRegex(relight.RelightError,'missing file'):
            relight.compose(self.manifest_path,self.base/'out')

    def test_wrong_bsp_version_fails(self):
        make_bsp(self.bsp_path, bad_version=True)
        self.manifest['file_sha256']['norway.bsp']=sha(self.bsp_path)
        self.save_manifest()
        with self.assertRaisesRegex(bsp.BspError,'v47'):
            relight.compose(self.manifest_path,self.base/'out')

    def test_wrong_base_fails(self):
        self.manifest['base_run']=40878732886
        self.save_manifest()
        with self.assertRaisesRegex(relight.RelightError,'incorrect base'):
            relight.compose(self.manifest_path,self.base/'out')

    def test_no_overwrite_existing_output(self):
        out=self.base/'out';out.mkdir();(out/'sentinel.txt').write_text('keep')
        with self.assertRaisesRegex(relight.RelightError,'already exists'):
            relight.compose(self.manifest_path,out)
        self.assertEqual((out/'sentinel.txt').read_text(),'keep')

    def test_cannot_modify_inputs(self):
        with self.assertRaisesRegex(relight.RelightError,'outside'):
            relight.compose(self.manifest_path,self.root/'output')


if __name__=='__main__':
    unittest.main(verbosity=2)
