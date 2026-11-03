#!/usr/bin/env python3
"""Reconstruct the exact accepted 41408153237 source, then apply only IFLC."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

BASE_RUN = 41408153237
BASE_COMMIT = "6fd61c7bd4e6a1c23c549c93d237f2204c9d3d89"
UPSTREAM = "438e7d413b5f7277187c35b032eb0ef9093ae778"
ARTIFACT = 13124382599
ZIP_SHA = "07da2eca174bce5d3e922954c50feabd9ef0270a057400d0a4361bd9bd08783c"
TAR_SHA = "bb520b4726232402a4cbd353a14274561d1676b8aa104666786a0213f220cb81"
V14_SHA = "0a17db572b5bf4ee9c5523a47dabf3302a36e23ec2e5fe0d0d3febb300fe7303"
KIT = Path(__file__).resolve().parent
ALLOWED = {
    "SP/code/rend2/tr_backend.c", "SP/code/rend2/tr_bsp.c",
    "SP/code/rend2/tr_init.c", "SP/code/rend2/tr_local.h",
    "SP/code/rend2/tr_scene.c", "SP/code/rend2/tr_iflc.inc", "SP/code/rend2/tr_main.c",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*cmd, **kw):
    subprocess.run(list(map(str, cmd)), check=True, **kw)


def hashes(root):
    return {str(p.relative_to(root)): sha(p)
            for p in sorted((root / "SP/code").rglob("*")) if p.is_file()}


def prepare(source, evidence, archive):
    evidence.mkdir(parents=True, exist_ok=True)
    if archive is None:
        archive = evidence / "base-source.zip"
        with archive.open("wb") as out:
            run("gh", "api", f"repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/{ARTIFACT}/zip", stdout=out)
    assert sha(archive) == ZIP_SHA, "Base artifact digest mismatch"
    original = evidence / "base"
    original.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        assert all(".." not in Path(n).parts and not Path(n).is_absolute() for n in z.namelist())
        z.extractall(original)
    tar = original / "DW_FIRE_MOTION_EXACT_PRODUCTION_SOURCE.tar.gz"
    assert sha(tar) == TAR_SHA, "Base source tar digest mismatch"
    if not source.exists():
        source.mkdir(parents=True)
        run("git", "-C", source, "init", "-q")
        run("git", "-C", source, "fetch", "--depth", "1", "https://github.com/iortcw/iortcw.git", UPSTREAM)
        run("git", "-C", source, "checkout", "-q", "--detach", "FETCH_HEAD")
    with tarfile.open(tar) as t:
        t.extractall(source, filter="data")
    manifest = json.loads((original / "DW_FIRE_MOTION_BASELINE_SOURCE_SHA256.json").read_text())
    before = hashes(source)
    assert before == manifest["source_sha256"], "Incomplete or unexpected baseline source files"
    assert len(before) == 1647
    run("python3", KIT.parent / "fire-world-pcf4x4-v14/apply.py", source,
        "--proof", evidence / "V14_RECONSTRUCTION.json")
    base = hashes(source)
    assert {p for p in base if base[p] != before[p]} == {"SP/code/rend2/tr_main.c"}
    assert base["SP/code/rend2/tr_main.c"] == V14_SHA
    base_main = (source / "SP/code/rend2/tr_main.c").read_text()
    (evidence / "IFLC_BASE_SHA256.json").write_text(json.dumps(base, indent=2) + "\n")
    run("git", "-C", source, "add", "SP/code")
    run("git", "-C", source, "-c", "user.name=DarkWolf CI", "-c", "user.email=ci@invalid.local",
        "commit", "-qm", "Exact source from accepted run 41408153237")
    patch = (KIT / "IFLC_V1.patch").resolve()
    run("git", "-C", source, "apply", "--check", patch)
    run("git", "-C", source, "apply", patch)
    run("git", "-C", source, "diff", "--check")
    run("git", "-C", source, "apply", "--reverse", "--check", patch)
    after = hashes(source)
    changed = {p for p in set(base) | set(after) if base.get(p) != after.get(p)}
    assert changed == ALLOWED, ("IFLC source allowlist mismatch", sorted(changed))
    final_main = (source / "SP/code/rend2/tr_main.c").read_text()
    def protected_capture(s):
        start = s.index("void R_RenderDlightWorldOcclusion(")
        end = s.index("static qboolean R_FireVolProductionCacheMatchesHint", start)
        return s[start:end]
    assert protected_capture(final_main) == protected_capture(base_main), "Accepted world capture/PCF changed"
    # The only tr_main delta is IFLC-only input restoration in the two selection
    # helpers; all actual cubemap generation functions are protected separately.
    def functions(s):
        import re
        found = {}
        for m in re.finditer(r"(?m)^(?:static )?(?:void|qboolean|float|int) (R_[A-Za-z0-9_]+)\(", s):
            brace = s.find("{", m.end())
            semicolon = s.find(";", m.end(), brace)
            if semicolon >= 0:
                continue
            depth, end = 1, brace + 1
            # C comments and quoted text can contain unmatched braces.
            tokens = re.finditer(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', s[brace + 1:], re.S)
            for token in tokens:
                if token[0] not in ("{", "}"):
                    continue
                depth += 1 if token[0] == "{" else -1
                if not depth:
                    end = brace + 1 + token.end()
                    break
            assert depth == 0, ("Unbalanced source function", m[1])
            found[m[1]] = s[m.start():end]
        return found
    old_funcs, new_funcs = functions(base_main), functions(final_main)
    main_changed = {n for n in old_funcs if old_funcs[n] != new_funcs.get(n)}
    assert main_changed == {"R_DlightShadowSelectionScore", "R_DarkWolfStaticPromoteShadowCompanionEquivalent"}, main_changed
    assert all(base[p] == after[p] for p in base if "/glsl/" in p)
    proof = {
        "base_run": BASE_RUN, "base_head_sha": BASE_COMMIT,
        "baseline_verified_files": len(base), "changed_files": sorted(changed),
        "changes": {p: {"before": base.get(p), "after": after.get(p)} for p in sorted(changed)},
        "patch_sha256": sha(patch), "v14_capture_and_pcf_unchanged": True,
        "shadow_selector_changes": sorted(main_changed),
        "all_glsl_unchanged": True, "cgame_abi_unchanged": True,
        "new_cvars": {"r_dwFireLightControl": "0"},
        "visual_status": "PENDING_REAL_GAME_CAPTURE_AND_REVIEW",
    }
    (evidence / "IFLC_SOURCE_PROOF.json").write_text(json.dumps(proof, indent=2) + "\n")
    (evidence / "IFLC_SOURCE_SHA256.json").write_text(json.dumps(after, indent=2) + "\n")
    print("IFLC_EXACT_BASE_AND_SOURCE_ALLOWLIST_PASS", len(base), sorted(changed), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("evidence", type=Path)
    ap.add_argument("--archive", type=Path)
    args = ap.parse_args()
    prepare(args.source.resolve(), args.evidence.resolve(), args.archive.resolve() if args.archive else None)
