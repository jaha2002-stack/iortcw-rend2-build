#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, math, os, re, shutil, signal, subprocess, sys, zipfile

sys.path.insert(0, str(Path("testlab/scripts").resolve()))
import rc4_requested_views as proof
import rc4_assault_camera as geom

STATIC_TARGET=[-1088.0,384.0,64.0]
MOVING_TARGET=[-1120.0,2448.0,344.0]

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def edit(path,old,new):
    s=path.read_text()
    if s.count(old)!=1:
        raise RuntimeError(f"{path}: anchor count {s.count(old)} for {old[:80]!r}")
    path.write_text(s.replace(old,new,1))

def instrument(root):
    code=root/"SP/code"
    renderer_before={str(p.relative_to(code)):digest(p) for p in (code/"rend2").rglob("*") if p.is_file()}
    proof.instrument(root)
    g=code/"game/g_cmds.c"
    helper=r'''
/* DW_CHATEAU_FIREPLACE_VISUAL_PROOF: game-module-only script mover trigger/logger. */
static gentity_t *DW_ProofFindScriptMover(const char *name) {
    return G_Find(&g_entities[MAX_CLIENTS], FOFS(scriptName), name);
}
static void Cmd_ProofTriggerScript_f(gentity_t *ent) {
    char name[MAX_TOKEN_CHARS], trigger[MAX_TOKEN_CHARS];
    gentity_t *mover;
    if (!g_cheats.integer || trap_Argc()!=3) return;
    trap_Argv(1,name,sizeof(name)); trap_Argv(2,trigger,sizeof(trigger));
    mover=DW_ProofFindScriptMover(name);
    if (!mover) {
        trap_SendServerCommand(ent-g_entities,va("print \"PROOF_SCRIPT_TRIGGER_MISSING name=%s\\n\"",name));
        return;
    }
    G_Script_ScriptEvent(mover,"trigger",trigger);
    trap_SendServerCommand(ent-g_entities,va("print \"PROOF_SCRIPT_TRIGGER name=%s trigger=%s entity=%d origin=%.3f,%.3f,%.3f\\n\"",
        name,trigger,mover-g_entities,mover->r.currentOrigin[0],mover->r.currentOrigin[1],mover->r.currentOrigin[2]));
}
static void Cmd_ProofScriptOrigin_f(gentity_t *ent) {
    char name[MAX_TOKEN_CHARS]; gentity_t *mover;
    if (!g_cheats.integer || trap_Argc()!=2) return;
    trap_Argv(1,name,sizeof(name)); mover=DW_ProofFindScriptMover(name);
    if (!mover) {
        trap_SendServerCommand(ent-g_entities,va("print \"PROOF_SCRIPT_ORIGIN_MISSING name=%s\\n\"",name));
        return;
    }
    trap_SendServerCommand(ent-g_entities,va("print \"PROOF_SCRIPT_ORIGIN name=%s entity=%d origin=%.3f,%.3f,%.3f angles=%.3f,%.3f,%.3f\\n\"",
        name,mover-g_entities,mover->r.currentOrigin[0],mover->r.currentOrigin[1],mover->r.currentOrigin[2],
        mover->r.currentAngles[0],mover->r.currentAngles[1],mover->r.currentAngles[2]));
}
'''
    edit(g,"static void Cmd_ProofView_f(gentity_t *ent) {",helper+"static void Cmd_ProofView_f(gentity_t *ent) {")
    anchor='} else if ( Q_stricmp( cmd, "proofView" ) == 0 ) {'
    replacement='} else if ( Q_stricmp( cmd, "proofTriggerScript" ) == 0 ) {\n        Cmd_ProofTriggerScript_f(ent);\n    } else if ( Q_stricmp( cmd, "proofScriptOrigin" ) == 0 ) {\n        Cmd_ProofScriptOrigin_f(ent);\n    '+anchor
    edit(g,anchor,replacement)
    renderer_after={str(p.relative_to(code)):digest(p) for p in (code/"rend2").rglob("*") if p.is_file()}
    if renderer_before!=renderer_after:
        raise RuntimeError("Renderer source changed by visual-proof instrumentation")
    Path("evidence").mkdir(exist_ok=True)
    (Path("evidence")/"CHATEAU_PROOF_SOURCE_ISOLATION.json").write_text(json.dumps({
        "renderer_source_unmodified":True,
        "game_cgame_client_helpers_only":True,
        "renderer_file_hashes":renderer_before
    },indent=2)+"\n")
    print("CHATEAU_PROOF_INSTRUMENTATION_PASS renderer_unchanged=true",flush=True)

