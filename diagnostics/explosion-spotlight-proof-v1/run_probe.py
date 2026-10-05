#!/usr/bin/env python3
from pathlib import Path
import os, shutil, subprocess, json

runtime=Path("runtime").resolve()
evidence=Path("evidence"); evidence.mkdir(exist_ok=True)
exe=next(p for p in runtime.iterdir() if p.is_file() and p.name.lower().startswith("iowolfsp"))
exe.chmod(0o755)

cases=[
 ("swf_gas","swf",1,["setviewpos 2280 -64 570 0"],4,"gas"),
 ("rocket_v2","rocket",2,["setviewpos -1700 1920 300 180"],6,"v2"),
 ("rocket_alarm","rocket",3,["setviewpos 1450 -4 210 0"],7,"alarm"),
 ("dam_spotlight","dam",4,[],None,"spotlight"),
 ("radio_profile","swf",5,["setviewpos 2280 -64 570 0"],5,"radio_profile"),
 ("me109_profile","swf",6,["setviewpos 2280 -64 570 0"],8,"me109_profile"),
]

summary={}
for label,mapname,mode,setup,profile,kind in cases:
    home=Path(f"home-{label}").resolve()
    (home/"main").mkdir(parents=True,exist_ok=True)
    cfg=[
      "set developer 1","set logfile 2","set cg_draw2D 0",
      "set r_dlightShadowMaxLights 3","set r_dlightMode 2","set r_volumetricLocal 1",
      "wait 140",*setup,"wait 40",
      f"echo DWPROOF_CASE_BEGIN_{label}",
      f"screenshot {label}_pre",
      "wait 20",
      "set dw_explosionProofFire 1",
      "wait 30",
      f"screenshot {label}_flash",
      "set dw_explosionProofFire 0",
      "wait 80",
      f"screenshot {label}_post",
      f"echo DWPROOF_CASE_END_{label}","quit"
    ]
    (runtime/"main"/"proof.cfg").write_text("\n".join(cfg)+"\n")
    args=[str(exe),"+set","fs_basepath",str(runtime),"+set","fs_homepath",str(home),
          "+set","developer","1","+set","com_introplayed","1","+set","dw_testAutomation","1",
          "+set","dw_explosionProofLab","1","+set","dw_explosionProofMode",str(mode),"+set","dw_explosionProofFire","0",
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
    assert "DWPROOF_SERVER_HEARTBEAT" in text,(label,"no qagame heartbeat")
    assert f"DWPROOF_SERVER_TRIGGER map={mapname} mode={mode}" in text,(label,"server trigger missing")
    assert f"DWPROOF_SERVER_ENTITY kind={kind}" in text,(label,"target entity/profile missing")

    if profile is not None:
        assert f"DWPROOF_CGAME_BLAST profile={profile}" in text,(label,profile,"no cgame blast")
        assert "DWPROOF_RENDERER_DLIGHT transientBlast=1" in text,(label,"renderer dlight missing")
        assert "DWPROOF_RENDERER_CLASS transientBlast=1" in text,(label,"renderer shadow class missing")
        summary[label]={"entity_or_profile":"PASS","cgame_profile":profile,"renderer_dlight":"PASS","shadow_class":"TRANSIENT_EXPLOSION"}
    else:
        assert "DWPROOF_SPOTLIGHT_ALIVE_SUBMIT" in text,(label,"no alive LocalVol submit")
        assert "DWPROOF_RENDERER_SPOT_LOCALVOL_ACCEPT" in text,(label,"renderer never accepted alive LocalVol")
        assert "DWPROOF_SERVER_SPOTLIGHT_DEAD" in text,(label,"spotlight did not enter dead state")
        assert "DWPROOF_SPOTLIGHT_DEAD_SUPPRESS" in text,(label,"dead LocalVol was not suppressed")
        summary[label]={"alive_localvol":"PASS","renderer_alive_accept":"PASS","dead_state":"PASS","dead_halo_suppression":"PASS"}

(evidence/"runtime-proof-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2))
