"""Compile and link affected Rend2 programs using the engine's GLSL aliases."""
from argparse import ArgumentParser
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

parser = ArgumentParser()
parser.add_argument('source', type=Path)
args = parser.parse_args()
root = args.source / 'SP/code/rend2/glsl'
programs = (
    ('volumetriclocal', 'volumetriclocal', ''),
    ('volumetriclocal', 'volumetriclocal_upscale', ''),
    ('volumetricsun', 'volumetricsun',
     '#define USE_SHADOW_CASCADE\n#define r_shadowMapSize 1024.0\n#define r_shadowCascadeZFar 1024.0\n'),
)
with TemporaryDirectory() as directory:
    for version in (120, 130, 150):
        for vertex, fragment, defines in programs:
            paths = []
            for stage, name, suffix in (('vert', vertex, 'vp'), ('frag', fragment, 'fp')):
                header = f'#version {version}\n#define M_PI 3.14159265358979323846\n'
                if version == 120:
                    header += '#define shadow2D(a,b) shadow2D(a,b).r\n'
                elif stage == 'vert':
                    header += '#define attribute in\n#define varying out\n'
                else:
                    header += ('#define varying in\nout vec4 out_Color;\n#define gl_FragColor out_Color\n'
                               '#define texture2D texture\n#define textureCubeLod textureLod\n#define shadow2D texture\n')
                path = Path(directory) / f'{name}-{version}.{stage}'
                path.write_text(header + defines + (root / f'{name}_{suffix}.glsl').read_text())
                paths.append(path)
            subprocess.run(['glslangValidator', '-l', *paths], check=True)