def map_data(retail):
    for p in sorted(retail.glob("*.pk3")):
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.lower()=="maps/chateau.bsp":
                    return z.read(n)
    raise RuntimeError("maps/chateau.bsp missing")

def view_angles(eye,target):
    dx,dy,dz=target[0]-eye[0],target[1]-eye[1],target[2]-eye[2]
    h=math.hypot(dx,dy)
    yaw=math.degrees(math.atan2(dy,dx))%360.0
    pitch=math.degrees(math.atan2(-dz,h))
    return [pitch,yaw,0.0]

def choose_views(retail,target,label):
    world=geom.World(map_data(retail))
    views=[]
    for az in range(0,360,45):
        a=math.radians(az)
        chosen=None
        for radius in (260.0,220.0,320.0,180.0,380.0):
            for zoff in (72.0,48.0,104.0):
                eye=[target[0]+math.cos(a)*radius,target[1]+math.sin(a)*radius,target[2]+zoff]
                if world.solid(eye):
                    continue
                if any(world.solid([eye[0]+x,eye[1]+y,eye[2]+z]) for x,y,z in ((12,0,0),(-12,0,0),(0,12,0),(0,-12,0),(0,0,-12))):
                    continue
                hit=world.trace(eye,target)
                frac=1.0 if not hit else float(hit.get("fraction",0.0))
                if hit and hit.get("startsolid"):
                    continue
                if frac<0.30:
                    continue
                chosen={"name":f"{label}_az{az:03d}","eye":eye,"angles":view_angles(eye,target),
                        "target":target,"trace_fraction":frac,"radius":radius,"zoff":zoff}
                break
            if chosen: break
        if chosen: views.append(chosen)
    if len(views)<3:
        raise RuntimeError(f"Too few valid {label} cameras: {len(views)}")
    return views

def prepare(build,retail):
    runtime=Path("chateau-fireplace-runtime").resolve()
    shutil.rmtree(runtime,ignore_errors=True)
    main=runtime/"main"; main.mkdir(parents=True)
    for p in build.iterdir():
        if p.is_file(): shutil.copy2(p,runtime/p.name)
    for p in (build/"main").glob("*.so"):
        shutil.copy2(p,main/p.name)
    pk3=[p for p in retail.iterdir() if p.is_file() and p.suffix.lower()==".pk3"]
    if not any(p.name.lower()=="pak0.pk3" for p in pk3):
        raise RuntimeError("Missing licensed pak0.pk3")
    for p in pk3:
        (main/p.name.lower()).symlink_to(p.resolve())
    return runtime,main

