#!/usr/bin/env python3
"""Android-only direct touch movement/look bridge, independent of SDL mouse focus.

Run --native after reconstructed GLES+Graphics Lab source patches; run --java
after generated Android SDL Activity, touch overlay and Graphics Lab injection.
Desktop ioRTCW source is never modified.
"""
from __future__ import annotations
from pathlib import Path
import sys

MARKER = "DARKWOLF_ANDROID_DIRECT_WASD_V01"

def once(s: str, old: str, new: str, label: str) -> str:
    hits = s.count(old)
    if hits != 1:
        raise RuntimeError(f"{label}: expected one anchor, got {hits}")
    return s.replace(old, new, 1)

def patch_native_ui(src: str) -> str:
    src = once(src,
        "static volatile unsigned int androidGameDesiredMask;\n",
        "static volatile unsigned int androidGameDesiredMask;\n"
        "static volatile unsigned int androidMoveTapMask;\n"
        "static volatile int androidLookMilliYaw;\n"
        "static volatile int androidLookMilliPitch;\n",
        "touch movement and camera state")
    src = once(src,
        "    if (down)\n        __sync_fetch_and_or(&androidGameDesiredMask, bit);\n    else\n        __sync_fetch_and_and(&androidGameDesiredMask, ~bit);",
        """    if (down) {
        __sync_fetch_and_or(&androidGameDesiredMask, bit);
        /* Preserve a quick tap even if touch down and up fall between
         * successive GL/game frames. */
        if (bit & (DW_ACT_FORWARD | DW_ACT_BACK |
                   DW_ACT_LEFT | DW_ACT_RIGHT))
            __sync_fetch_and_or(&androidMoveTapMask, bit);
    } else {
        __sync_fetch_and_and(&androidGameDesiredMask, ~bit);
    }""",
        "touch action press retention")
    src = once(src,
        "    __sync_lock_test_and_set(&androidGameDesiredMask, 0);\n}",
        """    __sync_lock_test_and_set(&androidGameDesiredMask, 0);
    __sync_lock_test_and_set(&androidMoveTapMask, 0);
    __sync_lock_test_and_set(&androidLookMilliYaw, 0);
    __sync_lock_test_and_set(&androidLookMilliPitch, 0);
}""",
        "clear held buttons, taps and camera delta")
    src = once(src,
        '        case DW_ACT_FORWARD:  cmd = down ? "+forward\\\\n"  : "-forward\\\\n"; break;\n'
        '        case DW_ACT_BACK:     cmd = down ? "+back\\\\n"     : "-back\\\\n"; break;\n'
        '        case DW_ACT_LEFT:     cmd = down ? "+moveleft\\\\n" : "-moveleft\\\\n"; break;\n'
        '        case DW_ACT_RIGHT:    cmd = down ? "+moveright\\\\n": "-moveright\\\\n"; break;',
        """        /* Directional touches are applied directly in CL_CreateCmd.
         * Console +forward would execute a frame too late (or be dropped). */
        case DW_ACT_FORWARD:
        case DW_ACT_BACK:
        case DW_ACT_LEFT:
        case DW_ACT_RIGHT:
            return;""",
        "replace delayed direction console path")
    native_function = r'''
/* DARKWOLF_ANDROID_DIRECT_WASD_V01
 * JNI UI thread publishes atomic inputs. CL_CreateCmd consumes them at the
 * correct simulation point, after CL_KeyMove and CL_MouseMove, before command
 * angles/serverTime are finalized. No unsafe cvar/client mutations on UI thread.
 */
JNIEXPORT void JNICALL
Java_org_darkwolf_rend2_DarkWolfActivity_nativeQueueLookDelta(
        JNIEnv *env, jclass clazz, jfloat dx, jfloat dy)
{
    int x, y;
    (void)env; (void)clazz;
    /* Clamp an individual SDL/Android touch event against extreme jumps.
     * Each physical screen pixel is ~0.15 degrees of view rotation. */
    if (dx < -250.0f) dx = -250.0f;
    if (dx > 250.0f) dx = 250.0f;
    if (dy < -250.0f) dy = -250.0f;
    if (dy > 250.0f) dy = 250.0f;
    x = (int)(dx * 150.0f);
    y = (int)(dy * 150.0f);
    __sync_fetch_and_add(&androidLookMilliYaw, x);
    __sync_fetch_and_add(&androidLookMilliPitch, y);
}

void CL_AndroidApplyTouchInput(usercmd_t *cmd)
{
    unsigned int bits, taps;
    int moveForward, moveSide, yaw, pitch, value;
    static int evidence;

    if (!cmd)
        return;
    taps = __sync_lock_test_and_set(&androidMoveTapMask, 0);
    yaw = __sync_lock_test_and_set(&androidLookMilliYaw, 0);
    pitch = __sync_lock_test_and_set(&androidLookMilliPitch, 0);
    if (clc.state != CA_ACTIVE ||
        (Key_GetCatcher() & (KEYCATCH_UI | KEYCATCH_CONSOLE)))
        return;

    bits = androidGameDesiredMask | taps;
    moveForward = ((bits & DW_ACT_FORWARD) ? 127 : 0) -
                  ((bits & DW_ACT_BACK) ? 127 : 0);
    moveSide = ((bits & DW_ACT_RIGHT) ? 127 : 0) -
               ((bits & DW_ACT_LEFT) ? 127 : 0);

    /* Preserve Bluetooth/USB keyboard inputs by adding, not replacing.
     * Clamp to signed usercmd_t movement range. */
    value = cmd->forwardmove + moveForward;
    if (value > 127) value = 127;
    if (value < -127) value = -127;
    cmd->forwardmove = (signed char)value;
    value = cmd->rightmove + moveSide;
    if (value > 127) value = 127;
    if (value < -127) value = -127;
    cmd->rightmove = (signed char)value;

    /* Mouse processing might be disabled by SDL's mouseActive flag on mobile.
     * Apply camera turn directly to RTCW client viewangles on its own thread. */
    if (yaw || pitch) {
        cl.viewangles[YAW] -= yaw * 0.001f;
        cl.viewangles[PITCH] += pitch * 0.001f;
        if (cl.viewangles[PITCH] > 89.0f)
            cl.viewangles[PITCH] = 89.0f;
        if (cl.viewangles[PITCH] < -89.0f)
            cl.viewangles[PITCH] = -89.0f;
    }
    if ((bits & (DW_ACT_FORWARD | DW_ACT_BACK |
                 DW_ACT_LEFT | DW_ACT_RIGHT)) && evidence < 4) {
        ++evidence;
        Com_Printf("DARKWOLF_ANDROID_DIRECT_WASD=PASS forward=%d side=%d\n",
                   cmd->forwardmove, cmd->rightmove);
    }
    if ((yaw || pitch) && evidence < 8) {
        ++evidence;
        Com_Printf("DARKWOLF_ANDROID_TOUCH_LOOK=PASS yaw=%d pitch=%d\n",
                   yaw, pitch);
    }
}
'''
    return once(src,
        "void CL_AndroidConsumeUiTap(void)",
        native_function + "\nvoid CL_AndroidConsumeUiTap(void)",
        "direct usercmd and look JNI function")

