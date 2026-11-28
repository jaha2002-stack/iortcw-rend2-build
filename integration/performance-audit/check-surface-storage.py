"""Exercise the renderer's actual enqueue, growth and sort code under sanitizers."""

from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

rend2 = Path(sys.argv[1]) / 'SP/code/rend2'
main = (rend2 / 'tr_main.c').read_text(encoding='latin-1')
header = (rend2 / 'tr_local.h').read_text(encoding='latin-1')
initial = re.search(r'^#define\s+INITIAL_DRAWSURFS\s+(0x[0-9a-fA-F]+)$', header, re.M)[1]
sort = main[main.index('static void R_RadixSort('):main.index('typedef struct drawSurfBuffer_s')]
storage = main[main.index('typedef struct drawSurfBuffer_s'):
               main.index('/*\n=================\nR_DecomposeSort')]

prefix = r'''
#include <assert.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#define qfalse 0
#define qtrue 1
#define ARRAY_LEN(a) ((int)(sizeof(a) / sizeof((a)[0])))
#define Com_Memcpy memcpy
#define ERR_DROP 1
#define QSORT_SHADERNUM_SHIFT 18
#define QSORT_ATI_TESS_SHIFT 17
#define QSORT_FOGNUM_SHIFT 2
#define QSORT_PSHADOW_SHIFT 1

typedef int qboolean;
typedef int surfaceType_t;
typedef struct { int sortedIndex; } shader_t;
typedef struct {
    unsigned sort;
    int cubemapIndex;
    unsigned mapLightingKey;
    surfaceType_t *surface;
} drawSurf_t;

static struct {
    struct { int numDrawSurfs; drawSurf_t *drawSurfs; } refdef;
    unsigned shiftedEntityNum;
} tr;
static struct { drawSurf_t drawSurfs[INITIAL_DRAWSURFS]; } base, *backEndData = &base;

static void fail(int severity, const char *message, ...) {
    (void)severity;
    fputs(message, stderr);
    abort();
}

static struct { void (*Error)(int, const char *, ...); } ri = {fail};
static int growths;
static void DwPerfDrawStorageGrowth(int previous, int capacity) {
    assert(capacity == previous * 2);
    ++growths;
}
'''

harness = r'''
int main(void) {
    shader_t shader = {0};
    surfaceType_t surface = 42;
    drawSurf_t *pending, *portalParent;
    const int initial = INITIAL_DRAWSURFS;
    const int total = initial * 2 + 123;
    tr.refdef.drawSurfs = R_DrawSurfStorage();
    pending = tr.refdef.drawSurfs;
    portalParent = NULL;
    for (int i = 0; i < total; ++i) {
        shader.sortedIndex = 2 - i % 3;
        R_AddDrawSurf(&surface, &shader, 0, 0, 0, i, 0);
        tr.refdef.drawSurfs[i].mapLightingKey = i + 1;
        if (i == initial)
            portalParent = tr.refdef.drawSurfs + initial;
    }
    assert(growths == 2 && tr.refdef.numDrawSurfs == total);
    assert(pending == base.drawSurfs && pending[0].cubemapIndex == 0);
    assert(pending[initial - 1].cubemapIndex == initial - 1);
    assert(portalParent[0].cubemapIndex == initial);
    assert(portalParent[initial - 1].cubemapIndex == initial * 2 - 1);
    drawSurf_t *current = R_DrawSurfStorage();
    R_RadixSort(current, total);
    for (int i = 0; i < total; ++i) {
        int original = current[i].cubemapIndex;
        assert(original >= 0 && original < total);
        assert(current[i].surface == &surface);
        assert(current[i].mapLightingKey == (unsigned)original + 1);
        if (i) {
            assert(current[i - 1].sort <= current[i].sort);
            if (current[i - 1].sort == current[i].sort)
                assert(current[i - 1].cubemapIndex < original);
        }
    }
    assert(portalParent[0].cubemapIndex == initial);
    R_ResetDrawSurfStorage(qfalse);
    assert(R_DrawSurfStorage() == current);
    tr.refdef.numDrawSurfs = 0;
    R_AddDrawSurf(&surface, &shader, 0, 0, 0, 9, 0);
    assert(tr.refdef.drawSurfs[0].cubemapIndex == 9 && growths == 2);
    R_ResetDrawSurfStorage(qtrue);
    assert(R_DrawSurfStorage() == base.drawSurfs);
}
'''

with TemporaryDirectory() as directory:
    path = Path(directory)
    test = path / 'draw_surface_storage.c'
    test.write_text(f'#define INITIAL_DRAWSURFS {initial}\n' + prefix + sort + storage + harness)
    binary = path / 'draw_surface_storage'
    subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-g',
                    '-fsanitize=address,undefined', '-fno-pie', '-no-pie',
                    str(test), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print('Draw surfaces preserved across two growths, stable large sorts, frame reset and shutdown.')