def capture(root,retail,out):
    from PIL import Image,ImageDraw
    import numpy as np
    out.mkdir(parents=True,exist_ok=True)
    static_views=choose_views(retail,STATIC_TARGET,"static")
    moving_views=choose_views(retail,MOVING_TARGET,"moving")
    (out/"CHATEAU_CAMERA_CANDIDATES.json").write_text(json.dumps({"static":static_views,"moving_post_move":moving_views},indent=2)+"\n")

    build=root/"SP/build/release-linux-x86_64"
    runtime,main=prepare(build,retail)
    scenario="CHATEAU_FIREPLACE_PROOF.cfg"
    cmds=[
      "set con_notifytime -1","set cg_draw2D 0","set cg_drawGun 0",
      "set cg_bobup 0","set cg_bobpitch 0","set cg_bobroll 0",
      "set r_volumetricFireStrength 1","set r_volumetricFire 1",
      "set r_dwFireVolContinuityDiag 0","set r_dwFireVolFixtureDiag 0",
      "god","notarget","wait 20"
    ]
    shots=[]; idx=0
    def add_pair(view,group):
        nonlocal idx
        cmds.extend(["set dw_proofFreeze 0","proofView "+" ".join(f"{x:.6f}" for x in view["eye"]+view["angles"]),
                     "wait 24","set dw_proofFreeze 1","wait 4"])
        for mode,val in (("on","1"),("off","0")):
            idx+=1; name=f"chateau_{view['name']}_{mode}"
            cmds.extend([f"set r_volumetricFire {val}","wait 8",f"set dw_proofShot {idx}","wait 4",f"screenshot {name}","wait 3"])
            shots.append({"id":idx,"group":group,"view":view["name"],"mode":mode,"name":name})
    for v in static_views:
        add_pair(v,"static")
    cmds.extend(["set dw_proofFreeze 0","proofScriptOrigin fireplace1","proofTriggerScript fireplace1 rotate1",
                 "wait 130","proofScriptOrigin fireplace1","wait 8"])
    for v in moving_views:
        add_pair(v,"moving_post_move")
    cmds.extend(["set r_volumetricFire 1","set dw_proofFreeze 0","echo CHATEAU_FIREPLACE_PROOF_COMPLETE","quit"])
    (main/scenario).write_text("\n".join(cmds)+"\n")
    (out/"CHATEAU_FIREPLACE_PROOF_SCENARIO.txt").write_text("\n".join(cmds)+"\n")

    setup=[
      "set r_mode -1","set r_customwidth 1280","set r_customheight 720","set r_fullscreen 0",
      "set r_renderer rend2","set cl_renderer rend2","set r_hdr 1","set r_postProcess 1",
      "set r_bloom 1","set r_bloomMode 2","set r_dlightMode 2",
      "set r_volumetricLocal 1","set r_volumetricFire 1","set r_volumetricFireStrength 1",
      "set r_ssgi 1","set r_forceSun 1","set r_ext_framebuffer_multisample 4",
      "set r_picmip 0","set r_picmip2 0","set s_initsound 0","set r_swapInterval 0",
      "set com_fixedtime 100","set cg_draw2D 0","set con_notifytime -1","set developer 0"
    ]
    cfg="CHATEAU_FIREPLACE_PROOF_SETUP.cfg"
    (main/cfg).write_text("\n".join(setup)+"\n")
    (out/"CHATEAU_FIREPLACE_PROOF_SETUP.txt").write_text("\n".join(setup)+"\n")
    home=runtime/"home"; home.mkdir(exist_ok=True)
    exe=next((p for p in runtime.iterdir() if p.name.lower().startswith("iowolfsp")),None)
    if not exe: raise RuntimeError("iowolfsp missing")
    exe.chmod(0o755)
    cmd=["xvfb-run","-a","-s","-screen 0 1600x900x24",str(exe),
         "+safe","+set","fs_basepath",str(runtime),"+set","fs_homepath",str(home),
         "+set","com_introplayed","1","+set","com_recommendedSet","1","+set","logfile","2",
         "+set","dw_proofAutomation","1","+set","r_renderer","rend2","+set","cl_renderer","rend2",
         "+exec",cfg,"+vid_restart","+set","dw_proofScenario",scenario,"+spdevmap","chateau"]
    env={k:v for k,v in os.environ.items() if not any(w in k.upper() for w in ("TOKEN","SECRET","PASSWORD","CREDENTIAL"))}
    env.update(LIBGL_ALWAYS_SOFTWARE="1",LP_NUM_THREADS="2",SDL_AUDIODRIVER="dummy")
    with (out/"chateau-fireplace-stdout.log").open("w") as log:
        p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try: rc=p.wait(timeout=900)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL); p.wait(); rc=124

    logs=[]
    for i,p in enumerate(sorted(home.rglob("*console*.log"))):
        data=p.read_text(errors="replace"); logs.append(data)
        (out/f"chateau-fireplace-console-{i}.log").write_text(data)
    joined="\n".join(logs)

    images={}
    for shot in shots:
        found=list(home.rglob(shot["name"]+".tga"))
        if len(found)==1:
            im=Image.open(found[0]).convert("RGB")
            fn=shot["name"]+".png"; im.save(out/fn); images[shot["name"]]=np.asarray(im,dtype=np.int16)

    origins=[]
    for m in re.finditer(r"PROOF_SCRIPT_ORIGIN name=fireplace1 entity=(\d+) origin=([^ ]+) angles=([^\s]+)",joined):
        origins.append({"entity":int(m.group(1)),"origin":m.group(2),"angles":m.group(3)})
    triggered="PROOF_SCRIPT_TRIGGER name=fireplace1 trigger=rotate1" in joined

    metrics=[]
    best={}
    for group,views in (("static",static_views),("moving_post_move",moving_views)):
        for v in views:
            on=images.get(f"chateau_{v['name']}_on"); off=images.get(f"chateau_{v['name']}_off")
            if on is None or off is None: continue
            d=np.abs(on-off)
            changed=np.any(d>1,axis=2)
            roi=d[int(d.shape[0]*.12):int(d.shape[0]*.92),int(d.shape[1]*.08):int(d.shape[1]*.92)]
            lum=float(on.mean())
            row={"group":group,"view":v["name"],"changed_pixels":int(changed.sum()),
                 "mean_abs_delta":float(d.mean()),"roi_mean_abs_delta":float(roi.mean()),
                 "on_mean_rgb":lum,"trace_fraction":v["trace_fraction"]}
            row["score"]=row["changed_pixels"]*(0.1+row["roi_mean_abs_delta"])*(0.4+min(lum,100.0)/100.0)
            metrics.append(row)
        cand=[x for x in metrics if x["group"]==group]
        if not cand: raise RuntimeError(f"No image pairs for {group}")
        cand.sort(key=lambda x:x["score"],reverse=True)
        best[group]=cand[0]
        src=out/(f"chateau_{cand[0]['view']}_on.png")
        shutil.copy2(src,out/("BEST_STATIC_FIREPLACE.png" if group=="static" else "BEST_MOVING_FIREPLACE_POST_MOVE.png"))

    # Contact sheets for visual QA.
    for group,views in (("static",static_views),("moving_post_move",moving_views)):
        valid=[v for v in views if (out/f"chateau_{v['name']}_on.png").exists()]
        if not valid: continue
        tw,th=320,180
        sheet=Image.new("RGB",(tw*4,(th+28)*math.ceil(len(valid)/4)),(16,16,16))
        draw=ImageDraw.Draw(sheet)
        for n,v in enumerate(valid):
            im=Image.open(out/f"chateau_{v['name']}_on.png").convert("RGB"); im.thumbnail((tw,th))
            x=(n%4)*tw; y=(n//4)*(th+28)
            draw.text((x+4,y+4),v["name"],fill="white"); sheet.paste(im,(x,y+24))
        sheet.save(out/f"{group.upper()}_CONTACT_SHEET.png")

    report={"map":"chateau","source":"Clean Production FireVol Final lineage from run 42060324463",
            "environment":"Linux Mesa llvmpipe + xvfb, real licensed RTCW Chateau BSP",
            "renderer_source_modified_by_lab":False,"runtime_exit":rc,
            "proof_ready":"PROOF_READY" in joined,"proof_complete":"CHATEAU_FIREPLACE_PROOF_COMPLETE" in joined,
            "moving_script_triggered":triggered,"fireplace1_origin_logs":origins,
            "r_volumetricFireStrength":1.0,"shots_expected":len(shots),"shots_captured":len(images),
            "metrics":metrics,"best":best}
    (out/"CHATEAU_FIREPLACE_VISUAL_PROOF_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("runtime_exit","proof_ready","proof_complete","moving_script_triggered","shots_expected","shots_captured","best")},indent=2),flush=True)
    if rc!=0 or not report["proof_ready"] or not report["proof_complete"] or not triggered or len(images)!=len(shots):
        raise RuntimeError("Chateau fireplace proof capture incomplete")
    if len(origins)<2:
        raise RuntimeError("Missing pre/post script mover origin proof")
    before=[float(x) for x in origins[0]["origin"].split(",")]
    after=[float(x) for x in origins[-1]["origin"].split(",")]
    if math.dist(before,after)<50.0:
        raise RuntimeError(f"fireplace1 did not move enough: {before} -> {after}")
    for group in ("static","moving_post_move"):
        if best[group]["changed_pixels"]<100:
            raise RuntimeError(f"FireVol ON/OFF contribution too small for {group}: {best[group]}")
    print("CHATEAU_FIREPLACE_CLEAN_PRODUCTION_VISUAL_PROOF_PASS",flush=True)

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest="cmd",required=True)
    p=sp.add_parser("instrument"); p.add_argument("source",type=Path)
    p=sp.add_parser("capture"); p.add_argument("source",type=Path); p.add_argument("retail",type=Path); p.add_argument("out",type=Path)
    a=ap.parse_args()
    instrument(a.source) if a.cmd=="instrument" else capture(a.source,a.retail,a.out)
