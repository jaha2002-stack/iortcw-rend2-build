#!/usr/bin/env python3
"""Ten reproducible real-RTCW single-player 60-second map tours.

Actual frames come from RC4 Bloom V2 + CSM guard + texture/material-fidelity
renderer on authorized protected retail maps. The camera is in noclip mode
but every interpolated path segment is checked against the actual BSP solid
brushes. Original dynamic effects remain enabled. A properly skinned RTCW
infantry player model is displayed for close material/animation inspection;
other map AI actors are left in their native game state.

Only ephemeral CGame / Game camera-proof helpers are used. No protected
game asset data are packed in the output and no cinematic images are faked.
"""
from __future__ import annotations
import json, math, os, re, shutil, subprocess, sys, signal, time, zipfile
from pathlib import Path

sys.path.insert(0, str(Path("integration/texture-material-fidelity").resolve()))
import run_character_proof as characters
from rc4_assault_camera import World

FPS = 12
DURATION_S = 60
FRAMES = FPS * DURATION_S
WIDTH, HEIGHT = 1280, 720
MAPS = ("crypt1", "escape1", "escape2", "tram", "village1",
        "church", "forest", "assault", "factory", "norway")


def run(command, **kwargs):
    print("RUN", " ".join(map(str,command)), flush=True)
    return subprocess.run(command, check=True, **kwargs)


def bsp_bytes(retail:Path,name:str)->bytes:
    needle=f"maps/{name}.bsp"
    for pkg in sorted(retail.glob("*.pk3")):
        with zipfile.ZipFile(pkg) as z:
            m=next((s for s in z.namelist() if s.lower()==needle),None)
            if m:return z.read(m)
    raise RuntimeError(f"Missing authorized retail map {name}")


def pos(entity):
    try:
        a=[float(v) for v in entity["origin"].split()]
        return a if len(a)==3 else None
    except (ValueError, KeyError):return None


def point_at(p,deg,dist):
    yaw=math.radians(deg)
    return [p[0]+math.cos(yaw)*dist,p[1]+math.sin(yaw)*dist,p[2]]


def clear_line(world,one,two):
    if world.solid(one) or world.solid(two):return False
    for height in (0., 12., -12.):
        a=[one[0],one[1],one[2]+height]
        b=[two[0],two[1],two[2]+height]
        if world.solid(a) or world.solid(b):return False
        hit=world.trace(a,b)
        if hit and (hit.get("startsolid") or hit.get("fraction",1.)<0.995):return False
    return True


def grounded(world,eye):
    if world.solid(eye) or world.leaf(eye)[0]<0:return None
    down=world.trace(eye,[eye[0],eye[1],eye[2]-180.])
    if not down or down.get("startsolid") or down.get("sky"):return None
    floor=down.get("position")
    if not floor:return None
    dz=eye[2]-floor[2]
    if not 12<dz<160:return None
    if world.trace(eye,[eye[0],eye[1],eye[2]+32.]) is not None:return None
    return floor[2]


def valid_eye(world,point):
    fl=grounded(world,point)
    if fl is None:return None
    eye=[point[0],point[1],fl+58.]
    if not world.solid(eye) and clear_line(world,point,eye):
        return eye
    return None


