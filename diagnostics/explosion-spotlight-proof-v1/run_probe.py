#!/usr/bin/env python3
from pathlib import Path
import os, shutil, subprocess, json

runtime=Path("runtime").resolve()
evidence=Path("evidence"); evidence.mkdir(exist_ok=True)
exe=next(p for p in runtime.iterdir() if p.is_file() and p.name.lower().startswith("iowolfsp"))
exe.chmod(0o755)

cases=[
 ("swf_explosions","swf",["setviewpos 2280 -64 570 0"]),
 ("rocket_explosions","rocket",["setviewpos -1700 1920 300 180"]),
 ("dam_spotlight","dam",[]),
]
summary={}
for label,mapname,setup in cases:
    home=Path(f"home-{label}").resolve()
    (home/"main").mkdir(parents=True,exist_ok=True)
    cfg=[
      "set developer 1","set logfile 2","set cg_draw2D 0",
      "set r_dlightShadowMaxLights 3","set r_dlightMode 2","set r_volumetricLocal 1",
      "wait 100",*setup,"wait 20",
      f"echo DWPROOF_CASE_BEGIN_{label}",
      f"screenshot {label}_pre",
      "wait 220",f"screenshot {label}_flash",
      "wait 380",f"screenshot {label}_post",
      f"echo DWPROOF_CASE_END_{label}","quit"
    ]
    (runtime/"main"/"proof.cfg").write_text("\n".join(cfg)+"\n")
    args=[str(exe),"+set","fs_basepath",str(runtime),"+set","fs_homepath",str(home),
          "+set","com_introplayed","1","+set","dw_testAutomation","1",
          "+set","vm_game","0","+set","vm_cgame","0","+set","vm_ui","0",
          "+set","r_renderer","rend2","+set","cl_renderer","rend2",
          "+set","r_fullscreen","0","+set","r_mode","-1","+set","r_customwidth","960","+set","r_customheight","540",
          "+set","r_swapInterval","0","+set","com_maxfps","76","+spdevmap",mapname,"+wait","60","+exec","proof.cfg"]
    env=dict(os.environ,LIBGL_ALWAYS_SOFTWARE="1")
    proc=evidence/f"{label}-process.log"
    with proc.open("w") as out:
        rc=subprocess.run(["xvfb-run","-a","timeout","-k","10s","360s",*args],env=env,stdout=out,stderr=subprocess.STDOUT).returncode
    logs=list(home.rglob("*console.log"))
    if not logs: raise AssertionError((label,"missing console"))
    qtext=logs[0].read_text(errors="replace")
    ptext=proc.read_text(errors="replace")
    text=qtext+"\n"+ptext
    (evidence/f"{label}-qconsole.log").write_text(qtext)
    for shot in home.rglob(f"{label}_*.tga"): shutil.copy2(shot,evidence/shot.name)
    assert rc==0,(label,rc)
    assert f"DWPROOF_CASE_BEGIN_{label}" in text
    assert f"DWPROOF_CASE_END_{label}" in text

    if mapname=="swf":
        assert "DWPROOF_SERVER_ENTITY kind=gas" in text
        for profile in (4,5,8):
            assert f"DWPROOF_CGAME_BLAST profile={profile}" in text,(label,profile,"no cgame blast")
        assert text.count("DWPROOF_RENDERER_DLIGHT transientBlast=1") >= 3
        assert text.count("DWPROOF_RENDERER_CLASS transientBlast=1") >= 3
        summary[label]={"gas_actual_entity":"PASS","radio_profile_runtime":"PASS","me109_profile_runtime":"PASS","renderer_shadow_class":"PASS"}
    elif mapname=="rocket":
        assert "DWPROOF_SERVER_ENTITY kind=v2" in text
        assert "DWPROOF_SERVER_ENTITY kind=alarm" in text
        for profile in (6,7):
            assert f"DWPROOF_CGAME_BLAST profile={profile}" in text,(label,profile,"no cgame blast")
        assert text.count("DWPROOF_RENDERER_DLIGHT transientBlast=1") >= 2
        assert text.count("DWPROOF_RENDERER_CLASS transientBlast=1") >= 2
        summary[label]={"v2_actual_entity":"PASS","alarm_actual_entity":"PASS","renderer_shadow_class":"PASS"}
    else:
        assert "DWPROOF_SPOTLIGHT_ALIVE_SUBMIT" in text,(label,"no alive submit")
        assert "DWPROOF_RENDERER_SPOT_LOCALVOL_ACCEPT" in text,(label,"no renderer alive localvol")
        assert "DWPROOF_SERVER_SPOTLIGHT_DEAD" in text,(label,"spotlight not killed")
        assert "DWPROOF_SPOTLIGHT_DEAD_SUPPRESS" in text,(label,"dead halo not suppressed")
        summary[label]={"alive_localvol":"PASS","dead_halo_suppression":"PASS"}

(evidence/"runtime-proof-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2))
