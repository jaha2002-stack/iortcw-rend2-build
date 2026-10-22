#!/usr/bin/env python3
"""Android Graphics Lab navigation diagnosis and explicit noclip cinematic escape.

Apply --native AFTER patch_touch_input.py --native and patch_lab_bridge.py;
apply --java AFTER patch_touch_input.py --java. This mutates reconstructed
Android source only. In-game status is published on the engine thread and read
from Android UI under a mutex. No engine CVar mutation from Java.
"""
from pathlib import Path
import sys

MARKER = "DARKWOLF_ANDROID_NAVIGATION_DIAGNOSTICS_V01"

def one(src: str, old: str, new: str, label: str) -> str:
    hits = src.count(old)
    if hits != 1:
        raise RuntimeError(f"{label}: expected 1 anchor, got {hits}")
    return src.replace(old, new, 1)

def patch_game(src: str) -> str:
    # RTCW's g_active.c zeroes all usercmd movement and sets PM_FREEZE when
    # cameraPortal is active. Noclip alone cannot bypass that. Explicitly
    # selecting noclip stops the active camera using the stock stopcam hook.
    src = one(
        src,
        "void Cmd_Noclip_f( gentity_t *ent ) {",
        """/* DW_ANDROID_LAB_NOCLIP_CINEMATIC_STOP_V01
 * Native Android launcher enables this only in its Graphics Lab mode.
 * QVM bytecode has no __ANDROID__; use a runtime CVar, not a macro. */
void Cmd_StopCamera_f( gentity_t *ent );
void Cmd_Noclip_f( gentity_t *ent ) {""",
        "declare original RTCW stopcam from noclip")
    src = one(
        src,
        "\tent->client->noclip = !ent->client->noclip;\n\n\ttrap_SendServerCommand",
        """\tent->client->noclip = !ent->client->noclip;
    if (ent->client->noclip &&
        trap_Cvar_VariableIntegerValue("dw_android_camera_noclip") &&
        ent->client->cameraPortal) {
        /* This explicit user action dismisses the scripted camera properly:
         * sends stopcam, clears EF_VIEWING_CAMERA and frees PM_NOCLIP movement.
         * Without this, g_active.c clears every WASD usercmd during cinematic. */
        Cmd_StopCamera_f(ent);
        trap_SendServerCommand(ent - g_entities,
            "print \\"DARKWOLF_ANDROID_NOCLIP_STOPCAM=PASS\\n\\"");
    }

\ttrap_SendServerCommand""",
        "noclip stops active cinematic if explicitly requested")
    return src

