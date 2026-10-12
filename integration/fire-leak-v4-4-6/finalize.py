#!/usr/bin/env python3
"""Repackage original strictly verified v4.4.6 Win64 outputs as standalone fire-leak RC."""
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

dist = Path(sys.argv[1]).resolve()
evidence = Path(sys.argv[2]).resolve()
src = Path(sys.argv[3]).resolve()
oldname = "DarkWolf-ioRTCW-Rend2-v4.4.6-Optimized-Clean-Candidate-Win64-SP"
name = "DarkWolf-ioRTCW-Rend2-v4.4.6-Fire-Light-Leak-Rootfix-RC1-Win64-SP"
base = dist / oldname
stage = dist / name
assert base.is_dir() and not stage.exists()
assert (dist / (oldname + ".zip")).is_file(), "Original packaging gates did not pass"
base.rename(stage)
cfg = stage / "Main/PRODUCTION_HIGH_QUALITY.cfg"
text = cfg.read_text()
old1 = 'seta r_dlightShadowStrength "0.88"'
old2 = 'seta r_volumetricFireMode "2"'
assert text.count(old1) == text.count(old2) == 1, "Unexpected source preset"
text = text.replace(old1, 'seta r_dlightShadowStrength "1.00"')
text = text.replace(old2, 'seta r_volumetricFireMode "3"')
cfg.write_text(text)
# Baseline already provides FireVol V07 native/synthetic shadow capture. Mode 3 -> shaped mode 6.
assert 'seta r_volumetricFireV07Mode "2"' in text
assert 'seta r_dlightMode "2"' in text
assert 'seta r_dlightShadowMaxLights "3"' in text
assert 'seta r_staticPromoteMaxLights "32"' in text
assert 'seta r_forceSun "1"' in text
assert 'seta r_volumetricFire "1"' in text
assert 'seta r_volumetricLocal "1"' in text
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
record = json.loads((stage / "docs/BUILD_PROVENANCE.json").read_text())
record.update({
    "status": "ROOTFIX_RC1_FOR_LOCAL_VISUAL_VERIFICATION",
    "rootfix": "DARKWOLF_V446_FIRE_LEAK_ROOTFIX_RC1",
    "behavior": "Persistent fire/physical direct lights without cubemap do not illuminate; shadow-aware volumetrics without map do not scatter; fire shape mode 6; full shadow opacity",
    "source_sha256": {path: sha(src / path) for path in (
        "SP/code/rend2/tr_shade.c",
        "SP/code/rend2/glsl/volumetriclocal_fp.glsl",
        "SP/code/rend2/tr_main.c",
        "SP/code/rend2/tr_scene.c",
    )},
    "production_profile_sha256": sha(cfg),
    "source_url": "https://github.com/jaha2002-stack/iortcw-rend2-build/tree/rend2-v4-4-6-fire-leak-rootfix-rc1-20261012",
    "RETAINED_LIGHTS_WITHOUT_SHADOW_CUBEMAP": "DIRECT_CONTRIBUTION_SUPPRESSED",
    "PERSISTENT_SHADOW_CACHE_V2": "NOT_IMPLEMENTED",
    "ESCAPE1_GAMEPLAY_VERIFICATION": "NOT_RUN",
    "WINDOWS_GPU_VERIFICATION": "NOT_RUN",
    "VISUAL_PARITY_ACCEPTANCE": "NOT_RUN",
})
(stage / "docs/BUILD_PROVENANCE.json").write_text(json.dumps(record, indent=2) + "\n")
shutil.copy2(evidence / "rootfix-source.json", stage / "docs/rootfix-source.json")
shutil.copy2(evidence / "v446-fire-leak-rootfix-delta.patch", stage / "docs/v446-fire-leak-rootfix-delta.patch")
(stage / "README_FIRE_LEAK_ROOTFIX_RU.txt").write_text(
    "DarkWolf ioRTCW Rend2 4.4.6 Fire Light Leak Rootfix RC1\n"
    "СТАТУС: кандидат для проверки в игре, НЕ подтверждённый clean production.\n"
    "Распакуйте в отдельную копию RTCW с легальными pak*.pk3 (не включены).\n"
    "Запускайте RUN_DARKWOLF_OPTIMIZED_CLEAN.bat для изолированного профиля.\n"
    "Включено: защитный отсев стационарного прямого света без теневой карты, "
    "отсев незатенённого объёмного огня, сила тени 1.0.\n"
    "СОЗНАТЕЛЬНЫЙ КОМПРОМИСС: у факела без теневого слота временно отсутствует "
    "добавочная динамическая засветка. Спрайт огня и исходные lightmaps сохранены.\n"
    "Необходимо проверить escape1: печь -> улица, факел -> этаж сверху, "
    "яркость внутри комнаты, двери и производительность.\n"
    "Это RC1. Для полного visual parity нужна реализация дополнительного shadow cache/LOS.\n",
    encoding="utf-8"
)
checksum_path = stage / "docs/SHA256SUMS.txt"
files = sorted(p for p in stage.rglob("*") if p.is_file() and p != checksum_path)
checksums = {p.relative_to(stage).as_posix(): sha(p) for p in files}
checksum_path.write_text("".join(f"{digest}  {path}\n" for path, digest in checksums.items()))
zippath = dist / (name + ".zip")
with zipfile.ZipFile(zippath, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for path in sorted(stage.rglob("*")):
        if path.is_file():
            z.write(path, arcname=name + "/" + path.relative_to(stage).as_posix())
with zipfile.ZipFile(zippath) as z:
    assert z.testzip() is None
    for path, digest in checksums.items():
        assert hashlib.sha256(z.read(name + "/" + path)).hexdigest() == digest, path
(dist / (name + ".zip.sha256")).write_text(sha(zippath) + "  " + zippath.name + "\n")
(dist / "ROOTFIX_BUILD_PROVENANCE.json").write_text(json.dumps(record, indent=2) + "\n")
# Keep the original optimized archive out of download package.
(dist / (oldname + ".zip")).unlink()
(dist / (oldname + ".zip.sha256")).unlink()
assert (stage / "renderer_sp_rend2_x64.dll").is_file()
assert (stage / "ioWolfSP.x64.exe").is_file()
print("FIRE_LEAK_ROOTFIX_RC1_WIN64_PACKAGE_PASS", sha(zippath))
