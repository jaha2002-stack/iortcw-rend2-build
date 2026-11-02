#!/usr/bin/env python3
"""Fail-closed source inventory. Source identity is not runtime/GPU validation."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

EXPECTED = frozenset({
    'SP/code/rend2/glsl/ssgi_fp.glsl',
    'SP/code/rend2/glsl/volumetriclocal_fp.glsl',
    'SP/code/rend2/glsl/volumetricsun_fp.glsl',
    'SP/code/rend2/tr_main.c',
    'SP/code/rend2/tr_scene.c',
})
FORBIDDEN = (b'DWPERF_FRAME', b'DWPERF_PROBE', b'DWPERF_CFG',
             b'DARKWOLF_V446_FULL_PERF_TELEMETRY_V01', b'DARKWOLF_TESTLAB_V0_1')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(root):
    folder = root / 'SP/code'
    require(folder.is_dir(), f'Missing source directory: {folder}')
    files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(folder.rglob('*')) if p.is_file()}
    require(bool(files), 'Empty source inventory')
    return files


def compare_inventories(candidate, baseline, expected=EXPECTED):
    require(bool(candidate) and bool(baseline), 'Empty source inventory')
    added = sorted(candidate.keys() - baseline.keys())
    deleted = sorted(baseline.keys() - candidate.keys())
    require(not added and not deleted, f'Source file set changed: added={added}, deleted={deleted}')
    changed = sorted(n for n in candidate if candidate[n] != baseline[n])
    require(set(changed) == set(expected), f'Unexpected source delta: {changed}')
    changed_shaders = [n for n in changed if n.endswith('.glsl')]
    return {'status': 'PASS', 'scope': 'SP/code inventory and SHA256 comparison',
            'source_file_count': len(baseline), 'added': added, 'deleted': deleted,
            'changed': changed, 'changed_shaders': changed_shaders,
            'all_other_source_files_byte_identical': True,
            'shaders_byte_identical': not changed_shaders,
            'unchanged_shaders_byte_identical': True,
            'changed_sha256': {n: candidate[n] for n in changed}, 'GPU_VALIDATION': 'NOT_RUN'}


def validate(root, baseline):
    result = compare_inventories(inventory(root), inventory(baseline))
    tracked = subprocess.check_output(
        ['git', '-C', str(root), 'diff', '--name-only', 'HEAD', '--'], text=True).splitlines()
    require(set(tracked) == EXPECTED, f'Tracked delta outside allowlist: {tracked}')
    untracked = subprocess.check_output(
        ['git', '-C', str(root), 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
    require(not untracked, f'Unexpected untracked source: {untracked}')
    lock = json.loads((Path(__file__).parent / 'baseline_source_manifest.json').read_text())
    tree = subprocess.check_output(
        ['git', '-C', str(baseline), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
    require(tree == lock['baseline_source_tree'], 'Baseline tree differs from provenance lock')
    result['baseline_source_tree'] = tree
    for p in (root / 'SP/code/rend2').rglob('*'):
        if p.is_file():
            data = p.read_bytes()
            require(not any(x in data for x in FORBIDDEN), f'Forbidden instrumentation: {p}')
    scene = (root / 'SP/code/rend2/tr_scene.c').read_text()
    main = (root / 'SP/code/rend2/tr_main.c').read_text()
    require('R_StaticPromoteReportIfChanged(' not in scene, 'Dead report writer returned')
    require('selectionSignature * 33' not in scene, 'Dead report signature returned')
    require(main.count('s_dwShadowGroupLabelsActive = qtrue;') == 1, 'Cache activation count changed')
    require(main.count('s_dwShadowGroupLabelsActive = qfalse;') == 2, 'Cache deactivation count changed')
    start = main.index('s_dwShadowGroupLabelsActive = qtrue;')
    end = main.index('s_dwShadowGroupLabelsActive = qfalse;', start)
    require('return;' not in main[start:end], 'Early return leaves cache active')
    markers = {
        'volumetriclocal_upscale_fp.glsl': ['DARKWOLF_VOLUMETRIC_COVERAGE_AA_FINAL_V1'],
        'ssgi_fp.glsl': ['DARKWOLF_V446_OPT09_SHARED_RAW_DEPTH'],
        'volumetriclocal_fp.glsl': ['DARKWOLF_V446_OPT04_LOCALVOL_LOOP_INVARIANTS',
                                  'DARKWOLF_V446_OPT06_FIRE_GAUSSIAN_SQRT_ELIMINATION'],
        'volumetricsun_fp.glsl': ['DARKWOLF_V446_OPT02_SUN_TRANSMITTANCE_RECURRENCE'],
    }
    for name, expected in markers.items():
        text = (root / 'SP/code/rend2/glsl' / name).read_text()
        require(all(m in text for m in expected), f'Missing source marker: {name}')
    require((root / 'SP/code/rend2/glsl/ssgi_fp.glsl').read_text().count('SsgiAccumulate(vec2(') == 12,
            'SSGI sample-call contract changed')
    require('DarkWolf_InjectIngameSystemRend2Tab' in (root / 'SP/code/ui/ui_shared.c').read_text(),
            'In-game Rend2 UI missing')
    require('+safe' in (Path(__file__).parent / 'RUN_DARKWOLF_OPTIMIZED_CLEAN.bat').read_text(),
            'Safe launcher missing')
    return result


def main():
    if len(sys.argv) != 4:
        raise SystemExit('usage: validate_source.py <candidate> <baseline> <evidence>')
    root, baseline, out = map(Path, sys.argv[1:])
    out.mkdir(parents=True, exist_ok=True)
    try:
        result = validate(root, baseline)
    except Exception as exc:
        result = {'status': 'FAIL', 'error': f'{type(exc).__name__}: {exc}'}
    (out / 'source-policy.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
