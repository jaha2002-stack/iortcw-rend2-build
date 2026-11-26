"""Exercise the renderer's real sun-source selection with deterministic shadow captures."""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

source = Path(sys.argv[1]).resolve()
renderer = source / 'SP/code/rend2'
scene = (renderer / 'tr_scene.c').read_text()
start = scene.index('static qboolean R_VolumetricSunMapSourceValid(')
end = scene.index('\nvoid RE_RenderScene(', start)
harness = Path(__file__).with_name('cascades-test.c').read_text()

with TemporaryDirectory() as directory:
    test = Path(directory) / 'cascades-test.c'
    test.write_text(harness.replace('/* SUN_CASCADE_FUNCTIONS */', scene[start:end]))
    executable = test.with_suffix('')
    subprocess.run([
        'cc', '-O2', '-Wall', '-Wextra', '-fsanitize=undefined',
        '-fno-sanitize-recover=undefined', '-DARCH_STRING="x86_64"',
        '-I', renderer, '-I', source / 'SP/code/SDL2/include', test, '-o', executable,
    ], check=True)
    subprocess.run([executable], check=True)
