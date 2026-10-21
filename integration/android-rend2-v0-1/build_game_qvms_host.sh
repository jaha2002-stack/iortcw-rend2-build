#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${1:-$ROOT/.android-rend2-work}"
SRC="$WORKDIR/source"
OUT="$WORKDIR/game-qvms"
BUILD="$OUT/build"

test -f "$SRC/SP/Makefile"
command -v make >/dev/null
command -v gcc >/dev/null
command -v python3 >/dev/null

rm -rf "$OUT"
mkdir -p "$OUT"/{bin,log}

# Q3LCC is intentionally old/C89-like and rejects two semantically-valid
# constructs introduced by the DarkWolf v4.4.x gameplay patches. Apply a
# QVM-only source compatibility rewrite, then restore the exact reconstructed
# source on exit so native Android builds retain their provenance byte-for-byte.
GPROPS="$SRC/SP/code/game/g_props.c"
GPROPS_BACKUP="$OUT/g_props.c.exact-source"
cp "$GPROPS" "$GPROPS_BACKUP"

restore_exact_source() {
  cp "$GPROPS_BACKUP" "$GPROPS"
}
trap restore_exact_source EXIT
trap 'rc=$?; echo "GAME_QVM_BUILD_FAILED=$rc"; if [ -f "$OUT/log/build.log" ]; then grep -n -E "illegal use|undeclared identifier|type error|Error [0-9]|undefined reference|No rule to make target" "$OUT/log/build.log" | head -n 120 || true; tail -n 120 "$OUT/log/build.log"; fi; exit $rc' ERR

python3 - "$GPROPS" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()

start = text.find("void Props_Barrel_Die(")
if start < 0:
    raise SystemExit("QVM compatibility: Props_Barrel_Die anchor not found")
end = text.find("\n}\n", start)
if end < 0:
    raise SystemExit("QVM compatibility: Props_Barrel_Die end not found")
end += 3
block = text[start:end]

if block.count("gentity_t *smoker;") != 1:
    raise SystemExit("QVM compatibility: unexpected smoker declaration count")
if "\tvec3_t dir;\n" not in block:
    raise SystemExit("QVM compatibility: vec3_t dir anchor not found")

# Q3LCC rejects the declaration after the DarkWolf blast-event statement block.
block = block.replace("\tgentity_t *smoker;\n", "", 1)
block = block.replace("\tvec3_t dir;\n", "\tvec3_t dir;\n\tgentity_t *smoker;\n", 1)
text = text[:start] + block + text[end:]

# G_ModelIndex has the historic char * signature. Modern compilers accept the
# const source with a warning; Q3LCC treats it as a hard type error.
count = text.count("G_ModelIndex(dead)")
if count != 2:
    raise SystemExit(f"QVM compatibility: expected 2 G_ModelIndex(dead) sites, found {count}")
text = text.replace("G_ModelIndex(dead)", "G_ModelIndex((char *)dead)")

path.write_text(text)
print("DARKWOLF_QVM_Q3LCC_COMPAT=PASS")
PY

make -C "$SRC/SP" -j2 release \
  BUILD_DIR="$BUILD" \
  BUILD_CLIENT=0 \
  BUILD_SERVER=0 \
  BUILD_GAME_SO=0 \
  BUILD_GAME_QVM=1 \
  BUILD_BASEGAME=1 \
  USE_OPENAL=0 \
  USE_CURL=0 \
  USE_CODEC_VORBIS=0 \
  USE_CODEC_OPUS=0 \
  USE_MUMBLE=0 \
  USE_VOIP=0 \
  USE_FREETYPE=0 \
  >"$OUT/log/build.log" 2>&1

for module in ui cgame qagame; do
  src="$(find "$BUILD" -type f -path "*/main/vm/$module.sp.qvm" -print -quit)"
  test -n "$src"
  test -s "$src"
  cp "$src" "$OUT/bin/$module.sp.qvm"
done

sha256sum "$OUT/bin/"*.sp.qvm | tee "$OUT/SHA256SUMS.txt"
{
  echo "EXACT_SOURCE_SP_QVM_BUILD=PASS"
  echo "QVM_ARCH=architecture-independent"
  echo "QVM_UI_BYTES=$(stat -c %s "$OUT/bin/ui.sp.qvm")"
  echo "QVM_CGAME_BYTES=$(stat -c %s "$OUT/bin/cgame.sp.qvm")"
  echo "QVM_QAGAME_BYTES=$(stat -c %s "$OUT/bin/qagame.sp.qvm")"
} | tee "$OUT/A6_QVM_BUILD_AUDIT.txt"
