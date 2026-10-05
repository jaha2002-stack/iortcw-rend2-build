#!/usr/bin/env python3
from pathlib import Path
import os, re, shutil, subprocess, json

runtime=Path("runtime").resolve()
evidence=Path("evidence"); evidence.mkdir(exist_ok=True)
exe=next(p for p in runtime.iterdir() if p.is_file() and p.name.lower().startswith("iowolfsp"))
exe.chmod(0o755)

cases=[
 ("swf_gas","swf",1,["setviewpos 2280 -64 570 0"]),
 ("rocket_v2","rocket",2,["setviewpos -1700 1920 300 180"]),
 ("rocket_alarm","rocket",3,["setviewpos 1450 -4 210 0"]),
 ("dam_spotlight","dam",4,[]),
 ("radio_profile","swf",5,["setviewpos 2060 -432 560 180"]),
 ("me109_profile","swf",6,["setviewpos 2060 -432 560 180"]),
]
summary={}
for label,mapname,mode,setup in cases:
    home=Path(f"home-{label}").resolve()
    (home/"main").mkdir(parents=True,exist_ok=True)
    cfg=[
      "set developer 1","set logfile 2","set cg_draw2D 0",
      "set r_dlightShadowMaxLights 3","set r_dlightMode 2","set r_volumetricLocal 1",
      "wait 160",*setup,"wait 20",
      f"echo DWPROOF_CASE_BEGIN_{label}",
      f"screenshot {label}_pre",
      "set dw_explosionProofFire 1",
      "wait 2",f"screenshot {label}_flash",
      "wait 50",f"screenshot {label}_post",
      f"echo DWPROOF_CASE_END_{label}","quit"
    ]
    (runtime/"main"/"proof.cfg").write_text("\n".join(cfg)+"\n")
    args=[str(exe),"+set","fs_basepath",str(runtime),"+set","fs_homepath",str(home),
          "+set","com_introplayed","1","+set","dw_testAutomation","1",
          "+set","dw_explosionProofLab","1","+set","dw_explosionProofMode",str(mode),
          "+set","dw_explosionProofFire","0","+set","r_renderer","rend2","+set","cl_renderer","rend2",
          "+set","r_fullscreen","0","+set","r_mode","-1","+set","r_customwidth","960","+set","r_customheight","540",
          "+set","r_swapInterval","0","+set","com_maxfps","76","+spdevmap",mapname,"+wait","60","+exec","proof.cfg"]
    env=dict(os.environ,LIBGL_ALWAYS_SOFTWARE="1")
    proc=evidence/f"{label}-process.log"
    with proc.open("w") as out:
        rc=subprocess.run(["xvfb-run","-a","timeout","-k","10s","360s",*args],env=env,stdout=out,stderr=subprocess.STDOUT).returncode
    logs=list(home.rglob("*console.log"))
    if not logs: raise AssertionError((label,"missing console"))
    text=logs[0].read_text(errors="replace")
    (evidence/f"{label}-qconsole.log").write_text(text)
    for shot in home.rglob(f"{label}_*.tga"): shutil.copy2(shot,evidence/shot.name)
    assert rc==0,(label,rc)
    assert f"DWPROOF_CASE_BEGIN_{label}" in text
    assert f"DWPROOF_CASE_END_{label}" in text
    assert "DWPROOF_SERVER_BEGIN" in text
    row={"map":mapname,"mode":mode}
    if mode in (1,2,3,5,6):
        assert "DWPROOF_CGAME_BLAST" in text,(label,"no cgame blast")
        assert "DWPROOF_RENDERER_DLIGHT transientBlast=1" in text,(label,"no renderer dlight")
        assert "DWPROOF_RENDERER_CLASS transientBlast=1" in text,(label,"no renderer class")
        profiles={1:4,2:6,3:7,5:5,6:8}
        assert f"DWPROOF_CGAME_BLAST profile={profiles[mode]}" in text,(label,"wrong profile")
        row["runtime_dlight"]="PASS"
        row["shadow_class"]="TRANSIENT_EXPLOSION"
    else:
        assert "DWPROOF_SPOTLIGHT_ALIVE_SUBMIT" in text,(label,"no alive spotlight submit")
        assert "DWPROOF_RENDERER_SPOT_LOCALVOL_ACCEPT" in text,(label,"renderer never accepted alive localvol")
        assert "DWPROOF_SERVER_SPOTLIGHT_DEAD" in text,(label,"spotlight not killed")
        assert "DWPROOF_SPOTLIGHT_DEAD_SUPPRESS" in text,(label,"dead state not suppressed")
        row["alive_localvol"]="PASS"
        row["dead_suppression"]="PASS"
    summary[label]=row

(evidence/"runtime-proof-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2))
