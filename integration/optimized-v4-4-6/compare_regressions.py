#!/usr/bin/env python3
"""Require real capture coverage before comparing inherited/new analyzer failures.

Unsynchronized animation/exposure means pixel errors are descriptive, not proof
of visual equivalence. Synthetic unit fixtures never establish game acceptance.
"""
from pathlib import Path
import hashlib
import json
import re
import sys
from PIL import Image, ImageChops, ImageStat

SCENARIOS = {'ring': 128, 'table-baseline': 16, 'table-exclude742': 16, 'table-exclude744': 16}
SHA256 = re.compile(r'^[0-9a-f]{64}$')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rgb(path):
    with Image.open(path) as image:
        image.load()
        return image.convert('RGB')


def captures(folder):
    rows = read_json(folder / 'scenario-results.json')
    require(isinstance(rows, list) and len(rows) == len(SCENARIOS), f'{folder}: incomplete scenario records')
    by_name, paths = {}, {}
    for row in rows:
        name = row.get('scenario')
        require(name in SCENARIOS and name not in by_name, f'{folder}: duplicate/unknown scenario {name}')
        expected = SCENARIOS[name]
        require(row.get('status') == 'CAPTURED' and row.get('exit_code') == 0, f'{name}: capture did not succeed')
        require(row.get('capture_ready') is True, f'{name}: missing capture-ready proof')
        require(row.get('expected') == expected and row.get('screenshots') == expected,
                f'{name}: incorrect declared coverage')
        resolution = row.get('resolution')
        require(isinstance(resolution, list) and len(resolution) == 2 and
                all(type(n) is int and n > 0 for n in resolution), f'{name}: invalid resolution')
        require(isinstance(row.get('hardware'), str) and bool(row['hardware']), f'{name}: missing hardware')
        require(bool(SHA256.fullmatch(row.get('preset_sha256', ''))), f'{name}: invalid preset hash')
        binaries = row.get('binary_sha256')
        require(isinstance(binaries, dict) and bool(binaries) and
                all(isinstance(v, str) and SHA256.fullmatch(v) for v in binaries.values()),
                f'{name}: invalid binary provenance')
        require(any('rend2' in k and k.endswith('.so') for k in binaries), f'{name}: Rend2 hash missing')
        directory = folder / name / 'screenshots'
        pngs = {p.stem: p for p in directory.glob('*.png')}
        tgas = {p.stem: p for p in directory.glob('*.tga')}
        require(len(pngs) == expected and pngs.keys() == tgas.keys(),
                f'{folder}/{name}: incomplete or unexpected PNG/TGA file set ({len(pngs)}/{expected})')
        for stem, path in sorted(pngs.items()):
            image, raw = rgb(path), rgb(tgas[stem])
            require(list(image.size) == resolution, f'{path}: dimensions differ from provenance')
            require(raw.size == image.size and ImageChops.difference(raw, image).getbbox() is None,
                    f'{path}: PNG does not reproduce engine TGA pixels')
            paths[path.relative_to(folder).as_posix()] = path
        by_name[name] = row
    require(set(by_name) == set(SCENARIOS), f'{folder}: missing scenario')
    require((folder / 'table-analyzer-exit-code.txt').read_text().strip() == '0', f'{folder}: table analyzer failed')
    return by_name, paths


def analyzer(folder):
    value = read_json(folder / 'ring/analysis.json')
    failures = value.get('failures')
    require(isinstance(failures, list) and all(isinstance(f, str) for f in failures), 'Invalid failure list')
    require(value.get('status') == ('FAIL' if failures else 'PASS'), f'{folder}: inconsistent analyzer status')
    return value


def compare(root):
    a, b = root / 'baseline-source-regression', root / 'source-regression'
    meta_a, images_a = captures(a)
    meta_b, images_b = captures(b)
    require(images_a.keys() == images_b.keys(), 'A/B image names do not match')
    require(len(images_a) == sum(SCENARIOS.values()), 'Incomplete A/B image population')
    for name in SCENARIOS:
        ra, rb = meta_a[name], meta_b[name]
        for key in ('preset_sha256', 'hardware', 'resolution'):
            require(ra[key] == rb[key], f'{name}: A/B {key} mismatch')
        ka = {k: v for k, v in ra['binary_sha256'].items() if 'rend2' in k and k.endswith('.so')}
        kb = {k: v for k, v in rb['binary_sha256'].items() if 'rend2' in k and k.endswith('.so')}
        require(ka.keys() == kb.keys() and ka != kb, f'{name}: absent or identical renderer identity')
    baseline, candidate = analyzer(a), analyzer(b)
    new = sorted(set(candidate['failures']) - set(baseline['failures']))
    rows = []
    for rel, pa in sorted(images_a.items()):
        pb = images_b[rel]
        ia, ib = rgb(pa), rgb(pb)
        require(ia.size == ib.size, f'A/B image size mismatch: {rel}')
        stat = ImageStat.Stat(ImageChops.difference(ia, ib))
        rows.append({'image': rel, 'mean_abs_rgb_0_255': sum(stat.mean) / 3,
                     'baseline_sha256': hashlib.sha256(pa.read_bytes()).hexdigest(),
                     'candidate_sha256': hashlib.sha256(pb.read_bytes()).hexdigest()})
    return {'gate': 'FAIL' if new else 'PASS_NO_NEW_ANALYZER_FAILURES',
            'capture_integrity': 'PASS', 'paired_image_count': len(rows),
            'expected_paired_images': sum(SCENARIOS.values()),
            'baseline_analyzer_status': baseline['status'], 'candidate_analyzer_status': candidate['status'],
            'baseline_failures': baseline['failures'], 'candidate_failures': candidate['failures'],
            'new_failures': new, 'images': rows,
            'semantic_acceptance': 'PASS' if not baseline['failures'] and not candidate['failures'] else 'NOT_ACCEPTED',
            'scope': 'Mesa capture integrity and analyzer regression comparison only. Animation, wall-clock '
                     'and exposure are not synchronized; pixel errors are descriptive, not visual acceptance.',
            'GPU_PERFORMANCE': 'NOT_RUN', 'WINDOWS_RUNTIME': 'NOT_RUN', 'VISUAL_ACCEPTANCE': 'NOT_RUN'}


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: compare_regressions.py <evidence>')
    root = Path(sys.argv[1])
    root.mkdir(parents=True, exist_ok=True)
    try:
        result = compare(root)
    except Exception as exc:
        result = {'gate': 'FAIL', 'capture_integrity': 'FAIL', 'error': f'{type(exc).__name__}: {exc}',
                  'VISUAL_ACCEPTANCE': 'NOT_RUN'}
    (root / 'regression-comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'images'}, indent=2))
    return 0 if result['gate'] == 'PASS_NO_NEW_ANALYZER_FAILURES' else 1


if __name__ == '__main__':
    raise SystemExit(main())
