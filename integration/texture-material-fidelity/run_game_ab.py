#!/usr/bin/env python3
"""Real ioRTCW/RC4 A/B screenshots. Same candidate binary, only opt-in CVars differ."""
from pathlib import Path
import json, math, os, re, shutil, signal, subprocess, sys, zipfile
from PIL import Image, ImageDraw, ImageChops
sys.path.insert(0, str(Path("testlab/scripts").resolve()))
import rc4_requested_views as photo
from rc4_assault_camera import World

MAPS = ("factory", "escape1", "assault")
PROFILE = {
 "OFF": ("0", "0"),
 "ON": ("1", "1")
}

def sh(args, **kwargs):
    print("COMMAND", " ".join(map(str,args)), flush=True)
    return subprocess.run(args, check=True, **kwargs)

def build(root, out):
    photo.instrument(root)
    log=out/"linux-build.log"
    with log.open("w") as f:
        p=subprocess.run(["make","-C",str(root/"SP"),"-j2","release",
            "VERSION=1.51d-SP-DarkWolf-TextureFidelity-Test",
            "BUILD_CLIENT=1","BUILD_SERVER=0","BUILD_GAME_SO=1",
            "BUILD_GAME_QVM=0","BUILD_BASEGAME=1","BUILD_RENDERER_REND2=1",
            "USE_RENDERER_DLOPEN=1"],stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:
        print(log.read_text(errors="replace")[-8000:],flush=True)
        raise RuntimeError("Linux renderer build failed")
    return root/"SP/build/release-linux-x86_64"

def maps_from(retail, mapname):
    name=f"maps/{mapname}.bsp"
    for pk3 in retail.glob("*.pk3"):
        with zipfile.ZipFile(pk3) as z:
            match=next((n for n in z.namelist() if n.lower()==name),None)
            if match:
                return z.read(match)
    raise RuntimeError("Missing protected BSP "+name)

def camera_views(retail, name):
    if name=="factory":
        views=photo.views("factory")
        return [dict(v) for v in views]
    if name=="assault":
        # Established RC4 sunlit viewpoints from photo mode, verified as free space.
        views=photo.views("assault")
        world=World(maps_from(retail,name))
        valid=[v for v in views if not world.solid(v["eye"])]
        if not valid:
            raise RuntimeError("Assault photo-mode camera poses are obstructed")
        return valid[:2]
    world=World(maps_from(retail,name))
    targets=[
      ("escape1_furnace",[-1226.,602.,-64.]),
      ("escape1_lamp",[-1076.,1172.,96.]),
      ("escape1_tesla",[328.,448.,-532.])
    ]
    result=[]
    for label,t in targets:
        selection=None
        for radius in (128,176,224,288):
            for dz in (0,48,-48,96):
                for deg in range(0,360,30):
                    ang=math.radians(deg)
                    eye=[t[0]+radius*math.cos(ang),t[1]+radius*math.sin(ang),t[2]+dz]
                    if world.solid(eye):
                        continue
                    if not world.trace(eye,t): # helper may return boolean
                        pass
                    d=[t[i]-eye[i] for i in range(3)]
                    pitch=-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1])))
                    yaw=math.degrees(math.atan2(d[1],d[0]))%360
                    selection={"name":label,"eye":eye,"angles":[pitch,yaw,0.]}
                    break
                if selection: break
            if selection: break
        if selection:result.append(selection)
    if len(result)<2:raise RuntimeError("No verifiable Escape1 camera viewpoints")
    return result[:3]

def prepare_runtime(build,retail,out):
    runtime=Path("fidelity-runtime").resolve()
    shutil.rmtree(runtime,ignore_errors=True)
    main=runtime/"main";main.mkdir(parents=True)
    for p in build.iterdir():
        if p.is_file():shutil.copy2(p,runtime/p.name)
    for p in (build/"main").glob("*.so"):shutil.copy2(p,main/p.name)
    for p in retail.glob("*.pk3"):
        (main/p.name.lower()).symlink_to(p.resolve())
    prod=Path("integration/optimized-v4-4-6")
    for p in [prod/"PRODUCTION_HIGH_QUALITY.cfg",prod/"payload/Main/darkwolf_ignition_rc_v0_6.pk3"]:
        if p.exists():shutil.copy2(p,main/p.name)
    if not (main/"PRODUCTION_HIGH_QUALITY.cfg").exists():
        raise RuntimeError("Production high-quality profile missing")
    return runtime,main