REPORT = r'''
/* DARKWOLF_ANDROID_NAVIGATION_DIAGNOSTICS_V01
 * Engine-thread-only player/cvar sampling with UI-thread snapshot retrieval.
 * This shows WHY native WASD does not move: inactive client, UI catcher,
 * paused SP simulation, PM_FREEZE/camera cutscene or server cheats disabled.
 */
static pthread_mutex_t dwTouchDebugLock = PTHREAD_MUTEX_INITIALIZER;
static char dwTouchDebugText[768] = "No gameplay usercmd received yet";
static volatile unsigned int dwTouchPressCounter;
static volatile unsigned int dwTouchLookCounter;
static unsigned int dwTouchUsercmdCounter;

JNIEXPORT jstring JNICALL
Java_org_darkwolf_rend2_DarkWolfActivity_nativeLabInputStatus(
    JNIEnv *env, jclass clazz)
{
    char local[sizeof(dwTouchDebugText)];
    jstring out;
    (void)clazz;
    pthread_mutex_lock(&dwTouchDebugLock);
    Q_strncpyz(local, dwTouchDebugText, sizeof(local));
    pthread_mutex_unlock(&dwTouchDebugLock);
    out = (*env)->NewStringUTF(env, local);
    return out;
}

static void DW_AndroidPublishTouchStatus(const usercmd_t *cmd,
    unsigned int bits, int yaw, int pitch, int blocked)
{
    char report[sizeof(dwTouchDebugText)];
    char lastCmd[DW_LAB_CMD_CAP];
    int catcher = Key_GetCatcher();
    int pm = cl.snap.valid ? (int)cl.snap.ps.pm_type : -1;
    const char *pmText = !cl.snap.valid ? "NO SNAPSHOT" :
        pm == PM_NOCLIP ? "NOCLIP" :
        pm == PM_FREEZE ? "FREEZE: cinematic/reloading" :
        pm == PM_NORMAL ? "NORMAL" :
        pm == PM_INTERMISSION ? "INTERMISSION" : "OTHER";
    pthread_mutex_lock(&dwLabQueueLock);
    Q_strncpyz(lastCmd, dwLabLastDispatched, sizeof(lastCmd));
    pthread_mutex_unlock(&dwLabQueueLock);
    ++dwTouchUsercmdCounter;
    snprintf(report, sizeof(report),
        "Touch presses: %u | look: %u | cmd: %u\n"
        "WASD mask: 0x%x | fwd: %d | side: %d\n"
        "Look delta: %d / %d\n"
        "Client state: %d | UI catcher: 0x%x | paused: %d\n"
        "Movement: %s%s | camera: %s\n"
        "Position: %.1f %.1f %.1f\n"
        "sv_cheats: %d | g_reloading: %d\n"
        "Last dispatch: %s",
        (unsigned)__sync_fetch_and_or(&dwTouchPressCounter, 0),
        (unsigned)__sync_fetch_and_or(&dwTouchLookCounter, 0),
        dwTouchUsercmdCounter, bits,
        cmd ? (int)cmd->forwardmove : 0,
        cmd ? (int)cmd->rightmove : 0,
        yaw, pitch,
        (int)clc.state, catcher,
        Cvar_VariableIntegerValue("cl_paused"),
        pmText, blocked ? " [INPUT BLOCKED]" : "",
        (cl.snap.valid && (cl.snap.ps.eFlags & EF_VIEWING_CAMERA)) ?
            "SCRIPTED" : "PLAYER",
        cl.snap.valid ? cl.snap.ps.origin[0] : 0.0f,
        cl.snap.valid ? cl.snap.ps.origin[1] : 0.0f,
        cl.snap.valid ? cl.snap.ps.origin[2] : 0.0f,
        Cvar_VariableIntegerValue("sv_cheats"),
        Cvar_VariableIntegerValue("g_reloading"),
        lastCmd);
    pthread_mutex_lock(&dwTouchDebugLock);
    Q_strncpyz(dwTouchDebugText, report, sizeof(dwTouchDebugText));
    pthread_mutex_unlock(&dwTouchDebugLock);
}
'''