def patch_input(src: str) -> str:
    src = once(src,
        "usercmd_t CL_CreateCmd( void ) {",
        """#ifdef __ANDROID__
extern void CL_AndroidApplyTouchInput(usercmd_t *cmd);
#endif
usercmd_t CL_CreateCmd( void ) {""",
        "declare usercmd bridge")
    src = once(src,
        "\tCL_MouseMove( &cmd );",
        """\tCL_MouseMove( &cmd );
#ifdef __ANDROID__
\t/* Direct WASD and look: never depend on delayed console commands. */
\tCL_AndroidApplyTouchInput(&cmd);
#endif""",
        "call bridge after mouse and keyboard movement")
    return src

def patch_activity(src: str) -> str:
    return once(src,
        "    static native void nativeSetGameAction(int action, boolean down);",
        "    static native void nativeSetGameAction(int action, boolean down);\n"
        "    static native void nativeQueueLookDelta(float deltaX, float deltaY);",
        "Android Activity JNI look method")

def patch_overlay(src: str) -> str:
    src = once(src,
        "    private final RectF menuRect = new RectF();",
        """    private final RectF menuRect = new RectF();
    private final RectF wRect = new RectF();
    private final RectF aRect = new RectF();
    private final RectF sRect = new RectF();
    private final RectF dRect = new RectF();""",
        "touch D-pad rectangles")
    src = once(src,
        "    private final Paint text = new Paint(Paint.ANTI_ALIAS_FLAG);",
        "    private final Paint text = new Paint(Paint.ANTI_ALIAS_FLAG);\n"
        "    private final Paint active = new Paint(Paint.ANTI_ALIAS_FLAG);",
        "pressed button paint")
    src = once(src,
        "        fill.setColor(0x55303030);",
        "        fill.setColor(0x55303030);\n"
        "        active.setColor(0xBB23A3C8);",
        "highlight pressed WASD")
    src = once(src,
        "        text.setTextSize(Math.max(dp(12), h * 0.032f));",
        """        float pad = moveRadius * 0.31f;
        setCircle(wRect, moveCx, moveCy - moveRadius * 0.64f, pad);
        setCircle(sRect, moveCx, moveCy + moveRadius * 0.64f, pad);
        setCircle(aRect, moveCx - moveRadius * 0.64f, moveCy, pad);
        setCircle(dRect, moveCx + moveRadius * 0.64f, moveCy, pad);
        text.setTextSize(Math.max(dp(12), h * 0.032f));""",
        "true four-button geometry")
    src = once(src,
        """        drawLabel(canvas, "W", moveCx, moveCy - moveRadius * 0.55f);
        drawLabel(canvas, "S", moveCx, moveCy + moveRadius * 0.62f);
        drawLabel(canvas, "A", moveCx - moveRadius * 0.58f, moveCy + text.getTextSize() * 0.35f);
        drawLabel(canvas, "D", moveCx + moveRadius * 0.58f, moveCy + text.getTextSize() * 0.35f);""",
        """        drawDirection(canvas, wRect, "W", wDown);
        drawDirection(canvas, aRect, "A", aDown);
        drawDirection(canvas, sRect, "S", sDown);
        drawDirection(canvas, dRect, "D", dDown);""",
        "render actual interactive WASD")
    src = once(src,
        "    private void drawLabel(Canvas canvas, String label, float x, float y) {",
        """    private void drawDirection(Canvas canvas, RectF r, String label, boolean pressed) {
        canvas.drawOval(r, pressed ? active : fill);
        canvas.drawOval(r, stroke);
        float labelY = r.centerY() - (text.ascent() + text.descent()) * 0.5f;
        canvas.drawText(label, r.centerX(), labelY, text);
    }

    private void drawLabel(Canvas canvas, String label, float x, float y) {""",
        "direction feedback drawing")
    src = once(src,
        """                        SDLActivity.onNativeMouse(
                                0, MotionEvent.ACTION_MOVE, dx, dy, true);""",
        """                        /* Feed the RTCW usercmd directly: mobile SDL
                         * mouseActive can suppress emulated mouse motion. */
                        DarkWolfActivity.nativeQueueLookDelta(dx, dy);""",
        "direct camera delta")
    return src

