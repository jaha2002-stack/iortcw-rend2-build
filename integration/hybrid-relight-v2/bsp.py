#!/usr/bin/env python3
"""Read-only Wolfenstein SP IBSP v47 audit and conservative lightmap-mask planning.

No changes to BSPs, game PK3s, or source lightmaps. RTCW BSP is COMPILED data,
not original .map geometry nor independently tagged direct/indirect lighting.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zipfile

BSP_VERSION = 47
HEADER_LUMPS = 17
HEADER_SIZE = 8 + HEADER_LUMPS * 8
ATLAS_SIDE = 128
ATLAS_RGB_BYTES = ATLAS_SIDE * ATLAS_SIDE * 3
SURFACE_SIZE = 104
MST_PLANAR, MST_PATCH, MST_TRIANGLE_SOUP, MST_FLARE = 1, 2, 3, 4
SHADER_SIZE = 72
MAX_BSP_SIZE = 128 * 1024 * 1024
MAX_PK3_MAPS = 128
LUMP_ENTITIES = 0
LUMP_SHADERS = 1
LUMP_SURFACES = 13
LUMP_LIGHTMAPS = 14

# SP/code/qcommon/surfaceflags.h, ioRTCW pinned 438e7d413b5f7277187c35b032eb0ef9093ae778
SURF_SKY = 0x4
SURF_NODRAW = 0x80
SURF_NOLIGHTMAP = 0x400
SURF_NODLIGHT = 0x20000
SURF_GLASS = 0x200000
CONTENTS_LIQUIDS_FOG = 8 | 16 | 32 | 64
CONTENTS_TRANSLUCENT = 0x20000000
PROTECTED_NAME = re.compile(r'(water|liquid|river|stream|pool|ocean|sea|lava|slime|fog|sky|cloud|portal|mirror|glass|refraction|ice|translucent|decal|sprite|alpha|flare)', re.I)


class BspError(ValueError):
    pass


def require(value, message):
    if not value:
        raise BspError(message)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def tokenize_entities(text):
    """Entity-lump tokenizer (not a general .map parser)."""
    pattern = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/|[{}]')
    for m in pattern.finditer(text):
        tok = m.group()
        if tok.startswith('//') or tok.startswith('/*'):
            continue
        if tok.startswith('"'):
            yield ('str', tok[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            yield ('brace', tok)


def entities_from_lump(data):
    data = data.split(b'\x00', 1)[0].decode('latin1')
    entries = []
    opened = False
    pending = None
    props = {}
    for kind, token in tokenize_entities(data):
        if kind == 'brace':
            if token == '{':
                require(not opened and pending is None, 'nested or malformed BSP entity')
                opened, props = True, {}
            else:
                require(opened and pending is None, 'malformed BSP entity closing brace')
                opened = False
                entries.append(props)
        elif opened:
            if pending is None:
                pending = token
            else:
                props[pending] = token
                pending = None
    require(not opened and pending is None, 'truncated BSP entity lump')
    return entries


def light_sources(entities):
    found = []
    for idx, ent in enumerate(entities):
        classname = ent.get('classname', '')
        if classname.lower().startswith('light'):
            found.append({'index': idx, 'classname': classname,
                          'origin': ent.get('origin'), 'targetname': ent.get('targetname'),
                          'light': ent.get('light'), '_color': ent.get('_color'),
                          'style': ent.get('style')})
    return found


class BSP:
    def __init__(self, data, name='unknown.bsp'):
        require(isinstance(data, bytes) and HEADER_SIZE <= len(data) <= MAX_BSP_SIZE,
                'invalid size for RTCW BSP')
        require(data[:4] == b'IBSP', 'not an IBSP map')
        self.version, = struct.unpack_from('<I', data, 4)
        require(self.version == BSP_VERSION, 'RTCW SP needs IBSP v47 (found %s)' % self.version)
        self.name = name
        self.data = data
        self.sha256 = sha_bytes(data)
        self.lumps = []
        extents = []
        for i in range(HEADER_LUMPS):
            offset, size = struct.unpack_from('<ii', data, 8 + i * 8)
            require(offset >= 0 and size >= 0 and offset + size <= len(data),
                    'out-of-bounds BSP lump %d' % i)
            require(size == 0 or offset >= HEADER_SIZE,
                    'BSP lump overlaps header %d' % i)
            self.lumps.append((offset, size))
            if size:
                extents.append((offset, offset + size, i))
        extents.sort()
        for a, b in zip(extents, extents[1:]):
            require(a[1] <= b[0], 'overlapping BSP lumps %s/%s' % (a[2], b[2]))
        require(self.lumps[LUMP_SHADERS][1] % SHADER_SIZE == 0, 'invalid BSP shader lump size')
        require(self.lumps[LUMP_SURFACES][1] % SURFACE_SIZE == 0, 'invalid BSP surface lump size')
        require(self.lumps[LUMP_LIGHTMAPS][1] % ATLAS_RGB_BYTES == 0,
                'nonstandard BSP lightmap layout (no implicit conversion permitted)')
        self.entities = entities_from_lump(self.lump(LUMP_ENTITIES))
        self.shaders = []
        blob = self.lump(LUMP_SHADERS)
        for off in range(0, len(blob), SHADER_SIZE):
            rawname, surface_flags, content_flags = struct.unpack_from('<64sii', blob, off)
            name = rawname.split(b'\x00', 1)[0].decode('latin1')
            self.shaders.append({'name': name, 'surface_flags': surface_flags, 'content_flags': content_flags})
        self.surfaces = []
        blob = self.lump(LUMP_SURFACES)
        for off in range(0, len(blob), SURFACE_SIZE):
            fields = struct.unpack_from('<12i', blob, off)
            shader_id, fog_num, surface_type = fields[:3]
            lm_num, x, y, width, height = fields[7:12]
            require(0 <= shader_id < len(self.shaders), 'invalid shader index at surface %d' % (off//SURFACE_SIZE))
            require(surface_type in (MST_PLANAR, MST_PATCH, MST_TRIANGLE_SOUP, MST_FLARE),
                    'unknown BSP surface type at surface %d' % (off//SURFACE_SIZE))
            # RTCW flares (MST_FLARE=4) have no lightmap, but the retail BSP
            # encoder often writes lightmapNum=0 and a ZERO-SIZED rectangle.
            # This is valid native map data, not a corrupted lightmap.
            # Such flares must never own/edit even one lightmap texel.
            if surface_type != MST_FLARE:
                require(lm_num < self.num_lightmaps,
                        'invalid lightmap number at surface %d' % (off//SURFACE_SIZE))
                if lm_num >= 0:
                    require(0 <= x <= ATLAS_SIDE and 0 <= y <= ATLAS_SIDE and
                            width > 0 and height > 0 and x + width <= ATLAS_SIDE and y + height <= ATLAS_SIDE,
                            'invalid surface lightmap rectangle at surface %d' % (off//SURFACE_SIZE))
            self.surfaces.append({'id': off//SURFACE_SIZE, 'shader_id': shader_id,
                                  'shader': self.shaders[shader_id]['name'],
                                  'surface_type': surface_type, 'lightmap_id': lm_num,
                                  'rect': [x, y, width, height],
                                  'classification': self.surface_class(shader_id, surface_type, lm_num)})

    def lump(self, n):
        offset, size = self.lumps[n]
        return self.data[offset:offset+size]

    @property
    def num_lightmaps(self):
        return self.lumps[LUMP_LIGHTMAPS][1] // ATLAS_RGB_BYTES

    def surface_class(self, shader_id, surface_type, lm_id):
        sh = self.shaders[shader_id]
        flag = sh['surface_flags']
        content = sh['content_flags']
        if surface_type == MST_FLARE:
            return 'protected-flare'
        if lm_id < 0:
            return 'unlightmapped'
        if flag & (SURF_SKY | SURF_NODRAW | SURF_NOLIGHTMAP | SURF_NODLIGHT | SURF_GLASS):
            return 'protected-flags'
        if content & (CONTENTS_LIQUIDS_FOG | CONTENTS_TRANSLUCENT):
            return 'protected-content'
        if PROTECTED_NAME.search(sh['name']):
            return 'protected-name'
        if surface_type not in (MST_PLANAR, MST_PATCH, MST_TRIANGLE_SOUP):
            return 'protected-surface-type'
        return 'opaque-candidate'

    def summary(self, include_surfaces=False):
        counts = {}
        for surf in self.surfaces:
            key = surf['classification']
            counts[key] = counts.get(key, 0) + 1
        kinds = {}
        for s in self.surfaces:
            k = {MST_PLANAR: 'planar', MST_PATCH: 'patch',
                 MST_TRIANGLE_SOUP: 'triangle-soup', MST_FLARE: 'flare'}[s['surface_type']]
            kinds[k] = kinds.get(k, 0) + 1
        result = {'file': self.name, 'bsp_sha256': self.sha256, 'format': 'IBSP v47',
                  'byte_count': len(self.data), 'atlas_layout': '128x128 RGB8 per lightmap',
                  'lightmap_count': self.num_lightmaps, 'atlas_layout_sha256': self.atlas_layout_sha256, 'shader_count': len(self.shaders),
                  'surface_count': len(self.surfaces), 'surface_types': kinds,
                  'entity_count': len(self.entities),
                  'embedded_light_entity_count': len(light_sources(self.entities)),
                  'embedded_light_entities': light_sources(self.entities),
                  'surface_classes': counts,
                  'exact_indirect_layer_available': False,
                  'exact_per_source_direct_layers_available': False,
                  'limitations': ['Compiled BSP includes combined RGB lightmaps only',
                                  'A BSP entity lump is not a full editable .map source',
                                  'Original indirect/direct components require tagged rebake']}
        if include_surfaces:
            result['surfaces'] = self.surfaces
        return result

    @property
    def atlas_layout_sha256(self):
        """Identifies BSP shader indices and per-surface lightmap UV layout.

        Deliberately independent of pixel colors in the existing baked lightmaps.
        """
        digest = hashlib.sha256()
        digest.update(b'DW_HYBRID_RELIGHT_V2_IBSP47_LAYOUT_V1\0')
        digest.update(struct.pack('<I', self.num_lightmaps))
        digest.update(self.lump(LUMP_SHADERS))
        digest.update(self.lump(LUMP_SURFACES))
        return digest.hexdigest()

    def build_mask(self, atlas_id, surface_ids):
        """RGB lightmap atlas policy mask, not a relighting result.

        Coordinate convention: top-left 0,0, PGM row order top-to-bottom.
        Protected texels ALWAYS win when rectangles overlap.
        """
        require(0 <= atlas_id < self.num_lightmaps, 'invalid atlas ID')
        require(isinstance(surface_ids, list) and surface_ids, 'surface selection required')
        eligible = bytearray(ATLAS_SIDE * ATLAS_SIDE)
        protected = bytearray(ATLAS_SIDE * ATLAS_SIDE)
        requested = set(surface_ids)
        require(len(requested) == len(surface_ids), 'duplicate selected surface ID')
        for surf_id in requested:
            require(isinstance(surf_id, int) and 0 <= surf_id < len(self.surfaces),
                    'surface ID outside BSP')
            s = self.surfaces[surf_id]
            require(s['lightmap_id'] == atlas_id, 'surface %d on different atlas' % surf_id)
            require(s['classification'] == 'opaque-candidate',
                    'fail-closed surface %d: %s' % (surf_id, s['classification']))
        for surf in self.surfaces:
            if surf['lightmap_id'] != atlas_id:
                continue
            x,y,w,h = surf['rect']
            # Flare indices are not rendered through lightmaps, even if the BSP
            # carries a misleading lightmapNum=0. Their zero-area rectangle
            # cannot become an editable texel.
            if surf['surface_type'] == MST_FLARE:
                continue
            target = eligible if surf['id'] in requested else protected
            # Even if unselected lightmapped surfaces overlap, a selected texel
            # cannot be changed unless there are no other owners.
            for yy in range(y, y+h):
                start = yy*ATLAS_SIDE+x
                target[start:start+w] = b'\xff'*w
        # A lightmap texel shared with an unselected/protected surface must stay unchanged.
        selected_total = sum(1 for v in eligible if v)
        result = bytes(255 if v and not protected[i] else 0 for i,v in enumerate(eligible))
        return result, {'selected_surface_ids': sorted(requested), 'atlas_id': atlas_id,
                        'candidate_texels': selected_total, 'eligible_texels': result.count(255),
                        'clipped_overlapping_texels': selected_total-result.count(255),
                        'mask_origin': 'upper-left', 'width': ATLAS_SIDE, 'height': ATLAS_SIDE}


def audit_archive(path, only=None):
    require(path.is_file(), 'archive not found')
    results = []
    with zipfile.ZipFile(path) as z:
        entries = [x for x in z.infolist() if re.fullmatch(r'maps/[a-zA-Z0-9_\-]+\.bsp', x.filename, re.I)]
        map_source_names = [x.filename for x in z.infolist()
                            if re.fullmatch(r'maps/[a-zA-Z0-9_\-]+\.map', x.filename, re.I)]
        require(len(entries) <= MAX_PK3_MAPS, 'too many maps in archive')
        for e in entries:
            if only and Path(e.filename).stem.lower() not in only:
                continue
            require(e.file_size <= MAX_BSP_SIZE, 'BSP exceeds input size limit: '+e.filename)
            try:
                results.append(BSP(z.read(e), e.filename).summary())
            except (BspError, zipfile.BadZipFile) as exc:
                results.append({'file':e.filename,'error':str(exc)})
    result = {'archive':str(path), 'archive_sha256':sha_file(path),
            'map_count':len(results), 'maps':results,
            'source_map_available':bool(map_source_names), 'source_map_paths':map_source_names,
            'notes':'Original game BSPs contain combined lightmaps; .map source is usually not shipped.'}
    result['valid_map_count'] = sum('error' not in x for x in results)
    result['rejected_map_count'] = len(results) - result['valid_map_count']
    result['total_lightmaps'] = sum(x.get('lightmap_count', 0) for x in results)
    result['total_surface_count'] = sum(x.get('surface_count', 0) for x in results)
    result['total_embedded_light_entities'] = sum(x.get('embedded_light_entity_count', 0) for x in results)
    return result


def load_bsp(path, bsp_name=None):
    if path.suffix.lower() in ('.pk3','.zip'):
        require(bsp_name is not None, 'specify --map when reading a game PK3')
        member = 'maps/'+bsp_name+'.bsp'
        with zipfile.ZipFile(path) as z:
            info = z.getinfo(member)
            require(info.file_size <= MAX_BSP_SIZE, 'BSP exceeds size limit')
            return BSP(z.read(member), member)
    require(path.stat().st_size <= MAX_BSP_SIZE, 'BSP exceeds size limit')
    return BSP(path.read_bytes(), path.name)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sp = p.add_subparsers(dest='mode',required=True)
    a = sp.add_parser('audit-pk3',help='audit all RTCW BSP map entries in original PK3 (read-only)')
    a.add_argument('archive',type=Path)
    a.add_argument('--only',nargs='*',help='map names to scan (default all)')
    b = sp.add_parser('audit-bsp',help='audit an RTCW SP BSP or individual map in PK3')
    b.add_argument('input',type=Path)
    b.add_argument('--map',help='map basename if input is PK3')
    b.add_argument('--surfaces',action='store_true')
    m = sp.add_parser('make-mask',help='create fail-closed 128x128 lightmap mask')
    m.add_argument('input',type=Path)
    m.add_argument('--map',help='map basename if input is PK3')
    m.add_argument('--atlas',required=True,type=int)
    m.add_argument('--surface',nargs='+',required=True,type=int)
    m.add_argument('--out',required=True,type=Path)
    args = p.parse_args(argv)
    try:
        if args.mode == 'audit-pk3':
            result = audit_archive(args.archive, set(x.lower() for x in args.only) if args.only else None)
        else:
            bsp = load_bsp(args.input,args.map)
            if args.mode == 'audit-bsp':
                result = bsp.summary(include_surfaces=args.surfaces)
            else:
                mask,meta=bsp.build_mask(args.atlas,args.surface)
                args.out.parent.mkdir(parents=True,exist_ok=True)
                args.out.write_bytes(b'P5\n128 128\n255\n'+mask)
                result = {'status':'MASK_ONLY_NOT_RELIT','meta':meta,'sha256':sha_bytes(args.out.read_bytes()),
                          'bsp_sha256':bsp.sha256,'path':str(args.out)}
        print(json.dumps(result,indent=2,ensure_ascii=False))
        return 0
    except (BspError, KeyError, zipfile.BadZipFile, OSError, ValueError) as e:
        p.exit(2,'HYBRID_RELIGHT_BSP_REJECTED: %s\n'%e)


if __name__ == '__main__':
    sys.exit(main())
