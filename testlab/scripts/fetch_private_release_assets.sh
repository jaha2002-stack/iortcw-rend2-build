#!/usr/bin/env bash
set -Eeuo pipefail

repo="${1:?usage: fetch_private_release_assets.sh owner/repo tag outdir}"
tag="${2:?usage: fetch_private_release_assets.sh owner/repo tag outdir}"
outdir="${3:-protected-assets}"

: "${GH_TOKEN:?GH_TOKEN must contain a read-only token for the private asset repository}"

rm -rf "$outdir"
mkdir -p "$outdir/release" "$outdir/unpacked"

names="$outdir/release-assets.txt"
gh release view "$tag" --repo "$repo" --json assets --jq '.assets[].name' | LC_ALL=C sort > "$names"

grep -Fxq 'rtcw-assets.sha256' "$names" || {
  echo "ERROR: release $repo@$tag has no rtcw-assets.sha256" >&2
  exit 2
}

mapfile -t parts < <(grep -E '^rtcw-assets\.zip\.part[0-9]{3,}$' "$names" | sort -V)
if [ "${#parts[@]}" -eq 0 ]; then
  echo "ERROR: release $repo@$tag has no rtcw-assets.zip.partNNN assets" >&2
  exit 2
fi

# Require a contiguous sequence part001..partNNN so a missing upload cannot
# silently produce a corrupt archive.
for i in "${!parts[@]}"; do
  expected="$(printf 'rtcw-assets.zip.part%03d' "$((i+1))")"
  test "${parts[$i]}" = "$expected" || {
    echo "ERROR: multipart sequence gap: expected $expected, got ${parts[$i]}" >&2
    exit 2
  }
done

gh release download "$tag" --repo "$repo" --dir "$outdir/release" --pattern 'rtcw-assets.sha256'
gh release download "$tag" --repo "$repo" --dir "$outdir/release" --pattern 'rtcw-assets.zip.part*'

archive="$outdir/rtcw-assets.zip"
: > "$archive"
for p in "${parts[@]}"; do
  test -s "$outdir/release/$p"
  cat "$outdir/release/$p" >> "$archive"
done

expected_sha="$(awk 'NF{print $1; exit}' "$outdir/release/rtcw-assets.sha256")"
test "${#expected_sha}" -eq 64 || {
  echo "ERROR: invalid rtcw-assets.sha256" >&2
  exit 2
}
actual_sha="$(sha256sum "$archive" | awk '{print $1}')"
test "$actual_sha" = "$expected_sha" || {
  echo "ERROR: reconstructed archive SHA-256 mismatch" >&2
  echo "expected=$expected_sha" >&2
  echo "actual=$actual_sha" >&2
  exit 2
}

unzip -q "$archive" -d "$outdir/unpacked"

pak0="$(find "$outdir/unpacked" -type f -iname 'pak0.pk3' -print -quit)"
test -n "$pak0" || {
  echo "ERROR: reconstructed retail bundle contains no pak0.pk3" >&2
  exit 2
}

retail_main="$(dirname "$pak0")"
find "$retail_main" -maxdepth 1 -type f -iname '*.pk3' -printf '%f\n' | LC_ALL=C sort > "$outdir/pk3-files.txt"
printf '%s\n' "$retail_main"
