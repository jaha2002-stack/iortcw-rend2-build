#!/usr/bin/env python3
"""Native TestLab-only causal controls; never part of the IFLC release patch.

The diagnostic mask changes only the two direct receiver passes.  It does not
change dlight objects, emitter positions, shadow allocation/capture, FireVol,
GLSL, authored entities or the accepted PCF implementation.
"""
import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TARGETS = {"SP/code/rend2/tr_init.c", "SP/code/rend2/tr_local.h", "SP/code/rend2/tr_shade.c"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def instrument(source, evidence):
    evidence.mkdir(parents=True, exist_ok=True)
    code = source / "SP/code"
    original = {str(p.relative_to(source)): p.read_bytes() for p in code.rglob("*") if p.is_file()}
    manifest = json.loads((evidence / "IFLC_SOURCE_SHA256.json").read_text())
    assert {p: sha(v) for p, v in original.items()} == manifest, "Source is not the verified IFLC candidate"

    spec = importlib.util.spec_from_file_location("iflc_production_runtime", REPO / "integration/iflc-v1/runtime.py")
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    base.instrument(source)

    def edit(rel, old, new, count=1):
        p = source / rel
        text = p.read_text()
        assert text.count(old) == count, (rel, "unexpected diagnostic anchor count", text.count(old), count)
        p.write_text(text.replace(old, new))

    edit("SP/code/cgame/cg_view.c", '"r_hdr","r_postProcess",',
         '"r_iflcShadowAudit","r_dwFireLightControl","r_dlightShadowStrength","r_dlightWorldContainment","r_hdr","r_postProcess",')
    edit("SP/code/rend2/tr_local.h", "extern cvar_t *r_dwFireLightControl;",
         "extern cvar_t *r_dwFireLightControl;\n/* Native shadow audit only, never shipped. */\nextern cvar_t *r_iflcShadowAudit, *r_iflcShadowAuditShot;")
    edit("SP/code/rend2/tr_init.c", "cvar_t  *r_dwFireLightControl; // DARKWOLF_IFLC_V1, explicit opt-in master.",
         "cvar_t  *r_dwFireLightControl; // DARKWOLF_IFLC_V1, explicit opt-in master.\n/* Native shadow audit only, never shipped. */\ncvar_t *r_iflcShadowAudit, *r_iflcShadowAuditShot;")
    edit("SP/code/rend2/tr_init.c", '\tr_dwFireLightControl = ri.Cvar_Get( "r_dwFireLightControl", "0", CVAR_ARCHIVE );',
         '\tr_iflcShadowAudit = ri.Cvar_Get("r_iflcShadowAudit", "0", 0);\n'
         '\tri.Cvar_CheckRange(r_iflcShadowAudit, 0.0f, 127.0f, qtrue);\n'
         '\tr_iflcShadowAuditShot = ri.Cvar_Get("dw_proofShot", "0", 0);\n'
         '\tr_dwFireLightControl = ri.Cvar_Get( "r_dwFireLightControl", "0", CVAR_ARCHIVE );')

    helpers = r'''
/* IFLC_SHADOW_AUDIT: isolated Crypt1 diagnostic, never a production control.
 * 1 = bypass opt-in world visibility; 2 = bypass opt-in ordinary shadow;
 * 4 = zero native291 receiver RGB; 8 = zero selected opt-in receiver RGB.
 * 16 = bypass native291 world visibility; 32 = bypass native291 ordinary shadow;
 * 64 = zero all dlight receiver RGB (including both targets).
 * Exact origins prevent accidental application to another fixture or map.
 * The dlight structures and all shadow/FireVol allocation remain untouched.
 */
static int RB_IFLCShadowAuditKind(const dlight_t *dl)
{
    if (!tr.world || Q_stricmp(tr.world->baseName, "crypt1")) return 0;
    if (dl->iflcOptIn && fabs(dl->origin[0] + 224.5f) < 0.01f &&
        fabs(dl->origin[1] - 1544.5f) < 0.01f && fabs(dl->origin[2] - 552.0f) < 0.01f) return 1;
    if (dl->nativeAuthoredDlight && dl->fireVolumetricNativeOrdinal == 291 &&
        fabs(dl->origin[0] + 152.0f) < 0.01f && fabs(dl->origin[1] - 1668.0f) < 0.01f &&
        fabs(dl->origin[2] - 636.0f) < 0.01f) return 2;
    return 0;
}

static qboolean RB_IFLCShadowAuditBypass(const dlight_t *dl, qboolean world)
{
    int kind = RB_IFLCShadowAuditKind(dl);
    int flags = r_iflcShadowAudit ? r_iflcShadowAudit->integer : 0;
    return (kind == 1 && (flags & (world ? 1 : 2))) || (kind == 2 && (flags & (world ? 16 : 32)));
}

static float RB_IFLCShadowAuditGain(const dlight_t *dl, int lightIndex)
{
    static int lastShot[3] = {-1, -1, -1};
    int kind = RB_IFLCShadowAuditKind(dl);
    int flags = r_iflcShadowAudit ? r_iflcShadowAudit->integer : 0;
    int shot = r_iflcShadowAuditShot ? r_iflcShadowAuditShot->integer : 0;
    float gain = ((flags & 64) || (kind == 1 && (flags & 8)) || (kind == 2 && (flags & 4))) ? 0.0f : 1.0f;
    if (kind && shot > 0 && lastShot[kind] != shot)
    {
        int ordinarySlot = -1;
        lastShot[kind] = shot;
        if (backEnd.refdef.dlightShadowMask & (1u << lightIndex))
            ordinarySlot = (int)backEnd.refdef.dlightShadowSlot[lightIndex];
        ri.Printf(PRINT_ALL,
            "IFLC_SHADOW_AUDIT shot=%d kind=%s flags=%d gain=%.1f light=%d nativeOrdinal=%d "
            "origin=%.3f,%.3f,%.3f color=%.6f,%.6f,%.6f radius=%.3f "
            "worldSlot=%d worldOrigin=%.3f,%.3f,%.3f,%.6f ordinarySlot=%d "
            "captureOrigin=%.3f,%.3f,%.3f captureRadius=%.3f sourceWorld=%d worldBypass=%d ordinaryBypass=%d\n",
            shot, kind == 1 ? "optin" : "native291", flags, gain, lightIndex, dl->fireVolumetricNativeOrdinal,
            dl->origin[0], dl->origin[1], dl->origin[2], dl->color[0], dl->color[1], dl->color[2], dl->radius,
            (int)backEnd.refdef.dlightWorldSlot[lightIndex],
            backEnd.refdef.dlightWorldOrigin[lightIndex][0], backEnd.refdef.dlightWorldOrigin[lightIndex][1],
            backEnd.refdef.dlightWorldOrigin[lightIndex][2], backEnd.refdef.dlightWorldOrigin[lightIndex][3],
            ordinarySlot, backEnd.refdef.dlightShadowCaptureOrigin[lightIndex][0],
            backEnd.refdef.dlightShadowCaptureOrigin[lightIndex][1], backEnd.refdef.dlightShadowCaptureOrigin[lightIndex][2],
            backEnd.refdef.dlightShadowCaptureRadius[lightIndex], (int)dl->worldOcclusion,
            RB_IFLCShadowAuditBypass(dl, qtrue) ? 1 : 0, RB_IFLCShadowAuditBypass(dl, qfalse) ? 1 : 0);
    }
    return gain;
}

'''
    shade = "SP/code/rend2/tr_shade.c"
    edit(shade, "// Architectural visibility is mandatory for tagged lights even when their", helpers + "// Architectural visibility is mandatory for tagged lights even when their")
    edit(shade, "\t\ttr.dlightWorldCubemaps[slot] && backEnd.refdef.dlights[lightIndex].worldOcclusion)",
         "\t\ttr.dlightWorldCubemaps[slot] && backEnd.refdef.dlights[lightIndex].worldOcclusion &&\n"
         "\t\t!RB_IFLCShadowAuditBypass(&backEnd.refdef.dlights[lightIndex], qtrue))")
    edit(shade, "\t\tfloat shadowTexelRadius;", "\t\tfloat shadowTexelRadius;\n\t\tfloat auditGain;", count=2)
    edit(shade, "\t\tdl = &backEnd.refdef.dlights[l];", "\t\tdl = &backEnd.refdef.dlights[l];\n\t\tauditGain = RB_IFLCShadowAuditGain(dl, l);", count=2)
    for channel in range(3):
        old = f"\t\tvector[{channel}] = dl->color[{channel}] * r_dlightIntensity->value;"
        edit(shade, old, old[:-1] + " * auditGain;")
    edit(shade, "\t\tVectorScale(dl->color, r_dlightIntensity->value, vector);",
         "\t\tVectorScale(dl->color, r_dlightIntensity->value * auditGain, vector);")
    edit(shade, "\t\t\t&& tr.shadowCubemaps[shadowSlot] != NULL;",
         "\t\t\t&& tr.shadowCubemaps[shadowSlot] != NULL\n"
         "\t\t\t&& !RB_IFLCShadowAuditBypass(dl, qfalse);", count=2)

    after = {str(p.relative_to(source)): p.read_bytes() for p in code.rglob("*") if p.is_file()}
    changed = {p for p in original if original[p] != after[p]}
    renderer = {p for p in changed if "/rend2/" in p}
    assert renderer == TARGETS, ("Unexpected renderer diagnostic changes", renderer)
    assert all(original[p] == after[p] for p in original if "/glsl/" in p)
    assert original["SP/code/rend2/tr_main.c"] == after["SP/code/rend2/tr_main.c"]
    assert original["SP/code/rend2/tr_backend.c"] == after["SP/code/rend2/tr_backend.c"]
    delta = "".join("".join(difflib.unified_diff(original[p].decode().splitlines(True), after[p].decode().splitlines(True),
                                              fromfile="a/" + p, tofile="b/" + p)) for p in sorted(changed))
    (evidence / "IFLC_SHADOW_AUDIT_HOOKS.patch").write_text(delta)
    proof = {"release_candidate_commit": "eb67a2dd0d1592311a155bc81e357698c3628c95",
             "release_candidate_run": 41691075610, "test_only_renderer_instrumentation": True,
             "production_patch_changed": False, "glsl_changed": False,
             "shadow_capture_and_selection_changed": False, "firevol_backend_changed": False,
             "changed_files": {p: {"before": sha(original[p]), "after": sha(after[p])} for p in sorted(changed)},
             "diagnostic_mask": {"1": "bypass selected opt-in world visibility", "2": "bypass selected opt-in ordinary shadow visibility",
                                 "4": "zero native291 direct receiver RGB", "8": "zero selected opt-in direct receiver RGB",
                                 "16": "bypass native291 world visibility", "32": "bypass native291 ordinary shadow visibility",
                                 "64": "zero all dlight direct receiver RGB"},
             "limitations": "Native-only causal instrumentation. RGB controls act on both direct receiver passes, not entity/model aggregate ambient lighting. Do not deploy this renderer. No Win64 release is produced."}
    (evidence / "IFLC_SHADOW_AUDIT_INSTRUMENTATION.json").write_text(json.dumps(proof, indent=2) + "\n")
    print("IFLC_SHADOW_AUDIT_NATIVE_ONLY_INSTRUMENTED", sorted(renderer), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    instrument(args.source.resolve(), args.evidence.resolve())
