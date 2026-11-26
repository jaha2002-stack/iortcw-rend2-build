"""Compile SunVol legacy and coverage paths against the Rend2 GLSL dialects."""
from argparse import ArgumentParser
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

parser = ArgumentParser()
parser.add_argument('source', type=Path)
args = parser.parse_args()
root = args.source / 'SP/code/rend2/glsl'
cases = ((120, 'legacy'), (130, 'legacy'), (150, 'legacy'),
         (120, 'coverage'), (130, 'coverage'), (150, 'coverage'), (150, 'msaa'))
with TemporaryDirectory() as directory:
    for version, mode in cases:
        for cascades in (False, True):
            options = '#define r_shadowMapSize 1024.0\n#define r_shadowCascadeZFar 1024.0\n'
            if cascades:
                options += '#define USE_SHADOW_CASCADE\n'
            if mode != 'legacy':
                options += '#define USE_SUN_COVERAGE_RESOLVE\n'
            if mode == 'msaa':
                options += '#define USE_SUN_MULTISAMPLE_DEPTH\n'
            paths = []
            for stage, suffix in (('vert', 'vp'), ('frag', 'fp')):
                header = f'#version {version}\n#define M_PI 3.14159265358979323846\n'
                if version == 120:
                    header += '#define shadow2D(a,b) shadow2D(a,b).r\n'
                elif stage == 'vert':
                    header += '#define attribute in\n#define varying out\n'
                else:
                    header += ('#define varying in\nout vec4 out_Color;\n#define gl_FragColor out_Color\n'
                               '#define texture2D texture\n#define textureCubeLod textureLod\n#define shadow2D texture\n')
                path = Path(directory) / f'{mode}-{version}-{int(cascades)}.{stage}'
                path.write_text(header + options + (root / f'volumetricsun_{suffix}.glsl').read_text())
                paths.append(path)
            subprocess.run(['glslangValidator', '-l', *paths], check=True)