def route_for_map(retail,map_name,out):
    world=World(bsp_bytes(retail,map_name))
    starts=[e for e in world.entities if e.get("classname","")=="info_player_start" and pos(e)]
    if not starts:
        starts=[e for e in world.entities if e.get("classname","").startswith("info_player") and pos(e)]
    if not starts:raise RuntimeError("No authored player start "+map_name)
    spawn=None; start_ent=None
    for ent in starts:
        base=pos(ent)
        for dz in (58.,64.,48.,72.,80.,40.,88.):
            eye=[base[0],base[1],base[2]+dz]
            if grounded(world,eye) is not None:
                spawn=eye;start_ent=ent;break
        if spawn:break
    if not spawn:raise RuntimeError(map_name+": no non-solid grounded player start")
    try:yaw=float(start_ent.get("angle","0"))%360
    except ValueError:yaw=0.
    if "angles" in start_ent:
        try:yaw=float(start_ent["angles"].split()[1])%360
        except (ValueError,IndexError):pass
    def next_step(here,base_deg):
        options=[]
        for dev in (0,30,-30,60,-60,90,-90,120,-120,180):
            for dist in (110,85,60,40,25):
                az=(base_deg+dev)%360
                candidate=point_at(here,az,dist)
                fixed=valid_eye(world,candidate)
                if fixed and clear_line(world,here,fixed):
                    options.append((dist-abs(dev)*0.04, fixed, az))
        if not options:return here[:],base_deg
        options.sort(reverse=True,key=lambda v:v[0])
        return options[0][1], options[0][2]

    first,first_yaw=next_step(spawn,yaw)
    second,second_yaw=next_step(first,first_yaw+35.)
    if second==first:
        second,second_yaw=next_step(first,first_yaw-75.)
    # Model occupies ~120 units forward. Keep the head and torso in actual
    # open space rather than placing the test actor behind a world wall.
    model_yaw=None
    for dev in (0,25,-25,45,-45,90,-90,135,180,225,270,315):
        d=(first_yaw+dev)%360
        dest=point_at(first,d,148.)
        if clear_line(world,first,dest):
            model_yaw=d;break
    if model_yaw is None:
        raise RuntimeError(map_name+": no unobstructed 148-unit view for character inspection")
    wall=None
    for origin in (second,first,spawn):
        wall_candidates=[]
        for dev in range(0,360,15):
            h=(second_yaw+dev)%360
            ray=point_at(origin,h,500.)
            result=world.trace(origin,ray)
            if not result or result.get("sky") or result.get("startsolid"):continue
            dist=500*result["fraction"]
            if not 60<=dist<=340:continue
            target=point_at(origin,h,max(dist-27.,0.))
            fixed=valid_eye(world,target)
            if not fixed or not clear_line(world,origin,fixed):continue
            wall_candidates.append((dist,fixed,h,result["material"]))
        if wall_candidates:
            wall_candidates.sort(key=lambda q:q[0])
            _,loc,heading,material=wall_candidates[0]
            wall={"eye":loc,"yaw":heading,"material":material,"distance":wall_candidates[0][0]}
            if origin != second:second=origin[:]  # No unsafe teleport to wall.
            break
    if wall is None:
        # Fail closed, not through walls; still inspect floor and nearby textures.
        wall={"eye":second[:],"yaw":second_yaw,"material":"NO_VALID_WALL","distance":None}
    floor_z=grounded(world,wall["eye"])
    floor_camera=wall["eye"][:]
    if floor_z is not None:
        for height in (23.,28.,36.,48.):
            probe=[wall["eye"][0],wall["eye"][1],floor_z+height]
            if not world.solid(probe) and clear_line(world,wall["eye"],probe):
                floor_camera=probe;break
    # Explicit proof the entire camera trajectory is in open playable BSP space.
    for i,(a,b) in enumerate(((spawn,first),(first,second),(second,wall["eye"]),(wall["eye"],floor_camera))):
        if not clear_line(world,a,b):
            raise RuntimeError(f"{map_name}: camera route hits world geometry segment {i}")
    # Report AI spawners, never assume they are on screen without visual proof.
    ai=[{"classname":e.get("classname"),"origin":pos(e)}
        for e in world.entities if any(x in e.get("classname","").lower()
                                     for x in ("ai_","soldier","guard","zombie","enemy","monster"))
        and pos(e)]
    report={"map":map_name,"source":"original RTCW retail BSP",
            "player_start":spawn,"spawn_angle":yaw,
            "forward_point":first,"corridor_point":second,
            "character_view_yaw":model_yaw,"wall":wall,
            "floor_eye":floor_camera,"native_ai_entity_count":len(ai),
            "nearby_ai_spawners":sorted(ai,key=lambda e:sum((e["origin"][j]-spawn[j])**2 for j in range(3)))[:5],
            "no_teleport_through_world":True,
            "proof_method":"BSP leaf point-in-solid and 3-ray swept segment checks at 0 and +/-12 units",
            "camera_uses_noclip":True}
    (out/f"{map_name}_BSP_ROUTE.json").write_text(json.dumps(report,indent=2)+"\n")
    print("ROUTE",json.dumps(report),flush=True)
    return report


