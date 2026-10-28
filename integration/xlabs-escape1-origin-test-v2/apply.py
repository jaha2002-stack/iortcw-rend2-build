#!/usr/bin/env python3
"""Test V2 only: Xlabs native Tesla anchor experiment + one-shot renderer source audit.
Source frozen at accepted #40640998083; ALL graphical shader inputs byte-identical.
"""
import argparse,hashlib,json
from pathlib import Path
PRE={
"SP/code/cgame/cg_main.c":"357779fb9ccb05b0f5c062d0c8d4b91037b22201b0386081ed0f47a3104abc01",
"SP/code/cgame/cg_local.h":"da191b91d8fe4f0b61c67ad3167111e10e31b326f44f4af93165a451c290e310",
"SP/code/cgame/cg_ents.c":"388404c23a0d091f3b929f66e805e2eff8949578a066891fe90c3130ed7dcc6c",
"SP/code/rend2/tr_main.c":"070f2bfa3c3f1d7beb02333f2ce124afc456e472e971a05afd68b6161448d0ea"}
MARK="DARKWOLF_XLABS_ESCAPE1_DIAGNOSTIC_V2_20261028"
def H(s):return hashlib.sha256(s.encode()).hexdigest()
def once(s,old,new,label):
    assert s.count(old)==1,(label,s.count(old))
    return s.replace(old,new,1)