def one_run(runtime,main,retail,mapname,mode,views,out):
    prefix=f"{mapname}_{mode}"
    scenario=f"DW_FIDELITY_AB_{prefix}.cfg"
    camera_cmds=["set con_notifytime -1","set cg_draw2D 0","set cg_drawGun 1",
        "set cg_bobup 0","set cg_bobpitch 0","set cg_bobroll 0",
        "set r_autoExposure 0","set r_forceAutoExposure 0",
        "set r_forceSunPause 1","god","notarget","give all","wait 12","weapon 3","wait 10"]
    for idx,v in enumerate(views):
        x=v["eye"]+v["angles"]
        shot=f"{prefix}_{v['name']}"
        camera_cmds+=["set dw_proofFreeze 0",
                      "proofView "+" ".join(f"{t:.6f}" for t in x),
                      "wait 14","set dw_proofFreeze 1","wait 3",
                      f"set dw_proofShot {idx+1}","wait 4",
                      f"screenshot {shot}","wait 2"]
    camera_cmds+=["set dw_proofFreeze 0","echo DW_FIDELITY_AB_COMPLETE","quit"]
    (main/scenario).write_text("\n".join(camera_cmds)+"\n")
    setup=["exec PRODUCTION_HIGH_QUALITY.cfg",
      "set r_mode -1","set r_customwidth 1280","set r_customheight 720",
      "set r_fullscreen 0","set r_renderer rend2","set cl_renderer rend2",
      "set r_ssgi 1","set r_volumetricSun 1","set r_volumetricLocal 1",
      "set r_volumetricFire 1","set r_forceSun 1","set r_dlightMode 2",
      "set r_picmip 0","set r_picmip2 0",
      "set r_ext_texture_filter_anisotropic 1","set r_ext_max_anisotropy 8",
      "set r_textureMode GL_LINEAR_MIPMAP_LINEAR",
      "set r_imageUpsample 0","set r_dwAdaptiveUpsample 1",
      "set r_dwCutoutMip 1",
      "set r_dwTextureFidelity "+PROFILE[mode][0],
      "set r_dwMaterialFidelity "+PROFILE[mode][1],
      "set s_initsound 0","set r_swapInterval 0","set fixedtime 100"]
    conf=f"DW_FIDELITY_SETUP_{mode}.cfg"
    (main/conf).write_text("\n".join(setup)+"\n")
    home=(runtime/f"home-{prefix}");home.mkdir(exist_ok=True)
    exe=next(p for p in runtime.iterdir() if p.name.lower().startswith("iowolfsp"))
    exe.chmod(0o755)
    cmd=["xvfb-run","-a",str(exe),"+safe","+set","fs_basepath",str(runtime),
        "+set","fs_homepath",str(home),"+set","com_introplayed","1",
        "+set","com_recommendedSet","1","+set","logfile","2",
        "+set","dw_proofAutomation","1","+set","r_renderer","rend2",
        "+set","cl_renderer","rend2","+exec",conf,"+vid_restart",
        "+set","dw_proofScenario",scenario,"+spdevmap",mapname]
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ("TOKEN","SECRET","PASSWORD","CREDENTIAL"))}
    env.update(LIBGL_ALWAYS_SOFTWARE="1",LP_NUM_THREADS="2")
    with (out/f"{prefix}-stdout.log").open("w") as f:
        proc=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try:code=proc.wait(timeout=540)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=124
    logs=[]
    for i,p in enumerate(home.rglob("*console*.log")):
        t=p.read_text(errors="replace")
        (out/f"{prefix}-console-{i}.log").write_text(t)
        logs.append(t)
    log="\n".join(logs)
    report={"exit":code,"ready":"PROOF_READY" in log,"complete":"DW_FIDELITY_AB_COMPLETE" in log,"images":{}}
    for v in views:
        name=f"{prefix}_{v['name']}"
        found=list(home.rglob(name+".tga"))
        if len(found)==1:
            img=Image.open(found[0]).convert("RGB")
            png=out/(name+".png");img.save(png)
            report["images"][v["name"]]=png.name
    matches=re.findall(r"PROOF_VIEW shot=(\d+) time=\d+ eye=([^ ]+) forward=([^ ]+) weapon=(\d+)",log)
    report["probes"]=[{"shot":int(v[0]),"eye":v[1],"forward":v[2],"weapon":v[3]} for v in matches]
    (out/f"{prefix}-result.json").write_text(json.dumps(report,indent=2)+"\n")
    if not (code==0 and report["ready"] and report["complete"] and len(report["images"])==len(views)):
        raise RuntimeError(f"Incomplete {prefix} runtime: "+json.dumps(report))
    return report

