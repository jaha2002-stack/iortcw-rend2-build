#!/usr/bin/env python3
"""Historical RC4 Bloom v2 + CSM Guard vs V05 at identical Crypt1 camera.
User-owned RTCW retail assets are never exported. TestLab camera probes only.
"""
from pathlib import Path
import json,os,sys,re,subprocess,signal
sys.path.insert(0,str(Path("testlab/scripts").resolve()))
import rc4_requested_views as proof
from crypt1_grate_closeup_ab_v05 import prepare,validate_cameras

VIEW={"name":"crypt1_grate_legacy_72_42",
      "eye":[-264.,1664.,512.125],"angles":[42.,180.,0.]}

def instrument(source):
    proof.instrument(source)
    print("LEGACY_RC4_CSM_GAME_CAMERA_INSTRUMENTED",flush=True)

def capture(source,retail,out):
    from PIL import Image,ImageDraw,ImageChops
    import numpy as np
    out.mkdir(parents=True,exist_ok=True)
    validate_cameras(retail)
    build=source/"SP/build/release-linux-x86_64"
    assert build.exists() and (build/"main").exists()
    runtime,main=prepare(build,retail)
    commands=[
      "set con_notifytime -1","set cg_draw2D 0","set cg_drawGun 0",
      "set cg_bobup 0","set cg_bobpitch 0","set cg_bobroll 0",
      "set r_autoExposure 0","set r_forceAutoExposure 0",
      "set r_forceSunPause 1","god","notarget","wait 12",
      "proofView "+" ".join(str(x) for x in VIEW["eye"]+VIEW["angles"]),
      "wait 45","set dw_proofFreeze 1","wait 8",
      "set dw_proofShot 1","wait 4","screenshot crypt1_rc4_bloom_csm_closeup",
      "wait 10","set dw_proofShot 2","wait 4","screenshot crypt1_rc4_bloom_csm_closeup_repeat",
      "set dw_proofFreeze 0","echo CRYPT1_LEGACY_RC4_CLOSEUP_COMPLETE","quit"
    ]
    (main/"CRYPT1_LEGACY_VIEW.cfg").write_text("\n".join(commands)+"\n")
    setup=[
      "set r_mode -1","set r_customwidth 1280","set r_customheight 720",
      "set r_fullscreen 0","set r_renderer rend2","set cl_renderer rend2",
      "set r_hdr 1","set r_postProcess 1","set r_bloom 1","set r_bloomMode 2",
      "set r_ssgi 1","set r_forceSun 1","set r_sunShadows 1",
      "set r_dlightMode 2","set r_dlightShadowStrength 0.88",
      "set r_dlightShadowFilter 2","set r_lightmap 0",
      "set r_volumetricSun 1","set r_volumetricLocal 1","set r_volumetricFire 1",
      "set r_ext_framebuffer_multisample 4","set r_picmip 0","set r_picmip2 0",
      "set s_initsound 0","set r_swapInterval 0","set fixedtime 100",
      "set cg_draw2D 0","set con_notifytime -1"
    ]
    (main/"CRYPT1_LEGACY_SETUP.cfg").write_text("\n".join(setup)+"\n")
    home=runtime/"home";home.mkdir(exist_ok=True)
    exe=next((x for x in runtime.iterdir() if x.name.lower().startswith("iowolfsp")),None)
    assert exe and exe.exists()
    exe.chmod(0o755)
    cmd=["xvfb-run","-a","-s","-screen 0 1600x900x24",str(exe),
      "+safe","+set","fs_basepath",str(runtime),"+set","fs_homepath",str(home),
      "+set","com_introplayed","1","+set","com_recommendedSet","1",
      "+set","logfile","2","+set","dw_proofAutomation","1",
      "+set","r_renderer","rend2","+set","cl_renderer","rend2",
      "+exec","CRYPT1_LEGACY_SETUP.cfg","+vid_restart",
      "+set","dw_proofScenario","CRYPT1_LEGACY_VIEW.cfg","+spdevmap","crypt1"]
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ("TOKEN","SECRET","PASSWORD","CREDENTIAL"))}
    env.update(LIBGL_ALWAYS_SOFTWARE="1",LP_NUM_THREADS="2",SDL_AUDIODRIVER="dummy")
    with (out/"legacy-stdout.log").open("w") as log:
        proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try:code=proc.wait(timeout=420)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=124
    logs=[]
    for k,p in enumerate(sorted(home.rglob("*console*.log"))):
        s=p.read_text(errors="replace");logs.append(s)
        (out/f"legacy-console-{k}.log").write_text(s)
    combined="\n".join(logs)
    captures=[]
    for name in ("crypt1_rc4_bloom_csm_closeup","crypt1_rc4_bloom_csm_closeup_repeat"):
        items=list(home.rglob(name+".tga"))
        if len(items)==1:
            im=Image.open(items[0]).convert("RGB")
            im.save(out/(name+".png"))
            captures.append(name)
    pos=re.findall(r"PROOF_VIEW shot=(\d+) time=\d+ eye=([^ ]+) forward=([^ ]+) weapon=(\d+)",combined)
    (out/"LEGACY_CRYPT1_CLOSEUP_STATUS.json").write_text(json.dumps(
       {"process_exit":code,"ready":"PROOF_READY" in combined,
        "complete":"CRYPT1_LEGACY_RC4_CLOSEUP_COMPLETE" in combined,
        "camera_proof":pos,"captured":captures,
        "legacy_renderer":"RC4 Bloom v2 original source + accepted CSM guard",
        "environment":"Linux Mesa llvmpipe, not Windows RTX"},indent=2)+"\n")
    assert code==0 and "PROOF_READY" in combined and "CRYPT1_LEGACY_RC4_CLOSEUP_COMPLETE" in combined,(code,combined[-2500:])
    assert len(captures)==2 and len(pos)==2,(captures,pos)
    assert pos[0][2:]==pos[1][2:],"Camera/weapon changed!"
    base=np.asarray(Image.open(out/(captures[0]+".png")))
    repeat=np.asarray(Image.open(out/(captures[1]+".png")))
    assert np.array_equal(base,repeat),"Legacy baseline not deterministic"
    print("CRYPT1_LEGACY_BLOOM_V2_CSM_CLOSEUP_CAPTURE_PASS",flush=True)

