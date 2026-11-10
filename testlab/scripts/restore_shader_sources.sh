#!/usr/bin/env bash
set -Eeuo pipefail

source_root="${1:-source}"
evidence_dir="${2:-evidence}"
mkdir -p "$evidence_dir"

required=(
  SHADER_DONOR_RUN_ID SHADER_DONOR_HEAD_SHA SHADER_DONOR_ARTIFACT_ID
  SHADER_DONOR_ARTIFACT_NAME SHADER_DONOR_ARTIFACT_DIGEST
  SHADER_DONOR_INNER_SHA256 SHADER_DONOR_PATCH SHADER_DONOR_PATCH_SHA256
)
for v in "${required[@]}"; do
  test -n "${!v:-}" || { echo "missing env: $v" >&2; exit 2; }
done

donor_json="$(gh api "/repos/${GITHUB_REPOSITORY}/actions/runs/${SHADER_DONOR_RUN_ID}")"
test "$(jq -r .head_sha <<<"$donor_json")" = "$SHADER_DONOR_HEAD_SHA"
test "$(jq -r .conclusion <<<"$donor_json")" = success

arts="/repos/${GITHUB_REPOSITORY}/actions/runs/${SHADER_DONOR_RUN_ID}/artifacts?per_page=100"
donor_name="$(gh api "$arts" --jq ".artifacts[] | select(.id == ${SHADER_DONOR_ARTIFACT_ID}) | .name")"
donor_expired="$(gh api "$arts" --jq ".artifacts[] | select(.id == ${SHADER_DONOR_ARTIFACT_ID}) | .expired")"
donor_digest="$(gh api "$arts" --jq ".artifacts[] | select(.id == ${SHADER_DONOR_ARTIFACT_ID}) | .digest")"
test "$donor_name" = "$SHADER_DONOR_ARTIFACT_NAME"
test "$donor_expired" = false
test "$donor_digest" = "$SHADER_DONOR_ARTIFACT_DIGEST"

rm -rf shader-donor shader-donor-release
mkdir -p shader-donor shader-donor-release
gh run download "$SHADER_DONOR_RUN_ID" --repo "$GITHUB_REPOSITORY" --name "$SHADER_DONOR_ARTIFACT_NAME" --dir shader-donor

donor_zip="shader-donor/$SHADER_DONOR_ARTIFACT_NAME.zip"
test -s "$donor_zip"
test "$(sha256sum "$donor_zip" | awk '{print $1}')" = "$SHADER_DONOR_INNER_SHA256"

unzip -q "$donor_zip" -d shader-donor-release
donor_base="$(find shader-donor-release -mindepth 1 -maxdepth 1 -type d -print -quit)"
test -n "$donor_base"
donor_patch="$donor_base/docs/$SHADER_DONOR_PATCH"
test -s "$donor_patch"
test "$(sha256sum "$donor_patch" | awk '{print $1}')" = "$SHADER_DONOR_PATCH_SHA256"

shader_paths=(
  SP/code/rend2/glsl/ssgi_fp.glsl
  SP/code/rend2/glsl/ssgi_vp.glsl
  SP/code/rend2/glsl/volumetriclocal_fp.glsl
  SP/code/rend2/glsl/volumetriclocal_upscale_fp.glsl
  SP/code/rend2/glsl/volumetriclocal_vp.glsl
  SP/code/rend2/glsl/volumetricsun_fp.glsl
  SP/code/rend2/glsl/volumetricsun_vp.glsl
)

for p in "${shader_paths[@]}"; do
  test ! -e "$source_root/$p"
  git -C "$source_root" apply --check --binary --whitespace=nowarn --include="$p" "../$donor_patch"
  git -C "$source_root" apply --binary --whitespace=nowarn --include="$p" "../$donor_patch"
  test -s "$source_root/$p"
done

printf '%s\n' "${shader_paths[@]}" > "$evidence_dir/recovered-shader-sources.txt"
for p in "${shader_paths[@]}"; do
  sha256sum "$source_root/$p"
done > "$evidence_dir/recovered-shader-sources.sha256"

echo "Historical GLSL source recovery PASS"
