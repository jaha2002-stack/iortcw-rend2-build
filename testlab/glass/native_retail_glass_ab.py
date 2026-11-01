#!/usr/bin/env python3
"""DarkWolf glass A/B on real RTCW retail BSP via the EXISTING native Renderer TestLab.

Captures genuine screenshots through the game's own screenshot command.
Test-only camera changes stay outside rend2. Never exports retail map data.
"""
import argparse, hashlib, json, math, os, re, shutil, signal, struct, subprocess, sys, zipfile
from pathlib import Path
sys.path.insert(0,str(Path("testlab/scripts").resolve()))
import rc4_requested_views as testlab
from rc4_assault_camera import World

PRIORITY=("escape1","factory","crypt1","norway","church","dam","boss1","tram","assault","swf","forest","trainyard")
EXCLUDED=("water","lava","mirror","blood","ice","shutter","shudder","frame","trim","panel","border")
MAX_MAPS=5
MAX_VIEWS_PER_MAP=2
STAMP="DW_GLASS_REAL_RETAIL_TESTLAB_V1"

def H(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def map_inventory(retail):
    maps={}
    for p in sorted(retail.iterdir()):
        if p.suffix.lower()!=".pk3":continue
        with zipfile.ZipFile(p) as z:
            for name in z.namelist():
                low=name.lower()
                if low.startswith("maps/") and low.endswith(".bsp"):
                    maps[Path(low).stem]=(p,name)
    return maps

def glass_candidate(shader_name):
    n=shader_name.rsplit("/",1)[-1].lower()
    return not any(w in n for w in EXCLUDED) and any(w in n for w in ("glass","window"))

def surface_views(data, world, max_views=2):
    # RTCW Q3 BSP: texture(1) x72, vertices(10) x44, surfaces(13) x104.
    def lump(n):
        off,length=struct.unpack_from("<ii",data,8+n*8)
        if off<0 or length<0 or off+length>len(data): raise ValueError("bad BSP lump "+str(n))
        return data[off:off+length]
    shaders=list(struct.iter_unpack("<64sii",lump(1)))
    surfaces=lump(13);verts=lump(10)
    if len(surfaces)%104 or len(verts)%44:raise ValueError("unexpected RTCW BSP surface/vertex stride")
    count=len(verts)//44
    candidates=[]
    catalog={}
    for off in range(0,len(surfaces),104):
        shader_idx,surf_type,first,num_verts=struct.unpack_from("<i4xiii",surfaces,off)
        if shader_idx<0 or shader_idx>=len(shaders) or num_verts<3 or first<0 or first+num_verts>count:continue
        material=shaders[shader_idx][0].split(b"\x00",1)[0].decode("ascii","replace").lower()
        if not glass_candidate(material):continue
        catalog[material]=catalog.get(material,0)+1
        if surf_type not in (1,2,3):continue
        # Sample a broad enough section without indexing every surface vertex.
        ids=sorted(set(first+int((num_verts-1)*k/6) for k in range(7)))
        coords=[];norms=[]
        for idx in ids:
            xyz=struct.unpack_from("<3f",verts,idx*44)
            normal=struct.unpack_from("<3f",verts,idx*44+28)
            if not all(math.isfinite(x) and abs(x)<65536 for x in (*xyz,*normal)):continue
            coords.append(xyz);norms.append(normal)
        if len(coords)<3:continue
        center=[sum(p[i] for p in coords)/len(coords) for i in range(3)]
        norm=[sum(n[i] for n in norms) for i in range(3)]
        magnitude=math.sqrt(sum(n*n for n in norm))
        if magnitude<0.1:continue
        norm=[n/magnitude for n in norm]
        extent=math.sqrt(sum((max(p[i] for p in coords)-min(p[i] for p in coords))**2 for i in range(3)))
        if extent<4:continue
        candidates.append((min(extent,4096),material,center,norm))
    # Largest glazed surfaces first, not area-specific hardcoded list.
    candidates.sort(reverse=True,key=lambda x:x[0])
    chosen=[];invalid={"solid":0,"trace":0,"cluster":0,"too_near":0}
    for size,material,center,normal in candidates[:250]:
        for sign in (1.,-1.):
            for dist in (68.,116.,192.):
                eye=[center[i]+sign*dist*normal[i] for i in range(3)]
                if world.solid(eye):
                    invalid["solid"]+=1;continue
                if world.leaf(eye)[0]<0:
                    invalid["cluster"]+=1;continue
                # A glass brush may itself stop trace at the surface. Allow only a
                # near-target obstruction, not opaque walls between eye and pane.
                target=[center[i]+sign*3.0*normal[i] for i in range(3)]
                tr=world.trace(eye,target)
                if tr and (tr.get("startsolid") or tr.get("fraction",1.0)<0.90):
                    invalid["trace"]+=1;continue
                if any(math.dist(eye,v["eye"])<155 for v in chosen):
                    invalid["too_near"]+=1;continue
                vec=[center[i]-eye[i] for i in range(3)]
                yaw=math.degrees(math.atan2(vec[1],vec[0]))%360
                pitch=-math.degrees(math.atan2(vec[2],math.hypot(vec[0],vec[1])))
                if abs(pitch)>78:continue
                selected={"name":"glass_view_"+str(len(chosen)+1),"eye":[round(n,4) for n in eye],
                    "angles":[round(pitch,4),round(yaw,4),0.0],
                    "material":material,"surface_extent":round(size,2),
                    "glass_surface_center":[round(x,4) for x in center],
                    "distance":dist}
                chosen.append(selected)
                break
            if len(chosen)>=max_views:break
        if len(chosen)>=max_views:break
    return {"candidate_material_counts":catalog,"candidate_surfaces":sum(catalog.values()),
        "camera_selection_rejections":invalid,"views":chosen}

def make_camera_matrix(retail,out):
    allmaps=map_inventory(retail)
    matrix={}
    for name in dict.fromkeys(list(PRIORITY)+sorted(allmaps)):
        if name not in allmaps:continue
        pk3,path=allmaps[name]
        with zipfile.ZipFile(pk3) as z:bsp=z.read(path)
        if bsp[:4]!=b"IBSP":continue
        try:
            w=World(bsp)
            info=surface_views(bsp,w,MAX_VIEWS_PER_MAP)
            info["bsp_sha256"]=hashlib.sha256(bsp).hexdigest()
            info["map"]=name
            matrix[name]=info
            print("REAL_BSP_GLASS",name,info["candidate_surfaces"],
                  "valid_cameras",len(info["views"]),flush=True)
        except Exception as ex:
            matrix[name]={"map":name,"error":type(ex).__name__+":"+str(ex)}
    eligible=[n for n in PRIORITY if n in matrix and matrix[n].get("views")]
    eligible+= [n for n in matrix if n not in eligible and matrix[n].get("views")]
    selected=eligible[:MAX_MAPS]
    inventory={"source":"actual original RTCW licensed retail BSP","source_pk3_data_exported":False,
               "maps_scanned":len(matrix),"maps_with_valid_glass_camera":len(eligible),
               "selected_maps":selected,"all_maps":matrix}
    (out/"REAL_BSP_GLASS_INVENTORY.json").write_text(json.dumps(inventory,indent=2)+"\n")
    if len(selected)<2:raise RuntimeError("Fewer than two real maps with safe glass camera angles; see inventory")
    return {n:matrix[n]["views"] for n in selected}

def instrument(source):
    before={str(p.relative_to(source)):H(p) for p in (source/"SP/code/rend2").rglob("*") if p.is_file()}
    testlab.instrument(source)
    after={str(p.relative_to(source)):H(p) for p in (source/"SP/code/rend2").rglob("*") if p.is_file()}
    assert before==after,"TestLab changed a production renderer source byte"
    print("GLASS_NATIVE_TESTLAB_CAMERA_ISOLATION_PASS",len(before),flush=True)

def prepare(source,retail,variant,mapname,profile):
    build=source/"SP/build/release-linux-x86_64"
    if not build.is_dir():raise RuntimeError("Missing native Linux Rend2 build: "+str(build))
    runtime=Path("glass-realgame-runtime")/f"{variant}-{mapname}"
    main=runtime/"main";main.mkdir(parents=True,exist_ok=True)
    for p in build.iterdir():
        if p.is_file():shutil.copy2(p,runtime/p.name)
    for p in (build/"main").glob("*"):
        if p.is_file():shutil.copy2(p,main/p.name)
    for p in retail.iterdir():
        if p.is_file() and p.suffix.lower()==".pk3":
            (main/p.name.lower()).symlink_to(p.resolve())
    shutil.copy2(profile,main/"DW_ACCEPTED_HIGH.cfg")
    exe=next((p for p in runtime.iterdir() if p.is_file() and p.name.lower().startswith("iowolfsp")),None)
    if not exe:raise RuntimeError("Native game exe absent")
    exe.chmod(0o755)
    return runtime.resolve(),main.resolve(),exe.resolve()

def capture(source,retail,profile,out,variant,mapname,views,enabled):
    from PIL import Image,ImageStat
    out.mkdir(parents=True,exist_ok=True)
    runtime,main,exe=prepare(source,retail,variant,mapname,profile)
    scen="DW_GLASS_V1_SCENE.cfg"
    cmds=["set cg_draw2D 0","set cg_drawGun 0","set con_notifytime -1",
          "set cg_bobup 0","set cg_bobpitch 0","set cg_bobroll 0",
          "set r_autoExposure 0","set r_forceAutoExposure 0","set r_forceSunPause 1",
          "god","notarget","wait 22"]
    shots=[]
    for i,view in enumerate(views,1):
        shot=f"dwglass_{mapname}_{variant}_{i}"
        cmds +=["set dw_proofFreeze 0",
                "proofView "+" ".join(f"{x:.4f}" for x in view["eye"]+view["angles"]),
                "wait 46","set dw_proofFreeze 1","wait 6",
                f"set dw_proofShot {i}","wait 5",f"screenshot {shot}","wait 5"]
        shots.append(shot)
    cmds+=["set dw_proofFreeze 0","echo DW_GLASS_REALGAME_COMPLETE","quit"]
    (main/scen).write_text("\n".join(cmds)+"\n")
    # Same accepted source profile for BASE, OFF and ON; only new glass cvar differs.
    setup=["exec DW_ACCEPTED_HIGH.cfg",
        "set r_mode -1","set r_customwidth 1280","set r_customheight 720","set r_fullscreen 0",
        "set cl_renderer rend2","set r_renderer rend2","set r_cubeMapping 0",
        "set r_dwGlassReflect "+str(enabled),
        "set r_dwGlassIntensity 0.60","set r_dwGlassAutoDetect 1",
        "set s_initsound 0","set r_swapInterval 0","set com_fixedtime 100",
        "set r_autoExposure 0","set r_forceAutoExposure 0",
        "set cg_draw2D 0","set con_notifytime -1"]
    (main/"DW_GLASS_SETUP.cfg").write_text("\n".join(setup)+"\n")
    (out/"scenario.cfg").write_text("\n".join(cmds)+"\n")
    (out/"setup.cfg").write_text("\n".join(setup)+"\n")
    home=(runtime/"home").resolve();home.mkdir(exist_ok=True)
    cmd=["xvfb-run","-a","-s","-screen 0 1600x900x24",str(exe),
        "+safe","+set","fs_basepath",str(runtime),"+set","fs_homepath",str(home),
        "+set","com_introplayed","1","+set","com_recommendedSet","1",
        "+set","logfile","2","+set","dw_proofAutomation","1",
        "+set","r_dwGlassReflect",str(enabled),
        "+set","r_cubeMapping","0",
        "+set","cl_renderer","rend2","+set","r_renderer","rend2",
        "+exec","DW_GLASS_SETUP.cfg","+vid_restart",
        "+set","dw_proofScenario",scen,"+spdevmap",mapname]
    env={k:v for k,v in os.environ.items() if not any(w in k.upper() for w in ("TOKEN","SECRET","PASSWORD","CREDENTIAL"))}
    env.update(LIBGL_ALWAYS_SOFTWARE="1",LP_NUM_THREADS="2",SDL_AUDIODRIVER="dummy")
    with (out/"stdout.log").open("w") as log:
        proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try:rc=proc.wait(timeout=420)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait();rc=124
    logs=[]
    for n,p in enumerate(sorted(home.rglob("*console*.log"))):
        text=p.read_text(errors="replace");logs.append(text)
        (out/f"console-{n}.log").write_text(text)
    text="\n".join(logs)
    images={}
    for n,shot in enumerate(shots,1):
        matches=list(home.rglob(shot+".tga"))
        if len(matches)==1:
            image=Image.open(matches[0]).convert("RGB")
            png=out/(shot+".png");image.save(png)
            st=ImageStat.Stat(image)
            images[str(n)]={"file":png.name,"sha256":H(png),"size":list(image.size),
                             "stddev":round(sum(st.stddev)/3,2),"mean":round(sum(st.mean)/3,2)}
    cameras={}
    for match in re.finditer(r"PROOF_VIEW shot=(\d+) time=\d+ eye=([^ ]+) forward=([^ ]+) weapon=(\d+)",text):
        cameras[match[1]]={"eye":match[2],"forward":match[3],"weapon":int(match[4])}
    report={"variant":variant,"map":mapname,"run_exit":rc,"ready":"PROOF_READY" in text,
            "complete":"DW_GLASS_REALGAME_COMPLETE" in text,
            "renderer":"native-linux-ioRTCW-Rend2-Mesa","base":41297344177,
            "glass_on":enabled,"images":images,"cameras":cameras}
    (out/"capture.json").write_text(json.dumps(report,indent=2)+"\n")
    print("DW_GLASS_REAL_CAPTURE",variant,mapname,rc,len(images),report["ready"],report["complete"],flush=True)
    assert rc==0 and report["ready"] and report["complete"],"Real RTCW camera automation never finished"
    assert len(images)==len(shots)==len(cameras),"Missing actual framebuffer image or camera probe"
    assert all(x["stddev"]>7 and x["mean"]>5 for x in images.values()),"Blank/black/invalid game screenshot"
    return report

def compare(out,matrix,all_reports):
    from PIL import Image,ImageChops,ImageStat,ImageDraw
    rows=[];sheet=Image.new("RGB",(1200,350*sum(len(v) for v in matrix.values())),(18,18,18))
    draw=ImageDraw.Draw(sheet);pos=0
    for name,views in matrix.items():
        v=all_reports[name]
        for i,view in enumerate(views,1):
            b,o,n=(v[x] for x in ("BASE","OFF","ON"))
            assert b["cameras"][str(i)]["eye"]==o["cameras"][str(i)]["eye"]==n["cameras"][str(i)]["eye"],"Camera mismatch"
            images=[Image.open(out/name/x/x["images"][str(i)]["file"]).convert("RGB") for x in ()] if False else []
            for mode in ("BASE","OFF","ON"):
                record=v[mode]["images"][str(i)]
                images.append(Image.open(out/name/mode/record["file"]).convert("RGB"))
            base,off,on=images
            assert base.size==off.size==on.size
            drift=ImageStat.Stat(ImageChops.difference(base,off))
            effect=ImageStat.Stat(ImageChops.difference(off,on))
            drift_mae=sum(drift.mean)/3
            effect_mae=sum(effect.mean)/3
            effect_chg=ImageChops.difference(off,on).getbbox() is not None
            row={"map":name,"view":i,"material":view["material"],"camera":view["eye"],
                 "base_off_mae":round(drift_mae,5),"off_on_mae":round(effect_mae,5),
                 "glass_effect_changed":effect_chg,"real_3d_game":True,
                 "base_off_same_camera":True,"lighting_profile":"ACCEPTED_HIGH"}
            rows.append(row)
            y=pos*350
            for k,(im,label) in enumerate(zip(images,("BASE #41297344177","Glass OFF","Glass ON"))):
                draw.text((8+k*400,y+8),f"{name} {view['material']}: {label}",fill=(255,255,255))
                im.thumbnail((400,310))
                sheet.paste(im,(k*400,y+35))
            pos+=1
    sheet.save(out/"DW_GLASS_REAL_RETAIL_AB_CONTACT_SHEET.png")
    report={"type":"REAL_RETAIL_GAME_TESTLAB_BASE_OFF_ON","parent_run":41297344177,
            "source_reference":"same accepted profile, camera and build family",
            "no_video_fabrication":True,"real_GLSL_shader_validation":"SEPARATE_CI",
            "windows_gpu_runtime":"NOT_TESTED","all_maps_visually_proven":False,"pairs":rows}
    (out/"REAL_GLASS_TESTLAB_AB_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
    print("REAL_RETAIL_GLASS_BASE_OFF_ON_SCREENS",len(rows),json.dumps([{"map":r["map"],"delta":r["off_on_mae"]} for r in rows]),flush=True)
    # A PASS requires a real in-game reflection difference, not merely a shader compiled successfully.
    assert any(r["off_on_mae"]>0.08 for r in rows),"No observable glass reflectivity in actual gameplay"
    # Baseline parity is quantified, not asserted exact, because time-dependent visuals can differ.
    return report

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="action",required=True)
    a=sub.add_parser("instrument");a.add_argument("source",type=Path)
    a=sub.add_parser("capture");a.add_argument("baseline",type=Path);a.add_argument("candidate",type=Path)
    a.add_argument("retail",type=Path);a.add_argument("profile",type=Path);a.add_argument("output",type=Path)
    args=p.parse_args()
    if args.action=="instrument":return instrument(args.source)
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    matrix=make_camera_matrix(args.retail,out)
    reports={}
    for mapname,views in matrix.items():
        reports[mapname]={}
        for variant,source,enabled in (("BASE",args.baseline,0),("OFF",args.candidate,0),("ON",args.candidate,1)):
            reports[mapname][variant]=capture(source,args.retail,args.profile,out/mapname/variant,variant,mapname,views,enabled)
    compare(out,matrix,reports)

if __name__=="__main__":main()
