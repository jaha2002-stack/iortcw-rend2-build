#!/usr/bin/env python3
"""Final SAFE Clean Production: accepted Texture/Material V2 package plus
ONE verified Boss1 shadow self-occlusion source-local correction. No debug.
The five accepted profile CFGs, game exe, qagame/cgame/ui, source assets and
existing launchers are all byte-identical to Actions #41286257713.
"""
import argparse,io,zipfile,hashlib,json,struct
from pathlib import Path
NAME="DarkWolf_PointShadow_SAFE_Clean_Production_TextureV2_Boss1_2026-11-01_Win64"
PARENT_NAME="DarkWolf_Texture_Material_Fidelity_FINAL_Clean_Production_2026-11-01_Win64"
PARENT_ZIP_SHA="2fa5947c2562db208ab586c450afbb93420423a0dbb67a4352d6ed06af720837"
PARENT_DLL_SHA="83e492871751cc4c37baf9909350a71ce0c90f3c21b895c2e8d572aa21b40acc"
def H(v):return hashlib.sha256(v).hexdigest()

README="""DarkWolf Rend2 — SAFE Point Shadow Clean Production
Дата: 2026-11-01. Windows x64 Single Player.

Уважаемый пользователь, это консервативное объединение принятого Texture &
Material Fidelity FINAL Clean Production (#41286257713) с ЕДИНСТВЕННЫМ
визуально доказанным исправлением точечной тени Boss1.
В нём НЕТ неподтверждённой универсальной системы выключения материалов.

ЧТО ИСПРАВЛЕНО
На Boss1 у прожектора устраняется гигантская сплошная тень от боковой части
корпуса; правильные тени крепления и стойки сохраняются. В проверочном GPU
A/B/A V3.2 (#41290226774) и V5 (#41294915333) этот эффект подтверждён.
В production не переносится номер 7232 как глобальный ID: проверяются карта,
точный capture origin, уникальный материал и реальные границы BSP-корпуса.
При несовпадении проверки тени рисуются оригинальным способом (fail-open).
Корпус видим в обычной сцене и отбрасывает тени от других источников.

ЧТО НЕ ОБЪЯВЛЕНО ИСПРАВЛЕННЫМ
Factory: широкая тень лестницы не исчезает при исключении двух парных
вертикальных стоек. Нет достаточного доказательства, что широкая проекция
является лишней, поэтому физические тени лестницы сохранены без вмешательства.

Crypt1/Crypt2: идентифицировано 10–18 полигонов нижней чаши и 16 вертикальных
панелей светильника; исключение чаши или всей конструкции изменяет тёмный
восьмиугольник, но может удалять физически обоснованные тени и вызывать
резкие локальные засветки. Состояние освещения заметно колебалось между
vid_restart и кадрами. Неподтверждённый алгоритм подавления НЕ внедрён.
Обе карты сохраняют прежнее поведение до отдельного обоснованного решения.

ЧТО СОХРАНЕНО
Accepted Texture/Material V2 (не V3/V3.1/V3.2), model-only Texture Fidelity,
model-only A2C, CAS, нейтральный analytic LUT strength 0, original BSP texture
sampling. Sun HDR16F, Bloom v2, ToneMap, SSGI, CSM, Fire/Tesla, Sky, Volumetric,
StaticPromote, лимит 32 lamps / 3 shadow slots и все пять CFG профилей
Performance/Balanced/Quality/High/Ultra — сохранены.
Все файлы прежнего принятого релиза, кроме renderer DLL и SHA индекса, побайтно
сохранены. Никаких новых telemetry/debug CVar, тестовых CFG, скрытых теневых
параметров или глобальных запретов материалов в новом рендерере нет.

УСТАНОВКА
1. Резервировать текущую игру и исходный DLL.
2. Распаковать архив в отдельную папку.
3. Скопировать свои лицензионные RTCW pak*.pk3 в Main.
4. Запуск: RUN_DARKWOLF_TEXTURE_MATERIAL_FINAL_CLEAN.bat из корня архива.
5. При желании выбрать профиль DW_HDR16F_V1_PERFORMANCE/BALANCED/QUALITY/
HIGH/ULTRA.cfg командой /exec и выполнить /vid_restart.
6. Возврат: восстановить DLL принятой сборки #41286257713.

ОГРАНИЧЕНИЕ ПРИЁМКИ
Этот Clean source rebuild прошёл CI, сверку бинарных форматов и архива.
Визуальная приёмка новой Clean DLL на пользовательском GPU отдельно не
проводилась; результат Boss1 опирается на предыдущий V3.2/V5 тест.
Формулировка «универсально устранены тени RTCW» здесь недопустима.

Источники: Actions #41019985033, #41286257713, #41290226774, #41294915333.
"""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--parent-artifact",required=True,type=Path)
    ap.add_argument("--renderer",required=True,type=Path)
    ap.add_argument("--proof",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    a=ap.parse_args()
    with zipfile.ZipFile(a.parent_artifact) as outer:
        assert outer.testzip() is None
        zipname="dist/"+PARENT_NAME+".zip"
        shaName=zipname+".sha256"
        assert zipname in outer.namelist() and shaName in outer.namelist()
        raw=outer.read(zipname)
        assert H(raw)==PARENT_ZIP_SHA
        assert H(raw)==outer.read(shaName).decode().split()[0]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        old={n[len(PARENT_NAME)+1:]:z.read(n) for n in z.namelist()
             if n.startswith(PARENT_NAME+"/") and not n.endswith("/")}
    assert len(old)==61,len(old)
    assert H(old["renderer_sp_rend2_x64.dll"])==PARENT_DLL_SHA
    for n in ("ioWolfSP.x64.exe","cgame_sp_x64.dll","qagame_sp_x64.dll",
              "ui_sp_x64.dll","RUN_DARKWOLF_TEXTURE_MATERIAL_FINAL_CLEAN.bat"):
        assert n in old,n
    profile_names=["PERFORMANCE","BALANCED","QUALITY","HIGH","ULTRA"]
    for p in profile_names:
        assert "Main/DW_HDR16F_V1_"+p+".cfg" in old,p
    dll=a.renderer.read_bytes()
    assert dll[:2]==b"MZ" and len(dll)>2800000
    pe=struct.unpack_from("<I",dll,60)[0]
    assert dll[pe:pe+4]==b"PE\x00\x00"
    for feature in (
        b"DARKWOLF_BOSS1_PROVEN_SOURCE_LOCAL_FIX_CLEAN_PRODUCTION_V1",
        b"r_dwTextureFidelity",b"r_dwMaterialFidelity",b"r_dwA2C",
        b"r_dwCas",b"r_dwLut",b"_dwSunHalfRGBA16F",
        b"textures/metal_misc/ametal_m03dm"):
        assert feature in dll,("required native feature missing",feature)
    for banned in (b"r_dwPointV5ProofMode",b"r_dwPointV5ProofAudit",
                   b"r_dwPointV4Scan",b"r_dwPointV4Mode",
                   b"r_dwPointV3Mode",b"r_dwPointV31AutoAudit",
                   b"r_dwPointV32FixtureGuard",b"DW_PS_V5_SOURCE_LOCAL_SKIP",
                   b"DW_PS_V4_REPORT_OK",b"DW_PS_V32_GUARD_APPLIED"):
        assert banned not in dll,("diagnostic feature in production",banned)
    proof=json.loads(a.proof.read_text())
    assert proof["accepted_texture_clean_run"]==41286257713
    assert proof["no_new_cvars"] and proof["no_debug_or_telemetry"]
    assert proof["fire_tesla_csm_unmodified"]
    assert proof["stage11_full_coverage_except_one_proven_boss1_source_caster"]
    assert proof["modified_source_files"]==["SP/code/rend2/tr_backend.c"]

    files=dict(old)
    files["renderer_sp_rend2_x64.dll"]=dll
    files["README_POINT_SHADOW_SAFE_FINAL_CLEAN_RU.txt"]=README.encode("utf-8")
    manifest={
        "type":"FINAL_CLEAN_PRODUCTION_SAFE_CONSOLIDATION_NOT_UNIVERSAL_SHADOW_FIX",
        "date":"2026-11-01",
        "parent_accepted_texture_material_clean_run":41286257713,
        "parent_zip_sha256":PARENT_ZIP_SHA,
        "parent_renderer_sha256":PARENT_DLL_SHA,
        "new_renderer_sha256":H(dll),
        "parent_files_unchanged_except_renderer_and_checksums":59,
        "preserved_profiles":profile_names,
        "production_caster_rule":"one uniquely fingerprinted Boss1 point-light housing only",
        "hardcoded_world_surface_id":False,
        "global_material_exclusion":False,
        "unresolved":["Factory heavy ladder silhouette", "Crypt1 octagon", "Crypt2 octagon"],
        "excluded_diagnostics":"V1/V2/V3/V31/V32/V4/V5 shadow test controls and JSON telemetry",
        "new_debug_cvars":False,
        "renderer_gpu_validation":"NOT_RETESTED final compiled DLL; V3.2 and V5 source-local Boss1 source visually proven",
        "protections":"other-light shadows, CSM, Fire/Tesla, Sun, SSGI, 32 StaticPromote / 3 slots remain at accepted behavior",
        "source_audit":proof
    }
    files["docs/DW_POINT_SHADOW_SAFE_FINAL_CLEAN_MANIFEST.json"]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    for n in old:
        if n not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt"):
            assert files[n]==old[n],n
    assert len(files)==63,len(files)
    files["docs/SHA256SUMS.txt"]="".join(
         H(data)+"  "+n+"\n" for n,data in sorted(files.items())
         if n!="docs/SHA256SUMS.txt").encode("ascii")
    a.out.mkdir(parents=True,exist_ok=True)
    out=a.out/(NAME+".zip")
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for n,contents in sorted(files.items()):
            info=zipfile.ZipInfo(NAME+"/"+n,(2026,11,1,12,0,0))
            info.external_attr=0o100644<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,contents)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        contents={n[len(NAME)+1:]:z.read(n) for n in z.namelist()}
        for line in contents["docs/SHA256SUMS.txt"].decode().splitlines():
            sh,n=line.split("  ",1)
            assert sh==H(contents[n]),n
        assert len(contents)==63 and len(contents["docs/SHA256SUMS.txt"].splitlines())==62
        assert all(contents[n]==old[n] for n in old
                   if n not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt"))
    (a.out/(NAME+".zip.sha256")).write_text(H(out.read_bytes())+"  "+out.name+"\n")
    print("DW_POINT_SHADOW_SAFE_CLEAN_FINAL_ALL_PROFILES_AND_59_PARENT_FILES_PASS",H(out.read_bytes()),H(dll))

if __name__=="__main__":main()
