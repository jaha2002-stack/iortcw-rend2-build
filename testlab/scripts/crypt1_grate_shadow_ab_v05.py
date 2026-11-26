#!/usr/bin/env python3
"""Crypt1 spawn-rear grate dynamic shadow vs SSGI: real RTCW framebuffer A/B.
This is an isolated TESTLAB source overlay. Never modifies a clean release.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys

sys.path.insert(0, str(Path("testlab/scripts").resolve()))
import rc4_requested_views as proof

CASES = [
    ("baseline", "0.88", "1"),
    ("no_dlight_shadow", "0", "1"),
    ("no_ssgi", "0.88", "0"),
    ("both_disabled", "0", "0"),
    ("baseline_restored", "0.88", "1"),
]
PITCHES = (18, 33)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def edit(path, old, new):
    data=path.read_text()
    if data.count(old)!=1:
        raise RuntimeError(f"instrumentation anchor drift in {path}: expected 1, got {data.count(old)}")
    path.write_text(data.replace(old,new,1))

def instrument(root):
    code=root/"SP/code"
    renderer_before={str(p.relative_to(code)): sha(p) for p in (code/"rend2").rglob("*") if p.is_file()}
    proof.instrument(root)
    g=code/"game/g_cmds.c"
    helper=r'''
/* CRYPT1_GRATE_AB_V01: rotate exactly 180 degrees from player initial spawn.
   Does not translate or teleport the player. TestLab game module ONLY. */
static void Cmd_ProofBackSpawn_f(gentity_t *ent) {
    vec3_t angles;
    if (!g_cheats.integer || !ent->client) return;
    trap_SendServerCommand(ent-g_entities, "stopCam");
    ent->client->noclip=qtrue;
    ent->client->ps.pm_type=PM_NOCLIP;
    ent->client->ps.pm_flags &= ~PMF_DUCKED;
    VectorClear(ent->client->ps.velocity);
    VectorCopy(ent->client->ps.viewangles,angles);
    angles[YAW]=AngleNormalize360(angles[YAW]+180.0f);
    angles[PITCH]=18.0f;
    angles[ROLL]=0.0f;
    SetClientViewAngle(ent,angles);
    ent->client->ps.weapon=WP_MP40;
    ent->client->ps.weaponstate=WEAPON_READY;
    ent->client->ps.weaponTime=0;
    trap_SendServerCommand(ent-g_entities,va("print \"CRYPT1_GRATE_REVERSE_SPAWN eyeOrigin=%.3f,%.3f,%.3f pitch=%.2f yaw=%.2f\n\"",
        ent->client->ps.origin[0],ent->client->ps.origin[1],ent->client->ps.origin[2],angles[PITCH],angles[YAW]));
}
/* Adjust pitch without relocating the camera, preserving identical A/B pose. */
static void Cmd_ProofGratePitch_f(gentity_t *ent) {
    char value[64];
    vec3_t angles;
    if (!g_cheats.integer || !ent->client || trap_Argc()!=2) return;
    trap_Argv(1,value,sizeof(value));
    VectorCopy(ent->client->ps.viewangles,angles);
    angles[PITCH]=atof(value);
    SetClientViewAngle(ent,angles);
}
'''
    edit(g,"static void Cmd_ProofView_f(gentity_t *ent) {",helper+"static void Cmd_ProofView_f(gentity_t *ent) {")
    a='} else if ( Q_stricmp( cmd, "proofView" ) == 0 ) {'
    b='} else if ( Q_stricmp( cmd, "proofBackSpawn" ) == 0 ) {\n        Cmd_ProofBackSpawn_f(ent);\n    } else if ( Q_stricmp( cmd, "proofGratePitch" ) == 0 ) {\n        Cmd_ProofGratePitch_f(ent);\n    '+a
    edit(g,a,b)
    view=code/"cgame/cg_view.c"
    edit(view,'static const char *names[]={"r_ssgi","r_volumetricSun"',
              'static const char *names[]={"r_ssgi","r_dlightShadowStrength","r_volumetricSun"')
    renderer_after={str(p.relative_to(code)): sha(p) for p in (code/"rend2").rglob("*") if p.is_file()}
    assert renderer_before==renderer_after,"RENDERER SOURCE MODIFIED IN TESTLAB!"
    log={"renderer_source_unmodified":True,"renderer_sha256_files":renderer_before,
         "client_game_helper_only":True,"method":"spawn origin, yaw +180, pitch 18/33"}
    Path("evidence").mkdir(exist_ok=True)
    (Path("evidence")/"crypt1-source-isolation.json").write_text(json.dumps(log,indent=2)+"\n")
    print("CRYPT1_GRATE_CAMERA_INSTRUMENTED renderer_unchanged=true",flush=True)

def prepare(build,retail):
    runtime=Path("crypt1-grate-runtime").resolve()
    shutil.rmtree(runtime,ignore_errors=True)
    main=runtime/"main"
    main.mkdir(parents=True)
    for p in build.iterdir():
        if p.is_file(): shutil.copy2(p,runtime/p.name)
    for p in (build/"main").glob("*.so"):
        shutil.copy2(p,main/p.name)
    pk3=[p for p in retail.iterdir() if p.is_file() and p.suffix.lower()==".pk3"]
    assert any(p.name.lower()=="pak0.pk3" for p in pk3),"Missing licensed retail pak0.pk3"
    for p in pk3:
        (main/p.name.lower()).symlink_to(p.resolve())
    return runtime,main

def capture(root,retail,out):
    from PIL import Image,ImageDraw,ImageChops
    import numpy as np
    out.mkdir(parents=True,exist_ok=True)
    build=root/"SP/build/release-linux-x86_64"
    assert build.exists() and (build/"main").exists(),f"Native build missing: {build}"
    runtime,main=prepare(build,retail)
    scenario="CRYPT1_GRATE_AB.cfg"
    commands=[
        "set con_notifytime -1",
        "set cg_draw2D 0",
        "set cg_drawGun 0",
        "set cg_bobup 0",
        "set cg_bobpitch 0",
        "set cg_bobroll 0",
        "set r_autoExposure 0",
        "set r_forceAutoExposure 0",
        "set r_forceSunPause 1",
        "god",
        "notarget",
        "wait 12",
        "proofBackSpawn",
        "wait 45",
    ]
    shot_table=[]
    shot_id=0
    for pitch in PITCHES:
        commands += ["set dw_proofFreeze 0",f"proofGratePitch {pitch}","wait 24","set dw_proofFreeze 1","wait 4"]
        for name,strength,ssgi in CASES:
            shot_id+=1
            shot=f"crypt1_grate_pitch{pitch}_{name}"
            commands.extend([
                f"set r_dlightShadowStrength {strength}",
                f"set r_ssgi {ssgi}",
                "wait 24",
                f"set dw_proofShot {shot_id}",
                "wait 5",
                f"screenshot {shot}",
                "wait 3",
            ])
            shot_table.append({"id":shot_id,"pitch":pitch,"variant":name,
                               "r_dlightShadowStrength":strength,"r_ssgi":ssgi,
                               "name":shot})
    commands += ["set dw_proofFreeze 0","echo CRYPT1_GRATE_AB_COMPLETE","quit"]
    (main/scenario).write_text("\n".join(commands)+"\n")
    (out/"CRYPT1_GRATE_AB_SCENARIO.txt").write_text("\n".join(commands)+"\n")
    setup=[
        "set r_mode -1","set r_customwidth 1280","set r_customheight 720","set r_fullscreen 0",
        "set r_renderer rend2","set cl_renderer rend2","set r_postProcess 1",
        "set r_hdr 1","set r_bloom 1","set r_bloomMode 2",
        "set r_dwCas 1","set r_dwCasStrength 0.55",
        "set r_dwLut 1","set r_dwLutMode 1","set r_dwLutStrength 0.80",
        "set r_dwA2C 1","set r_dwTextureFidelity 1","set r_dwMaterialFidelity 1",
        "set r_ssgi 1","set r_forceSun 1","set r_sunShadows 1","set r_dlightMode 2",
        "set r_dlightShadowStrength 0.88","set r_dlightShadowFilter 2",
        "set r_dlightShadowMapSize 2048",
        "set r_volumetricSun 1","set r_volumetricLocal 1","set r_volumetricFire 1",
        "set r_picmip 0","set r_picmip2 0",
        "set r_ext_framebuffer_multisample 4",
        "set s_initsound 0","set r_swapInterval 0","set fixedtime 100",
        "set cg_draw2D 0","set con_notifytime -1",
    ]
    conf="CRYPT1_GRATE_SETUP.cfg"
    (main/conf).write_text("\n".join(setup)+"\n")
    (out/"CRYPT1_GRATE_SETUP.txt").write_text("\n".join(setup)+"\n")
    home=runtime/"home";home.mkdir(exist_ok=True)
    exe=next((p for p in runtime.iterdir() if p.name.lower().startswith("iowolfsp")),None)
    assert exe is not None,"No Linux executable"
    exe.chmod(0o755)
    cmd=["xvfb-run","-a","-s","-screen 0 1600x900x24",str(exe),
         "+safe","+set","fs_basepath",str(runtime),
         "+set","fs_homepath",str(home),
         "+set","com_introplayed","1","+set","com_recommendedSet","1",
         "+set","logfile","2","+set","dw_proofAutomation","1",
         "+set","r_renderer","rend2","+set","cl_renderer","rend2",
         "+exec",conf,"+vid_restart",
         "+set","dw_proofScenario",scenario,"+spdevmap","crypt1"]
    env={k:v for k,v in os.environ.items() if not any(w in k.upper() for w in ("TOKEN","SECRET","PASSWORD","CREDENTIAL"))}
    env.update({"LIBGL_ALWAYS_SOFTWARE":"1","LP_NUM_THREADS":"2","SDL_AUDIODRIVER":"dummy"})
    with (out/"crypt1-game-stdout.log").open("w") as log:
        p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try: rc=p.wait(timeout=540)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL)
            p.wait()
            rc=124
    logs=[]
    for i,p in enumerate(sorted(home.rglob("*console*.log"))):
        v=p.read_text(errors="replace")
        (out/f"crypt1-console-{i}.log").write_text(v)
        logs.append(v)
    joined="\n".join(logs)
    (out/"CRYPT1_CAPTURE_COMMAND.txt").write_text(" ".join(cmd)+"\n")
    shots=[]
    for shot in shot_table:
        found=list(home.rglob(shot["name"]+".tga"))
        if len(found)!=1:
            print("MISSING_TGA",shot["name"],len(found),flush=True)
            continue
        img=Image.open(found[0]).convert("RGB")
        name=shot["name"]+".png"
        img.save(out/name)
        shots.append({**shot,"file":name,"resolution":img.size})
    rows=[]
    for match in re.finditer(r"PROOF_VIEW shot=(\d+) time=(\d+) eye=([^ ]+) forward=([^ ]+) weapon=(\d+)",joined):
        rows.append({"shot":int(match[1]),"time":int(match[2]),"eye":match[3],
                     "forward":match[4],"weapon":int(match[5])})
    cvar_rows={}
    for match in re.finditer(r"PROOF_CVAR shot=(\d+) name=([^\s]+) value=([^\s]+)",joined):
        cvar_rows.setdefault(int(match[1]),{})[match[2]]=match[3]
    ready=("PROOF_READY" in joined and "CRYPT1_GRATE_REVERSE_SPAWN" in joined)
    complete="CRYPT1_GRATE_AB_COMPLETE" in joined
    report={"reference":"FourWeek Master SourceDefaultsON + LUT V05 (not direct EXE fog guard)",
            "source":"exact validated V05 renderer with isolated TestLab game/cgame camera helpers",
            "environment":"real RTCW retail crypt1 BSP + Linux Mesa llvmpipe + xvfb; NOT NVIDIA Windows RTX 3060 Ti",
            "map":"crypt1","pose":"actual player spawn, yaw + 180 degrees, pitches 18/33",
            "renderer_source_modified":False,"runtime_exit":rc,"ready":ready,"complete":complete,
            "requested":shot_table,"captured":shots,"proof_camera":rows,
            "proof_cvars":cvar_rows,"captured_count":len(shots),
            "graphical_acceptance":"PENDING visual review of screenshot vs user original",
            "screenshot_count_expected":len(shot_table)}
    (out/"CRYPT1_GRATE_CAPTURE_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("runtime_exit","ready","complete","captured_count","screenshot_count_expected")},
          indent=2),flush=True)
    if rc!=0 or not ready or not complete or len(shots)!=len(shot_table):
        raise RuntimeError("Crypt1 retail runtime A/B incomplete; review screenshot/log evidence")
    camera=dict((x["shot"],x) for x in rows)
    assert set(camera)=={x["id"] for x in shot_table},("Camera proof count or identities wrong",camera)
    for pitch in PITCHES:
        points=[camera[x["id"]] for x in shot_table if x["pitch"]==pitch]
        assert len({x["eye"] for x in points})==1,("Camera moved between A/B",pitch,points)
        assert len({x["forward"] for x in points})==1,("Camera rotated between A/B",pitch,points)
    for x in shot_table:
        cv=cvar_rows.get(x["id"],{})
        assert float(cv["r_dlightShadowStrength"])==float(x["r_dlightShadowStrength"]),x
        assert int(cv["r_ssgi"])==int(x["r_ssgi"]),x
    changes=[]
    for pitch in PITCHES:
        groups={x["variant"]:x for x in shots if x["pitch"]==pitch}
        orig=np.asarray(Image.open(out/groups["baseline"]["file"]).convert("RGB")).astype(np.int16)
        repeat=np.asarray(Image.open(out/groups["baseline_restored"]["file"]).convert("RGB")).astype(np.int16)
        for variant in ("no_dlight_shadow","no_ssgi","both_disabled","baseline_restored"):
            cmp=np.asarray(Image.open(out/groups[variant]["file"]).convert("RGB")).astype(np.int16)
            diff=np.abs(orig-cmp)
            box=(slice(int(orig.shape[0]*0.46),int(orig.shape[0]*0.93)),
                 slice(int(orig.shape[1]*0.12),int(orig.shape[1]*0.88)))
            change={"pitch":pitch,"variant":variant,
                    "changed_pixels":int(np.any(diff>0,axis=2).sum()),
                    "mean_abs_rgb_delta":round(float(diff.mean()),5),
                    "ground_region_mean_abs_rgb_delta":round(float(diff[box].mean()),5),
                    "max_channel_delta":int(diff.max())}
            changes.append(change)
        # contact sheet: same pose, two independent CVars, and repeat for drift.
    w,h=480,270
    board=Image.new("RGB",(w*5,(h+38)*len(PITCHES)),(20,20,20))
    draw=ImageDraw.Draw(board)
    for row,pitch in enumerate(PITCHES):
        groups={x["variant"]:x for x in shots if x["pitch"]==pitch}
        for col,(variant,_,_) in enumerate(CASES):
            img=Image.open(out/groups[variant]["file"]).convert("RGB")
            img.thumbnail((w,h))
            xx=col*w;yy=row*(h+38)
            draw.text((xx+7,yy+6),f"Crypt1 rear-spawn grate | pitch {pitch} | {variant}",fill="white")
            board.paste(img,(xx,yy+35))
    board.save(out/"CRYPT1_GRATE_FIVE_WAY_AB_CONTACT_SHEET.png")
    for pitch in PITCHES:
        group={x["variant"]:x for x in shots if x["pitch"]==pitch}
        imgs=[]
        for variant in ("baseline","no_dlight_shadow","no_ssgi","both_disabled"):
            im=Image.open(out/group[variant]["file"]).convert("RGB")
            crop=im.crop((int(im.width*.12),int(im.height*.46),int(im.width*.88),int(im.height*.93)))
            imgs.append(crop)
        w2,h2=imgs[0].size
        detail=Image.new("RGB",(w2*4,h2+32),(20,20,20))
        d=ImageDraw.Draw(detail)
        for i,(variant,im) in enumerate(zip(("baseline","no_dlight_shadow","no_ssgi","both_disabled"),imgs)):
            d.text((i*w2+8,8),variant,fill="white")
            detail.paste(im,(i*w2,32))
        detail.save(out/f"CRYPT1_GRATE_GROUND_DETAIL_PITCH{pitch}.png")
    (out/"CRYPT1_GRATE_PIXEL_DIFF_REPORT.json").write_text(json.dumps({"pairs":changes},indent=2)+"\n")
    assert all(x["captured_count"]==len(shot_table) for x in [report])
    print("CRYPT1_GRATE_REAL_MAP_AB_SCREENSHOTS_PASS",len(shots),len(changes),flush=True)

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    s=parser.add_subparsers(dest="command",required=True)
    p=s.add_parser("instrument")
    p.add_argument("source",type=Path)
    p=s.add_parser("capture")
    p.add_argument("source",type=Path)
    p.add_argument("retail_main",type=Path)
    p.add_argument("out",type=Path)
    args=parser.parse_args()
    if args.command=="instrument":
        instrument(args.source)
    else:
        capture(args.source,args.retail_main,args.out)
