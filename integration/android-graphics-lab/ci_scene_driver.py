#!/usr/bin/env python3
"""Run an evidence-based Android game-scene gate. No blind taps or guessed orientation."""
from __future__ import annotations
import re
import subprocess
import sys
import time
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image, ImageDraw

PKG = "org.darkwolf.rend2"
BTN = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
FATAL = ("FATAL EXCEPTION", "Fatal signal", "GLSL compile error", "GLSL link error",
         "UnsatisfiedLinkError", "JNI DETECTED ERROR IN APPLICATION")
MARKER = "GRAPHICS_LAB_CI_GAMEVIEW=PASS"
# Logcat contains unrelated Android services. Restrict critical checks to game PID.
GAME_THREADTIME = re.compile(r"^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+\s+(\d+)\s+\d+\s+[A-Z]\s+")

def extract_game_log(raw: str, pid: int) -> str:
    lines = [line for line in raw.splitlines()
             if (match := GAME_THREADTIME.match(line)) and int(match.group(1)) == pid]
    return "\n".join(lines) + ("\n" if lines else "")

def current_game_pid() -> int:
    values = adb("shell", "pidof", PKG, timeout=12, check=False).decode("utf-8", "replace").split()
    if len(values) != 1 or not values[0].isdigit():
        raise RuntimeError("Game process missing or ambiguous: %r" % values)
    return int(values[0])

def run(args, *, timeout=25, check=True):
    r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError("command failed rc=%d args=%r stderr=%s" %
                           (r.returncode, args, r.stderr.decode("utf-8", "replace")[-1500:]))
    return r.stdout

def adb(*args, timeout=25, check=True):
    return run(("adb",) + tuple(args), timeout=timeout, check=check)

def logcat(out):
    data = adb("logcat", "-d", "-v", "threadtime", timeout=35)
    (out / "logcat.txt").write_bytes(data)
    pid = current_game_pid()
    filtered = extract_game_log(data.decode("utf-8", "replace"), pid)
    (out / "game-logcat.txt").write_text(filtered, encoding="utf-8")
    return filtered

def snapshot(out, name):
    dst = out / name
    dst.write_bytes(adb("exec-out", "screencap", "-p", timeout=25))
    with Image.open(dst) as im:
        im.verify()
    with Image.open(dst) as im:
        w,h=im.size
    if not (w >= 300 and h >= 180):
        raise RuntimeError("screen too small: %dx%d" % (w,h))
    return dst, (w,h)

