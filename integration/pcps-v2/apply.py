#!/usr/bin/env python3
"""Apply PCPS V2 durable per-map journaling ON TOP of exact PCPS V1 runtime.
The only new production source change is tr_main.c; tr_backend, tr_init,
tr_local and all shaders remain as in V1. Runtime defaults are unchanged.
"""
import argparse,hashlib,json
from pathlib import Path
MARK="DARKWOLF_PCPS_PERSISTENCE_V2_20261102"
ROOT=Path("SP/code/rend2")
def once(s,a,b,label):
    n=s.count(a)
    if n!=1:raise RuntimeError(f"{label}: exact anchor count {n}, expected 1")
    return s.replace(a,b,1)
def patch(root,check=False,proof=None):
    repo=Path(__file__).resolve().parent.parent
    old=(repo/"pcps-v1/runtime.inc").read_text(encoding="utf-8")
    addon=Path(__file__).with_name("persistence.inc").read_text(encoding="utf-8")
    assert "DARKWOLF_PCPS_RUNTIME_V1" in old
    assert MARK in addon
    file=Path(root)/ROOT/"tr_main.c"
    original=file.read_text(encoding="utf-8")
    assert MARK not in original
    assert original.count(old)==1, "PCPS V1 source must match EXACT shipped runtime"
    assert "DARKWOLF_BOSS1_PROVEN_SOURCE_LOCAL_FIX_CLEAN_PRODUCTION_V1" not in old
    rt=old
    rt=once(rt,'static char dwpsMap[MAX_QPATH]="";',
       'static char dwpsMap[MAX_QPATH]="";\n'
       '/* V2: defined after runtime functions, executes only in main-thread source selection. */\n'
       'static void DWPS_LoadCurrentMap(void);\n'
       'static qboolean DWPS_SaveCurrentMap(void);\n'
       'static void DWPS_PersistAfterChange(void);\n'
       'static void DWPS_Save_f(void);\n'
       'static void DWPS_Reload_f(void);\n'
       'static void DWPS_File_f(void);',
       "v2 persistence declarations")
    rt=once(rt,
       '    Q_strncpyz(dwpsMap,tr.world->name,sizeof(dwpsMap));\n'
       '    dwpsNumRules=0;\n'
       '    dwpsSelected=-1;\n'
       '    dwpsLastSurface=-1;\n'
       '}\nstatic qboolean DWPS_SameSource',
       '    Q_strncpyz(dwpsMap,tr.world->name,sizeof(dwpsMap));\n'
       '    dwpsNumRules=0;\n'
       '    dwpsSelected=-1;\n'
       '    dwpsLastSurface=-1;\n'
       '    DWPS_LoadCurrentMap(); /* V2: source/caster rules auto-load on BSP transition */\n'
       '}\nstatic qboolean DWPS_SameSource',
       "autoload each map")
    rt=once(rt,
       '"DarkWolf PCPS V1 (session-only; all defaults unchanged)\\n"',
       '"DarkWolf PCPS V2 (persistent per-map rules; all renderer defaults unchanged)\\n"',
       "help release")
    rt=once(rt,
       '"dw_ps_reset       clear ALL PCPS rules for current map\\n"',
       '"dw_ps_reset       clear ALL rules AND permanently save cleared profile\\n"\n'
       '      "dw_ps_save        save current map rules now (automatic after edits)\\n"\n'
       '      "dw_ps_reload      discard in-memory edits, reload saved per-map rules\\n"\n'
       '      "dw_ps_file        print current map and two persistent profile paths\\n"',
       "help commands")
    rt=once(rt,
       '"A saved index is not portable to another BSP.\\n"',
       '"A saved index is not portable to another BSP; V2 checks BSP fingerprint.\\n"',
       "help scope")
    rt=once(rt,
       '    dwpsRules[dwpsSelected].shadowOff=qtrue;\n',
       '    dwpsRules[dwpsSelected].shadowOff=qtrue;\n'
       '    DWPS_PersistAfterChange(); /* V2 file autosave */\n',
       "light off save")
    rt=once(rt,
       '    dwpsRules[dwpsSelected].shadowOff=qfalse;\n',
       '    dwpsRules[dwpsSelected].shadowOff=qfalse;\n'
       '    DWPS_PersistAfterChange(); /* V2 file autosave */\n',
       "light on save")
    rt=once(rt,
       '    r->numCasters++;\n',
       '    r->numCasters++;\n'
       '    DWPS_PersistAfterChange(); /* V2 file autosave */\n',
       "caster off save")
    rt=once(rt,
       '        r->numCasters--;\n',
       '        r->numCasters--;\n'
       '        DWPS_PersistAfterChange(); /* V2 file autosave */\n',
       "caster on save")
    rt=once(rt,
       '    Com_Memset(dwpsRules,0,sizeof(dwpsRules));\n'
       '    ri.Printf(PRINT_ALL,"PCPS: ALL overrides cleared; original point shadows restored\\n");',
       '    Com_Memset(dwpsRules,0,sizeof(dwpsRules));\n'
       '    DWPS_PersistAfterChange(); /* explicit reset persists empty map profile */\n'
       '    ri.Printf(PRINT_ALL,"PCPS: ALL overrides cleared; original point shadows restored\\n");',
       "reset persists")
    rt=once(rt,
       '    ri.Cmd_AddCommand("dw_ps_reset",DWPS_Reset_f);',
       '    ri.Cmd_AddCommand("dw_ps_reset",DWPS_Reset_f);\n'
       '    ri.Cmd_AddCommand("dw_ps_save",DWPS_Save_f);\n'
       '    ri.Cmd_AddCommand("dw_ps_reload",DWPS_Reload_f);\n'
       '    ri.Cmd_AddCommand("dw_ps_file",DWPS_File_f);',
       "register commands")
    rt=once(rt,
       '    ri.Cmd_RemoveCommand("dw_ps_reset");\n'
       '    DWPS_Reset_f();',
       '    ri.Cmd_RemoveCommand("dw_ps_reset");\n'
       '    ri.Cmd_RemoveCommand("dw_ps_save");\n'
       '    ri.Cmd_RemoveCommand("dw_ps_reload");\n'
       '    ri.Cmd_RemoveCommand("dw_ps_file");\n'
       '    /* V2: Unload renderer/reset session memory WITHOUT deleting saved rules. */\n'
       '    dwpsNumRules=0;\n'
       '    dwpsSelected=-1;\n'
       '    dwpsLastSurface=-1;\n'
       '    dwpsWorld=NULL;\n'
       '    dwpsWorldSurfaces=NULL;\n'
       '    dwpsMap[0]=0;',
       "vid_restart safe unregister")
    rt=rt.rstrip()+"\n\n"+addon.rstrip()+"\n"
    new=once(original,old,rt,"replace only injected PCPS V1 runtime")
    assert new.count(MARK)==1
    assert 'DWPS_LoadCurrentMap(); /* V2:' in new
    assert 'DWPS_PersistAfterChange(); /* V2 file autosave */' in new
    assert "DWPS_Reset_f();" not in new[new.index('void DWPS_Unregister(void)'):new.index('unsigned int DWPS_ApplyPendingMask')]
    assert 'pendingLightsMask = DWPS_ApplyPendingMask(pendingLightsMask);' in new
    assert 'DARKWOLF_CRYPT1_PERSISTENT_FIRE_SHADOW_PRIORITY_FIX_V1_20261028' in new
    if not check:file.write_text(new,encoding="utf-8")
    result={
      "type":"DW_PCPS_V2_PERSISTENT_MAP_PROFILES",
      "parent_run":41322232296,
      "accepted_clean_parent_run":41297344177,
      "accepted_texture_material_run":41286257713,
      "source_before":hashlib.sha256(original.encode()).hexdigest(),
      "source_after":hashlib.sha256(new.encode()).hexdigest(),
      "changed_source_files":["SP/code/rend2/tr_main.c"],
      "no_cvar_or_shader_changes":True,
      "no_global_material_suppression":True,
      "no_slot_budget_increase":True,
      "saved_operations":["dw_ps_light_off","dw_ps_light_on","dw_ps_caster_off","dw_ps_caster_on","dw_ps_reset"],
      "file_format":"DWPCPS_V2; per-BSP dual-slot journal with FNV checksum and map hash",
      "map_world_hash":"BSP world surface material/bounds/type, surface count, map path, data size",
      "caster_validation":"map-local surface ID AND current shader and AABB and ptr, fail-open",
      "source_validation":"origin/radius/class/fixtureId, old V1 runtime matcher",
      "all_rules_auto_load":"first source-shadow selection on each loaded map",
      "vid_restart":"memory only cleared; persisted files never reset by renderer shutdown",
      "game_restart":"profiles loaded again from active fs_homepath",
      "readback_validation":"read-after-write verifies exact bytes before declaring save",
      "local_disk_and_GPU_testing":"PENDING user hardware validation"
    }
    if proof:
        out=Path(proof);out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DW_PCPS_V2_PERSISTENT_SOURCE_PASS",json.dumps(result,ensure_ascii=False))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("root",type=Path)
    p.add_argument("--check-only",action="store_true")
    p.add_argument("--proof",type=Path)
    a=p.parse_args()
    patch(a.root,a.check_only,a.proof)
