#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UPSTREAM_SHA=438e7d413b5f7277187c35b032eb0ef9093ae778
BASE_PATCH="$ROOT/integration/base/darkwolf-rend2-cumulative-escape1-table-shadow-rc-v0-2-persistent-physical-set-residency-sp.patch"
BASE_PATCH_SHA=1b766221df31b483877cee2378e3696c7a992abc9cd61628e945b16c145bebe2
DELTA="$ROOT/integration/release/darkwolf-unified-production-v1-integration-delta.patch"
CUMULATIVE="$ROOT/integration/release/darkwolf-rend2-unified-production-v1-cumulative.patch"
NAME=DarkWolf-ioRTCW-Rend2-Unified-Production-V1-Win64
WORK="${RUNNER_TEMP:-/tmp}/darkwolf-unified-production"
SRC="$WORK/source"
REPLAY="$WORK/replay"
STAGE="$ROOT/dist/$NAME"

rm -rf "$WORK" "$ROOT/dist"
mkdir -p "$WORK" "$ROOT/dist/upload" "$ROOT/integration/release"

actual_base_sha="$(sha256sum "$BASE_PATCH" | awk '{print $1}')"
[[ "$actual_base_sha" == "$BASE_PATCH_SHA" ]]

git clone -q https://github.com/iortcw/iortcw.git "$SRC"
git -C "$SRC" checkout -q --detach "$UPSTREAM_SHA"
git -C "$SRC" apply --check --binary --whitespace=nowarn "$BASE_PATCH"
git -C "$SRC" apply --binary --whitespace=nowarn "$BASE_PATCH"
git -C "$SRC" apply --check --binary --whitespace=nowarn "$DELTA"
git -C "$SRC" apply --binary --whitespace=nowarn "$DELTA"

git -C "$SRC" diff --binary HEAD -- . > "$CUMULATIVE"
test -s "$CUMULATIVE"

git -C "$SRC" diff --name-only HEAD -- | sort > "$ROOT/integration/release/CHANGED_FILES.txt"
grep '^@@' "$DELTA" | sed -E 's/^@@[^@]*@@ ?//' | sed '/^$/d' > "$ROOT/integration/release/CHANGED_FUNCTIONS.txt" || true
: > "$ROOT/integration/release/FINAL_SOURCE_SHA256.txt"
while IFS= read -r rel; do
  [[ -f "$SRC/$rel" ]] || continue
  sha256sum "$SRC/$rel" | sed "s#  $SRC/#  #" >> "$ROOT/integration/release/FINAL_SOURCE_SHA256.txt"
done < "$ROOT/integration/release/CHANGED_FILES.txt"

git -C "$SRC" worktree add -q --detach "$REPLAY" "$UPSTREAM_SHA"
{
  echo "git apply --check --binary --whitespace=nowarn $CUMULATIVE"
  git -C "$REPLAY" apply --check --binary --whitespace=nowarn "$CUMULATIVE"
  echo "git apply --binary --whitespace=nowarn $CUMULATIVE"
  git -C "$REPLAY" apply --binary --whitespace=nowarn "$CUMULATIVE"
  echo "REPLAY_APPLY=PASS"
} > "$ROOT/integration/release/REPLAY_APPLY_LOG.txt" 2>&1
: > "$ROOT/integration/release/REPLAY_SOURCE_SHA256.txt"
while IFS= read -r rel; do
  [[ -f "$REPLAY/$rel" ]] || continue
  sha256sum "$REPLAY/$rel" | sed "s#  $REPLAY/#  #" >> "$ROOT/integration/release/REPLAY_SOURCE_SHA256.txt"
done < "$ROOT/integration/release/CHANGED_FILES.txt"
cmp "$ROOT/integration/release/FINAL_SOURCE_SHA256.txt" "$ROOT/integration/release/REPLAY_SOURCE_SHA256.txt"

(
  cd "$SRC/SP"
  ./cross-make-mingw64.sh -j1 \
    BUILD_CLIENT=1 BUILD_SERVER=0 BUILD_GAME_SO=1 BUILD_GAME_QVM=0 \
    BUILD_BASEGAME=1 BUILD_RENDERER_REND2=1 USE_RENDERER_DLOPEN=1
)

BUILD="$SRC/SP/build/release-mingw32-x86_64"
mkdir -p "$STAGE/Main" "$STAGE/docs"
cp "$BUILD/ioWolfSP.x64.exe" "$BUILD/renderer_sp_rend2_x64.dll" \
   "$BUILD/renderer_sp_opengl1_x64.dll" "$BUILD/SDL264.dll" "$BUILD/OpenAL64.dll" "$STAGE/"
cp "$BUILD/main/cgame_sp_x64.dll" "$BUILD/main/qagame_sp_x64.dll" "$BUILD/main/ui_sp_x64.dll" "$STAGE/Main/"
cp "$ROOT/integration/release/UNIFIED_PRODUCTION.cfg" "$STAGE/Main/"
cp "$ROOT/integration/release/README_UNIFIED_PRODUCTION.md" "$STAGE/README.md"
cp "$DELTA" "$CUMULATIVE" \
   "$ROOT/integration/release/FINAL_SOURCE_SHA256.txt" \
   "$ROOT/integration/release/REPLAY_SOURCE_SHA256.txt" \
   "$ROOT/integration/release/CHANGED_FILES.txt" \
   "$ROOT/integration/release/CHANGED_FUNCTIONS.txt" \
   "$ROOT/integration/release/REPLAY_APPLY_LOG.txt" "$STAGE/docs/"

renderer_sha="$(sha256sum "$STAGE/renderer_sp_rend2_x64.dll" | awk '{print $1}')"
cgame_sha="$(sha256sum "$STAGE/Main/cgame_sp_x64.dll" | awk '{print $1}')"
delta_sha="$(sha256sum "$DELTA" | awk '{print $1}')"
cumulative_sha="$(sha256sum "$CUMULATIVE" | awk '{print $1}')"

cat > "$STAGE/docs/PROVENANCE.txt" <<PROV
DARKWOLF IORTCW REND2 UNIFIED PRODUCTION V1
pinned_upstream_sha=$UPSTREAM_SHA
base_run_id=35503262322
base_artifact_id=10603017159
base_cumulative_patch_sha256=$BASE_PATCH_SHA
integration_commit_sha=${GITHUB_SHA:-LOCAL}
integration_delta_sha256=$delta_sha
final_cumulative_patch_sha256=$cumulative_sha
renderer_sp_rend2_x64_sha256=$renderer_sha
cgame_sp_x64_sha256=$cgame_sha
workflow_run_id=${GITHUB_RUN_ID:-LOCAL}
actions_artifact_id=assigned_after_upload
PROV

(cd "$STAGE" && find . -type f ! -path './docs/SHA256SUMS.txt' -print0 | sort -z | xargs -0 sha256sum > docs/SHA256SUMS.txt)
(cd "$ROOT/dist" && zip -q -r -9 "upload/$NAME.zip" "$NAME")
sha256sum "$ROOT/dist/upload/$NAME.zip" > "$ROOT/dist/upload/$NAME.zip.sha256"
printf '%s\n' "$renderer_sha" > "$ROOT/dist/renderer.sha256"
printf '%s\n' "$cgame_sha" > "$ROOT/dist/cgame.sha256"
printf '%s\n' "$delta_sha" > "$ROOT/dist/delta.sha256"
printf '%s\n' "$cumulative_sha" > "$ROOT/dist/cumulative.sha256"