def selftest() -> None:
    demo = '    static native void nativeSetGameAction(int action, boolean down);'
    assert "nativeQueueLookDelta" in patch_activity(demo)
    src = ('usercmd_t CL_CreateCmd( void ) {\n'
           '\tCL_MouseMove( &cmd );')
    assert 'CL_AndroidApplyTouchInput(&cmd);' in patch_input(src)
    fake = ("static volatile unsigned int androidGameDesiredMask;\n"
            "    if (down)\n        __sync_fetch_and_or(&androidGameDesiredMask, bit);\n"
            "    else\n        __sync_fetch_and_and(&androidGameDesiredMask, ~bit);\n"
            "    __sync_lock_test_and_set(&androidGameDesiredMask, 0);\n}\n"
            '        case DW_ACT_FORWARD:  cmd = down ? "+forward\\\\n"  : "-forward\\\\n"; break;\n'
            '        case DW_ACT_BACK:     cmd = down ? "+back\\\\n"     : "-back\\\\n"; break;\n'
            '        case DW_ACT_LEFT:     cmd = down ? "+moveleft\\\\n" : "-moveleft\\\\n"; break;\n'
            '        case DW_ACT_RIGHT:    cmd = down ? "+moveright\\\\n": "-moveright\\\\n"; break;\n'
            "void CL_AndroidConsumeUiTap(void)")
    parsed = patch_native_ui(fake)
    assert "DARKWOLF_ANDROID_DIRECT_WASD_V01" in parsed
    assert "androidMoveTapMask" in parsed
    assert "nativeQueueLookDelta" in parsed
    assert "CL_AndroidApplyTouchInput(usercmd_t *cmd)" in parsed
    assert "Cbuf_ExecuteText(EXEC_APPEND" not in parsed
    print("GRAPHICS_LAB_DIRECT_TOUCH_SELFTEST=PASS")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    elif len(sys.argv) == 3 and sys.argv[1] in ("--native", "--java"):
        root = Path(sys.argv[2])
        if sys.argv[1] == "--native":
            ui = root/"SP/code/client/cl_ui.c"
            client_input = root/"SP/code/client/cl_input.c"
            native = patch_native_ui(ui.read_text())
            cli = patch_input(client_input.read_text())
            ui.write_text(native)
            client_input.write_text(cli)
            print("GRAPHICS_LAB_DIRECT_WASD_NATIVE=PASS")
        else:
            activity = root/"app/src/main/java/org/darkwolf/rend2/DarkWolfActivity.java"
            touch = root/"app/src/main/java/org/darkwolf/rend2/DarkWolfTouchOverlay.java"
            act = patch_activity(activity.read_text())
            overlay = patch_overlay(touch.read_text())
            activity.write_text(act)
            touch.write_text(overlay)
            print("GRAPHICS_LAB_WASD_DPAD_AND_LOOK=PASS")
    else:
        raise SystemExit("usage: patch_touch_input.py --selftest | --native <source> | --java <gradle>")
