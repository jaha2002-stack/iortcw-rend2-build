"""Replace only Rend2 in the validated full Win64 runtime for testing."""
from argparse import ArgumentParser
from pathlib import Path
import json
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'localvol-production'))
from prepare import checksum_index, digest, inspect_binaries, inspect_configs, unpack

parser = ArgumentParser()
parser.add_argument('baseline', type=Path)
parser.add_argument('renderer', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--commit', required=True)
parser.add_argument('--run', required=True)
args = parser.parse_args()

baseline_sha = 'b1a40500ea1ef1c4a90b4236c5e4f0d93ffadbb7c1d1838656f34cce904af8e7'
assert digest(args.baseline.read_bytes()) == baseline_sha
base = unpack(args.baseline)
assert checksum_index({n: d for n, d in base.items() if n != 'SHA256SUMS.txt'}) == base['SHA256SUMS.txt']
manifest = json.loads(base['PRODUCTION_MANIFEST.json'])
assert manifest['tested_build_run'] == 45778124832
renderer = 'renderer_sp_rend2_x64.dll'
new_renderer = args.renderer.read_bytes()
assert new_renderer != base[renderer] and b'USE_SUN_MULTISAMPLE_DEPTH' in new_renderer
assert b'volumetricsun_coverage' in new_renderer and b'stableLampJitter' in new_renderer

docs = Path(__file__).resolve().parent
files = {n: d for n, d in base.items() if n not in {
    'SHA256SUMS.txt', 'PRODUCTION_MANIFEST.json', 'PRODUCTION_RELEASE_FINALIZATION_REPORT_RU.md',
}}
files['docs/BASE_PRODUCTION_MANIFEST.json'] = base['PRODUCTION_MANIFEST.json']
files[renderer] = new_renderer
runtime = {n for n in base if Path(n).suffix.lower() in {'.exe', '.dll', '.cfg', '.bat', '.glsl'}}
assert all(files[n] == base[n] for n in runtime - {renderer})
inspect_configs(files)
expected = manifest['binary_and_import_audit']
expected[renderer]['sha256'] = digest(new_renderer)
with tempfile.TemporaryDirectory() as directory:
    audit = inspect_binaries(Path(directory), files, {'architecture_and_imports': expected})
files['README_SUN_EDGE_TEST_RU.md'] = (docs / 'README_RU.md').read_bytes()
files['SUN_EDGE_TECH_REPORT_RU.md'] = (docs / 'TECH_REPORT_RU.md').read_bytes()
files['SUN_EDGE_TEST_MANIFEST.json'] = (json.dumps({
    'status': 'WIN64_TEST_CANDIDATE',
    'accepted_base_run': 45778124832,
    'base_production_zip_sha256': baseline_sha,
    'patch_sha256': digest((docs / 'fix.patch').read_bytes()),
    'test_build_commit': args.commit,
    'test_build_run': args.run,
    'only_runtime_file_replaced': renderer,
    'binary_audit': audit,
}, ensure_ascii=False, indent=2) + '\n').encode()
assert not any(n.lower().endswith(('.pk3', '.pk4', '.log', '.pdb')) or n.lower().startswith('main/dw_ai/') for n in files)
files['SHA256SUMS.txt'] = checksum_index(files)
args.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for name, data in sorted(files.items()):
        archive.writestr(f'{args.output.stem}/{name}', data)
assert unpack(args.output) == files
args.output.with_suffix('.zip.sha256').write_text(f'{digest(args.output.read_bytes())}  {args.output.name}\n')
print(f'PASS {len(files)} files, only Rend2 changed, all 8 PE modules verified')