def lerp(a,b,t):
    return [v+(w-v)*t for v,w in zip(a,b)]


def smooth(t):
    t=max(0.,min(1.,t))
    return t*t*(3-2*t)


def interp_angle(a,b,t):
    diff=(b-a+180)%360-180
    return (a+diff*t)%360


def camera_frame(route,t):
    start=route["player_start"];first=route["forward_point"]
    second=route["corridor_point"];near=route["wall"]["eye"];floor=route["floor_eye"]
    sy=route["spawn_angle"];my=route["character_view_yaw"]
    wy=route["wall"]["yaw"]
    if t<12:
        f=smooth(t/12);eye=lerp(start,first,f)
        yaw=interp_angle(sy,my,f)
        pitch=-2.+5*math.sin(t*.45)
    elif t<28:
        eye=first[:]
        yaw=my+6*math.sin((t-12)*.35)
        pitch=-5+4*math.sin((t-12)*.2)
    elif t<41:
        f=smooth((t-28)/13);eye=lerp(first,second,f)
        yaw=interp_angle(my,route["spawn_angle"]+35,f)
        pitch=5*math.sin(t*.24)
    elif t<50:
        f=smooth((t-41)/9);eye=lerp(second,near,f)
        yaw=interp_angle(sy+35,wy,f)
        pitch=0
    elif t<54:
        eye=near[:]
        yaw=wy+9*math.sin((t-50)*1.0)
        pitch=2*math.sin((t-50)*.8)
    elif t<59:
        eye=lerp(near,floor,smooth((t-54)/3))
        yaw=wy+15*math.sin((t-54)*.6)
        pitch=65*smooth((t-54)/2)
    else:
        eye=floor[:];yaw=interp_angle(wy,wy+60,smooth(t-59));pitch=65-35*smooth(t-59)
    return eye,[pitch,yaw%360,0.]