def patch_engine(src: str) -> str:
    src = one(src,
        "static volatile unsigned int androidGameDesiredMask;\n",
        "static volatile unsigned int androidGameDesiredMask;\n"
        "static volatile unsigned int dwTouchPressCounter;\n"
        "static volatile unsigned int dwTouchLookCounter;\n",
        "declare touch counters before JNI calls")
    # REPORT defines a different module-global declaration only if insertion
    # below already supplies those; keep a single definition.
    report = REPORT.replace(
        "static volatile unsigned int dwTouchPressCounter;\n"
        "static volatile unsigned int dwTouchLookCounter;\n", "")
    src = one(src,
        "    if (down) {\n        __sync_fetch_and_or(&androidGameDesiredMask, bit);",
        "    if (down) {\n"
        "        __sync_fetch_and_add(&dwTouchPressCounter, 1);\n"
        "        __sync_fetch_and_or(&androidGameDesiredMask, bit);",
        "count actual JNI button down calls")
    src = one(src,
        "    x = (int)(dx * 150.0f);",
        "    __sync_fetch_and_add(&dwTouchLookCounter, 1);\n"
        "    x = (int)(dx * 150.0f);",
        "count actual JNI camera swipe events")
    src = one(src,
        "void CL_AndroidApplyTouchInput(usercmd_t *cmd)",
        report + "\nvoid CL_AndroidApplyTouchInput(usercmd_t *cmd)",
        "insert read-only client status telemetry")
    src = one(src,
        """    if (clc.state != CA_ACTIVE ||
        (Key_GetCatcher() & (KEYCATCH_UI | KEYCATCH_CONSOLE)))
        return;""",
        """    if (clc.state != CA_ACTIVE ||
        (Key_GetCatcher() & (KEYCATCH_UI | KEYCATCH_CONSOLE))) {
        DW_AndroidPublishTouchStatus(cmd,
            androidGameDesiredMask | taps, yaw, pitch, 1);
        return;
    }""",
        "report blocked movement as well as working movement")
    src = one(src,
        "\n}\n\nvoid CL_AndroidConsumeUiTap(void)",
        "\n    DW_AndroidPublishTouchStatus(cmd, bits, yaw, pitch, 0);\n"
        "}\n\nvoid CL_AndroidConsumeUiTap(void)",
        "report input after final usercmd movement and yaw")
    src = one(src,
        "static unsigned dwLabCmdRead, dwLabCmdWrite;",
        "static unsigned dwLabCmdRead, dwLabCmdWrite;\n"
        'static char dwLabLastDispatched[DW_LAB_CMD_CAP] = "(none)";',
        "command execution marker backing storage")
    src = one(src,
        "        Cbuf_ExecuteText(EXEC_APPEND,local);",
        """        pthread_mutex_lock(&dwLabQueueLock);
        Q_strncpyz(dwLabLastDispatched,local,sizeof(dwLabLastDispatched));
        dwLabLastDispatched[strcspn(dwLabLastDispatched,"\\r\\n")]=0;
        pthread_mutex_unlock(&dwLabQueueLock);
        Cbuf_ExecuteText(EXEC_APPEND,local);""",
        "report last command actually handed to command buffer")
    return src

def patch_activity(src: str) -> str:
    src = one(src,
        "    static native String nativeLabCvars();",
        "    static native String nativeLabCvars();\n"
        "    static native String nativeLabInputStatus();",
        "expose JNI game-state status to Android Activity")
    return src

def selftest() -> None:
    from textwrap import dedent
    g = ('void Cmd_Noclip_f( gentity_t *ent ) {\n'
         '\tent->client->noclip = !ent->client->noclip;\n\n'
         '\ttrap_SendServerCommand')
    out = patch_game(g)
    assert "Cmd_StopCamera_f(ent);" in out
    assert 'trap_Cvar_VariableIntegerValue("dw_android_camera_noclip")' in out
    assert "DW_ANDROID_LAB_NOCLIP_CINEMATIC_STOP_V01" in out
    j = "    static native String nativeLabCvars();"
    assert "nativeLabInputStatus();" in patch_activity(j)
    assert "dwTouchDebugText" in REPORT
    assert "PM_FREEZE" in REPORT
    assert "sv_cheats" in REPORT
    print("GRAPHICS_LAB_NAVIGATION_DIAGNOSTICS_SELFTEST=PASS")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    elif len(sys.argv) == 3 and sys.argv[1] in ("--native", "--java"):
        root = Path(sys.argv[2])
        if sys.argv[1] == "--native":
            engine = root/"SP/code/client/cl_ui.c"
            game = root/"SP/code/game/g_cmds.c"
            engine.write_text(patch_engine(engine.read_text()))
            game.write_text(patch_game(game.read_text()))
            print("GRAPHICS_LAB_NAVIGATION_NATIVE_AND_GAME_VM=PASS")
        else:
            act = root/"app/src/main/java/org/darkwolf/rend2/DarkWolfActivity.java"
            act.write_text(patch_activity(act.read_text()))
            print("GRAPHICS_LAB_NAVIGATION_STATUS_JAVA=PASS")
    else:
        raise SystemExit(
            "usage: patch_navigation_diag.py --selftest | --native <source> | --java <project>")
