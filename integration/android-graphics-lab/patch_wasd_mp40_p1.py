#!/usr/bin/env python3
"""Android-only P1 movement / first-person MP40 acceptance patch.

Applied to reconstructed source after existing navigation patch. Do not touch
desktop production. Instrument the actual server simulation rather than
declaring PASS when a JNI button was tapped.
"""
from pathlib import Path
import sys

def one(s, old, new, label):
    if s.count(old) != 1:
        raise RuntimeError(f"{label}: expected one anchor; got {s.count(old)}")
    return s.replace(old, new, 1)

def patch_game(s):
    needle = """        Cmd_StopCamera_f(ent);
        trap_SendServerCommand(ent - g_entities,
            "print \\"DARKWOLF_ANDROID_NOCLIP_STOPCAM=PASS\\n\\"");"""
    repl = """        Cmd_StopCamera_f(ent);
        /* Synchronize the cgame camera and its first-person view as well.
         * This is requested ONLY by the user explicitly selecting noclip;
         * regular story cinematics remain unchanged. */
        trap_SendServerCommand(ent - g_entities, "stopCam");
        trap_SendServerCommand(ent - g_entities,
            "print \\"DARKWOLF_ANDROID_NOCLIP_STOPCAM=PASS\\n\\"");"""
    return one(s,needle,repl,"stop client and server cameras")

def patch_active(s):
    # Throttled server-side observation, after PMove, never force PM_NORMAL.
    needle = "\tmonsterslick = Pmove( &pm );"
    repl = r'''	monsterslick = Pmove( &pm );
    /* DW_ANDROID_SERVER_PMOVE_P1: the authoritative check. The client-side
     * usercmd marker alone is insufficient to establish player motion.
     * Never change command inputs, weapons or cinematic state here. */
    if (trap_Cvar_VariableIntegerValue("dw_android_nav_trace") &&
        !(ent->r.svFlags & SVF_CASTAI) &&
        (pm.cmd.forwardmove || pm.cmd.rightmove || pm.cmd.upmove)) {
        static int dwLastTrace;
        if (level.time - dwLastTrace >= 700) {
            dwLastTrace = level.time;
            G_Printf("DW_NAV_SERVER cmd=%d,%d,%d pm=%d camera=%d "
                     "origin=%.1f,%.1f,%.1f delta=%.2f,%.2f,%.2f "
                     "weapon=%d health=%d\\n",
                     pm.cmd.forwardmove, pm.cmd.rightmove, pm.cmd.upmove,
                     client->ps.pm_type, client->cameraPortal != NULL,
                     client->ps.origin[0],client->ps.origin[1],client->ps.origin[2],
                     client->ps.origin[0]-client->oldOrigin[0],
                     client->ps.origin[1]-client->oldOrigin[1],
                     client->ps.origin[2]-client->oldOrigin[2],
                     client->ps.weapon,client->ps.stats[STAT_HEALTH]);
        }
    }'''
    return one(s,needle,repl,"server PMove trace")

def patch_client(s):
    # Show weapon/camera state from actual server snapshot in existing monitor.
    needle = '"Movement: %s%s | camera: %s\\n"'
    repl = ('"Movement: %s%s | camera: %s\\n"\n'
            '        "Weapon: %d | gun: %d | FP gun: %d | third: %d\\n"')
    s = one(s,needle,repl,"monitor weapon format")
    needle = '        cl.snap.valid ? cl.snap.ps.origin[0] : 0.0f,'
    repl = ('        cl.snap.valid ? (int)cl.snap.ps.weapon : -1,\n'
            '        Cvar_VariableIntegerValue("cg_drawGun"),\n'
            '        Cvar_VariableIntegerValue("cg_drawFPGun"),\n'
            '        Cvar_VariableIntegerValue("cg_thirdPerson"),\n'
            '        cl.snap.valid ? cl.snap.ps.origin[0] : 0.0f,')
    s = one(s,needle,repl,"monitor weapon args")
    return s

def patch_ui(s):
    # Dedicated explicit test button. No forced campaign inventory changes.
    s = one(s,
        '"INPUT & COMMAND MONITOR (toggle)"',
        '"INPUT & COMMAND MONITOR (toggle)",\n'
        '            "EQUIP MP40 (TEST ONLY)"',
        "lab item")
    s = one(s,
        '                case 17: labToggleInputMonitor(); break;',
        '                case 17: labToggleInputMonitor(); break;\n'
        '                case 18: labEquipMp40Test(); break;',
        "lab handler")
    needle = '    private void labHelp() {'
    impl = '''    private void labEquipMp40Test() {
        new android.app.AlertDialog.Builder(this)
            .setTitle("MP40 visual test")
            .setMessage("Requires a cheats-enabled SP map (MAP uses spdevmap). "
                + "This gives weapons/ammo and selects MP40 only on request. "
                + "After the cutscene check Weapon=3 and cg_drawGun=1 "
                + "in INPUT & COMMAND MONITOR. Ordinary campaign inventory "
                + "is not modified automatically.")
            .setPositiveButton("EQUIP", (d,w) -> {
                labSend("cg_drawGun 1");
                labSend("cg_drawFPGun 1");
                labSend("cg_thirdPerson 0");
                labSend("cg_norender 0");
                labSend("give weapons");
                labSend("give ammo");
                labSend("weapon 3");
            }).setNegativeButton("CANCEL", null).show();
    }

'''
    s=one(s,needle,impl+needle,"lab equip test")
    return s

def selftest():
    assert 'stopCam' in patch_game('''        Cmd_StopCamera_f(ent);
        trap_SendServerCommand(ent - g_entities,
            "print \\"DARKWOLF_ANDROID_NOCLIP_STOPCAM=PASS\\n\\"");''')
    assert 'DW_NAV_SERVER' in patch_active("\tmonsterslick = Pmove( &pm );")
    demo = ('"Movement: %s%s | camera: %s\\n"\n'
            '        cl.snap.valid ? cl.snap.ps.origin[0] : 0.0f,')
    assert "Weapon: %d" in patch_client(demo)
    demo_ui=('"INPUT & COMMAND MONITOR (toggle)"\n'
             '                case 17: labToggleInputMonitor(); break;\n'
             '    private void labHelp() {')
    assert 'labEquipMp40Test' in patch_ui(demo_ui)
    print("DW_WASD_MP40_P1_SELFTEST=PASS")

def main(root):
    game=root/"SP/code/game/g_cmds.c"
    active=root/"SP/code/game/g_active.c"
    client=root/"SP/code/client/cl_ui.c"
    for p,fn in ((game,patch_game),(active,patch_active),(client,patch_client)):
        p.write_text(fn(p.read_text()))
    print("DW_WASD_MP40_P1_NATIVE=PASS")

if __name__=="__main__":
    if len(sys.argv)==2 and sys.argv[1]=="--selftest":
        selftest()
    elif len(sys.argv)==3 and sys.argv[1]=="--native":
        main(Path(sys.argv[2]))
    elif len(sys.argv)==3 and sys.argv[1]=="--java":
        p=Path(sys.argv[2])/"app/src/main/java/org/darkwolf/rend2/DarkWolfActivity.java"
        p.write_text(patch_ui(p.read_text()))
        print("DW_WASD_MP40_P1_JAVA=PASS")
    else:
        raise SystemExit("usage: --selftest | --native ROOT | --java PROJECT")
