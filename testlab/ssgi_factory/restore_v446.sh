#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p evidence
repo="jaha2002-stack/iortcw-rend2-build"
run=37266797451
sha=e410db87b5704fb1518740f1cfc760e9ea67d34f
name="DarkWolf-ioRTCW-Rend2-v4.4.6-Explosion-Coverage-Candidate-Win64"
j="$(gh api "/repos/$repo/actions/runs/$run")"
test "$(jq -r .head_sha <<<"$j")" = "$sha"
test "$(jq -r .conclusion <<<"$j")" = success
gh run download "$run" --repo "$repo" --name "$name" --dir base-artifact
inner="base-artifact/$name.zip"
test "$(sha256sum "$inner" | awk '{print $1}')" = "10ca3d568fdca89569912835d110fa9f365d531ec83982927fb5c1fe590f7aea"
mkdir -p v446
unzip -q "$inner" -d v446
base="v446/$name"
test -d "$base/docs"
(cd "$base" && sha256sum -c docs/SHA256SUMS.txt)
for f in darkwolf-rend2-cumulative-ignitable-props-rc-v0-6.patch darkwolf-volumetric-aa-v4-4-3-production.patch darkwolf-force-sun-csm-smart-v4-4-4-production.patch darkwolf-dam-spotlight-halo-v4-4-5.patch darkwolf-explosion-coverage-v4-4-6.patch; do
  cp "$base/docs/$f" "$f"
done
donor="iortcw-rend2-escape1-table-shadow-rc-v0-2-residency-full-sp-windows-x64-1"
gh run download 35503262322 --repo "$repo" --name "$donor" --dir donor-artifact
test "$(sha256sum "donor-artifact/$donor.zip" | awk '{print $1}')" = "efe9a4f3b33e5dd4b621ed3fa0d87abe677c85d09ca29088a380d813b5c082bb"
mkdir -p donor
unzip -q "donor-artifact/$donor.zip" -d donor
cp "donor/$donor/docs/darkwolf-rend2-cumulative-dlight-fx-shadow-eligibility-loper-complete-electrical-pc-v0-3-sp.patch" donor.patch
git clone -q https://github.com/iortcw/iortcw.git source
git -C source checkout -q --detach 438e7d413b5f7277187c35b032eb0ef9093ae778
git -C source apply --check --binary --whitespace=nowarn ../darkwolf-rend2-cumulative-ignitable-props-rc-v0-6.patch
git -C source apply --binary --whitespace=nowarn ../darkwolf-rend2-cumulative-ignitable-props-rc-v0-6.patch
for p in ssgi_fp.glsl ssgi_vp.glsl volumetriclocal_fp.glsl volumetriclocal_upscale_fp.glsl volumetriclocal_vp.glsl volumetricsun_fp.glsl volumetricsun_vp.glsl; do
  shader="SP/code/rend2/glsl/$p"
  test ! -e "source/$shader"
  git -C source apply --check --binary --whitespace=nowarn --include="$shader" ../donor.patch
  git -C source apply --binary --whitespace=nowarn --include="$shader" ../donor.patch
done
for f in darkwolf-volumetric-aa-v4-4-3-production.patch darkwolf-force-sun-csm-smart-v4-4-4-production.patch darkwolf-dam-spotlight-halo-v4-4-5.patch darkwolf-explosion-coverage-v4-4-6.patch; do
  git -C source apply --check --binary --whitespace=nowarn "../$f"
  git -C source apply --binary --whitespace=nowarn "../$f"
done
grep -Fq 'DARKWOLF_SSGI_BRIGHT_SOURCE_HALO_FIX_V0_2' source/SP/code/rend2/glsl/ssgi_fp.glsl
grep -Fq 'r_ssgiResolveMode' source/SP/code/rend2/tr_backend.c
python3 testlab/scripts/apply_testlab_instrumentation.py source
python3 - <<'PY'
from pathlib import Path
p=Path("source/SP/code/rend2/tr_init.c")
s=p.read_text()
old="r_ssgiTrace = &s_darkwolfProductionDiagOffCvar;"
assert s.count(old)==1,"trace gate not unique"
p.write_text(s.replace(old,'r_ssgiTrace = ri.Cvar_Get("r_ssgiTrace", "0", 0); // TESTLAB_FACTORY_ONLY'))
PY
git -C source diff --check
grep -Fq 'Cmd_DWTestView_f' source/SP/code/game/g_cmds.c
sha256sum source/SP/code/rend2/glsl/ssgi_fp.glsl > evidence/shader-source-sha256.txt
printf 'BASE_RUN=%s\nBASE_SHA=%s\nSOURCE_RECONSTRUCTION_PASS\n' "$run" "$sha" > evidence/provenance.txt
