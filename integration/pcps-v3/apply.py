#!/usr/bin/env python3
"""PCPS V3 scoped source patch on top of the EXACT proven PCPS V2.
Only tr_main.c and tr_scene.c: target preview and UI overlay, and per-BSP
Main/dw_pcps/ folders with safe legacy import. No shader/CVar/budget edits.
"""
import argparse,json,hashlib
from pathlib import Path
NAME="DARKWOLF_PCPS_V3_PICK_VISUAL_20261102"
ROOT=Path("SP/code/rend2")
def once(s,old,new,label):
    count=s.count(old)
    if count!=1:raise RuntimeError(f"{label}: expected 1 source anchor, found {count}")
    return s.replace(old,new,1)
def apply(root,check=False,proof=None):
    root=Path(root)/ROOT
    base=Path(__file__).resolve().parents[1]
    oldpersist=(base/"pcps-v2/persistence.inc").read_text(encoding="utf-8")
    newpersist=(base/"pcps-v3/persistence_v3.inc").read_text(encoding="utf-8")
    picker=(base/"pcps-v3/picker_overlay.inc").read_text(encoding="utf-8")
    before={f:(root/f).read_text(encoding="utf-8") for f in ("tr_main.c","tr_scene.c")}
    m=before["tr_main.c"]
    assert "DARKWOLF_PCPS_RUNTIME_V1" in m
    assert "DARKWOLF_PCPS_PERSISTENCE_V2_20261102" in m
    assert NAME not in m and NAME in picker
    assert oldpersist in m and newpersist not in m
    assert "DARKWOLF_CRYPT1_PERSISTENT_FIRE_SHADOW_PRIORITY_FIX_V1_20261028" in m
    m=once(m,oldpersist,newpersist.rstrip()+"\n\n"+picker.rstrip()+"\n",
      "replace V2 persistence with compatible folder version and add selector")
    m=once(m,'static char dwpsMap[MAX_QPATH]="";',
      'static char dwpsMap[MAX_QPATH]="";\n'
      'static void DWPS3_OnWorldChanged(void);\n'
      'static void DWPS3_ConfirmedIndex(int index);\n'
      'static void DWPS3_OnCasterPicked(void);\n'
      'static void DWPS3_PickLight_f(void);\n'
      'static void DWPS3_Confirm_f(void);\n'
      'static void DWPS3_Candidates_f(void);\n'
      'static void DWPS3_Next_f(void);\n'
      'static void DWPS3_Prev_f(void);\n'
      'static void DWPS3_Overlay_f(void);',
      "forward selector callbacks")
    m=once(m,
      '    DWPS_LoadCurrentMap(); /* V2: source/caster rules auto-load on BSP transition */',
      '    DWPS_LoadCurrentMap(); /* V2: source/caster rules auto-load on BSP transition */\n'
      '    DWPS3_OnWorldChanged(); /* clear per-map visual selection, not saved rules */',
      "map change reset debug only")
    m=once(m,'    dwpsSelected=r;\n    dwpsLastSurface=-1;\n',
      '    dwpsSelected=r;\n    dwpsLastSurface=-1;\n'
      '    DWPS3_ConfirmedIndex(index); /* exact source selection; no CVar mutation */\n',
      "confirmed manual selection hook")
    m=once(m,'    dwpsLastSurface=best;\n',
      '    dwpsLastSurface=best;\n'
      '    DWPS3_OnCasterPicked(); /* show actual selected BSP mesh triangles */\n',
      "caster highlighted selection")
    m=once(m,'ri.Cmd_AddCommand("dw_ps_picklight",DWPS_PickLight_f);',
      'ri.Cmd_AddCommand("dw_ps_picklight",DWPS3_PickLight_f);',
      "replace 14 degree picker")
    m=once(m,'    ri.Cmd_AddCommand("dw_ps_file",DWPS_File_f);',
      '    ri.Cmd_AddCommand("dw_ps_file",DWPS_File_f);\n'
      '    ri.Cmd_AddCommand("dw_ps_candidates",DWPS3_Candidates_f);\n'
      '    ri.Cmd_AddCommand("dw_ps_confirm",DWPS3_Confirm_f);\n'
      '    ri.Cmd_AddCommand("dw_ps_next",DWPS3_Next_f);\n'
      '    ri.Cmd_AddCommand("dw_ps_prev",DWPS3_Prev_f);\n'
      '    ri.Cmd_AddCommand("dw_ps_overlay",DWPS3_Overlay_f);',
      "register preview commands")
    m=once(m,'    ri.Cmd_RemoveCommand("dw_ps_file");',
      '    ri.Cmd_RemoveCommand("dw_ps_file");\n'
      '    ri.Cmd_RemoveCommand("dw_ps_candidates");\n'
      '    ri.Cmd_RemoveCommand("dw_ps_confirm");\n'
      '    ri.Cmd_RemoveCommand("dw_ps_next");\n'
      '    ri.Cmd_RemoveCommand("dw_ps_prev");\n'
      '    ri.Cmd_RemoveCommand("dw_ps_overlay");\n'
      '    DWPS3_OnWorldChanged();',
      "unregister visualization only")
    m=once(m,
      '"DarkWolf PCPS V2 (persistent per-map rules; all renderer defaults unchanged)\\n"',
      '"DarkWolf PCPS V3 (persistent folder + visual confirmed aiming)\\n"',
      "help version")
    m=once(m,
      '"dw_ps_lights       list available dynamic lights\\n"',
      '"dw_ps_lights       list available dynamic lights\\n"\n'
      '      "dw_ps_picklight    preview ranked lights under crosshair (NO edit)\\n"\n'
      '      "dw_ps_confirm [rank] select verified light from preview\\n"\n'
      '      "dw_ps_next/prev    cycle preview before confirmation\\n"\n'
      '      "dw_ps_candidates   rescan crosshair candidate list\\n"\n'
      '      "dw_ps_overlay 0|1  toggle on-screen light IDs and BSP outline\\n"',
      "help new options")
    scene=before["tr_scene.c"]
    assert 'DARKWOLF_PCPS_V3_PICK_VISUAL' not in scene
    scene=once(scene,'#include "tr_local.h"',
       '#include "tr_local.h"\n'
       '/* DARKWOLF_PCPS_V3_PICK_VISUAL_20261102: postprocess UI only. */\n'
       'extern void DWPS3_DrawOverlay(const refdef_t *fd);',
       "overlay prototype")
    scene=once(scene,'\t\tR_AddPostProcessCmd();\n\n\tRE_EndScene();',
       '\t\tR_AddPostProcessCmd();\n'
       '\t/* V3 debug UI is queued AFTER main post-process, BEFORE cgame 2D HUD. */\n'
       '\tDWPS3_DrawOverlay(fd);\n\n\tRE_EndScene();',
       "render overlay after postprocess")
    after={"tr_main.c":m,"tr_scene.c":scene}
    assert after["tr_main.c"].count(NAME)==1
    assert after["tr_scene.c"].count(NAME)==1
    assert "DARKWOLF_PCPS_PERSISTENCE_V3_FOLDER" in after["tr_main.c"]
    assert 'pendingLightsMask = DWPS_ApplyPendingMask(pendingLightsMask)' in m
    assert "R_RenderDlightCubemaps" in m
    assert "R_AddPostProcessCmd();" in scene
    if not check:
        for name,text in after.items():(root/name).write_text(text,encoding="utf-8")
    audit={
        "kind":"PCPS_V3_VISUAL_AIM_AND_PERMAP_FOLDER_EXPERIMENTAL",
        "parent_PCPS_V2_run":41427487879,
        "parent_safe_clean_run":41297344177,
        "parent_texture_fidelity_v2_run":41286257713,
        "modified_renderer_sources":["SP/code/rend2/tr_main.c","SP/code/rend2/tr_scene.c"],
        "unchanged_renderer_sources":["tr_backend.c","tr_init.c","tr_local.h","tr_shade.c","tr_world.c"],
        "new_GL_features":False,"new_GLSL_shaders":False,"new_CVar":False,
        "new_GPU_shadows_or_slot_budgets":False,
        "point_shadow_behavior":"Original PCPS V2; UI preview cannot change shadows before dw_ps_confirm",
        "source_picker":"raycast world BSP, combine distance-to-hit + angular source projection, 5 candidates",
        "light_selection":"explicit confirmed identity, reject changed or ambiguous current light",
        "visual":"postprocess queued 2D light IDs + preview candidate list + sampled selected BSP triangle wireframe",
        "saved_profile_directory":"active fs_homepath/Main/dw_pcps",
        "migration":"read valid old flat PCPS V2 profiles once only if no V3 folder file exists; preserve old originals",
        "folder_compatibility":"original DWPCPS_V2 journal/checksum/BSP signature kept",
        "source_before_sha256":{n:hashlib.sha256(v.encode()).hexdigest() for n,v in before.items()},
        "source_after_sha256":{n:hashlib.sha256(v.encode()).hexdigest() for n,v in after.items()},
        "GPU_user_acceptance":"PENDING; user confirmed PCPS V2 light#23 Factory worked"
    }
    if proof:
        p=Path(proof);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DW_PCPS_V3_SOURCE_SCOPE_AND_IDENTITIES_PASS")
    return audit
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("root",type=Path);a.add_argument("--check-only",action="store_true")
    a.add_argument("--proof",type=Path)
    p=a.parse_args()
    apply(p.root,p.check_only,p.proof)
