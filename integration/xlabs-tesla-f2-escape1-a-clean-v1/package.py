#!/usr/bin/env python3
"""Exact frozen #40640998083 CLEAN Win64 runtime + one production Rend2 DLL."""
import argparse,hashlib,io,json,re,struct,zipfile
from pathlib import Path
BASE_ARTIFACT_SHA="51b946bd21c7a80f9c4940612b61b01fcd7c83eccfb7e4684a681727764a9be6"
BASE_ZIP_SHA="d43a166c3f7c0b9ecb92767401c1617aecfea0337c137e28ae175b3d4db900b1"
BASE_DLL_SHA="1d27de162dff6328c1504781edd973fa286289101a0557a1012252d618804c47"
PATCH_SHA="78b377e8b45b969f541e82052130babc9db8918e07c92becd7f7fc10e0539a0f"
BASE_ROOT="DarkWolf_Sun3_FireE_Crypt1_Shadow_Fidelity_Clean_Production_Win64"
ROOT="DarkWolf_Sun3_FireE_Crypt1_TeslaX2_F2_Escape1A_Clean_Production_Win64"
H=lambda b:hashlib.sha256(b).hexdigest()
def pack(a):
 data=a.base_zip.read_bytes()
 assert H(data)==BASE_ZIP_SHA,("FROZEN_INNER_ARCHIVE_MISMATCH",H(data))
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  assert z.testzip() is None
  original={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
 assert len(original)==40 and {p.split("/")[0] for p in original}=={BASE_ROOT}
 files={p.split("/",1)[1]:b for p,b in original.items()}
 assert H(files["renderer_sp_rend2_x64.dll"])==BASE_DLL_SHA
 assert "ioWolfSP.x64.exe" in files and "Main/cgame_sp_x64.dll" in files
 oldexe=H(files["ioWolfSP.x64.exe"])
 oldgame=H(files["Main/cgame_sp_x64.dll"])
 dll=a.renderer.read_bytes()
 assert H(dll)!=BASE_DLL_SHA and len(dll)>2_000_000
 pe=struct.unpack_from("<I",dll,0x3c)[0]
 assert dll[:2]==b"MZ" and dll[pe:pe+4]==b"PE\x00\x00"
 assert struct.unpack_from("<H",dll,pe+4)[0]==0x8664
 for forbidden in (b"r_dwTeslaWorldCaptureXTest",b"r_dwTeslaWorldFilterTest",
                   b"r_dwEscape1NativeWorldMaskTest",b"r_dwMainSceneLightAuditOnce",
                   b"DW_MAIN_SCENE_AUDIT_V4"):
  assert forbidden not in dll,("TEST_CVAR_OR_TELEMETRY_IN_PRODUCTION_DLL",forbidden)
 patch=a.patch.read_bytes()
 assert H(patch)==PATCH_SHA
 for forbidden in (b"r_dwTeslaWorldFilterTest",b"r_dwTeslaWorldCaptureXTest",
                   b"r_dwEscape1NativeWorldMaskTest",b"r_dwMainSceneLightAuditOnce"):
  assert forbidden not in patch
 qa=json.loads(a.qa.read_text())
 assert qa["status"]=="DARKWOLF_X2_F2_ESCAPE1_A_FULL_GLSL_QA_PASS"
 assert qa["glsl_variants_passed"]==17
 assert qa["temp_cvars"]==[] and qa["engine_code_files_changed"]==5
 assert qa["crypt1_original_pcf_unchanged"] is True
 files["renderer_sp_rend2_x64.dll"]=dll
 files["docs/DARKWOLF_X2_F2_ESCAPE1_A_EXACT_SOURCE_DELTA.patch"]=patch
 readme="""DarkWolf Rend2 SP - Tesla X2 F2 + Escape1 A Clean Production
============================================================
Основа: проверенный в игре релиз #40640998083.

Xlabs: свет Tesla остаётся на прежней точке. Только архитектурная
cubemap захватывается из X2 (+64 по X). Границы теней обрабатываются
проверенным F2: signed CubeFace PCF 4x4 Tent. Старый PCF 2x2 на
Crypt1 и всех остальных картах не меняется.

Escape1: архитектурная защита добавлена только для подтверждённого
источника A (-1340, 692, -36). Источник B и остальные лампы не затронуты.
Исправлен размер буфера загрузки GLSL lightall до 65536 байт.

Sun3, Fire E, Local, CSM, SSGI, Sky, Bloom, CAS/LUT/A2C, материалы,
StaticPromote и бюджеты теней сохранены. EXE, CGame, QGame, UI DLL,
BAT и все настройки базового релиза побайтово идентичны #40640998083.
Новых CVAR, диагностических режимов и телеметрии нет.

Запуск: распакуйте отдельно от рабочей базы, добавьте оригинальные
легальные игровые PK3 и запустите RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat.
Чтобы повторно применить настройки Sun3/Fire E и containment:
    exec DW_CRYPT1_SHADOW_FIDELITY_PRODUCTION.cfg

Проверки пользователем: Crypt1 (решётка/PCF), Xlabs (синий свет,
тени и отсутствие световых утечек), Escape1 (стена печки снаружи и
внутри), SWF (три лампы), Sun3/Fire E, FPS при одинаковом ракурсе.
Сборка CI не заменяет испытания на видеокарте.
"""
 files["README_XLABS_TESLA_F2_X2_ESCAPE1_A_CLEAN_RU.txt"]=readme.encode("utf-8")
 manifest={
  "release_status":"CI_COMPILE_AND_STATIC_PASS_RUNTIME_USER_TEST_PENDING",
  "accepted_base_run":40640998083,
  "accepted_artifact_id":12796125440,
  "accepted_artifact_sha256":BASE_ARTIFACT_SHA,
  "accepted_inner_zip_sha256":BASE_ZIP_SHA,
  "source_delta_sha256":PATCH_SHA,
  "source_delta_allowlist":qa["source_allowlist"],
  "original_file_count":40,
  "original_byte_identical_count":38,
  "replaced_files":["renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt"],
  "original_exe_sha256_unchanged":oldexe,
  "original_cgame_sha256_unchanged":oldgame,
  "old_renderer_sha256":BASE_DLL_SHA,
  "new_renderer_sha256":H(dll),
  "xlabs_capture_offset_x":64,
  "xlabs_filter":"F2 signed OpenGL cube-face 4x4 tent",
  "escape1_only_source_A":[-1340,692,-36],
  "shader_loader_fp_capacity":65536,
  "diagnostic_cvars":[],
  "debug_telemetry":False,
  "performance_test_by_user":"PENDING",
  "full_shader_qa":qa}
 files["docs/XLABS_TESLA_X2_F2_ESCAPE1_A_CLEAN_PRODUCTION_MANIFEST.json"]=(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n").encode()
 files["docs/SHA256SUMS.txt"]="".join(H(b)+"  "+p+"\n" for p,b in sorted(files.items())
                               if p!="docs/SHA256SUMS.txt").encode("ascii")
 assert len(files)==43
 assert not any(re.search(r"(^|/)pak[0-9]*\.pk3$",p,re.I) for p in files)
 assert not any("DW_V5_" in p or "DW_V4_" in p or "DW_TEST_V" in p for p in files)
 a.out.mkdir(parents=True,exist_ok=True)
 target=a.out/(ROOT+".zip")
 with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
  for p,b in sorted(files.items()):
   info=zipfile.ZipInfo(ROOT+"/"+p,date_time=(2026,10,28,0,0,0))
   info.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(info,b)
 with zipfile.ZipFile(target) as z:
  assert z.testzip() is None
  final={name.split("/",1)[1]:z.read(name) for name in z.namelist()}
 assert len(final)==len(files)
 for name,b in original.items():
  p=name.split("/",1)[1]
  if p not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt"):
   assert final[p]==b,("ACCEPTED_BASE_FILE_CHANGED",p)
 assert H(final["renderer_sp_rend2_x64.dll"])==H(dll)
 for line in final["docs/SHA256SUMS.txt"].decode("ascii").splitlines():
  sha,name=line.split("  ",1)
  assert H(final[name])==sha,("INTERNAL_ZIP_SHA_MISMATCH",name)
 summary={
   "status":"DARKWOLF_TESLA_X2_F2_ESCAPE1_A_CLEAN_PACKAGE_PASS",
   "inner_zip_sha256":H(target.read_bytes()),
   "original_byte_identical_files":38,
   "file_count":43,
   "new_renderer_sha256":H(dll),
   "source_patch_sha256":PATCH_SHA,
   "runtime_status":"PENDING_USER_VISUAL_FPS_REGRESSION"}
 (a.out/"DARKWOLF_CLEAN_PRODUCTION_FINAL_AUDIT.json").write_text(json.dumps(summary,indent=2)+"\n")
 (a.out/(target.name+".sha256")).write_text(summary["inner_zip_sha256"]+"  "+target.name+"\n")
 print(summary["status"],target,summary["inner_zip_sha256"])
if __name__=="__main__":
 ap=argparse.ArgumentParser()
 for name in ("base-zip","renderer","patch","qa","out"):
  ap.add_argument("--"+name,type=Path,required=True)
 pack(ap.parse_args())
