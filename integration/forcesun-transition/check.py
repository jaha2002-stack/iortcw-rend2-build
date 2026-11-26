"""Exercise cascade selection and point-light shader state from the renderer source."""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

source = Path(sys.argv[1]).resolve()
renderer = source / 'SP/code/rend2'
scene = (renderer / 'tr_scene.c').read_text()
start = scene.index('static qboolean R_VolumetricSunMapSourceValid(')
end = scene.index('\nvoid RE_RenderScene(', start)

shade = (renderer / 'tr_shade.c').read_text()
forward = shade[shade.index('static void ForwardDlight( void )'):shade.index('static void ProjectPshadowVBOGLSL(')]
environment = forward.index('\n\t\t{\n\t\t\tvec4_t enableTextures;')
occlusion = forward.index('\n\t\tRB_BindDlightWorldOcclusion(sp, l);', environment)
tests = (
    ('cascades-test.c', '/* SUN_CASCADE_FUNCTIONS */', scene[start:end]),
    ('dlight-state-test.c', '/* POINT_LIGHT_ENVIRONMENT_SETUP */', forward[environment:occlusion]),
)

with TemporaryDirectory() as directory:
    for name, marker, implementation in tests:
        harness = Path(__file__).with_name(name).read_text()
        test = Path(directory) / name
        test.write_text(harness.replace(marker, implementation))
        executable = test.with_suffix('')
        subprocess.run([
            'cc', '-O2', '-Wall', '-Wextra', '-fsanitize=undefined',
            '-fno-sanitize-recover=undefined', '-DARCH_STRING="x86_64"',
            '-I', renderer, '-I', source / 'SP/code/SDL2/include', test, '-o', executable,
        ], check=True)
        subprocess.run([executable], check=True)