def parse_immersive(xml):
    """Return the center of Android's actual button bounds, never wm size."""
    root=ET.fromstring(xml)
    nodes=list(root.iter("node"))
    title=any("Viewing full screen" in n.get("text","") or
              "immersive_cling" in n.get("resource-id","") for n in nodes)
    if not title:
        return None
    buttons=[n for n in nodes if n.get("resource-id","")=="android:id/ok"
             or n.get("text","").strip()=="Got it"]
    if not buttons:
        raise RuntimeError("Android immersive dialog present, but its button is missing")
    m=BTN.fullmatch(buttons[-1].get("bounds",""))
    if not m:
        raise RuntimeError("Android immersive dialog button has unknown bounds")
    x0,y0,x1,y1=map(int,m.groups())
    if x1<=x0 or y1<=y0:
        raise RuntimeError("Android immersive dialog button has zero size")
    return ((x0+x1)//2,(y0+y1)//2)

def xml_dump(out, index):
    dst=out / ("android-ui-%02d.xml" % index)
    result=adb("shell","uiautomator","dump","/sdcard/graphics-lab-ui.xml",
               timeout=25,check=False)
    if b"dumped" not in result.lower():
        # Some system images do not echo the status. Check the resulting XML instead.
        pass
    xml=adb("exec-out","cat","/sdcard/graphics-lab-ui.xml",timeout=15,check=False)
    dst.write_bytes(xml)
    if b"<hierarchy" not in xml:
        raise RuntimeError("UI hierarchy not available: %s" % (result[-250:],))
    text=xml.decode("utf-8","replace")
    return text

def clear_android_immersive(out):
    # The setting prevents the first-run dialog on most AOSP images.
    adb("shell","settings","put","secure","immersive_mode_confirmations",
        "confirmed",timeout=15,check=False)
    for idx in range(1,5):
        text=xml_dump(out,idx)
        point=parse_immersive(text)
        if point is None:
            print("ANDROID_IMMERSIVE_DIALOG=ABSENT",flush=True)
            return
        print("ANDROID_IMMERSIVE_BUTTON=%d,%d" % point,flush=True)
        adb("shell","input","tap",str(point[0]),str(point[1]),timeout=15)
        time.sleep(2.0)
    text=xml_dump(out,5)
    if parse_immersive(text) is not None:
        raise RuntimeError("Android immersive dialog remains after XML-guided dismissal")

def wait_gameview(out, seconds=180):
    start=time.monotonic()
    while time.monotonic()-start < seconds:
        log=logcat(out)
        if any(z in log for z in FATAL):
            raise RuntimeError("fatal exception or shader failure in game logcat")
        if MARKER in log:
            if "DARKWOLF_ANDROID_MAP_AUTOSTART=PASS" not in log:
                raise RuntimeError("active game view without stock map-autostart event")
            print("GAMEVIEW_NATIVE_MARKER=PASS",flush=True)
            print("MAP_AUTOSTART_WITHOUT_ENTER=PASS",flush=True)
            return
        # No Android key events or game taps: startup must be completely automatic.
        time.sleep(2)
    # Keep visual evidence even when the native active-scene marker is absent.
    try:
        snapshot(out, "gameview-timeout.png")
        xml_dump(out, 90)
    except Exception as exc:
        print("GAMEVIEW_TIMEOUT_DIAGNOSTICS_FAILED=%s" % exc, flush=True)
    raise RuntimeError("gameview marker absent: active 3D state unverified")

def verify_frame(path):
    # run() intentionally returns stdout bytes for adb helpers; a frame probe
    # also needs its exit status. Use CompletedProcess directly here.
    r = subprocess.run(
        (sys.executable, "integration/android-graphics-lab/verify_rend2_frame.py", str(path)),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25, check=False)
    detail = r.stdout.decode("utf-8", "replace").strip()
    if r.returncode and not detail:
        detail = r.stderr.decode("utf-8", "replace").strip()[-1000:]
    return r.returncode == 0, detail

def visual_motion(before, after):
    """Compare center of view, excluding touch controls, buttons and HUD edges."""
    with Image.open(before).convert("RGB") as a, Image.open(after).convert("RGB") as b:
        if a.size != b.size:
            return False, "different_viewport_sizes"
        w, h = a.size
        changed = total = energy = 0
        ap = a.load()
        bp = b.load()
        for y in range(int(h * .20), int(h * .76), 3):
            for x in range(int(w * .22), int(w * .78), 3):
                delta = max(abs(ap[x,y][i] - bp[x,y][i]) for i in range(3))
                changed += delta >= 20
                energy += delta
                total += 1
        ratio = changed / max(1,total)
        mean = energy / max(1,total)
        return ratio >= .08 and mean >= 6.0, ("changed=%.3f mean_delta=%.2f" %
                                             (ratio,mean))

def camera_test_swipe(size):
    w,h=size
    # Existing DarkWolfTouchOverlay uses right-center swipes for LOOK.
    # Avoid buttons at x=.75-.94 and the upper-right Graphics Lab button.
    adb("shell","input","swipe",
        str(int(w * .61)), str(int(h * .40)),
        str(int(w * .51)), str(int(h * .55)),
        "420", timeout=20)

def main(out):
    out.mkdir(parents=True,exist_ok=True)
    (out/"STATUS.txt").write_text("VISUAL_GATE=NOT_RUN\n")
    if not adb("shell","pidof",PKG,check=False).strip():
        raise RuntimeError("game process not alive before visual gate")
    clear_android_immersive(out)
    wait_gameview(out)
    lines=[]
    for i in range(1,7):
        ui=xml_dump(out,10+i)
        point=parse_immersive(ui)
        if point is not None:
            raise RuntimeError("system immersive dialog reappeared at frame %d" % i)
        frame,(w,h)=snapshot(out,"retail-frame-%d.png"%i)
        passed,details=verify_frame(frame)
        lines.append(details)
        print("SCENE_CAPTURE=%d size=%dx%d %s"%(i,w,h,details),flush=True)
        (out/"frame-audit.txt").write_text("\n".join(lines)+"\n")
        if passed:
            # Preserve the game screenshot BEFORE any gesture; this alone
            # proves map auto-entry without manual input.
            (out/"retail-frame.png").write_bytes(frame.read_bytes())
            camera_test_swipe((w,h))
            time.sleep(3)
            changed_frame, _ = snapshot(out,"camera-motion-%d.png"%i)
            after_ok, after_detail = verify_frame(changed_frame)
            motion_ok, motion_detail = visual_motion(frame, changed_frame)
            print("SCENE_MOTION=%d %s after=%s"%(i,motion_detail,after_detail),flush=True)
            camera_pass=bool(after_ok and motion_ok)
            if not camera_pass:
                lines.append("CAMERA_MOTION=NOT_CONFIRMED "+motion_detail+" "+after_detail)
                (out/"frame-audit.txt").write_text("\n".join(lines)+"\n")
            log=logcat(out)
            if MARKER not in log:
                raise RuntimeError("gameview marker disappeared before accepted frame")
            if not adb("shell","pidof",PKG,check=False).strip():
                raise RuntimeError("game process exited after screenshot")
            (out/"STATUS.txt").write_text("RETAIL_RUNTIME=PASS_PLAYERSTART\n"
                     "GAMEVIEW_NATIVE_MARKER=PASS\n"
                     "ANDROID_OVERLAY=ABSENT\n"
                     "GPU_RENDERED_FRAME=VISUAL_SMOKE_PASS\n"
                     "IME_AND_FULLSCREEN_OVERLAY=REJECTED\n"
                     "MAP_AUTOSTART_WITHOUT_ENTER=PASS\n"
                     "CAMERA_MOTION=%s\n" % ("VERIFIED" if camera_pass else "NOT_CONFIRMED"))
            print("GRAPHICS_LAB_RETAIL_RUNTIME=PASS_MAP_AUTOSTART",flush=True)
            print("GRAPHICS_LAB_CAMERA_MOTION=%s" % ("PASS" if camera_pass else "NOT_CONFIRMED"),flush=True)
            return
        time.sleep(2)
    raise RuntimeError("visual gate: all six captures failed image quality")

def selftest():
    fixture=("<hierarchy><node text='Viewing full screen' bounds='[0,0][640,320]'>"
             "<node text='Got it' resource-id='android:id/ok' "
             "bounds='[475,166][546,214]'/></node></hierarchy>")
    assert parse_immersive(fixture)==(510,190)
    assert parse_immersive("<hierarchy><node text='RTCW' /></hierarchy>") is None
    # A Google/Widevine dlopen warning cannot fail the game process.
    foreign = "10-21 20:02:50.127   432   432 W WVCdm: dlopen failed: liboemcrypto.so"
    game = "10-21 20:03:35.760  2879  2947 I DarkWolfEngine: loaded 282 GLSL shaders"
    assert extract_game_log(foreign + "\n" + game, 2879).strip() == game
    assert not any(err in extract_game_log(foreign, 2879) for err in FATAL)
    own_error = "10-21 20:03:50.127  2879  2947 E DarkWolfEngine: GLSL compile error"
    assert "GLSL compile error" in extract_game_log(own_error, 2879)
    assert extract_game_log(game, 9999) == ""
    # Explicitly reject foreign PID errors and preserve all game PID lines.
    second = "10-21 20:03:50.128  2879  2948 W DarkWolfEngine: CVar registered"
    another = "10-21 20:03:50.129  3288  3290 E App: FATAL EXCEPTION"
    sample = "\n".join((foreign, game, second, another))
    assert extract_game_log(sample, 2879).splitlines() == [game, second]
    assert "FATAL EXCEPTION" not in extract_game_log(sample, 2879)
    assert extract_game_log(sample, 3288).splitlines() == [another]
    assert GAME_THREADTIME.match(game).group(1) == "2879"
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as d:
        bad=Path(d)/"blank.png"
        Image.new("RGB",(640,320),(0,0,0)).save(bad)
        good=Path(d)/"gradient.png"
        pic=Image.new("RGB",(640,320))
        dr=ImageDraw.Draw(pic)
        for y in range(320):
            for x in range(640):
                pic.putpixel((x,y),(x%256,y%256,(x*y//29)%256))
        pic.save(good)
        assert not verify_frame(bad)[0], "black frame accepted"
        assert verify_frame(good)[0], "multicolor image rejected"
        # Regression fixture for the successful-but-false Run 39709755979:
        # sepia/photo top, pale Android keyboard covering bottom 65%.
        keyboard=Path(d)/"keyboard.png"
        fake=Image.new("RGB",(640,320),(36,34,31))
        fake.paste(pic.crop((0,0,640,110)),(0,0))
        ImageDraw.Draw(fake).rectangle((0,110,639,319),fill=(239,241,248))
        fake.save(keyboard)
        assert not verify_frame(keyboard)[0], "Android IME false-positive accepted"
        assert not visual_motion(good,good)[0], "static menu accepted as camera motion"
        moved=Path(d)/"moved.png"
        Image.new("RGB",(640,320),(0,0,0)).save(moved)
        assert visual_motion(good,moved)[0], "large image difference not detected"
    print("GRAPHICS_LAB_SCENE_DRIVER_SELFTEST=PASS",flush=True)

if __name__=="__main__":
    if len(sys.argv)==2 and sys.argv[1]=="--selftest":
        selftest()
    elif len(sys.argv)==2:
        out=Path(sys.argv[1])
        try:
            main(out)
        except Exception as exc:
            out.mkdir(parents=True,exist_ok=True)
            (out/"STATUS.txt").write_text("VISUAL_GATE=FAIL\nREASON=%s\n"%exc)
            print("GRAPHICS_LAB_SCENE_DRIVER_FAILED: %s"%exc,file=sys.stderr,flush=True)
            raise SystemExit(1)
    else:
        raise SystemExit("usage: ci_scene_driver.py --selftest | <out-directory>")
