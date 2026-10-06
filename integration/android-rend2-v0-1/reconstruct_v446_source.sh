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

PATCHES=(
  "darkwolf-rend2-cumulative-ignitable-props-rc-v0-6.patch"
  "darkwolf-force-sun-csm-smart-v4-4-4-production.patch"
  "darkwolf-dam-spotlight-halo-v4-4-5.patch"
  "darkwolf-explosion-coverage-v4-4-6.patch"
)

command -v gh >/dev/null
command -v git >/dev/null
command -v unzip >/dev/null
command -v jq >/dev/null

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR/artifact" "$WORKDIR/release"

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

for patch in "${PATCHES[@]}"; do
  patch_path="$release_root/docs/$patch"
  test -s "$patch_path"
  git -C "$SOURCE_DIR" apply --check --binary --whitespace=nowarn "$patch_path"
  git -C "$SOURCE_DIR" apply --binary --whitespace=nowarn "$patch_path"
done

# Provenance gates from the Windows v4.4.6 candidate.
grep -Fq "DARKWOLF_FORCE_SUN_CSM_SMART_PRODUCTION_V444" "$SOURCE_DIR/SP/code/rend2/tr_scene.c"
grep -Fq "DARKWOLF_SPOTLIGHT_DEATH_LOCALVOL_SYNC_V445" "$SOURCE_DIR/SP/code/cgame/cg_ents.c"
grep -Fq "#define DARKWOLF_BARREL_BLAST_EVENT_MARKER 0x4457424C" "$SOURCE_DIR/SP/code/cgame/cg_event.c"
grep -Fq "#define DARKWOLF_DAMAGE_PROP_BLAST_MARKER  0x44575046" "$SOURCE_DIR/SP/code/cgame/cg_event.c"
grep -Fq "self->s.time2 = 0x44575046" "$SOURCE_DIR/SP/code/game/g_mover.c"

git -C "$SOURCE_DIR" diff --check

cat > "$WORKDIR/PROVENANCE.txt" <<EOF
BASE_RUN_ID=$BASE_RUN_ID
BASE_HEAD_SHA=$BASE_HEAD_SHA
BASE_ARTIFACT_ID=$BASE_ARTIFACT_ID
BASE_ARTIFACT_NAME=$BASE_ARTIFACT_NAME
BASE_ARTIFACT_DIGEST=$BASE_ARTIFACT_DIGEST
BASE_INNER_SHA256=$actual_inner
UPSTREAM_SHA=$UPSTREAM_SHA
TARGET_ABI=arm64-v8a
ANDROID_MIN_API=29
EOF

printf 'ANDROID_REND2_SOURCE_READY=%s\n' "$SOURCE_DIR"
cat "$WORKDIR/PROVENANCE.txt"
