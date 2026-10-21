#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${1:-$ROOT/.android-rend2-work}"
SOURCE_DIR="$WORKDIR/source"

BASE_RUN_ID="37266797451"
BASE_HEAD_SHA="e410db87b5704fb1518740f1cfc760e9ea67d34f"
BASE_ARTIFACT_ID="11326603946"
BASE_ARTIFACT_NAME="DarkWolf-ioRTCW-Rend2-v4.4.6-Explosion-Coverage-Candidate-Win64"
BASE_ARTIFACT_DIGEST="sha256:51a49587a0c4e7ad9c7ad651d5a4fcc34c7774d89ed9366dd659ed7efa97154b"
UPSTREAM_REPO="https://github.com/iortcw/iortcw.git"
UPSTREAM_SHA="438e7d413b5f7277187c35b032eb0ef9093ae778"

SHADER_DONOR_RUN_ID="35503262322"
SHADER_DONOR_HEAD_SHA="80fde84b6e91febd5ab5a8c10e37ed0d6dd01476"
SHADER_DONOR_ARTIFACT_ID="10603017159"
SHADER_DONOR_ARTIFACT_NAME="iortcw-rend2-escape1-table-shadow-rc-v0-2-residency-full-sp-windows-x64-1"
SHADER_DONOR_ARTIFACT_DIGEST="sha256:51ef9cb590b5e9c2ae96d8305eb4e63bae005b993acdca48af7b6ff51e0d0409"
SHADER_DONOR_INNER_SHA256="efe9a4f3b33e5dd4b621ed3fa0d87abe677c85d09ca29088a380d813b5c082bb"
SHADER_DONOR_PATCH="darkwolf-rend2-cumulative-dlight-fx-shadow-eligibility-loper-complete-electrical-pc-v0-3-sp.patch"
SHADER_DONOR_PATCH_SHA256="cb8379d56e57ec83be75251756ecea781dc9d2c6d66620e17fb56538ba157d97"

PATCHES=(
  "darkwolf-rend2-cumulative-ignitable-props-rc-v0-6.patch"
  "darkwolf-volumetric-aa-v4-4-3-production.patch"
  "darkwolf-force-sun-csm-smart-v4-4-4-production.patch"
  "darkwolf-dam-spotlight-halo-v4-4-5.patch"
  "darkwolf-explosion-coverage-v4-4-6.patch"
)

command -v gh >/dev/null
command -v git >/dev/null
command -v unzip >/dev/null
command -v jq >/dev/null

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR/artifact" "$WORKDIR/release" "$WORKDIR/donor-artifact" "$WORKDIR/donor-release"

run_json="$(gh api "/repos/${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}/actions/runs/$BASE_RUN_ID")"
test "$(jq -r .head_sha <<<"$run_json")" = "$BASE_HEAD_SHA"
test "$(jq -r .conclusion <<<"$run_json")" = "success"

artifact_json="$(gh api "/repos/$GITHUB_REPOSITORY/actions/artifacts/$BASE_ARTIFACT_ID")"
test "$(jq -r .name <<<"$artifact_json")" = "$BASE_ARTIFACT_NAME"
test "$(jq -r .digest <<<"$artifact_json")" = "$BASE_ARTIFACT_DIGEST"

gh run download "$BASE_RUN_ID" \
  --repo "$GITHUB_REPOSITORY" \
  --name "$BASE_ARTIFACT_NAME" \
  --dir "$WORKDIR/artifact"

inner_zip="$WORKDIR/artifact/$BASE_ARTIFACT_NAME.zip"
inner_sha_file="$WORKDIR/artifact/$BASE_ARTIFACT_NAME.zip.sha256"
test -s "$inner_zip"
test -s "$inner_sha_file"

expected_inner="$(awk '{print $1}' "$inner_sha_file")"
actual_inner="$(sha256sum "$inner_zip" | awk '{print $1}')"
test "$actual_inner" = "$expected_inner"

unzip -q "$inner_zip" -d "$WORKDIR/release"
release_root="$(find "$WORKDIR/release" -mindepth 1 -maxdepth 1 -type d | head -1)"
test -n "$release_root"
test -f "$release_root/docs/SHA256SUMS.txt"
(
  cd "$release_root"
  sha256sum -c docs/SHA256SUMS.txt
)

git clone -q "$UPSTREAM_REPO" "$SOURCE_DIR"
git -C "$SOURCE_DIR" checkout -q --detach "$UPSTREAM_SHA"

# v4.4.3 introduced seven shader files that are not present in upstream ioRTCW.
# Reconstruct them from the exact donor used by the original Windows v4.4.3
# production workflow before applying the v4.4.3+ incremental patch chain.
donor_run_json="$(gh api "/repos/$GITHUB_REPOSITORY/actions/runs/$SHADER_DONOR_RUN_ID")"
test "$(jq -r .head_sha <<<"$donor_run_json")" = "$SHADER_DONOR_HEAD_SHA"
test "$(jq -r .conclusion <<<"$donor_run_json")" = "success"

donor_artifact_json="$(gh api "/repos/$GITHUB_REPOSITORY/actions/artifacts/$SHADER_DONOR_ARTIFACT_ID")"
test "$(jq -r .name <<<"$donor_artifact_json")" = "$SHADER_DONOR_ARTIFACT_NAME"
test "$(jq -r .expired <<<"$donor_artifact_json")" = "false"
test "$(jq -r .digest <<<"$donor_artifact_json")" = "$SHADER_DONOR_ARTIFACT_DIGEST"

