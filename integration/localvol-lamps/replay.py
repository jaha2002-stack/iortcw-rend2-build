"""Reuse the accepted renderer build workflow at its exact source revision."""
import argparse
import os
import subprocess
from pathlib import Path

import yaml

parser = argparse.ArgumentParser()
parser.add_argument('kit', type=Path)
parser.add_argument('phase', choices=('prepare', 'build'))
args = parser.parse_args()

base = '250669a231dc7bd571b4e2b3405c045f90ba64c1'
actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.kit, text=True).strip()
if actual != base:
    raise SystemExit(f'Expected accepted commit {base}, found {actual}')

workflow = args.kit / '.github/workflows/DW_LAMP_CONTROL_V12_EXACT_VISIBLE_WIN64_TEST.yml'
job = yaml.load(workflow.read_text(), Loader=yaml.BaseLoader)['jobs']['build-test-package']
steps = {step['name']: step['run'] for step in job['steps'] if 'run' in step}
phases = {
    'prepare': ('Pin exact accepted Owner and Texture integrations',
                'Reconstruct exact Final V2 source postimage',
                'Apply Lamp Control V1 renderer-only patch'),
    'build': ('Build Win64 renderer',),
}

for name in phases[args.phase]:
    print(name, flush=True)
    command = steps[name]
    if name == 'Reconstruct exact Final V2 source postimage':
        command = command.replace('rm -rf source evidence\n', 'test ! -e source && test ! -e evidence\n')
    subprocess.run(
        ['bash', '-c', command],
        cwd=args.kit,
        env={**os.environ, 'DLO_OWNER_SHA': job['env']['DLO_OWNER_SHA'], 'TEXTURE_SHA': job['env']['TEXTURE_SHA']},
        check=True,
    )
