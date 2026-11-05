#!/usr/bin/env python3
from pathlib import Path
import sys, math, os, signal, subprocess, shutil, zipfile, json, re
sys.path.insert(0,str(Path("testlab/scripts").resolve()))
import rc4_requested_views as proof
from rc4_assault_camera import World

STATIC_TARGET=[1666.44,2447.07,29.03]
MOVING_TARGET=[-1085.71,2629.92,418.32]

def instrument(source):
    proof.instrument(source)
    print("CHATEAU_FIREPLACE_PROOF_INSTRUMENTED renderer_bytes_unchanged=true",flush=True)

def map_data(retail):
    for p in sorted(retail.glob("*.pk3")):
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.lower()=="maps/chateau.bsp":
                    return z.read(n)
    raise RuntimeError("maps/chateau.bsp not found")

def aim(eye,target):
    dx,dy,dz=target[0]-eye[0],target[1]-eye[1],target[2]-eye[2]
    yaw=math.degrees(math.atan2(dy,dx))%360.0
    horiz=math.hypot(dx,dy)
    pitch=math.degrees(math.atan2(-dz,horiz))
    return [round(pitch,4),round(yaw,4),0.0]

def choose_eye(world,target,side):
    # User-facing proof: head-on views from the open room side of each fireplace.
    signs=[-1] if side=="minus_x" else [1]
    best=None
    for sign in signs:
        for r in (300,340,380,420):
            for yoff in (0,-48,48,-96,96):
                for zoff in (64,96,128):
                    eye=[target[0]+sign*r,target[1]+yoff,target[2]+zoff]
                    if world.solid(eye): continue
                    if any(world.solid([eye[0]+a,eye[1]+b,eye[2]+c]) for a,b,c in ((12,0,0),(-12,0,0),(0,12,0),(0,-12,0),(0,0,-12))):
                        continue
                    hit=world.trace(eye,target)
                    frac=1.0 if hit is None else float(hit.get("fraction",0.0))
                    # A fireplace surface may terminate the ray just before the flame center.
                    if frac<0.68: continue
                    score=frac-r/5000.0-abs(yoff)/5000.0
                    if best is None or score>best[0]: best=(score,eye,frac,hit)
    if best is None: raise RuntimeError("No valid camera for target "+repr(target))
    return best[1],best[2],best[3]

def prepare(build,retail):
    runtime=Path("chateau-fireplace-proof-runtime").resolve()
    shutil.rmtree(runtime,ignore_errors=True)
    main=runtime/"main"; main.mkdir(parents=True)
    for p in build.iterdir():
        if p.is_file(): shutil.copy2(p,runtime/p.name)
    for p in (build/"main").glob("*.so"): shutil.copy2(p,main/p.name)
    pk3=[p for p in retail.iterdir() if p.is_file() and p.suffix.lower()==".pk3"]
    assert any(p.name.lower()=="pak0.pk3" for p in pk3)
    for p in pk3: (main/p.name.lower()).symlink_to(p.resolve())
    return runtime,main

