#!/usr/bin/env python3
"""FINAL Clean Production: freeze *accepted V2 binary*, never rebuild V3.

Reads canonical GitHub Actions #41019985033 and V2 #41200040113 artifact
ZIPs, compares ALL 57 accepted files and ALL five quality CFGs bytewise.
Copies V2 renderer unchanged, removes three diagnostic configs, adds only
documentation and an isolated Clean launcher. V3/V3.1/V3.2 source is excluded.
No authored game assets/pak*.pk3 are shipped.
"""
import argparse,hashlib,io,json,struct,zipfile
from pathlib import Path

NAME="DarkWolf_Texture_Material_Fidelity_FINAL_Clean_Production_2026-11-01_Win64"
BASE_RUN=41019985033
V2_RUN=41200040113
EXPECTED_BASE_RENDERER="d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45"
EXPECTED_FINAL_RENDERER="83e492871751cc4c37baf9909350a71ce0c90f3c21b895c2e8d572aa21b40acc"
H=lambda b:hashlib.sha256(b).hexdigest()

TEST_CFGS={
    "Main/DW_TEXTURE_MATERIAL_V2_OFF_TEST.cfg",
    "Main/DW_TEXTURE_MATERIAL_V2_ON_TEST.cfg",
    "Main/DW_LUT_ANALYTIC_V2_OPTIONAL_TEST.cfg",
}
V2_STALE_NOTES={"README_TEXTURE_MATERIAL_V2_RU.txt"}
EXPECTED_V2_EXTRAS=(TEST_CFGS | V2_STALE_NOTES | {"docs/DW_TEXTURE_MATERIAL_V2_SOURCE_AUDIT.json"})

def load_nested(artifact,required_fragment):
    with zipfile.ZipFile(artifact) as outer:
        assert outer.testzip() is None
        candidates=[n for n in outer.namelist()
                    if n.startswith("dist/") and n.endswith(".zip") and required_fragment in n]
        assert len(candidates)==1,(artifact, candidates)
        data=outer.read(candidates[0])
        sha_names=[n for n in outer.namelist() if n==candidates[0]+".sha256"]
        assert len(sha_names)==1,"missing matching outer SHA manifest"
        assert H(data)==outer.read(sha_names[0]).decode("utf-8").split()[0],"parent artifact SHA mismatch"
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None
        all_names=z.namelist()
        prefixes={n.split("/")[0] for n in all_names if not n.endswith("/")}
        assert len(prefixes)==1,prefixes
        prefix=next(iter(prefixes))+"/"
        out={n[len(prefix):]:z.read(n) for n in all_names if not n.endswith("/")}
        assert all("/../" not in name and not name.startswith("/") and "\\" not in name
                   for name in out)
    return out,H(data)

def validate_sha_index(data):
    assert "docs/SHA256SUMS.txt" in data
    lines=data["docs/SHA256SUMS.txt"].decode("utf-8").splitlines()
    seen=set()
    for row in lines:
        digest,rel=row.split("  ",1)
        assert rel not in seen and rel in data,rel
        seen.add(rel)
        assert H(data[rel])==digest,rel
    assert seen == (set(data)-{"docs/SHA256SUMS.txt"}),(len(seen),len(data))
    return len(lines)

