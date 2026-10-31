#!/usr/bin/env python3
"""TEST ONLY: source-indexed BSP caster attribution for accepted DarkWolf #41019985033.
Apply after V1 scope diagnostics and the exact V2 patch; never modify production.
All V3 defaults are passive. Diagnostic include/exclude modes affect only one
explicitly targeted ordinary point-shadow capture, never Fire/Tesla or sun CSM.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

MARK = "DARKWOLF_POINT_SHADOW_GEOMETRY_FIDELITY_V3_41019985033"
FILES = ("tr_local.h", "tr_init.c", "tr_main.c", "tr_backend.c")
NAMES = (
    "r_dwPointV3ListLight",
    "r_dwPointV3Mode",
    "r_dwPointV3SourceX",
    "r_dwPointV3SourceY",
    "r_dwPointV3SourceZ",
    "r_dwPointV3TargetTolerance",
    "r_dwPointV3SurfaceFirst",
    "r_dwPointV3SurfaceLast",
    "r_dwPointV3InspectSurface",
)
GUARD_SHA = {
    "tr_local.h": "69ea144044ca3083d98520580f37473dab0ce02c08d081ac5d156bc137915e61",
    "tr_init.c": "54e7030c2b4c33a1c3bc11b1d2976a4aad3d8025338496e591931ebb9667fb18",
    "tr_main.c": "0c400e188ad4d5cb11210094f7a9d2a4b168f3330bca2e2d1b82670c6e30967b",
}

def digest(v):
    return hashlib.sha256(v.encode("utf-8")).hexdigest()

def replace_once(s, old, new, tag):
    assert s.count(old) == 1, (tag, s.count(old))
    return s.replace(old, new, 1)

def after_line(s, prefix, block, tag):
    assert s.count(prefix) == 1, (tag, s.count(prefix))
    at = s.index("\n", s.index(prefix)) + 1
    return s[:at] + block + s[at:]

C_SOURCE_LOG = r'''
        /* DARKWOLF_POINT_SHADOW_GEOMETRY_FIDELITY_V3_41019985033:
         * Source enumeration only. This does not alter capture or direct light.
         * -2 prints the available light indices periodically; -1 is silent.
         * The shadow slot / FixtureId mapping is NOT inferred from an index.
         */
        if (r_dwPointV3ListLight &&
            (r_dwPointV3ListLight->integer == -2 ||
             r_dwPointV3ListLight->integer == i) &&
            (tr.frameCount % 120) == 0)
        {
            ri.Printf(PRINT_ALL,
                "DW_PS_V3_SOURCE map=%s frame=%d dlight=%d direct=(%.3f %.3f %.3f) capture=(%.3f %.3f %.3f) delta=(%.3f %.3f %.3f) near=%.3f far=%.3f directRadius=%.3f facePx=%dx%d (FixtureId/slot not proven)\n",
                tr.world ? tr.world->baseName : "unknown", tr.frameCount, i,
                tr.refdef.dlights[i].origin[0], tr.refdef.dlights[i].origin[1], tr.refdef.dlights[i].origin[2],
                shadowParms.or.origin[0], shadowParms.or.origin[1], shadowParms.or.origin[2],
                shadowParms.or.origin[0] - tr.refdef.dlights[i].origin[0],
                shadowParms.or.origin[1] - tr.refdef.dlights[i].origin[1],
                shadowParms.or.origin[2] - tr.refdef.dlights[i].origin[2],
                shadowParms.zNear, shadowParms.zFar, tr.refdef.dlights[i].radius,
                shadowParms.viewportWidth, shadowParms.viewportHeight);
        }
'''

C_BACKEND_HELPERS = r'''
/* DARKWOLF_POINT_SHADOW_GEOMETRY_FIDELITY_V3_41019985033
 * TEST-ONLY stable msurface index look-up. Geometry is never altered at defaults.
 * BSP world->surfaces[] IDs persist within a given map, unlike pointer values.
 * Build a sorted pointer->ID table ONLY during explicitly requested filtering.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
typedef struct {
    uintptr_t surfacePtr;
    int worldSurfaceId;
} dwPointV3SurfaceEntry_t;
static dwPointV3SurfaceEntry_t *dwPointV3Entries = NULL;
static const world_t *dwPointV3CachedWorld = NULL;
static const msurface_t *dwPointV3CachedSurfaces = NULL;
static int dwPointV3CachedCount = -1;
static int dwPointV3TableCount = 0;
static char dwPointV3MapName[MAX_QPATH] = "";
static int dwPointV3LastInfoTime = -200000;
static int dwPointV3LastSeenTime = -200000;

static int DWPointV3CompareEntry(const void *a, const void *b)
{
    const dwPointV3SurfaceEntry_t *aa = (const dwPointV3SurfaceEntry_t *)a;
    const dwPointV3SurfaceEntry_t *bb = (const dwPointV3SurfaceEntry_t *)b;
    if (aa->surfacePtr < bb->surfacePtr) return -1;
    if (aa->surfacePtr > bb->surfacePtr) return 1;
    return aa->worldSurfaceId - bb->worldSurfaceId;
}

static int DWPointV3SurfaceId(const surfaceType_t *surface)
{
    int lo, hi;
    uintptr_t key;
    if (!tr.world || !tr.world->surfaces || !surface)
        return -2;
    if (dwPointV3CachedWorld != tr.world ||
        dwPointV3CachedSurfaces != tr.world->surfaces ||
        dwPointV3CachedCount != tr.world->numsurfaces ||
        strcmp(dwPointV3MapName, tr.world->name))
    {
        int k, count = 0;
        free(dwPointV3Entries);
        dwPointV3Entries = NULL;
        dwPointV3TableCount = 0;
        dwPointV3CachedWorld = tr.world;
        dwPointV3CachedSurfaces = tr.world->surfaces;
        dwPointV3CachedCount = tr.world->numsurfaces;
        Q_strncpyz(dwPointV3MapName, tr.world->name, sizeof(dwPointV3MapName));
        if (tr.world->numsurfaces < 1 || tr.world->numsurfaces > 500000)
        {
            ri.Printf(PRINT_WARNING, "DW_PS_V3 mapping disabled: unexpected surface count %d\n",
                      tr.world->numsurfaces);
            return -2;
        }
        dwPointV3Entries = (dwPointV3SurfaceEntry_t *)malloc(
            (size_t)tr.world->numsurfaces * sizeof(*dwPointV3Entries));
        if (!dwPointV3Entries)
        {
            ri.Printf(PRINT_WARNING, "DW_PS_V3 mapping disabled: allocation failed\n");
            return -2;
        }
        for (k = 0; k < tr.world->numsurfaces; ++k)
        {
            if (tr.world->surfaces[k].data)
            {
                dwPointV3Entries[count].surfacePtr =
                    (uintptr_t)tr.world->surfaces[k].data;
                dwPointV3Entries[count].worldSurfaceId = k;
                ++count;
            }
        }
        qsort(dwPointV3Entries, (size_t)count, sizeof(*dwPointV3Entries),
              DWPointV3CompareEntry);
        dwPointV3TableCount = count;
        ri.Printf(PRINT_ALL, "DW_PS_V3 BSP map=%s totalWorldSurfaces=%d mapped=%d\n",
                  dwPointV3MapName, tr.world->numsurfaces, count);
    }
    if (!dwPointV3Entries) return -2;
    key = (uintptr_t)surface;
    lo = 0;
    hi = dwPointV3TableCount - 1;
    while (lo <= hi)
    {
        int mid = lo + (hi - lo) / 2;
        if (dwPointV3Entries[mid].surfacePtr == key)
            return dwPointV3Entries[mid].worldSurfaceId;
        if (dwPointV3Entries[mid].surfacePtr < key) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1; /* Not a member of this BSP world's drawable surfaces. */
}

static qboolean DWPointV3CaptureSelected(void)
{
    float dx, dy, dz, tolerance;
    if (!r_dwPointV3TargetTolerance) return qfalse;
    tolerance = r_dwPointV3TargetTolerance->value;
    if (tolerance <= 0.0f) return qfalse; /* zero means no source targeted */
    if ((backEnd.viewParms.flags & (VPF_SHADOWMAP | VPF_DEPTHSHADOW)) !=
        (VPF_SHADOWMAP | VPF_DEPTHSHADOW)) return qfalse;
    if (backEnd.viewParms.flags &
        (VPF_DLIGHT_WORLD_OCCLUSION | VPF_FIREVOL_SYNTHETIC_SHADOW))
        return qfalse;
    dx = backEnd.viewParms.or.origin[0] - r_dwPointV3SourceX->value;
    dy = backEnd.viewParms.or.origin[1] - r_dwPointV3SourceY->value;
    dz = backEnd.viewParms.or.origin[2] - r_dwPointV3SourceZ->value;
    return dx*dx + dy*dy + dz*dz <= tolerance*tolerance ? qtrue : qfalse;
}

static void DWPointV3InspectSelectedSurface(void)
{
    const msurface_t *s;
    const cullinfo_t *c;
    int id = r_dwPointV3InspectSurface ? r_dwPointV3InspectSurface->integer : -1;
    float dx, dy, dz, distance;
    if (!tr.world || !tr.world->surfaces || id < 0 ||
        id >= tr.world->numsurfaces) return;
    if (backEnd.refdef.time >= dwPointV3LastInfoTime &&
        backEnd.refdef.time - dwPointV3LastInfoTime < 1400) return;
    dwPointV3LastInfoTime = backEnd.refdef.time;
    s = &tr.world->surfaces[id];
    c = &s->cullinfo;
    if (c->type & CULLINFO_BOX)
    {
        float x = 0.5f*(c->bounds[0][0] + c->bounds[1][0]);
        float y = 0.5f*(c->bounds[0][1] + c->bounds[1][1]);
        float z = 0.5f*(c->bounds[0][2] + c->bounds[1][2]);
        dx = x - backEnd.viewParms.or.origin[0];
        dy = y - backEnd.viewParms.or.origin[1];
        dz = z - backEnd.viewParms.or.origin[2];
        distance = sqrtf(dx*dx + dy*dy + dz*dz);
        ri.Printf(PRINT_ALL,
            "DW_PS_V3_BSP_INFO map=%s id=%d shader=%s surfType=%d cullType=%d bounds=(%.2f %.2f %.2f)-(%.2f %.2f %.2f) centroid=(%.2f %.2f %.2f) sourceDist=%.2f capture=(%.2f %.2f %.2f)\n",
            tr.world->baseName, id, s->shader ? s->shader->name : "(none)",
            s->data ? (int)*s->data : -1, c->type,
            c->bounds[0][0], c->bounds[0][1], c->bounds[0][2],
            c->bounds[1][0], c->bounds[1][1], c->bounds[1][2],
            x, y, z, distance,
            backEnd.viewParms.or.origin[0], backEnd.viewParms.or.origin[1],
            backEnd.viewParms.or.origin[2]);
    }
    else
    {
        ri.Printf(PRINT_ALL,
            "DW_PS_V3_BSP_INFO map=%s id=%d shader=%s surfType=%d cullType=%d (no valid AABB; no centroid inferred)\n",
            tr.world->baseName, id, s->shader ? s->shader->name : "(none)",
            s->data ? (int)*s->data : -1, c->type);
    }
}
'''

C_BACKEND_PER_SURF = r'''
        /* V3 attribution is active only for a manually matched point light.
         * Modes 1/2 temporarily alter ONE shadow capture for binary attribution.
         * All world/entity casters remain eligible when mode=0 (the default).
         */
        if (r_dwPointV3Mode && r_dwPointV3InspectSurface &&
            (r_dwPointV3Mode->integer != 0 ||
             r_dwPointV3InspectSurface->integer >= 0) &&
            DWPointV3CaptureSelected())
        {
            int dwMode = r_dwPointV3Mode->integer;
            int dwEntityNum = (drawSurf->sort >> QSORT_REFENTITYNUM_SHIFT) &
                              REFENTITYNUM_MASK;
            int dwId = -1;
            if (i == 0)
                DWPointV3InspectSelectedSurface();
            if (dwEntityNum == REFENTITYNUM_WORLD && dwMode != 0)
                dwId = DWPointV3SurfaceId(drawSurf->surface);
            else if (dwEntityNum == REFENTITYNUM_WORLD &&
                     r_dwPointV3InspectSurface->integer >= 0)
            {
                int wanted = r_dwPointV3InspectSurface->integer;
                if (tr.world && wanted < tr.world->numsurfaces &&
                    wanted >= 0 && tr.world->surfaces[wanted].data ==
                    drawSurf->surface)
                    dwId = wanted;
            }
            if (dwId >= 0 && dwId == r_dwPointV3InspectSurface->integer &&
                (backEnd.refdef.time < dwPointV3LastSeenTime ||
                 backEnd.refdef.time - dwPointV3LastSeenTime >= 1400))
            {
                dwPointV3LastSeenTime = backEnd.refdef.time;
                ri.Printf(PRINT_ALL,
                    "DW_PS_V3_BSP_IN_DRAWLIST surfaceID=%d sort=%u faceForward=(%.1f %.1f %.1f) mode=%d (not proof of depth win)\n",
                    dwId, drawSurf->sort,
                    backEnd.viewParms.or.axis[0][0],
                    backEnd.viewParms.or.axis[0][1],
                    backEnd.viewParms.or.axis[0][2], dwMode);
            }
            if (dwMode == 1) /* include only selected BSP ID interval for this capture */
            {
                if (dwEntityNum != REFENTITYNUM_WORLD)
                    continue; /* diagnostic scope only */
                if (dwId >= 0 &&
                    (dwId < r_dwPointV3SurfaceFirst->integer ||
                     dwId > r_dwPointV3SurfaceLast->integer))
                    continue;
                if (dwId == -1)
                    continue; /* BSP alias not in world->surfaces: log via modes */
            }
            else if (dwMode == 2) /* exclude only selected BSP interval */
            {
                if (dwEntityNum == REFENTITYNUM_WORLD && dwId >= 0 &&
                    dwId >= r_dwPointV3SurfaceFirst->integer &&
                    dwId <= r_dwPointV3SurfaceLast->integer)
                    continue;
            }
            /* lookup error -2 is fail-open, not a reason to drop geometry */
        }
'''

def apply(root, check=False, proof=None):
    base = Path(root) / "SP/code/rend2"
    original = {f: (base / f).read_text(encoding="utf-8") for f in FILES}
    for name, expected in GUARD_SHA.items():
        assert digest(original[name]) == expected, ("V2 exact source drift", name)
    assert all(MARK not in value for value in original.values()), "V3 already installed"
    assert "DARKWOLF_POINT_SHADOW_SCOPE_DIAGNOSTIC_V1_41019985033" in original["tr_backend.c"]
    assert "DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886" in original["tr_backend.c"]
    assert "DARKWOLF_POINT_SHADOW_NEARWORLD_ORIGIN_DIAG_V2_41019985033" in original["tr_main.c"]
    changed = dict(original)
    ext = "".join(f"extern cvar_t  *{name}; // {MARK}\n" for name in NAMES)
    decl = "".join(f"cvar_t  *{name}; // {MARK}\n" for name in NAMES)
    changed["tr_local.h"] = after_line(changed["tr_local.h"],
        "extern cvar_t  *r_dwPointOriginShift;", ext, "extern")
    changed["tr_init.c"] = after_line(changed["tr_init.c"],
        "cvar_t  *r_dwPointOriginShift;", decl, "definitions")

    reg = [
        ("\tr_dwPointV3ListLight = ri.Cvar_Get( \"r_dwPointV3ListLight\", \"-1\", 0 );", "r_dwPointV3ListLight", -2, 63, True),
        ("\tr_dwPointV3Mode = ri.Cvar_Get( \"r_dwPointV3Mode\", \"0\", CVAR_LATCH );", "r_dwPointV3Mode", 0, 2, True),
        ("\tr_dwPointV3SourceX = ri.Cvar_Get( \"r_dwPointV3SourceX\", \"0\", CVAR_LATCH );", "r_dwPointV3SourceX", -131072, 131072, False),
        ("\tr_dwPointV3SourceY = ri.Cvar_Get( \"r_dwPointV3SourceY\", \"0\", CVAR_LATCH );", "r_dwPointV3SourceY", -131072, 131072, False),
        ("\tr_dwPointV3SourceZ = ri.Cvar_Get( \"r_dwPointV3SourceZ\", \"0\", CVAR_LATCH );", "r_dwPointV3SourceZ", -131072, 131072, False),
        ("\tr_dwPointV3TargetTolerance = ri.Cvar_Get( \"r_dwPointV3TargetTolerance\", \"0\", CVAR_LATCH );", "r_dwPointV3TargetTolerance", 0, 16, False),
        ("\tr_dwPointV3SurfaceFirst = ri.Cvar_Get( \"r_dwPointV3SurfaceFirst\", \"0\", CVAR_LATCH );", "r_dwPointV3SurfaceFirst", 0, 500000, True),
        ("\tr_dwPointV3SurfaceLast = ri.Cvar_Get( \"r_dwPointV3SurfaceLast\", \"500000\", CVAR_LATCH );", "r_dwPointV3SurfaceLast", 0, 500000, True),
        ("\tr_dwPointV3InspectSurface = ri.Cvar_Get( \"r_dwPointV3InspectSurface\", \"-1\", 0 );", "r_dwPointV3InspectSurface", -1, 500000, True),
    ]
    registers = f"\t// {MARK}: all modes unarchived, filter selection latched.\n"
    for assign, name, minimum, maximum, integer in reg:
        registers += assign + "\n"
        registers += f"\tri.Cvar_CheckRange( {name}, {minimum}, {maximum}, {'qtrue' if integer else 'qfalse'} );\n"
    changed["tr_init.c"] = after_line(changed["tr_init.c"],
        "ri.Cvar_CheckRange( r_dwPointOriginShift, -16.0f, 16.0f, qfalse );",
        registers, "register")

    main = changed["tr_main.c"]
    v2start = main.index("DARKWOLF_POINT_SHADOW_NEARWORLD_ORIGIN_DIAG_V2_41019985033: fixed-world-axis")
    jpos = main.index("\t\tfor (j = 0; j < 6; j++)", v2start)
    changed["tr_main.c"] = main[:jpos] + C_SOURCE_LOG + main[jpos:]

    backend = changed["tr_backend.c"]
    signature = re.search(r"(?m)^void\s+RB_RenderDrawSurfList\(\s*drawSurf_t \*drawSurfs,\s*int numDrawSurfs\s*\)\s*\{", backend)
    assert signature, "RB_RenderDrawSurfList signature changed"
    backend = backend[:signature.start()] + C_BACKEND_HELPERS + backend[signature.start():]
    loop_anchor = "\tfor (i = 0, drawSurf = drawSurfs ; i < numDrawSurfs ; i++, drawSurf++) {\n"
    backend = replace_once(backend, loop_anchor, loop_anchor + C_BACKEND_PER_SURF, "backend loop")
    changed["tr_backend.c"] = backend

    assert len([f for f in FILES if changed[f] != original[f]]) == len(FILES)
    assert "DARKWOLF_STAGE11_UNIFIED_ASSET_SHADOW_COVERAGE_CLEAN_PRODUCTION_V1" in changed["tr_backend.c"]
    assert "DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886" in changed["tr_backend.c"]
    assert "DWPointV3CaptureSelected()" in changed["tr_backend.c"]
    assert "r_dwPointV3Mode->integer != 0" in changed["tr_backend.c"]
    if not check:
        for name in FILES:
            (base / name).write_text(changed[name], encoding="utf-8")
    summary = {
        "type": "TEST_ONLY_ATTRIBUTION",
        "accepted_baseline_run": 41019985033,
        "base_commit": "c653433e1b0a29b2f43f29a240b96a8192acb617",
        "source_stage": "after exact V1+V2 debug patches",
        "marker": MARK, "check_only": check,
        "modified_files": ["SP/code/rend2/" + f for f in FILES],
        "sha256_before": {f: digest(original[f]) for f in FILES},
        "sha256_after": {f: digest(changed[f]) for f in FILES},
        "v3_default_has_no_draw_or_light_changes": True,
        "only_selected_ordinary_point_capture_modified_when_mode_1_or_2": True,
        "global_world_clipping": False,
        "global_origin_shift": False,
        "stage11_asset_coverage_preserved_at_defaults": True,
        "fire_worldmask_sun_hdr16f_and_glsl_not_changed_in_v3": True,
        "bsp_identity": "world->surfaces[index] (not brush number)",
        "identity_limitations": "only captures submitted to renderer; draw-list presence does not prove depth win",
        "gpu_visual_validation": "PENDING",
    }
    if proof:
        p = Path(proof)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("DW_POINT_SHADOW_GEOMETRY_FIDELITY_V3_SOURCE_PASS")
    return summary

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--proof", type=Path)
    args = ap.parse_args()
    apply(args.root, check=args.check_only, proof=args.proof)