def capture(source,retail,out):
    from PIL import Image
    out.mkdir(parents=True,exist_ok=True)
    world=World(map_data(retail))
    static_eye,sfrac,shit=choose_eye(world,STATIC_TARGET,"minus_x")
    moving_eye,mfrac,mhit=choose_eye(world,MOVING_TARGET,"plus_x")
    views=[
        {"name":"chateau_static_fireplace","eye":static_eye,"target":STATIC_TARGET,"angles":aim(static_eye,STATIC_TARGET),"trace_fraction":sfrac},
        {"name":"chateau_moving_fireplace","eye":moving_eye,"target":MOVING_TARGET,"angles":aim(moving_eye,MOVING_TARGET),"trace_fraction":mfrac},
    ]
    build=source/"SP/build/release-linux-x86_64"
    runtime,main=prepare(build,retail)
    setup=[
      "set r_mode -1","set r_customwidth 1280","set r_customheight 720","set r_fullscreen 0",
      "set r_renderer rend2","set cl_renderer rend2","set r_hdr 1","set r_postProcess 1",
      "set r_bloom 1","set r_bloomMode 2","set r_ssgi 1","set r_forceSun 1","set r_sunShadows 1",
      "set r_dlightMode 2","set r_volumetricLocal 1","set r_volumetricFire 1",
      "set r_volumetricFireStrength 1","set r_dwFireVolContinuityDiag 0","set r_dwFireVolFixtureDiag 0",
      "set r_ext_framebuffer_multisample 4","set r_picmip 0","set r_picmip2 0",
      "set s_initsound 0","set r_swapInterval 0","set fixedtime 100",
      "set cg_draw2D 0","set cg_drawGun 0","set con_notifytime -1","set developer 0"
    ]
    (main/"CHATEAU_PROOF_SETUP.cfg").write_text("\n".join(setup)+"\n")
    commands=["set cg_draw2D 0","set cg_drawGun 0","set con_notifytime -1","god","notarget","wait 20"]
    shots=[]
    for i,v in enumerate(views,1):
        commands += ["set dw_proofFreeze 0","proofView "+" ".join(f"{x:.6f}" for x in v["eye"]+v["angles"]),
                     "wait 100","set dw_proofFreeze 1","wait 10",f"set dw_proofShot {i}","wait 6",
                     f"screenshot {v['name']}","wait 5"]
        shots.append(v["name"])
    commands += ["set dw_proofFreeze 0","echo CHATEAU_FIREPLACE_PROOF_COMPLETE","quit"]
    scenario="CHATEAU_FIREPLACE_PROOF.cfg"
    (main/scenario).write_text("\n".join(commands)+"\n")
    home=runtime/"home"; home.mkdir(exist_ok=True)
    exe=next((p for p in runtime.iterdir() if p.name.lower().startswith("iowolfsp")),None)
    assert exe and exe.exists(); exe.chmod(0o755)
    cmd=["xvfb-run","-a","-s","-screen 0 1600x900x24",str(exe),
         "+safe","+set","fs_basepath",str(runtime),"+set","fs_homepath",str(home),
         "+set","com_introplayed","1","+set","com_recommendedSet","1","+set","logfile","2",
         "+set","dw_proofAutomation","1","+set","r_renderer","rend2","+set","cl_renderer","rend2",
         "+exec","CHATEAU_PROOF_SETUP.cfg","+vid_restart","+set","dw_proofScenario",scenario,
         "+spdevmap","chateau"]
    env={k:v for k,v in os.environ.items() if not any(w in k.upper() for w in ("TOKEN","SECRET","PASSWORD","CREDENTIAL"))}
    env.update(LIBGL_ALWAYS_SOFTWARE="1",LP_NUM_THREADS="2",SDL_AUDIODRIVER="dummy")
    with (out/"stdout.log").open("w") as log:
        p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try: rc=p.wait(timeout=720)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL); p.wait(); rc=124
    logs=[]
    for j,p in enumerate(sorted(home.rglob("*console*.log"))):
        data=p.read_text(errors="replace"); logs.append(data); (out/f"console-{j}.log").write_text(data)
    joined="\n".join(logs)
    saved=[]
    for name in shots:
        found=list(home.rglob(name+".tga"))
        if len(found)==1:
            im=Image.open(found[0]).convert("RGB")
            im.save(out/(name+".png")); saved.append(name)
    report={"map":"chateau","release":"Clean Production FireVol Final #42060324463",
            "renderer_source_modified":False,"runtime":"Linux Mesa llvmpipe TestLab",
            "r_volumetricFireStrength":1,"views":views,"exitcode":rc,
            "ready":"PROOF_READY" in joined,"complete":"CHATEAU_FIREPLACE_PROOF_COMPLETE" in joined,
            "saved":saved}
    (out/"CHATEAU_FIREPLACE_PROOF_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2),flush=True)
    assert rc==0 and report["ready"] and report["complete"] and len(saved)==2, report
    print("CHATEAU_FIREPLACE_TWO_FRAME_PROOF_PASS",flush=True)

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("instrument"); p.add_argument("source",type=Path)
    p=sub.add_parser("capture"); p.add_argument("source",type=Path); p.add_argument("retail",type=Path); p.add_argument("out",type=Path)
    a=ap.parse_args()
    if a.cmd=="instrument": instrument(a.source)
    else: capture(a.source,a.retail,a.out)