def launcher():
    return (
      '@echo off\r\n'
      'setlocal EnableExtensions DisableDelayedExpansion\r\n'
      'cd /d "%~dp0"\r\n'
      'if not exist "ioWolfSP.x64.exe" exit /b 1\r\n'
      'if not exist "renderer_sp_rend2_x64.dll" exit /b 1\r\n'
      'set "DW_HOME=%CD%\\DW_TM_Fidelity_FINAL_Clean_Home"\r\n'
      'if not exist "%DW_HOME%\\Main" mkdir "%DW_HOME%\\Main"\r\n'
      'if not exist "%DW_HOME%\\Main" exit /b 1\r\n'
      'set "DW_FIRST="\r\n'
      'if not exist "%DW_HOME%\\Main\\DW_TM_FINAL_FIRST_RUN.txt" (\r\n'
      '  copy /y "Main\\DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg" "%DW_HOME%\\Main\\DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg" >nul\r\n'
      '  if errorlevel 1 exit /b 1\r\n'
      '  echo First launch applied accepted V2 with neutral LUT > "%DW_HOME%\\Main\\DW_TM_FINAL_FIRST_RUN.txt"\r\n'
      '  set "DW_FIRST=+exec DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg"\r\n'
      ')\r\n'
      '"%CD%\\ioWolfSP.x64.exe" +set fs_basepath "%CD%" +set fs_homepath "%DW_HOME%" +set cl_renderer rend2 +set r_renderer rend2 +set com_recommendedSet 1 %DW_FIRST%\r\n'
      'exit /b %errorlevel%\r\n'
    ).encode("ascii")

