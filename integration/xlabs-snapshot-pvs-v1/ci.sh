#!/usr/bin/env bash
set -Eeuo pipefail
name=integration/xlabs-snapshot-pvs-v1
mkdir -p evidence/xlabs-snapshot-v1-replay/SP/code/server evidence/xlabs-snapshot-v1-qa
python3 -m py_compile "$name/apply.py" "$name/qa.py" "$name/package.py"
# Verify that the previously accepted feature chain DID NOT MODIFY server PVS.
# This allows a truly surgical snapshot delta with no source ambiguity.
git -C sept-source show 438e7d413b5f7277187c35b032eb0ef9093ae778:SP/code/server/sv_snapshot.c > evidence/XLABS_PVS_UPSTREAM_SNAPSHOT_ORIGINAL.c
cmp sept-source/SP/code/server/sv_snapshot.c evidence/XLABS_PVS_UPSTREAM_SNAPSHOT_ORIGINAL.c
sha256sum sept-source/SP/code/server/sv_snapshot.c | tee evidence/XLABS_PVS_SERVER_BEFORE_SHA256.txt
cp sept-source/SP/code/server/sv_snapshot.c evidence/xlabs-snapshot-v1-replay/SP/code/server/sv_snapshot.c
git -C sept-source diff --name-only > evidence/XLABS_PVS_ALL_CHANGES_BEFORE.txt
python3 "$name/apply.py" sept-source \
  --proof evidence/XLABS_SNAPSHOT_V1_SOURCE_PROOF.json \
  --patch evidence/XLABS_SNAPSHOT_V1_EXACT_SOURCE.patch \
  | tee evidence/XLABS_SNAPSHOT_V1_APPLY.txt
grep -Fq DW_XLABS_LINKED_TESLA_NEAR_SNAPSHOT_PVS_TEST_V1_SOURCE_PASS evidence/XLABS_SNAPSHOT_V1_APPLY.txt
git -C sept-source diff --check
git -C sept-source apply --reverse --check ../evidence/XLABS_SNAPSHOT_V1_EXACT_SOURCE.patch
if git -C sept-source apply --check ../evidence/XLABS_SNAPSHOT_V1_EXACT_SOURCE.patch >/dev/null 2>&1; then
  echo 'DUPLICATE_PVS_PATCH_NOT_REJECTED' >&2
  exit 1
fi
# Independent patch replay in a separate directory, byte-compare result,
# then undo and verify every byte matches untouched upstream server source.
(cd evidence/xlabs-snapshot-v1-replay && git apply --check ../XLABS_SNAPSHOT_V1_EXACT_SOURCE.patch && git apply ../XLABS_SNAPSHOT_V1_EXACT_SOURCE.patch)
cmp sept-source/SP/code/server/sv_snapshot.c evidence/xlabs-snapshot-v1-replay/SP/code/server/sv_snapshot.c
(cd evidence/xlabs-snapshot-v1-replay && git apply --reverse --check ../XLABS_SNAPSHOT_V1_EXACT_SOURCE.patch && git apply --reverse ../XLABS_SNAPSHOT_V1_EXACT_SOURCE.patch)
cmp evidence/XLABS_PVS_UPSTREAM_SNAPSHOT_ORIGINAL.c evidence/xlabs-snapshot-v1-replay/SP/code/server/sv_snapshot.c
git -C sept-source diff --name-only > evidence/XLABS_PVS_ALL_CHANGES_AFTER.txt
python3 - <<'PY'
from pathlib import Path
before=set(Path("evidence/XLABS_PVS_ALL_CHANGES_BEFORE.txt").read_text().splitlines())
after=set(Path("evidence/XLABS_PVS_ALL_CHANGES_AFTER.txt").read_text().splitlines())
assert after-before=={"SP/code/server/sv_snapshot.c"},("PVS_SOURCE_SCOPE_DRIFT",after-before)
assert not (before-after),("REMOVED_ACCEPTED_FEATURE_FILES",before-after)
print("DW_XLABS_PVS_SERVER_ONLY_PATCH_SOURCE_ALLOWLIST_PASS")
PY
python3 "$name/qa.py" sept-source \
  --proof evidence/XLABS_SNAPSHOT_V1_SOURCE_PROOF.json \
  --out evidence/xlabs-snapshot-v1-qa | tee evidence/XLABS_SNAPSHOT_V1_QA.txt
grep -Fq DW_XLABS_PVS_TEST_V1_SOURCE_AND_SNAPSHOT_ELIGIBILITY_PASS evidence/XLABS_SNAPSHOT_V1_QA.txt
echo DW_XLABS_ACTIVE_TESLA_LOCAL_PVS_SOURCE_AND_REPLAY_PASS
