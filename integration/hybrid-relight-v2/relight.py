#!/usr/bin/env python3
"""DarkWolf Hybrid Relight V2: conservative offline tagged-bake compositor.

This tool does NOT derive direct light from a pre-existing RGB lightmap.
It requires independently tagged direct/indirect contributions from ONE bake.
It never edits game files, BSP files, or production renderers.
"""
import argparse
import bsp as rtcw_bsp
import array
from contextlib import ExitStack
import shutil
import tempfile
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

SCHEMA = 'darkwolf.hybrid-relight.v2.tagged-bake.v1'
BASE_COMMIT = 'c653433e1b0a29b2f43f29a240b96a8192acb617'
BASE_RUN = 41019985033
HEX256 = re.compile(r'^[a-f0-9]{64}$')


class RelightError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise RelightError(message)


def checksum(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for buf in iter(lambda: f.read(1048576), b''):
            h.update(buf)
    return h.hexdigest()


def inside(root, path):
    require(isinstance(path, str) and path and '\\' not in path, 'path must be a relative POSIX path')
    p = Path(path)
    require(not p.is_absolute() and '..' not in p.parts, 'unsafe relative path: ' + path)
    resolved = (root / p).resolve()
    require(resolved.is_relative_to(root.resolve()), 'path escaped manifest root: ' + path)
    require(resolved.is_file(), 'missing file: ' + path)
    return resolved


def hex_sha(value, key):
    require(isinstance(value, str) and HEX256.fullmatch(value) is not None, 'invalid SHA256 for ' + key)


def checked_file(root, name, hashes):
    p = inside(root, name)
    want = hashes.get(name)
    hex_sha(want, name)
    got = checksum(p)
    require(got == want, 'SHA256 mismatch for ' + name)
    return p


def words(data):
    # .map entity key-value pairs exist only at entity depth 1; brushes are nested.
    pattern = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/|[{}]|[^\s{}"]+')
    for m in pattern.finditer(data):
        token = m.group()
        if token.startswith('//') or token.startswith('/*'):
            continue
        if token.startswith('"'):
            yield ('string', token[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            yield ('syntax', token)


def parse_map(path):
    contents = path.read_text('utf-8', errors='replace')
    depth, pending, props, entities = 0, None, None, []
    for typ, val in words(contents):
        if val == '{' and typ == 'syntax':
            if depth == 0:
                props, pending = {}, None
            depth += 1
        elif val == '}' and typ == 'syntax':
            require(depth > 0, 'unexpected closing map brace')
            if depth == 1:
                require(pending is None, 'unpaired entity property')
                entities.append(props)
                props = None
            depth -= 1
        elif depth == 1 and typ == 'string':
            if pending is None:
                pending = val
            else:
                props[pending] = val
                pending = None
    require(depth == 0 and len(entities) > 0, 'unbalanced or empty .map')
    result = []
    for index, props in enumerate(entities):
        classname = props.get('classname', '')
        if classname.lower().startswith('light'):
            serialized = json.dumps(props, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
            signature = hashlib.sha256(serialized.encode()).hexdigest()
            result.append({'entity_index': index, 'classname': classname,
                           'origin': props.get('origin', ''), 'targetname': props.get('targetname', ''),
                           'entity_signature_sha256': signature,
                           'source_id': 'map-entity-' + str(index) + '-' + signature[:16]})
    return {'source_map_sha256': checksum(path), 'entity_count': len(entities),
            'map_light_candidates': result,
            'limitations': 'Shader-emissive, sun, skylight and bounce sources require tagged compiler provenance.'}


class PFM:
    def __init__(self, path):
        self.file = path.open('rb')
        require(self.file.readline() == b'PF\n', 'RGB PFM (PF) required: ' + str(path))
        dims = self.file.readline().split()
        require(len(dims) == 2, 'invalid PFM dimensions')
        self.width, self.height = [int(x) for x in dims]
        require(0 < self.width <= 16384 and 0 < self.height <= 16384, 'invalid PFM extent')
        scale = float(self.file.readline().strip())
        require(math.isfinite(scale) and scale != 0.0 and abs(scale) == 1.0,
                'PFM scale must be +1/-1 for unambiguous linear RGB')
        self.little = scale < 0.0
        self.offset = self.file.tell()
        expected = self.offset + self.width * self.height * 12
        require(path.stat().st_size == expected, 'PFM data length mismatch: ' + str(path))

    def row(self, index):
        require(0 <= index < self.height, 'PFM row out of bounds')
        self.file.seek(self.offset + index * self.width * 12)
        data = self.file.read(self.width * 12)
        floats = array.array('f')
        floats.frombytes(data)
        if (sys.byteorder == 'little') != self.little:
            floats.byteswap()
        for val in floats:
            require(math.isfinite(val) and val >= 0.0, 'nonfinite/negative linear irradiance')
        return floats

    def close(self):
        self.file.close()


class PGM:
    def __init__(self, path):
        self.file = path.open('rb')
        require(self.file.readline() == b'P5\n', 'binary PGM (P5) required for texel mask')
        # Require a canonical header (no comments) for deterministic tagged export.
        dims = self.file.readline().split()
        require(len(dims) == 2, 'invalid PGM dimensions')
        self.width, self.height = [int(x) for x in dims]
        require(self.file.readline() == b'255\n', 'PGM mask must have maxvalue 255')
        self.offset = self.file.tell()
        require(path.stat().st_size == self.offset + self.width * self.height, 'PGM data size mismatch')

    def row(self, index):
        # PFM is stored bottom row FIRST, PGM is stored top row FIRST.
        # Match both conventions by exposing PGM as bottom-up to the compositor.
        require(0 <= index < self.height, 'PGM row out of bounds')
        self.file.seek(self.offset + (self.height - 1 - index) * self.width)
        return self.file.read(self.width)

    def close(self):
        self.file.close()


class atlas_mask_reader:
    def __init__(self, path):
        self.image = PGM(path)
    def __enter__(self):
        return self.image
    def __exit__(self, exc_type, exc, tb):
        self.image.close()


def write_pfm_row(f, floats):
    data = array.array('f', floats)
    if sys.byteorder != 'little':
        data.byteswap()
    f.write(data.tobytes())


def validate_manifest(path):
    require(path.is_file(), 'manifest not found')
    obj = json.loads(path.read_text('utf-8'))
    require(obj.get('schema') == SCHEMA, 'invalid tagged bake schema')
    require(obj.get('base_run') == BASE_RUN and obj.get('base_commit') == BASE_COMMIT,
            'incorrect base: must derive from Actions #41019985033 exact SHA')
    name = obj.get('map_name')
    require(isinstance(name, str) and re.fullmatch('[a-zA-Z0-9_-]{1,60}', name), 'invalid map name')
    compiler = obj.get('compiler', {})
    require(compiler.get('tagged_direct_indirect') is True and
            compiler.get('same_radiosity_solution') is True and
            compiler.get('color_space') == 'linear-rgb' and
            compiler.get('output_units') == 'irradiance',
            'V2 requires same-solution tagged direct/indirect linear irradiance, not independent bake guesses')
    require(isinstance(compiler.get('build_id'), str) and compiler.get('build_id').strip(),
            'tagged compiler build ID required')
    hex_sha(obj.get('atlas_layout_sha256'), 'atlas_layout_sha256')
    root = path.parent
    hashes = obj.get('file_sha256')
    require(isinstance(hashes, dict), 'file_sha256 must pin every input file')
    source_map = checked_file(root, obj.get('source_map'), hashes)
    source_bsp = checked_file(root, obj.get('source_bsp'), hashes)
    require(source_map.suffix.lower() == '.map' and source_bsp.suffix.lower() == '.bsp',
            'V2 requires an original .map and matching compiled .bsp')
    bsp = rtcw_bsp.BSP(source_bsp.read_bytes(), source_bsp.name)
    require(source_map.stem.lower() == name.lower() == source_bsp.stem.lower(),
            'source map/BSP identity mismatch')
    require(bsp.atlas_layout_sha256 == obj.get('atlas_layout_sha256'),
            'BSP atlas layout does not match tagged bake')
    audit = parse_map(source_map)
    require(isinstance(obj.get('atlases'), list) and obj['atlases'], 'no tagged atlases')
    registry = obj.get('source_registry', [])
    require(isinstance(registry, list), 'source_registry must be a list')
    ids = set()
    map_source_ids = {x['source_id'] for x in audit['map_light_candidates']}
    for item in registry:
        sid, kind = item.get('id'), item.get('kind')
        require(isinstance(sid, str) and sid and sid not in ids, 'invalid/duplicate source ID')
        require(kind in ('map-light', 'shader-sun', 'shader-emissive'), 'unknown light source kind')
        if kind == 'map-light':
            require(sid in map_source_ids, 'map light ID not matched to source .map')
        else:
            require(isinstance(item.get('shader_name'), str) and item['shader_name'] and
                    isinstance(item.get('shader_file'), str), 'shader source provenance missing')
            checked_file(root, item['shader_file'], hashes)
        ids.add(sid)
    atlas_ids = set()
    for atlas in obj['atlases']:
        aid = atlas.get('id')
        require(isinstance(aid, str) and re.fullmatch('[a-zA-Z0-9_-]{1,40}', aid) and aid not in atlas_ids,
                'invalid/duplicate atlas ID')
        atlas_ids.add(aid)
        require(type(atlas.get('lightmap_index')) is int and 0 <= atlas['lightmap_index'] < bsp.num_lightmaps,
                'invalid lightmap index for ' + aid)
        chosen = atlas.get('selected_surface_ids')
        try:
            expected_mask, policy = bsp.build_mask(atlas['lightmap_index'], chosen)
            require(policy['eligible_texels'] > 0, 'no eligible surface texels remain after safety clipping')
        except rtcw_bsp.BspError as e:
            raise RelightError('unsafe BSP surface selection: ' + str(e)) from e
        for key in ('full', 'indirect', 'unselected_direct', 'eligible_mask'):
            checked_file(root, atlas.get(key), hashes)
        with atlas_mask_reader(inside(root, atlas['eligible_mask'])) as png_mask:
            require((png_mask.width, png_mask.height) == (128, 128), 'only native 128x128 RTCW lightmaps supported')
            # Use top-to-bottom bytes to match mask builder, not PFM row order.
            for i in range(128):
                require(png_mask.row(127-i) == expected_mask[i*128:(i+1)*128],
                        'eligible mask does not exactly match fail-closed BSP surface ownership')
        sources = atlas.get('selected_direct', [])
        require(isinstance(sources, list), 'selected_direct must be array')
        seen = set()
        for src in sources:
            sid = src.get('source_id')
            require(sid in ids and sid not in seen, 'unknown/duplicate selected source ID')
            seen.add(sid)
            fraction = src.get('remove_fraction')
            require(type(fraction) in (int, float) and math.isfinite(fraction) and 0.0 <= fraction <= 1.0,
                    'remove_fraction out of 0..1')
            checked_file(root, src.get('file'), hashes)
    return obj, audit


def compose(manifest, output, check_only=False):
    obj, map_audit = validate_manifest(manifest)
    root = manifest.parent
    output = output.resolve()
    require(output != root.resolve() and root.resolve() not in output.parents,
            'output must be outside immutable tagged-bake input directory')
    if not check_only:
        require(not output.exists(), 'output path already exists; refusing to overwrite')
        output.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix='.hybrid-v2-pending-', dir=output.parent))
    else:
        temp_dir = None
    results = []
    try:
        results = _compose_atlases(obj, root, temp_dir, check_only)
        report = {'status': 'TAGGED_BAKE_PARITY_PASS', 'base_run': BASE_RUN, 'base_commit': BASE_COMMIT,
                  'schema': SCHEMA, 'map': obj['map_name'], 'map_source_audit': map_audit,
                  'production_renderer_modified': False, 'atlases': results,
                  'tagged_compiler_claim_only': 'Baking provenance is asserted by manifest; the bake producer must be audited separately.'}
        if temp_dir is not None:
            (temp_dir / 'HYBRID_RELIGHT_V2_REPORT.json').write_text(json.dumps(report, indent=2) + '\n', 'utf-8')
            temp_dir.rename(output)
            temp_dir = None
        return report
    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)


def _compose_atlases(obj, root, temp_dir, check_only):
    results = []
    for atlas in obj['atlases']:
        with ExitStack() as stack:
            def op(name):
                x = PFM(inside(root, name))
                stack.callback(x.close)
                return x
            full = op(atlas['full'])
            indirect = op(atlas['indirect'])
            keep = op(atlas['unselected_direct'])
            mask = PGM(inside(root, atlas['eligible_mask']))
            stack.callback(mask.close)
            tagged = [(src, op(src['file'])) for src in atlas['selected_direct']]
            for x in [indirect, keep] + [reader for _, reader in tagged] + [mask]:
                require((x.width, x.height) == (full.width, full.height),
                        'atlas dimensions mismatch: ' + atlas['id'])
            require(full.width == 128 and full.height == 128,
                    'native RTCW 128x128 atlas dimensions required')
            target_name = obj['map_name'] + '_' + atlas['id'] + '_relit.pfm'
            target = temp_dir / target_name if temp_dir is not None else None
            f = None
            if not check_only:
                f = stack.enter_context(target.open('wb'))
                f.write(('PF\n%d %d\n-1.0\n' % (full.width, full.height)).encode('ascii'))
            max_abs_err = 0.0
            max_rel_err = 0.0
            removed_energy = 0.0
            eligible_count = 0
            for row in range(full.height):
                original = full.row(row)
                retained = keep.row(row)
                indirect_row = indirect.row(row)
                mask_row = mask.row(row)
                selected_rows = [(src, img.row(row)) for src, img in tagged]
                outrow = array.array('f', original)
                for x in range(full.width):
                    eligibility = mask_row[x] / 255.0
                    if eligibility:
                        eligible_count += 1
                    for c in range(3):
                        k = 3*x+c
                        reconstructed = indirect_row[k] + retained[k]
                        for _, samples in selected_rows:
                            reconstructed += samples[k]
                        err = abs(reconstructed - original[k])
                        max_abs_err = max(max_abs_err, err)
                        max_rel_err = max(max_rel_err, err / max(original[k], 0.00001))
                        # Linear HDR source parity must pass before subtraction is trusted.
                        require(err <= 0.0001 + 0.00001*max(original[k], reconstructed),
                                'tagged decomposition differs from full bake at atlas %s row %d x %d channel %d'
                                % (atlas['id'], row, x, c))
                        subtraction = sum(samples[k]*eligibility*src['remove_fraction']
                                          for src, samples in selected_rows)
                        val = original[k] - subtraction
                        require(val >= -0.0001, 'negative relight energy; incorrect tagged bake')
                        outrow[k] = max(0.0, val)
                        removed_energy += subtraction
                if f is not None:
                    write_pfm_row(f, outrow)
        info = {'atlas_id': atlas['id'], 'lightmap_index': atlas['lightmap_index'], 'width': full.width, 'height': full.height,
                'eligible_texels': eligible_count, 'max_decomposition_abs_error': max_abs_err,
                'max_decomposition_rel_error': max_rel_err,
                'removed_rgb_energy': removed_energy, 'output': target_name if not check_only else None}
        if not check_only:
            info['output_sha256'] = checksum(target)
        results.append(info)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    audit = sub.add_parser('audit-map', help='inspect .map light entity candidates; NOT a light solve')
    audit.add_argument('map', type=Path)
    bake = sub.add_parser('compose', help='verify and compose same-solve tagged bake')
    bake.add_argument('manifest', type=Path)
    bake.add_argument('--out', required=True, type=Path)
    bake.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.action == 'audit-map':
            report = parse_map(args.map)
        else:
            report = compose(args.manifest, args.out, args.check_only)
    except (RelightError, rtcw_bsp.BspError, FileNotFoundError, OSError, json.JSONDecodeError, ValueError) as err:
        parser.exit(2, 'HYBRID_RELIGHT_V2_REJECTED: %s\n' % err)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
