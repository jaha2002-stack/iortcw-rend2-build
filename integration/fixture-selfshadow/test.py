"""Run renderer policy functions with synthetic scene state and test the patch scope."""
import hashlib
import re
from pathlib import Path
import subprocess
import sys
import tempfile


def function(path, name):
    source = path.read_text()
    start = re.search(rf'^(?:static )?\w+ {name}\(', source, re.M).start()
    brace = source.index('{', start)
    depth = 0
    for token in re.finditer(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[{}]',
                             source[brace:], re.S):
        if token[0] == '{':
            depth += 1
        elif token[0] == '}':
            depth -= 1
            if not depth:
                return source[start:brace + token.end()]
    raise ValueError(name)


source = Path(sys.argv[1])
root = source / 'SP/code/rend2'
functions = {
    'tr_main.c': ['R_ElectricCapturePolicy', 'R_ElectricFixtureForCapture',
                  'R_DlightWorldCacheMatches', 'R_FireVolProductionCacheMatchesHint'],
    'tr_iflc_self.inc': ['R_IFLC_PickBodySurface', 'R_IFLC_CustomFixture', 'R_IFLC_SuppressCustom'],
}
with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    harness = Path(__file__).with_name('policy_test.c').read_text()
    actual = '\n\n'.join(function(root / filename, name)
                         for filename, names in functions.items() for name in names)
    program = work / 'policy.c'
    program.write_text(harness.replace('/* RENDERER_FUNCTIONS */', actual))
    for flags in (['-O2', '-ffast-math'], ['-O1', '-fsanitize=undefined']):
        executable = work / 'policy'
        subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', '-g', *flags,
                        '-fno-sanitize-recover=undefined', str(program), '-lm', '-o', str(executable)], check=True)
        subprocess.run([executable], check=True)

# Verify out-of-scope renderer and game code against the production source index.
allowed = {f'SP/code/rend2/{name}' for name in (
    'tr_main.c', 'tr_local.h', 'tr_scene.c', 'tr_iflc.inc', 'tr_iflc_self.inc', 'tr_elss.inc',
)}
changed = set()
entries = 0
for line in (source / 'SOURCE_SHA256SUMS.txt').read_text().splitlines():
    digest, path = line.split('  ', 1)
    if hashlib.sha256((source / path).read_bytes()).hexdigest() != digest:
        changed.add(path)
    entries += 1
assert changed == allowed, changed
print(f'PASS exact source scope: {entries - len(changed)} production files unchanged')
