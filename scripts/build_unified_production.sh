#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UPSTREAM_SHA=438e7d413b5f7277187c35b032eb0ef9093ae778
CUMULATIVE="$ROOT/integration/release/darkwolf-rend2-unified-production-v1-cumulative.patch"
NAME=DarkWolf-ioRTCW-Rend2-Unified-Production-V1-Win64
WORK="${RUNNER_TEMP:-/tmp}/darkwolf-unified-production"
rm -rf "$WORK" "$ROOT/dist"
git clone -q https://github.com/iortcw/iortcw.git "$WORK/source"
git -C "$WORK/source" checkout -q --detach "$UPSTREAM_SHA"
git -C "$WORK/source" apply --check --binary --whitespace=nowarn "$CUMULATIVE"
git -C "$WORK/source" apply --binary --whitespace=nowarn "$CUMULATIVE"
(
 cd "$WORK/source/SP"
 jobs=1
 ./cross-make-mingw64.sh -j"$jobs" \
   BUILD_CLIENT=1 BUILD_SERVER=0 BUILD_GAME_SO=1 BUILD_GAME_QVM=0 \
   BUILD_BASEGAME=1 BUILD_RENDERER_REND2=1 USE_RENDERER_DLOPEN=1
)
BUILD="$WORK/source/SP/build/release-mingw32-x86_64"
STAGE="$ROOT/dist/$NAME"
mkdir -p "$STAGE/Main" "$STAGE/docs"
cp "$BUILD/ioWolfSP.x64.exe" "$BUILD/renderer_sp_rend2_x64.dll" \
   "$BUILD/renderer_sp_opengl1_x64.dll" "$BUILD/SDL264.dll" "$BUILD/OpenAL64.dll" "$STAGE/"
cp "$BUILD/main/cgame_sp_x64.dll" "$BUILD/main/qagame_sp_x64.dll" "$BUILD/main/ui_sp_x64.dll" "$STAGE/Main/"
cp "$ROOT/integration/release/UNIFIED_PRODUCTION.cfg" "$STAGE/Main/"
cp "$ROOT/integration/release/README_UNIFIED_PRODUCTION.md" "$STAGE/README.md"
cp "$ROOT/integration/release/"{darkwolf-unified-production-v1-integration-delta.patch,darkwolf-rend2-unified-production-v1-cumulative.patch,FINAL_SOURCE_SHA256.txt,CHANGED_FILES.txt,CHANGED_FUNCTIONS.txt,REPLAY_APPLY_LOG.txt} "$STAGE/docs/"
renderer_sha="$(sha256sum "$STAGE/renderer_sp_rend2_x64.dll" | awk '{print $1}')"
cgame_sha="$(sha256sum "$STAGE/Main/cgame_sp_x64.dll" | awk '{print $1}')"
sed -e "s/\${INTEGRATION_COMMIT_SHA}/${GITHUB_SHA:-$(git -C "$ROOT" rev-parse HEAD)}/" \
    -e "s/\${WORKFLOW_RUN_ID}/${GITHUB_RUN_ID:-LOCAL}/" \
    -e "s/\${ARTIFACT_ID_ASSIGNED_AFTER_UPLOAD}/assigned-by-GitHub-Actions-after-upload/" \
    -e "s/\${RENDERER_SHA256}/$renderer_sha/" -e "s/\${CGAME_SHA256}/$cgame_sha/" \
    "$ROOT/integration/release/PROVENANCE_TEMPLATE.txt" > "$STAGE/docs/PROVENANCE.txt"
(cd "$STAGE" && find . -type f ! -name SHA256SUMS.txt -print0 | sort -z | xargs -0 sha256sum > docs/SHA256SUMS.txt)
mkdir -p "$ROOT/dist/upload"
(cd "$ROOT/dist" && zip -q -r -9 "upload/$NAME.zip" "$NAME")
sha256sum "$ROOT/dist/upload/$NAME.zip" > "$ROOT/dist/upload/$NAME.zip.sha256"
printf '%s\n' "$renderer_sha" > "$ROOT/dist/renderer.sha256"
printf '%s\n' "$cgame_sha" > "$ROOT/dist/cgame.sha256"