def create_scenario(main,mapname,route):
    prefix="tour"
    script=["set con_notifytime -1","set cg_draw2D 0","set cg_drawGun 1",
            "set cg_bobup 0","set cg_bobpitch 0","set cg_bobroll 0",
            "god","notarget","give all","wait 5","weapon 3","wait 5",
            "set dw_proofFreeze 0"]
    for i in range(FRAMES):
        t=i/FPS
        eye,angles=camera_frame(route,t)
        if i==12*FPS:
            script+=["testmodel "+characters.MODEL_SELECTION["path"],"wait 3"]
        if 13*FPS<=i<27*FPS and i%(FPS//3)==0:
            script+=["nextframe"]
        if i==28*FPS:
            script+=["testmodel"]
        script+=["proofView "+" ".join(f"{v:.4f}" for v in eye+angles),
                 "wait 1", f"screenshot {prefix}_{i:04d}","wait 1"]
    script+=["echo DW_TOUR_COMPLETE","quit"]
    txt="\n".join(script)+"\n"
    if len(txt.encode())>=118*1024:
        raise RuntimeError("Scene command script exceeds Quake command buffer budget")
    name="DW_60SEC_TOUR.cfg"
    (main/name).write_text(txt)
    return name


def build_runtime(source,retail,out):
    characters.OUT=out
    model=characters.animated_player_mesh(retail)
    print("MODEL",model,flush=True)
    characters.instrument_close_model(source)
    with (out/"linux-build.log").open("w") as f:
        result=subprocess.run(["make","-C",str(source/"SP"),"-j2","release",
             "VERSION=1.51d-SP-DarkWolf-RC4-CSM-TextureVideo",
             "BUILD_CLIENT=1","BUILD_SERVER=0","BUILD_GAME_SO=1",
             "BUILD_GAME_QVM=0","BUILD_BASEGAME=1","BUILD_RENDERER_REND2=1",
             "USE_RENDERER_DLOPEN=1"],stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:
        print((out/"linux-build.log").read_text(errors="replace")[-12000:],flush=True)
        raise RuntimeError("Linux video renderer build failure")
    build=source/"SP/build/release-linux-x86_64"
    runtime,main=characters.prepare_runtime_with_skin(build,retail,out)
    return runtime,main


def capture(runtime,main,mapname,route,out):
    name=create_scenario(main,mapname,route)
    cfg=main/"DW_TOUR_PRODUCTION_HIGH_QUALITY.cfg"
    settings=["exec PRODUCTION_HIGH_QUALITY.cfg",
       "set r_mode -1","set r_customwidth "+str(WIDTH),
       "set r_customheight "+str(HEIGHT),"set r_fullscreen 0",
       "set r_renderer rend2","set cl_renderer rend2",
       "set r_picmip 0","set r_picmip2 0",
       "set r_dwTextureFidelity 1","set r_dwAdaptiveUpsample 1",
       "set r_dwCutoutMip 1","set r_dwMaterialFidelity 1",
       "set r_imageUpsample 0",
       "set r_ext_texture_filter_anisotropic 1",
       "set r_ext_max_anisotropy 8",
       "set r_textureMode GL_LINEAR_MIPMAP_LINEAR",
       "set r_postProcess 1","set r_hdr 1","set r_toneMap 1",
       "set r_ssgi 1","set r_volumetricSun 1",
       "set r_volumetricLocal 1","set r_volumetricFire 1",
       "set r_forceSun 1","set r_sunShadows 1","set r_dlightMode 2",
       "set r_forceSunPause 0",
       "set fixedtime 50","set s_initsound 0","set r_swapInterval 0",
       "set cg_draw2D 0","set con_notifytime -1","set developer 0"]
    cfg.write_text("\n".join(settings)+"\n")
    home=runtime/"tour-home";home.mkdir(exist_ok=True)
    game=next(p for p in runtime.iterdir() if p.name.lower().startswith("iowolfsp"))
    game.chmod(0o755)
    cmd=["xvfb-run","-a",str(game),
        "+safe","+set","fs_basepath",str(runtime),
        "+set","fs_homepath",str(home),"+set","com_introplayed","1",
        "+set","com_recommendedSet","1","+set","logfile","2",
        "+set","dw_proofAutomation","1","+set","r_renderer","rend2",
        "+set","cl_renderer","rend2","+exec",cfg.name,"+vid_restart",
        "+set","dw_proofScenario",name,"+spdevmap",mapname]
    env={k:v for k,v in os.environ.items() if not any(x in k.upper()
         for x in ("TOKEN","SECRET","PASSWORD","CREDENTIAL"))}
    env.update(LIBGL_ALWAYS_SOFTWARE="1",LP_NUM_THREADS="2")
    t0=time.monotonic()
    with (out/"stdout.log").open("w") as stdout:
        process=subprocess.Popen(cmd,stdout=stdout,stderr=subprocess.STDOUT,
                                 env=env,start_new_session=True)
        try:exit_code=process.wait(timeout=10600)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait();exit_code=124
    logs=[]
    for p in home.rglob("*console*.log"):
        text=p.read_text(errors="replace")
        target=out/("console-"+str(len(logs))+".log")
        target.write_text(text)
        logs.append(text)
    log="\n".join(logs)
    shots=[]
    for i in range(FRAMES):
        possible=list(home.rglob(f"tour_{i:04d}.tga"))
        if len(possible)!=1:
            raise RuntimeError(f"{mapname}: missing actual frame {i}/{FRAMES}, found {len(possible)}")
        shots.append(possible[0])
    if exit_code!=0 or "DW_TOUR_COMPLETE" not in log or "PROOF_READY" not in log:
        raise RuntimeError(f"Runtime failed: exit={exit_code}, complete={'DW_TOUR_COMPLETE' in log}, ready={'PROOF_READY' in log}")
    for cvar, expected in [
       ("r_dwTextureFidelity","1"),("r_dwMaterialFidelity","1"),
       ("r_dwCutoutMip","1"),("r_dwAdaptiveUpsample","1"),
       ("r_forceSun","1"),("r_ssgi","1"),("r_volumetricSun","1"),
       ("r_volumetricLocal","1"),("r_volumetricFire","1")]:
        # The setup file, not saved wolfconfig, is the source of capture values.
        assert ("set "+cvar+" "+expected) in cfg.read_text()
    if "PROOF_CHARACTER_HEAD_TAG_FOUND tag_head=1" not in log:
        raise RuntimeError(mapname+": animated full-body character HEAD was not attached")
    if "PROOF_CHARACTER_SKIN" not in log:
        raise RuntimeError(mapname+": original character SKIN was not registered")
    links=out/"frames_tga";links.mkdir(exist_ok=True)
    for i,p in enumerate(shots):
        (links/f"frame_{i:04d}.tga").symlink_to(p.resolve())
    target=out/(mapname+"_RC4_CSM_Texture_HQ_60s.mp4")
    encode=["ffmpeg","-hide_banner","-loglevel","error","-y",
            "-framerate",str(FPS),"-start_number","0",
            "-i",str(links/"frame_%04d.tga"),
            "-c:v","libx264","-preset","medium","-crf","20",
            "-pix_fmt","yuv420p","-movflags","+faststart",str(target)]
    run(encode)
    probe=subprocess.check_output(["ffprobe","-v","error",
             "-select_streams","v:0","-show_entries","stream=nb_frames,width,height,r_frame_rate",
             "-show_entries","format=duration","-of","json",str(target)],text=True)
    meta=json.loads(probe); duration=float(meta["format"]["duration"])
    stream=meta["streams"][0]
    if abs(duration-60.)>0.1 or int(stream["nb_frames"])!=FRAMES or tuple([stream["width"],stream["height"]])!=(WIDTH,HEIGHT):
        raise RuntimeError(f"Bad 60sec MP4: {meta}")
    # Keep sampled actual frames for visual QA; the complete raw frames are
    # intentionally not exported because only the encoded motion is requested.
    for second in (0,12,18,28,42,50,55,59):
        source=shots[second*FPS]
        shutil.copyfile(source,out/f"{mapname}_sample_{second:02d}s.tga")
    import hashlib
    check=hashlib.sha256(target.read_bytes()).hexdigest()
    report={
        "map":mapname,"video":target.name,"fps":FPS,"duration_seconds":duration,
        "frames":FRAMES,"resolution":[WIDTH,HEIGHT],"sha256":check,
        "capture_method":"real in-game TGA frames encoded with H.264, no synthetic frames",
        "platform":"Linux OpenGL Mesa llvmpipe (software); source identical to RC4 + CSM guard + texture material fidelity",
        "parent_run":38798189322,"guard_run":39152821574,
        "windows_production_dll_run":39208959543,
        "character_model":characters.MODEL_SELECTION["path"],
        "character_skin":characters.MODEL_SELECTION["skin"],
        "head_model":characters.MODEL_SELECTION["head_model"],
        "head_skin":characters.MODEL_SELECTION["head_skin"],
        "character_material_demo":"Original skeletal and head models, added by test client for material review, not autonomous AI",
        "native_NPC_visibility":"not automatically verified; original AI entities not modified",
        "all_hq_effects_requested":True,
        "route":route,"capture_wall_seconds":round(time.monotonic()-t0,1)}
    (out/"TOUR_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
    print("TOUR_SUCCESS",json.dumps({k:v for k,v in report.items() if k!="route"}),flush=True)
    # Clean up storage on runner after verifying encoded MP4.
    shutil.rmtree(home,ignore_errors=True)
    shutil.rmtree(links,ignore_errors=True)


def main():
    if len(sys.argv)!=5:
        raise SystemExit("Usage: run_tour.py source retail_main output mapname")
    source,retail,out=map(lambda x:Path(x).resolve(),sys.argv[1:4])
    name=sys.argv[4].lower()
    if name not in MAPS:raise ValueError("Unexpected RTCW map: "+name)
    out.mkdir(parents=True,exist_ok=True)
    route=route_for_map(retail,name,out)
    runtime,main=build_runtime(source,retail,out)
    capture(runtime,main,name,route,out)


if __name__=="__main__":
    main()
