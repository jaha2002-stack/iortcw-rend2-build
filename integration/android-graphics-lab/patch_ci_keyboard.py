#!/usr/bin/env python3
"""CI-only SDL2 keyboard suppression. Production ARM64 APK is not modified."""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    raise SystemExit("usage: patch_ci_keyboard.py <gradle-project>")
src = Path(sys.argv[1]) / "app/src/main/java/org/libsdl/app/SDLActivity.java"
s = src.read_text()
needle = "return mSingleton.commandHandler.post(new ShowTextInputTask(x, y, w, h));"
assert s.count(needle) == 1, "pinned SDL2 JNI input anchor drifted"
s = s.replace(needle, """// CI x86 emulator: suppress SDL auto-text-input during RTCW intro.
        // Graphics Lab Android EditText dialogs remain functional.
        return true;""", 1)
src.write_text(s)
print("GRAPHICS_LAB_CI_SDL_SOFT_KEYBOARD_SUPPRESSED=PASS")
