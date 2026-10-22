#!/usr/bin/env python3
"""Android-only safe scripted AI readiness for auto-playerstart.

RTCW SP must finish AICast_CheckLoadGame before the UI's automated arrow can
start the player script. Unready ai_* placeholder entities have neither a
client nor a use callback. Never bypass a script command or fabricate use().
Only wait for real AIChar_spawn placeholders, with a hard upper bound.
"""
from __future__ import annotations
from pathlib import Path
import sys


def one(text: str, old: str, new: str, context: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{context}: expected unique anchor, got {count}")
    return text.replace(old, new, 1)


def patch_game_main(src: str) -> str:
    src = one(
        src,
        "void G_UpdateCvars( void ) {",
        """/* DW_ANDROID_AI_READY_PLAYERSTART_V01: QVM runs on host builds too.
 * Read the Android launcher cvar at runtime, never use __ANDROID__ here. */
static qboolean dwAndroidDeferredAutoPlayerstart;

void G_UpdateCvars( void ) {""",
        "playerstart deferred state")
    src = one(
        src,
        "if ( cv->modificationCount != cv->vmCvar->modificationCount ) {",
        """if ( cv->modificationCount != cv->vmCvar->modificationCount ||
                     (dwAndroidDeferredAutoPlayerstart &&
                      !Q_stricmp(cv->cvarName, "g_playerStart")) ) {""",
        "recheck queued g_playerStart after AI readiness")
    src = one(
        src,
        "if ( player && cv->vmCvar->integer ) {",
        """if ( player && cv->vmCvar->integer ) {
                        /* Android UI may dismiss its mission panel before the
                         * server finishes spawning the cast. In RTCW, the
                         * normal 'rockandroll' signal is sent only once
                         * AICast_CheckLoadGame clears saveGamePending.
                         * Never save/run playerstart while NPCs are pending. */
                        if (trap_Cvar_VariableIntegerValue("dw_android_auto_playerstart") &&
                            saveGamePending) {
                            if (!dwAndroidDeferredAutoPlayerstart) {
                                G_Printf("DW_ANDROID_PLAYERSTART_DEFERRED_AI=PASS\\n");
                            }
                            dwAndroidDeferredAutoPlayerstart = qtrue;
                            continue;
                        }
                        if (dwAndroidDeferredAutoPlayerstart) {
                            G_Printf("DW_ANDROID_PLAYERSTART_AI_READY=PASS\\n");
                            dwAndroidDeferredAutoPlayerstart = qfalse;
                        }""",
        "defer early Android playerstart without losing request")
    src = one(
        src,
        "void G_InitGame( int levelTime, int randomSeed, int restart ) {\n\tint i;",
        "void G_InitGame( int levelTime, int randomSeed, int restart ) {\n\tint i;\n"
        "\tdwAndroidDeferredAutoPlayerstart = qfalse;",
        "clear pending request on map restart")
    return src


def patch_game_script(src: str) -> str:
    src = one(
        src,
        "qboolean G_ScriptAction_AlertEntity( gentity_t *ent, char *params ) {",
        """/* DW_ANDROID_AI_ALERT_WAIT_V01: wait only for a real delayed AI spawn.
 * Never hide legitimate scripting errors or drop the alertentity event. */
void AIChar_spawn( gentity_t *ent );
qboolean G_ScriptAction_AlertEntity( gentity_t *ent, char *params ) {""",
        "declare RTCW's genuine pending AI spawn callback")
    src = one(
        src,
        """\t\tif ( !alertent->use ) {
\t\t\tG_Error( "G_Scripting: alertentity \\"%s\\" (classname = %s) doesn't have a \\"use\\" function\\n", params, alertent->classname );
\t\t}""",
        """\t\tif ( !alertent->use ) {
            if (trap_Cvar_VariableIntegerValue("dw_android_auto_playerstart") &&
                alertent->inuse && alertent->classname &&
                !Q_stricmpn(alertent->classname, "ai_", 3) &&
                alertent->think == AIChar_spawn) {
                int elapsed = level.time - ent->scriptStatus.scriptStackChangeTime;
                /* G_Script_ScriptRun retries the same action on qfalse.
                 * The delay is finite; a genuinely broken spawn stays fatal. */
                if (elapsed >= 0 && elapsed < 15000) {
                    if (elapsed == 0) {
                        G_Printf("DW_ANDROID_AI_ALERT_WAIT=target:%s pending_spawn=1\\n",
                                 params);
                    }
                    return qfalse;
                }
            }
            G_Printf("DW_ANDROID_AI_ALERT_INVALID target=%s class=%s client=%d "
                     "use=%d delayedAI=%d time=%d\\n",
                     params, alertent->classname ? alertent->classname : "(null)",
                     alertent->client != NULL, alertent->use != NULL,
                     alertent->think == AIChar_spawn, level.time);
\t\t\tG_Error( "G_Scripting: alertentity \\"%s\\" (classname = %s) doesn't have a \\"use\\" function\\n", params, alertent->classname );
\t\t}""",
        "bounded retry for genuine unspawned AI")
    return src


def selftest() -> None:
    main = (
        'void G_UpdateCvars( void ) {\n'
        'if ( cv->modificationCount != cv->vmCvar->modificationCount ) {\n'
        'if ( player && cv->vmCvar->integer ) {\n'
        'void G_InitGame( int levelTime, int randomSeed, int restart ) {\n\tint i;')
    m = patch_game_main(main)
    assert "dwAndroidDeferredAutoPlayerstart = qtrue;" in m
    assert 'dw_android_auto_playerstart' in m
    assert "DW_ANDROID_PLAYERSTART_AI_READY" in m
    assert "dwAndroidDeferredAutoPlayerstart = qfalse;" in m
    script = (
        'qboolean G_ScriptAction_AlertEntity( gentity_t *ent, char *params ) {\n'
        '\t\tif ( !alertent->use ) {\n'
        '\t\t\tG_Error( "G_Scripting: alertentity \\"%s\\" (classname = %s) '
        'doesn\'t have a \\"use\\" function\\n", params, alertent->classname );\n'
        '\t\t}')
    s = patch_game_script(script)
    assert "alertent->think == AIChar_spawn" in s
    assert "return qfalse;" in s
    assert "elapsed < 15000" in s
    assert s.count("G_Error(") == 1
    print("DW_ANDROID_AI_SCRIPT_READY_SELFTEST=PASS")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    elif len(sys.argv) == 3 and sys.argv[1] == "--native":
        source = Path(sys.argv[2])
        main = source / "SP/code/game/g_main.c"
        script = source / "SP/code/game/g_script_actions.c"
        patched_main = patch_game_main(main.read_text())
        patched_script = patch_game_script(script.read_text())
        main.write_text(patched_main)
        script.write_text(patched_script)
        print("DW_ANDROID_AI_SCRIPT_READY_SOURCE=PASS")
    else:
        raise SystemExit("usage: patch_ai_script_ready.py --selftest | --native SOURCE")