def compare(out,maps,results):
    pairs=[]
    thumb=(640,360)
    all_views=sum(len(views) for views in maps.values())
    canvas=Image.new("RGB",(thumb[0]*2,(thumb[1]+55)*all_views),(20,20,20))
    draw=ImageDraw.Draw(canvas)
    row=0
    for mapname,views in maps.items():
        a=results[mapname]["OFF"];b=results[mapname]["ON"]
        assert len(a["probes"])==len(b["probes"])==len(views)
        for i,v in enumerate(views):
            off=a["probes"][i];on=b["probes"][i]
            assert off["eye"]==on["eye"] and off["forward"]==on["forward"],(mapname,v["name"],"camera mismatch")
            assert off["weapon"]==on["weapon"],"weapon not matched"
            left=Image.open(out/a["images"][v["name"]]).convert("RGB")
            right=Image.open(out/b["images"][v["name"]]).convert("RGB")
            assert left.size==right.size
            difference=ImageChops.difference(left,right)
            bbox=difference.getbbox()
            summary={"map":mapname,"view":v["name"],"off":a["images"][v["name"]],
                     "on":b["images"][v["name"]],"changed":bool(bbox),
                     "identical_camera":True,"identical_weapon":True,
                     "diff_bbox":list(bbox) if bbox else None}
            pairs.append(summary)
            y=row*(thumb[1]+55)
            draw.text((10,y+10),f"{mapname} | {v['name']} | OFF",fill="white")
            draw.text((thumb[0]+10,y+10),"ON: texture and materials",fill="white")
            for x,im in ((0,left),(thumb[0],right)):
                im.thumbnail(thumb)
                canvas.paste(im,(x,y+55))
            row+=1
    canvas.save(out/"DARKWOLF_TEXTURE_MATERIAL_AB.png")
    report={"base_run":38798189322,"csm_guard_run":39152821574,
            "candidate_build_run":39159770141,"runtime":"real RTCW map assets + Linux Mesa",
            "windows_gaming_gpu_fps":"NOT_RUN","visual_acceptance":"PENDING_USER_REVIEW",
            "same_renderer_executable":True,"all_other_effects_left_enabled":True,
            "pairs":pairs}
    (out/"AB_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2),flush=True)

def main():
    root=Path(sys.argv[1]).resolve()
    retail=Path(sys.argv[2]).resolve()
    out=Path(sys.argv[3]).resolve();out.mkdir(parents=True,exist_ok=True)
    builddir=build(root,out)
    rt,main=prepare_runtime(builddir,retail,out)
    maps={name:camera_views(retail,name) for name in MAPS}
    (out/"CAMERAS.json").write_text(json.dumps(maps,indent=2)+"\n")
    results={}
    for name,views in maps.items():
        results[name]={}
        for mode in ("OFF","ON"):
            results[name][mode]=one_run(rt,main,retail,name,mode,views,out)
    compare(out,maps,results)

if __name__=="__main__":main()
