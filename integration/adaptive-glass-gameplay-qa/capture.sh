#!/usr/bin/env bash
# Real gameplay screenshot experiment. The legal demo data are discarded, not uploaded.
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
mkdir -p evidence dist qa-unpack qa-installed
sudo apt-get install -y --no-install-recommends curl p7zip-full x11-apps xvfb imagemagick wine wine64 python3-pil mesa-utils libgl1-mesa-dri x11-utils xdotool xclip unzip >/tmp/qa-apt.log 2>&1 || { tail -60 /tmp/qa-apt.log; exit 1; }
# Pin candidate to source commit 7cae5e67; never substitute unrelated builds.
# Exact source revision with safe basename-based material classifier.
# Do not consume previous #41332242795 binary: that version misclassifies shutters.
source_sha=cee0c6ba893d0cfc98916ec31312a780a6d015f7
run_id=41333112870
artifact_id=""
for attempt in $(seq 1 20); do
  conclusion="$(gh api "repos/$GITHUB_REPOSITORY/actions/runs/$run_id" --jq .conclusion 2>/dev/null || true)"
  if [[ "$conclusion" == "failure" ]]; then echo TARGET_BUILD_FAILED; exit 1; fi
  artifact_id="$(gh api "repos/$GITHUB_REPOSITORY/actions/runs/$run_id/artifacts" --jq '.artifacts[] | select(.name=="DarkWolf-AdaptiveGlass-Cubemap-Fresnel-V1-from-41297344177") | .id' 2>/dev/null | head -1 || true)"
  if [[ -n "$artifact_id" && "$conclusion" == "success" ]]; then break; fi
  sleep 25
done
test -n "$artifact_id" || { echo NO_SUCCESSFUL_PINNED_CANDIDATE; exit 1; }
test "$(gh api "repos/$GITHUB_REPOSITORY/actions/runs/$run_id" --jq .head_sha)" = "$source_sha" || { echo WRONG_SOURCE_SHA; exit 1; }
gh api "repos/$GITHUB_REPOSITORY/actions/artifacts/$artifact_id/zip" > evidence/glass-ci-outer.zip
release_name=DarkWolf_Adaptive_Glass_Reflections_V1_Clean_Candidate_Win64
unzip -p evidence/glass-ci-outer.zip "dist/$release_name.zip" > evidence/glass-release.zip
unzip -p evidence/glass-ci-outer.zip "dist/$release_name.zip.sha256" > evidence/parent-release.sha256
test "$(sha256sum evidence/glass-release.zip | cut -c1-64)" = "$(cut -d' ' -f1 evidence/parent-release.sha256)"
unzip -q evidence/glass-release.zip -d qa-installed
game="qa-installed/$release_name"
test -s "$game/ioWolfSP.x64.exe"
test -s "$game/renderer_sp_rend2_x64.dll"
# Official idgames RTCW SP demo; no proprietary full-game assets uploaded.
curl -fLsS --retry 2 --connect-timeout 20 --max-time 300 \
  https://www.gamers.org/pub/idgames/idstuff/wolf/linux/wolfspdemo-linux-1.1b.x86.run \
  -o evidence/rtcw-demo-installer.run
echo "dbff5ea928802b1bddfd4c171bf08ed4294b2da0273e1cf0802fdcedc40c23c3  evidence/rtcw-demo-installer.run" | sha256sum -c -
7z x -y -oqa-unpack evidence/rtcw-demo-installer.run > evidence/demo_extract_7z.txt 2>&1 || true
pakfile="$(find qa-unpack -type f -path '*/demomain/pak0.pk3' -print -quit)"
if [[ -z "$pakfile" ]]; then
  # 7z extracts the .run's GZIP into a TAR named after the local installer,
  # not after the original upstream filename. Recursively unpack large TAR.
  while IFS= read -r -d '' f; do
    7z x -y -oqa-unpack "$f" >> evidence/demo_extract_7z.txt 2>&1 || true
  done < <(find qa-unpack -maxdepth 3 -type f -size +100M -print0)
  pakfile="$(find qa-unpack -type f -path '*/demomain/pak0.pk3' -print -quit)"
fi
test -n "$pakfile" || { echo UNABLE_TO_EXTRACT_DEMO_PK3; tail -50 evidence/demo_extract_7z.txt; exit 1; }
python3 integration/adaptive-glass-gameplay-qa/bsp_glass_audit.py "$pakfile" \
  --out evidence/REAL_RTCW_DEMO_BSP_MATERIAL_AUDIT.json
