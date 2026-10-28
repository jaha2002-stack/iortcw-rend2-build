#!/usr/bin/env python3
"""Repack byte-exact #40683914514 as isolated one-EXE Xlabs snapshot TEST."""
from pathlib import Path
import argparse,hashlib,json,struct,zipfile,re,io
H=lambda x:hashlib.sha256(x).hexdigest()
BASE_SHA="5527c6725b02fc067ef652f4aa2346342804b04a7f3d0a972c8b9d8d506d5e92"
BASE_EXE_SHA="c8dba37ee2eb3aa902083dfa6f99c203f37fb1dcf766c5a63bf91911b5ef8e5a"
BASE_RENDERER_SHA="f15d93af7e57c6fb94066a4c1ab5974e40a8850b7e84acab72193bc4ddc04ba2"
BASE_ROOT="DarkWolf_Sun3_FireE_Crypt1_TeslaX2_F2_Escape1A_Clean_Production_Win64"
OUT_ROOT="DarkWolf_Xlabs_Active_Tesla_Local_Snapshot_PVS_Test_V1_Win64"
p=argparse.ArgumentParser()
for v in ("base-zip","engine","proof","patch","qa","out"):p.add_argument("--"+v,required=True,type=Path)
a=p.parse_args()
data=a.base_zip.read_bytes()
assert H(data)==BASE_SHA,("BAD_FROZEN_406839_BASE",H(data))
with zipfile.ZipFile(io.BytesIO(data)) as z:
 assert z.testzip() is None
 original={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
assert len(original)==43 and {n.split("/")[0] for n in original}=={BASE_ROOT}
files={name.split("/",1)[1]:b for name,b in original.items()}
assert H(files["ioWolfSP.x64.exe"])==BASE_EXE_SHA
assert H(files["renderer_sp_rend2_x64.dll"])==BASE_RENDERER_SHA
original_game={k:H(files[k]) for k in ("Main/cgame_sp_x64.dll","Main/qagame_sp_x64.dll","Main/ui_sp_x64.dll")}
exe=a.engine.read_bytes()
assert H(exe)!=BASE_EXE_SHA and len(exe)>3_000_000
pe=struct.unpack_from("<I",exe,0x3c)[0]
assert exe[:2]==b"MZ" and exe[pe:pe+4]==b"PE\x00\x00"
assert struct.unpack_from("<H",exe,pe+4)[0]==0x8664
for marker in (b"sv_dwXlabsTeslaPvsRangeTest",b"sv_dwXlabsTeslaPvsAuditOnce",
               b"DW_XLABS_PVS_TEST_V1_BEGIN",b"DW_XLABS_PVS_TEST_V1_TESLA",
               b"DW_XLABS_PVS_TEST_V1_END"):
 assert marker in exe,("MISSING_SNAPSHOT_TEST_SYMBOL",marker)
proof=json.loads(a.proof.read_text())
qa=json.loads(a.qa.read_text())
assert proof["marker"]=="DARKWOLF_XLABS_LINKED_TESLA_NEAR_SNAPSHOT_PVS_TEST_V1_20261028"
assert proof["source_base_run"]==40683914514
assert proof["changed_source_files"]==["SP/code/server/sv_snapshot.c"]
assert proof["no_renderer_or_cgame_changes"] is True
assert qa["status"]=="DW_XLABS_PVS_TEST_V1_SOURCE_AND_SNAPSHOT_ELIGIBILITY_PASS"
assert qa["tested_predicate_combinations"]==15360
assert qa["no_broadcast_override"] is True
patch=a.patch.read_bytes()
assert H(patch)==proof["delta_patch_sha256"]
assert b"SP/code/server/sv_snapshot.c" in patch
assert not any(k in patch for k in (b"cg_xlabsTeslaDoorRadius",
                                    b"r_dlightWorldContainment",
                                    b"r_dlightShadowMaxLights"))
files["ioWolfSP.x64.exe"]=exe
files["docs/XLABS_ACTIVE_TESLA_LOCAL_SNAPSHOT_PVS_TEST_V1_SOURCE.patch"]=patch
files["README_XLABS_ACTIVE_TESLA_SNAPSHOT_PVS_TEST_V1_RU.txt"]="""DarkWolf Xlabs - локальное серверное исправление PVS, тест V1
=============================================================
ОСНОВА: полный неизменённый чистый релиз GitHub Actions #40683914514.
ОТЛИЧИЕ ОТ БАЗЫ: только ioWolfSP.x64.exe (серверный snapshot).
Все оригинальные DLL, CFG, BAT и визуальные эффекты сохранены побайтово.
Это ТЕСТОВАЯ, НЕ production сборка. Два дополнительных CVAR не архивируются.

ПРОБЛЕМА: при переходе игрока между соседними BSP-кластерами на Xlabs
у одной из трёх дверей исчезают одновременно разряды Tesla и синий свет.

ИСПРАВЛЕНИЕ: движок передаёт в snapshot только связанные (активные)
ET_TESLA_EF, если ближайшая точка их разряда находится в радиусе,
заданном тестовым параметром. Прочие объекты сохраняют обычный PVS.
Триггеры включения/выключения Tesla НЕ изменяются. Рендерер, GLSL,
F2 CubeFace, StaticPromote и количество динамических теней НЕ меняются.
Флаг глобальной рассылки SVF_BROADCAST НЕ добавлен.

ПРОВЕРКА (Xlabs, одно и то же сохранение, камера у трёх дверей):
  1. В точке, где дверь выключается, в консоли:
     sv_dwXlabsTeslaPvsRangeTest 0
     sv_dwXlabsTeslaPvsAuditOnce 1
     condump xlabs_pvs_v1_off.txt
     Снимок OFF, затем смещение 1-2 метра, наблюдение за разрядами.
  2. В той же точке:
     sv_dwXlabsTeslaPvsRangeTest 768
     sv_dwXlabsTeslaPvsAuditOnce 1
     condump xlabs_pvs_v1_768.txt
     Снимок ON, обход по двум соседним кластерам.
  3. Если разряды ещё пропадают:
     sv_dwXlabsTeslaPvsRangeTest 1024
     sv_dwXlabsTeslaPvsAuditOnce 1
     condump xlabs_pvs_v1_1024.txt
  4. Для возврата к исходному серверному поведению:
     sv_dwXlabsTeslaPvsRangeTest 0

CVAR меняется на лету, без vid_restart или map_restart.
Содержимое консоли между командами может включать предыдущие записи:
сохраняйте файлы с разными именами, ищите DW_XLABS_PVS_TEST_V1_BEGIN/END.

Пришлите три снимка (OFF, 768, 1024), логи консоли, информацию о
видимости всех трёх дверей и приблизительный FPS. Для критерия
успеха важны одновременно электрические разряды и синий свет.
Не запускать с загруженным старым qagame или cgame из других тестов.
Лицензионные PK3 RTCW в пакет не включены.
""".encode("utf-8")
manifest={
 "release_type":"TEST_ONLY_NOT_CLEAN_PRODUCTION",
 "frozen_parent_run":40683914514,
 "frozen_parent_zip_sha256":BASE_SHA,
 "frozen_parent_exe_sha256":BASE_EXE_SHA,
 "test_exe_sha256":H(exe),
 "unchanged_production_renderer_sha256":BASE_RENDERER_SHA,
 "original_production_game_modules_sha256":original_game,
 "original_file_count":43,
 "original_byte_identical":41,
 "replaced_original":["ioWolfSP.x64.exe","docs/SHA256SUMS.txt"],
 "added_test":["docs/XLABS_ACTIVE_TESLA_LOCAL_SNAPSHOT_PVS_TEST_V1_SOURCE.patch",
               "docs/XLABS_ACTIVE_TESLA_SNAPSHOT_PVS_TEST_V1_MANIFEST.json",
               "README_XLABS_ACTIVE_TESLA_SNAPSHOT_PVS_TEST_V1_RU.txt"],
 "new_cvars":["sv_dwXlabsTeslaPvsRangeTest","sv_dwXlabsTeslaPvsAuditOnce"],
 "source_proof":proof,
 "source_qa":qa,
 "runtime_visual_fps_regression":"PENDING_USER_TEST"}
files["docs/XLABS_ACTIVE_TESLA_SNAPSHOT_PVS_TEST_V1_MANIFEST.json"]=(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
files["docs/SHA256SUMS.txt"]="".join(H(v)+"  "+k+"\n" for k,v in sorted(files.items()) if k!="docs/SHA256SUMS.txt").encode("ascii")
assert len(files)==46
assert not any(re.search(r"(^|/)pak[0-9]*\.pk3$",k,re.I) for k in files)
a.out.mkdir(parents=True,exist_ok=True)
output=a.out/(OUT_ROOT+".zip")
with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
 for name,data in sorted(files.items()):
  info=zipfile.ZipInfo(OUT_ROOT+"/"+name,date_time=(2026,10,28,0,0,0))
  info.compress_type=zipfile.ZIP_DEFLATED
  z.writestr(info,data)
with zipfile.ZipFile(output) as z:
 assert z.testzip() is None
 assembled={name.split("/",1)[1]:z.read(name) for name in z.namelist()}
assert len(assembled)==46
for n,body in original.items():
 key=n.split("/",1)[1]
 if key not in ("ioWolfSP.x64.exe","docs/SHA256SUMS.txt"):
  assert assembled[key]==body,("PRODUCTION_REGRESSION",key)
for line in assembled["docs/SHA256SUMS.txt"].decode("ascii").splitlines():
 sha,k=line.split("  ",1)
 assert H(assembled[k])==sha,("INNER_SHA256_MISMATCH",k)
report={
 "status":"DW_XLABS_TESLA_PVS_TEST_V1_EXACT_PARENT_PACKAGE_PASS",
 "parent_run":40683914514,"parent_zip_sha256":BASE_SHA,
 "package_sha256":H(output.read_bytes()),"changed_existing_files":2,
 "original_byte_identical_files":41,"total_files":46,
 "modified_executable":"ioWolfSP.x64.exe",
 "new_cvars":manifest["new_cvars"],"GPU_TEST":"PENDING"}
(a.out/"XLABS_TESLA_PVS_TEST_V1_FINAL_AUDIT.json").write_text(json.dumps(report,indent=2)+"\n")
(a.out/(output.name+".sha256")).write_text(report["package_sha256"]+"  "+output.name+"\n")
print(report["status"],output,report["package_sha256"])