README = """DarkWolf Rend2 — Texture & Material Fidelity FINAL Clean Production
Дата: 2026-11-01. Windows x64 Single Player.
База: GitHub Actions #41019985033.
Исходный код исправления V2 и проверенный бинарник: Actions #41200040113.
Финальный DLL SHA-256: 83e492871751cc4c37baf9909350a71ce0c90f3c21b895c2e8d572aa21b40acc.

РЕШЕНИЕ ПО ЦИКЛУ V2 -> V3.2
Изменения V2 приняты как окончательное исправление Texture & Material Fidelity.
V3: opt-in модельные категории дали только флаг NO_COMPRESSION без изменения формата.
V3.1: Escape1 и XLabs подтвердили отсутствие изменения GPU-формата и размеров.
V3.2: LOD bias -0.25 реально применялся на Escape1, но заметной выгоды не показал.
Экспериментальный LOD bias, расширение областей модели и диагностический
инструментарий V3/V3.1/V3.2 не входят в эту Clean Production.
Этот релиз не перекомпилирует и не изменяет принятый V2 renderer DLL.

ИСПРАВЛЕННОЕ И СОХРАНЁННОЕ
* Возвращено исходное поведение текстур BSP-окружения.
* Texture Fidelity и Material Fidelity ограничены модельным путём V2.
* Alpha-to-Coverage не применяется к решёткам BSP.
* Исключены проблемные автоматический upsample и CPU cutout mip generation.
* CAS сохранён, аналитический LUT нейтрален при strength=0.
* HDR16F, Bloom v2, SSGI, CSM Guard, volumetrics, Tesla, StaticPromote,
  texture filtering, MSAA и прочие эффекты сохранены из принятой базы.
* Все пять CFG Performance/Balanced/Quality/High/Ultra побайтово сохранены.
* В сборке нет тестовых V2 OFF/ON/LUT CFG; не добавлены новые debug CVars.

КАК УСТАНОВИТЬ
1. Сохранить резервную копию установленной игры и прежнего renderer DLL.
2. Распаковать целый архив в отдельную папку с сохранением папки Main.
3. Разместить собственные лицензионные RTCW pak*.pk3 в Main.
   Коммерческие игровые ресурсы в архив не входят.
4. Запустить RUN_DARKWOLF_TEXTURE_MATERIAL_FINAL_CLEAN.bat.
   Скрипт создаст отдельный homepath и один раз применит базовый visual CFG;
   дальше сохранённые параметры можно редактировать без переустановки.
5. Для явного выбора одного из пяти профилей (необязательно):
   /exec DW_HDR16F_V1_PERFORMANCE.cfg
   /exec DW_HDR16F_V1_BALANCED.cfg
   /exec DW_HDR16F_V1_QUALITY.cfg
   /exec DW_HDR16F_V1_HIGH.cfg
   /exec DW_HDR16F_V1_ULTRA.cfg
   После выбора профиля выполнить /vid_restart.

НУЖНЫЕ ПАРАМЕТРЫ ПО УМОЛЧАНИЮ
r_dwTextureFidelity 1
r_dwMaterialFidelity 1
r_dwA2C 1
r_dwCas 1
r_dwLut 1
r_dwLutStrength 0.00 (нейтральная LUT, избегаем красного оттенка).
r_forceSun 1, r_dlightMode 2, r_staticPromoteMaxLights 32.
Отдельных параметров r_dwModelMipBias и r_dwModelTextureScope в финальной DLL НЕТ.
Исторические r_dwAdaptiveUpsample и r_dwCutoutMip, встречающиеся в сохранённых
CFG из #41019985033, больше не управляют отдельными алгоритмами в V2.

ОГРАНИЧЕНИЯ ПОДТВЕРЖДЕНИЯ
Тестировались пары ON/OFF для BSP лестниц и решёток, пара модели солдата
и оружия, LUT в одной красноосвещённой комнате, сравнение V3/V3.2 в Escape1.
Это достаточное основание завершить ограниченный цикл изменений текстур,
но не означает сертификата отсутствия визуальных дефектов на любой карте.
Контролируемый FPS-бенчмарк не проводился.

Все игровые бинарники, кроме заранее принятого V2 renderer DLL, взяты из
точного проверенного baseline #41019985033, без новой компиляции.
""" 

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base-artifact",type=Path,required=True)
    ap.add_argument("--v2-artifact",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    base,baseZipSha=load_nested(args.base_artifact,"HDR16F_Precision_V1_Clean_Production_Win64")
    v2,v2ZipSha=load_nested(args.v2_artifact,"Texture_Material_Quality_V2_Exact_41019985033_Win64")
    validate_sha_index(base)
    validate_sha_index(v2)
    assert len(base)==57,(len(base),"expected frozen baseline 57 files")
    assert len(v2)==62,(len(v2),"expected V2 parent 62 files")
    assert set(v2)-set(base)==EXPECTED_V2_EXTRAS,sorted(set(v2)-set(base))
    assert not (set(base)-set(v2)),sorted(set(base)-set(v2))
    assert H(base["renderer_sp_rend2_x64.dll"])==EXPECTED_BASE_RENDERER
    assert H(v2["renderer_sp_rend2_x64.dll"])==EXPECTED_FINAL_RENDERER
    for name in sorted(set(base)-{"renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt"}):
        assert base[name]==v2[name],("baseline changed by V2",name)
    # Reject unknown or experimental CVars in binary, not just final CFG.
    dll=v2["renderer_sp_rend2_x64.dll"]
    assert dll[:2]==b"MZ" and dll[struct.unpack_from("<I",dll,60)[0]:struct.unpack_from("<I",dll,60)[0]+4]==b"PE\0\0"
    for banned in (b"r_dwModelMipBias",b"r_dwModelTextureScope",b"r_dwModelFidelityReport"):
        assert banned not in dll,("V3+ experimental feature leaked",banned)
    for required in (b"r_dwTextureFidelity",b"r_dwMaterialFidelity",b"r_dwA2C",
                     b"r_dwCas",b"r_dwLut",b"r_ssgi",b"r_bloom"):
        assert required in dll,("missing V2 CVar",required)

    # Preserve accepted all-ON profile values exactly from #41019985033.
    profiles=["PERFORMANCE","BALANCED","QUALITY","HIGH","ULTRA"]
    markers=("seta r_hdr \"1\"","seta r_bloom \"1\"","seta r_ssgi \"1\"",
             "seta r_forceSun \"1\"","seta r_dlightMode \"2\"",
             "seta r_staticPromote \"1\"","seta r_volumetricSun \"1\"",
             "seta r_volumetricLocal \"1\"","seta r_volumetricFire \"1\"",
             "seta r_dwTextureFidelity \"1\"","seta r_dwMaterialFidelity \"1\"",
             "seta r_dwCas \"1\"","seta r_dwA2C \"1\"",
             "seta r_dwLut \"1\"","seta r_dwLutStrength \"0.00\"")
    for profile in profiles:
        name=f"Main/DW_HDR16F_V1_{profile}.cfg"
        assert name in base and v2[name]==base[name],name
        txt=v2[name].decode("utf-8")
        for marker in markers:
            assert marker in txt,("profile not all-ON",profile,marker)

    files={name:data for name,data in v2.items() if name not in TEST_CFGS|V2_STALE_NOTES}
    assert len(files)==58,("unexpected number after test file removal",len(files))
    files["README_TEXTURE_MATERIAL_FINAL_CLEAN_RU.txt"]=README.encode("utf-8")
    files["RUN_DARKWOLF_TEXTURE_MATERIAL_FINAL_CLEAN.bat"]=launcher()
    manifest={
      "release":NAME,
      "release_status":"FINAL_CLEAN_PRODUCTION_ACCEPTED_V2_NO_EXPERIMENTAL_V3",
      "date":"2026-11-01",
      "original_exact_clean_production_run":BASE_RUN,
      "accepted_v2_compilation_run":V2_RUN,
      "original_baseline_inner_zip_sha256":baseZipSha,
      "accepted_v2_inner_zip_sha256":v2ZipSha,
      "accepted_base_files":len(base),
      "baseline_bytewise_unchanged_except_renderer_and_sha256_index":len(base)-2,
      "final_renderer_sha256":EXPECTED_FINAL_RENDERER,
      "renderer_new_build":False,
      "preserved_quality_cfgs":profiles,
      "neutral_LUT_strength":"0.00",
      "experimental_v3_v31_v32_code_included":False,
      "no_new_debug_cvars":True,
      "removed_test_cfgs":sorted(TEST_CFGS),
      "removed_outdated_v2_test_readme":sorted(V2_STALE_NOTES),
      "user_AB_visual_evidence":"4 mesh/ladder pairs; model/weapon pair; single LUT scene; V3.2 Escape1 A/B",
      "new_gpu_full_suite":"NOT_PERFORMED",
      "benchmarked_FPS":"NOT_PERFORMED",
      "licensed_RTCW_retail_assets":"NOT_INCLUDED"
    }
    files["docs/DW_TEXTURE_MATERIAL_FINAL_CLEAN_FREEZE_MANIFEST.json"]=(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n").encode()
    # Final must have no diagnostics/experimental configs added to this exact baseline.
    assert set(files) & (TEST_CFGS|V2_STALE_NOTES) == set()
    assert not any("DW_V3_" in x or "V31_" in x or "V32_" in x for x in files)
    for name in base:
        if name not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt"):
            assert files[name]==base[name],name
    assert files["renderer_sp_rend2_x64.dll"]==dll
    files["docs/SHA256SUMS.txt"]="".join(
        H(data)+"  "+name+"\n" for name,data in sorted(files.items())
        if name!="docs/SHA256SUMS.txt"
    ).encode("ascii")

    path=args.out/(NAME+".zip")
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for name,data in sorted(files.items()):
            arcname=NAME+"/"+name
            info=zipfile.ZipInfo(arcname,date_time=(2026,11,1,12,0,0))
            info.external_attr=0o100644<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        actual={n[len(NAME)+1:]:z.read(n) for n in z.namelist() if not n.endswith("/")}
        assert len(actual)==len(files)
        validate_sha_index(actual)
        assert all(actual[name]==base[name] for name in base
                   if name not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt"))
        assert H(actual["renderer_sp_rend2_x64.dll"])==EXPECTED_FINAL_RENDERER
        assert all(actual[f"Main/DW_HDR16F_V1_{p}.cfg"]==base[f"Main/DW_HDR16F_V1_{p}.cfg"]
                   for p in profiles)
    sha=H(path.read_bytes())
    (args.out/(NAME+".zip.sha256")).write_text(sha+"  "+path.name+"\n")
    manifest["final_archive_sha256"]=sha
    manifest["archive_file_count"]=len(files)
    manifest["internal_sha256_index_entries"]=len(files)-1
    (args.out/"DW_TEXTURE_MATERIAL_FINAL_CLEAN_AUDIT.json").write_text(
        json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"
    )
    print("DW_FINAL_CLEAN_V2_EXACT_ALL_PROFILES_AND_55_BASE_FILES_PASS",len(files),sha)

if __name__=="__main__":
    main()