cp "$pakfile" "$game/Main/pak0.pk3"
winebinary="$(command -v wine || command -v wine64 || true)"
if [[ -z "$winebinary" && -x /usr/lib/wine/wine64 ]]; then winebinary=/usr/lib/wine/wine64; fi
test -n "$winebinary"
command -v wineboot || { echo WINE_BOOT_WRAPPER_MISSING; exit 1; }
command -v wineserver || { echo WINE_SERVER_WRAPPER_MISSING; exit 1; }
export DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1 MESA_GL_VERSION_OVERRIDE=3.3COMPAT
export WINEDEBUG=-all WINEPREFIX="$PWD/.wine-glass-qa" SDL_AUDIODRIVER=dummy
export WINEARCH=win64 WINEDLLOVERRIDES="mscoree,mshtml="
Xvfb :99 -screen 0 1280x720x24 -nolisten tcp > evidence/xvfb.log 2>&1 &
xvfbpid=$!
trap 'kill "$xvfbpid" 2>/dev/null || true' EXIT
sleep 4
# Initialize Wine's prefix and all Microsoft Windows system files BEFORE timed A/B.
# Initial startup can take >32 seconds and otherwise yields misleading empty screens.
timeout 120 wineboot -u > evidence/wineboot.log 2>&1 || { tail -50 evidence/wineboot.log; echo WINE_BOOT_FAILURE; exit 1; }
timeout 30 wineserver -w >> evidence/wineboot.log 2>&1 || true
echo "WINE_PREFIX_INITIALIZED" >> evidence/wineboot.log
set +e
for mode in off on; do
  if [[ "$mode" == off ]]; then flag=0; else flag=1; fi
  (cd "$game" && timeout 75 "$winebinary" ioWolfSP.x64.exe \
    +set cl_renderer rend2 +set r_fullscreen 0 +set r_mode -1 \
    +set r_customwidth 1280 +set r_customheight 720 \
    +set r_cubeMapping 0 +set r_dwGlassReflect "$flag" \
    +set r_externalGLSL 0 +set r_hdr 1 +set developer 1 \
    +set logfile 2 +devmap escape1 ) > "evidence/real-game-$mode.log" 2>&1 &
  gamepid=$!
  sleep 46
  xwininfo -root -tree -display "$DISPLAY" > "evidence/x11-windows-$mode.txt" 2>&1 || true
  xwd -root -silent -display "$DISPLAY" -out "evidence/real-$mode.xwd"
  convert "evidence/real-$mode.xwd" "dist/REAL_RTCW_ESCAPE1_Glass_$mode.png"
  # On a REAL engine fatal dialog, retrieve actual console data rather than
  # pretending the popup is a gameplay screenshot.
  errwin="$(xdotool search --name '^Error$' 2>/dev/null | head -1 || true)"
  if [[ -n "$errwin" ]]; then
    echo "WINE_GAME_ENGINE_ERROR_WINDOW: $errwin" >> "evidence/gui-error-$mode.log"
    xdotool windowactivate --sync "$errwin" >/dev/null 2>&1 || true
    xdotool key --window "$errwin" Return >/dev/null 2>&1 || true
    sleep 2
    timeout 6 xclip -selection clipboard -o > "evidence/gui-error-console-$mode.log" 2>&1 || true
    qconsole="$(find "$game" -type f -iname qconsole.log -print -quit)"
    if [[ -n "$qconsole" ]]; then cp "$qconsole" "evidence/engine-qconsole-$mode.log"; fi
  fi
  kill "$gamepid" 2>/dev/null || true
  wait "$gamepid" 2>/dev/null || true
done
set -e
python3 - <<'PY'
from PIL import Image,ImageStat,ImageChops
from pathlib import Path
import json,hashlib
imgs=[]
proof={"origin":"ORIGINAL_RTCW_SP_DEMO_RUNTIME","engine":"DarkWolf Windows renderer via Wine Xvfb Mesa llvmpipe",
       "full_game_maps_tested":False,"gameplay_confirmed":False,"screenshots":[]}