gh run download "$SHADER_DONOR_RUN_ID" \
  --repo "$GITHUB_REPOSITORY" \
  --name "$SHADER_DONOR_ARTIFACT_NAME" \
  --dir "$WORKDIR/donor-artifact"

donor_zip="$WORKDIR/donor-artifact/$SHADER_DONOR_ARTIFACT_NAME.zip"
test -s "$donor_zip"
test "$(sha256sum "$donor_zip" | awk '{print $1}')" = "$SHADER_DONOR_INNER_SHA256"
unzip -q "$donor_zip" -d "$WORKDIR/donor-release"
donor_root="$(find "$WORKDIR/donor-release" -mindepth 1 -maxdepth 1 -type d | head -1)"
test -n "$donor_root"
donor_patch="$donor_root/docs/$SHADER_DONOR_PATCH"
test -s "$donor_patch"
test "$(sha256sum "$donor_patch" | awk '{print $1}')" = "$SHADER_DONOR_PATCH_SHA256"

for shader in \
  SP/code/rend2/glsl/ssgi_fp.glsl \
  SP/code/rend2/glsl/ssgi_vp.glsl \
  SP/code/rend2/glsl/volumetriclocal_fp.glsl \
  SP/code/rend2/glsl/volumetriclocal_upscale_fp.glsl \
  SP/code/rend2/glsl/volumetriclocal_vp.glsl \
  SP/code/rend2/glsl/volumetricsun_fp.glsl \
  SP/code/rend2/glsl/volumetricsun_vp.glsl
do
  test ! -e "$SOURCE_DIR/$shader"
  git -C "$SOURCE_DIR" apply --check --binary --whitespace=nowarn --include="$shader" "$donor_patch"
  git -C "$SOURCE_DIR" apply --binary --whitespace=nowarn --include="$shader" "$donor_patch"
  test -s "$SOURCE_DIR/$shader"
done

for patch in "${PATCHES[@]}"; do
  patch_path="$release_root/docs/$patch"
  test -s "$patch_path"
  git -C "$SOURCE_DIR" apply --check --binary --whitespace=nowarn "$patch_path"
  git -C "$SOURCE_DIR" apply --binary --whitespace=nowarn "$patch_path"
done

# Provenance gates from the Windows v4.4.6 candidate.
grep -Fq "DARKWOLF_VOLUMETRIC_COVERAGE_AA_PRODUCTION_V443" "$SOURCE_DIR/SP/code/rend2/tr_backend.c"
grep -Fq "DARKWOLF_VOLUMETRIC_COVERAGE_AA_FINAL_V1" "$SOURCE_DIR/SP/code/rend2/glsl/volumetriclocal_upscale_fp.glsl"
grep -Fq "DARKWOLF_FORCE_SUN_CSM_SMART_PRODUCTION_V444" "$SOURCE_DIR/SP/code/rend2/tr_scene.c"
grep -Fq "DARKWOLF_SPOTLIGHT_DEATH_LOCALVOL_SYNC_V445" "$SOURCE_DIR/SP/code/cgame/cg_ents.c"
grep -Fq "#define DARKWOLF_BARREL_BLAST_EVENT_MARKER 0x4457424C" "$SOURCE_DIR/SP/code/cgame/cg_event.c"
grep -Fq "#define DARKWOLF_DAMAGE_PROP_BLAST_MARKER  0x44575046" "$SOURCE_DIR/SP/code/cgame/cg_event.c"
grep -Fq "self->s.time2 = 0x44575046" "$SOURCE_DIR/SP/code/game/g_mover.c"

# The accepted v4.4.6 patch stack contains one known inherited trailing-space
# line in tr_scene.c. Provenance is enforced by artifact/patch hashes above;
# whitespace diagnostics are informational here and must not block Android.
git -C "$SOURCE_DIR" diff --check || true

cat > "$WORKDIR/PROVENANCE.txt" <<EOF
BASE_RUN_ID=$BASE_RUN_ID
BASE_HEAD_SHA=$BASE_HEAD_SHA
BASE_ARTIFACT_ID=$BASE_ARTIFACT_ID
BASE_ARTIFACT_NAME=$BASE_ARTIFACT_NAME
BASE_ARTIFACT_DIGEST=$BASE_ARTIFACT_DIGEST
BASE_INNER_SHA256=$actual_inner
UPSTREAM_SHA=$UPSTREAM_SHA
SHADER_DONOR_RUN_ID=$SHADER_DONOR_RUN_ID
SHADER_DONOR_HEAD_SHA=$SHADER_DONOR_HEAD_SHA
SHADER_DONOR_ARTIFACT_ID=$SHADER_DONOR_ARTIFACT_ID
SHADER_DONOR_ARTIFACT_DIGEST=$SHADER_DONOR_ARTIFACT_DIGEST
SHADER_DONOR_INNER_SHA256=$SHADER_DONOR_INNER_SHA256
SHADER_DONOR_PATCH_SHA256=$SHADER_DONOR_PATCH_SHA256
TARGET_ABI=arm64-v8a
ANDROID_MIN_API=29
EOF

printf 'ANDROID_REND2_SOURCE_READY=%s\n' "$SOURCE_DIR"
cat "$WORKDIR/PROVENANCE.txt"