def compare(old,master,out):
    from PIL import Image,ImageDraw
    import numpy as np
    a=Image.open(old/"crypt1_rc4_bloom_csm_closeup.png").convert("RGB")
    b=Image.open(master/"crypt1_grate_near72_pitch42_baseline.png").convert("RGB")
    assert a.size==b.size==(1280,720)
    p=np.asarray(a,dtype=np.int16);q=np.asarray(b,dtype=np.int16)
    diff=np.abs(p-q)
    report={
       "camera":"Crypt1 -264 1664 512.125 yaw180 pitch42",
       "legacy_source":"Bloom V2 RC4 + CSM guard, no later Texture Fidelity/3FX/VisibleV03",
       "current_source":"FourWeek master + accepted LUT V05",
       "same_retained_map":"retail Crypt1 on protected TestLab Linux Mesa",
       "visual_accepted_by_windows_user":"legacy CSM overall lighting only, grille specifically NOT previously pixel-matched",
       "changed_pixels_pct":float(np.mean(np.any(diff>0,axis=2))*100),
       "mean_abs_rgb_delta":float(diff.mean()),
       "max_abs_rgb_delta":int(diff.max()),
       "camera_position_verified":"same explicit proofView in world coords; compare game proof logs",
       "quality_regression":"REQUIRES human visual review of grate floor shadow edge contour"
    }
    (out/"CRYPT1_LEGACY_VS_V05_METRICS.json").write_text(json.dumps(report,indent=2)+"\n")
    W,H=800,450
    board=Image.new("RGB",(W*2,H+55),(20,20,20))
    d=ImageDraw.Draw(board)
    for i,(label,im) in enumerate((("Historical Bloom v2 + CSM Guard",a),("FourWeek Master + LUT V05",b))):
        im=im.resize((W,H),Image.Resampling.LANCZOS)
        board.paste(im,(i*W,55))
        d.text((i*W+14,15),label,fill=(255,255,255))
    board.save(out/"CRYPT1_GRATE_LEGACY_VS_V05_SAME_CAMERA.png")
    print("CRYPT1_LEGACY_VS_V05_COMPARE_PASS",json.dumps(report),flush=True)

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    subs=p.add_subparsers(dest="cmd",required=True)
    s=subs.add_parser("instrument");s.add_argument("source",type=Path)
    s=subs.add_parser("capture");s.add_argument("source",type=Path);s.add_argument("retail",type=Path);s.add_argument("out",type=Path)
    s=subs.add_parser("compare");s.add_argument("old",type=Path);s.add_argument("master",type=Path);s.add_argument("out",type=Path)
    a=p.parse_args()
    if a.cmd=="instrument":instrument(a.source)
    elif a.cmd=="capture":capture(a.source,a.retail,a.out)
    else:compare(a.old,a.master,a.out)