for mode in ("off","on"):
 p=Path(f"dist/REAL_RTCW_ESCAPE1_Glass_{mode}.png")
 assert p.exists(),p
 a=Image.open(p).convert("RGB")
 st=ImageStat.Stat(a)
 std=sum(st.stddev)/3
 avg=sum(st.mean)/3
 assert a.width>=640 and a.height>=480 and std>8 and avg>6,(mode,"empty frame")
 log=Path(f"evidence/real-game-{mode}.log").read_text(errors="replace")
 assert ("rend2" in log.lower() or "renderer_sp_rend2" in log.lower()),(mode,"Rend2 renderer not proven")
 assert "escape1" in log.lower() and (
    "loadworldmap" in log.lower() or "world map" in log.lower()
    or "maps/escape1.bsp" in log.lower()
 ),(mode,"BSP world loading not proven")
 imgs.append(a)
 proof["screenshots"].append({"mode":mode,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                             "size":[a.width,a.height],"stddev":std,"mean":avg})
dif=ImageChops.difference(imgs[0],imgs[1])
proof["ab_mean_absolute_difference"]=sum(ImageStat.Stat(dif).mean)/3
proof["gameplay_confirmed"]=True
Path("evidence/REAL_GAMEPLAY_CAPTURE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n")
print("REAL_RTCW_DEMO_ENGINE_SCREENSHOTS_VERIFIED",proof["ab_mean_absolute_difference"])
PY
# Never upload the installer, extracted game data or copyrighted PK3.
rm -f "$game/Main/pak0.pk3" evidence/rtcw-demo-installer.run evidence/real-*.xwd
 2>/dev/null | head -1 || true)"
  if [[ -n "$errwin" ]]; then
    echo "WINE_GAME_ENGINE_ERROR_WINDOW: $errwin" >> "evidence/gui-error-$mode.log"
    xdotool windowactivate --sync "$errwin" >/dev/null 2>&1 || true
    xdotool key --window "$errwin" Return >/dev/null 2>&1 || true
    sleep 2
    timeout 6 xclip -selection clipboard -o > "evidence/gui-error-console-$mode.log" 2>&1 || true
    find "$game" -iname qconsole.log -type f -exec sh -c 'cp "$1" "$2"' sh '{}' "evidence/engine-qconsole-$mode.log" \; 2>/dev/null || true
  fi
  kill "$gamepid" 2>/dev/null || true
  wait "$gamepid" 2>/dev/null || true
done
set -e
python3 - <<'PY'
from PIL import Image,ImageStat,ImageChops
from pathlib import Path
import json,hashlib
imgs=[]
proof={"origin":"ORIGINAL_RTCW_SP_DEMO_RUNTIME","engine":"DarkWolf Windows renderer via Wine Xvfb Mesa llvmpipe",
       "full_game_maps_tested":False,"gameplay_confirmed":False,"screenshots":[]}
for mode in ("off","on"):
 p=Path(f"dist/REAL_RTCW_ESCAPE1_Glass_{mode}.png")
 assert p.exists(),p
 a=Image.open(p).convert("RGB")
 st=ImageStat.Stat(a)
 std=sum(st.stddev)/3
 avg=sum(st.mean)/3
 assert a.width>=640 and a.height>=480 and std>8 and avg>6,(mode,"empty frame")
 log=Path(f"evidence/real-game-{mode}.log").read_text(errors="replace")
 assert ("rend2" in log.lower() or "renderer_sp_rend2" in log.lower()),(mode,"Rend2 renderer not proven")
 assert "escape1" in log.lower() and (
    "loadworldmap" in log.lower() or "world map" in log.lower()
    or "maps/escape1.bsp" in log.lower()
 ),(mode,"BSP world loading not proven")
 imgs.append(a)
 proof["screenshots"].append({"mode":mode,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                             "size":[a.width,a.height],"stddev":std,"mean":avg})
dif=ImageChops.difference(imgs[0],imgs[1])
proof["ab_mean_absolute_difference"]=sum(ImageStat.Stat(dif).mean)/3
proof["gameplay_confirmed"]=True
Path("evidence/REAL_GAMEPLAY_CAPTURE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n")
print("REAL_RTCW_DEMO_ENGINE_SCREENSHOTS_VERIFIED",proof["ab_mean_absolute_difference"])
PY
# Never upload the installer, extracted game data or copyrighted PK3.
rm -f "$game/Main/pak0.pk3" evidence/rtcw-demo-installer.run evidence/real-*.xwd