def apply(root):
    prior={p:(root/p).read_text() for p in PRE}
    assert {p:H(s) for p,s in prior.items()}==PRE,"WRONG_FROZEN_40640998083_SOURCE"
    main=prior["SP/code/cgame/cg_main.c"]
    main=once(main,"vmCvar_t cg_xlabsTeslaDoorShadows;",
      "vmCvar_t cg_xlabsTeslaDoorShadows;\n// "+MARK+": test only, 0 is exact existing light position.\nvmCvar_t cg_dwTeslaNativeShiftTest;","CG_TEST_DECL")
    main=once(main,'\t{ &cg_xlabsTeslaDoorShadows, "cg_xlabsTeslaDoorShadows", "1", CVAR_ARCHIVE },',
      '\t{ &cg_xlabsTeslaDoorShadows, "cg_xlabsTeslaDoorShadows", "1", CVAR_ARCHIVE },\n'
      '\t{ &cg_dwTeslaNativeShiftTest, "cg_dwTeslaNativeShiftTest", "0", 0 },',
      "CG_TEST_REG")
    local=once(prior["SP/code/cgame/cg_local.h"],
      "extern vmCvar_t cg_xlabsTeslaDoorShadows;",
      "extern vmCvar_t cg_xlabsTeslaDoorShadows;\nextern vmCvar_t cg_dwTeslaNativeShiftTest; // "+MARK,
      "CG_TEST_EXTERN")
    ents=prior["SP/code/cgame/cg_ents.c"]
    original=(
       "\t\t\t\tif ( electricDistance > 1.0f ) {\n"
       "\t\t\t\t\telectricOffset = electricDistance * 0.08f;\n"
       "\t\t\t\t\tif ( electricOffset > 32.0f ) {\n"
       "\t\t\t\t\t\telectricOffset = 32.0f;\n"
       "\t\t\t\t\t}\n"
       "\t\t\t\t\tVectorMA( cent->currentState.origin, electricOffset, electricDir, electricLightOrigin );\n"
       "\t\t\t\t}")
    changed=(
       "\t\t\t\tif ( electricDistance > 1.0f ) {\n"
       "\t\t\t\t\telectricOffset = electricDistance * 0.08f;\n"
       "\t\t\t\t\tif ( electricOffset > 32.0f ) {\n"
       "\t\t\t\t\t\telectricOffset = 32.0f;\n"
       "\t\t\t\t\t}\n"
       "\t\t\t\t\t// "+MARK+": Xlabs native Tesla only. Never shift the actual bolt geometry.\n"
       '\t\t\t\t\tif ( strstr( cgs.mapname, "xlabs" ) != NULL && cg_dwTeslaNativeShiftTest.integer > 0 ) {\n'
       "\t\t\t\t\t\tfloat factor = (cg_dwTeslaNativeShiftTest.integer == 1) ? 0.16f : 0.24f;\n"
       "\t\t\t\t\t\tfloat cap = (cg_dwTeslaNativeShiftTest.integer == 1) ? 64.0f : 96.0f;\n"
       "\t\t\t\t\t\telectricOffset = electricDistance * factor;\n"
       "\t\t\t\t\t\tif ( electricOffset > cap ) electricOffset = cap;\n"
       "\t\t\t\t\t}\n"
       "\t\t\t\t\tVectorMA( cent->currentState.origin, electricOffset, electricDir, electricLightOrigin );\n"
       "\t\t\t\t}")
    ents=once(ents,original,changed,"ET_TESLA_EF_LIGHT_POSITION")
    assert ents.count("CG_AddEffectLightToScene( electricLightOrigin,")==1
    assert "DARKWOLF_REF_WORLD_OCCLUSION" in ents and "CG_EFFECTLIGHT_ENVIRONMENTAL_TESLA" in ents
    render=prior["SP/code/rend2/tr_main.c"]
    render=once(render,"void R_RenderDlightWorldOcclusion(const refdef_t *fd)\n{\n\tqboolean active[DLIGHT_WORLD_CACHE_MAX];",
        "void R_RenderDlightWorldOcclusion(const refdef_t *fd)\n{\n"
        "\t// "+MARK+": one-shot console audit, not continuous telemetry.\n"
        "\tstatic cvar_t *auditOnce = NULL;\n\tqboolean auditThisFrame;\n"
        "\tqboolean active[DLIGHT_WORLD_CACHE_MAX];","AUDIT_SCOPE")
    render=once(render,
        "\tCom_Memset(tr.refdef.dlightWorldSlot, -1, sizeof(tr.refdef.dlightWorldSlot));",
        '\tif (!auditOnce) auditOnce = ri.Cvar_Get("r_dwWorldGateAuditOnce", "0", 0);\n'
        "\tauditThisFrame = (auditOnce && auditOnce->integer > 0) ? qtrue : qfalse;\n"
        "\tCom_Memset(tr.refdef.dlightWorldSlot, -1, sizeof(tr.refdef.dlightWorldSlot));","AUDIT_INIT")
    end=(
       "\t\ttr.refdef.dlightWorldOrigin[i][3] = 1.0f / cache->radius;\n"
       "\t}\n}\n\nstatic qboolean R_FireVolProductionCacheMatchesHint")
    replacement=(
       "\t\ttr.refdef.dlightWorldOrigin[i][3] = 1.0f / cache->radius;\n"
       "\t}\n"
       "\t// "+MARK+": only prints upon explicit console request.\n"
       "\tif (auditThisFrame)\n\t{\n"
       "\t\tint k;\n"
       '\t\tri.Printf(PRINT_ALL, "WG_AUDIT_V2_BEGIN map=%s sceneDlights=%d containment=%d\\n",\n'
       '\t\t\ttr.world ? tr.world->baseName : "none", tr.refdef.num_dlights,\n'
       "\t\t\tr_dlightWorldContainment ? r_dlightWorldContainment->integer : -1);\n"
       "\t\tfor (k = 0; k < tr.refdef.num_dlights && k < MAX_DLIGHTS; ++k)\n\t\t{\n"
       "\t\t\tconst dlight_t *dl = &tr.refdef.dlights[k];\n"
       "\t\t\tvec3_t delta;\n"
       "\t\t\tfloat cameraDistance;\n"
       "\t\t\tVectorSubtract(dl->origin, fd->vieworg, delta);\n"
       "\t\t\tcameraDistance = VectorLength(delta);\n"
       '\t\t\tri.Printf(PRINT_ALL, "WG_AUDIT_V2_LIGHT index=%d origin=%.1f,%.1f,%.1f rgb=%.3f,%.3f,%.3f radius=%.1f cameraDist=%.1f world=%d slot=%d native=%d fire=%d class=%d\\n",\n'
       "\t\t\t\tk, dl->origin[0], dl->origin[1], dl->origin[2],\n"
       "\t\t\t\tdl->color[0], dl->color[1], dl->color[2], dl->radius,\n"
       "\t\t\t\tcameraDistance, (int)dl->worldOcclusion,\n"
       "\t\t\t\t(int)tr.refdef.dlightWorldSlot[k], (int)dl->nativeAuthoredDlight,\n"
       "\t\t\t\t(int)dl->fireVolumetricSource, (int)dl->shadowSourceClass);\n"
       "\t\t}\n"
       '\t\tri.Printf(PRINT_ALL, "WG_AUDIT_V2_END\\n");\n'
       '\t\tri.Cvar_Set("r_dwWorldGateAuditOnce", "0");\n'
       "\t}\n}\n\nstatic qboolean R_FireVolProductionCacheMatchesHint")
    render=once(render,end,replacement,"AUDIT_AT_END_OF_WORLD_CAPTURE")
    assert render.count("r_dwWorldGateAuditOnce")==2
    after={"SP/code/cgame/cg_main.c":main,"SP/code/cgame/cg_local.h":local,
           "SP/code/cgame/cg_ents.c":ents,"SP/code/rend2/tr_main.c":render}
    for p,s in after.items():(root/p).write_text(s)
    return {"marker":MARK,"frozen_binary_run":40640998083,
        "changed_source_files":sorted(after),
        "source_sha256_before":PRE,
        "source_sha256_after":{p:H(s) for p,s in after.items()},
        "tesla_modes":{"0":"exact_original","1":"16pct_max64","2":"24pct_max96"},
        "audit_once":"print nearest/active all scene dlights then reset to 0",
        "temporary_test_cvars":["cg_dwTeslaNativeShiftTest","r_dwWorldGateAuditOnce"],
        "unchanged":["Crypt1 PCF2x2","Sun3","Fire E","Local","Sky","SSGI","CSM",
                     "point shadow slot budgets","Fire source classification",
                     "shadow-depth capture and packed RGB decoder"],
        "telemetry_on_by_default":False,"production":False,"requires_user_gpu_test":True}
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("source",type=Path)
    ap.add_argument("--proof",type=Path);args=ap.parse_args()
    proof=apply(args.source)
    if args.proof:
        args.proof.parent.mkdir(parents=True,exist_ok=True)
        args.proof.write_text(json.dumps(proof,indent=2)+"\n")
    print("DW_TESLA_FIRE_DIAG_V2_PATCH_PASS")
