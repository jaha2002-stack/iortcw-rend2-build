#!/usr/bin/env python3
"""Crypt1 root-cause isolation: full/diagnostic lightmap with CAS/LUT ablations.
Source variant is specified by runner. TestLab camera helpers only; preserved comparison geometry.
"""
from pathlib import Path
import sys,re,json,os,signal,subprocess,shutil,zipfile
sys.path.insert(0,str(Path("testlab/scripts").resolve()))
import crypt1_grate_shadow_ab_v05 as lab
import rc4_assault_camera as geom

VIEWS=[
    ("grate_near48_pitch28",[-240.,1664.,512.125],[28.,180.,0.]),
    ("grate_near72_pitch42",[-264.,1664.,512.125],[42.,180.,0.]),
]
# shadow strength, SSGI, CAS sharpness, alpha-to-coverage, baked lightmap mode
MODES=[
    ("baseline","0.88","1","0.55","0.80","0"),
    ("no_cas","0.88","1","0","0.80","0"),
    ("no_lut","0.88","1","0.55","0","0"),
    ("lightmap_only","0.88","1","0.55","0.80","1"),
    ("lightmap_no_cas","0.88","1","0","0.80","1"),
    ("lightmap_no_lut","0.88","1","0.55","0","1"),
    ("lightmap_no_cas_lut","0.88","1","0","0","1"),
    ("baseline_repeat","0.88","1","0.55","0.80","0"),
]
FIELDS=("r_dlightShadowStrength","r_forceSun","r_dwCasStrength","r_dwLutStrength","r_lightmap")
def instrument(src):
    lab.instrument(src)
    p=src/"SP/code/cgame/cg_view.c"
    s=p.read_text()
    old='static const char *names[]={"r_ssgi","r_dlightShadowStrength","r_volumetricSun"'
    new='static const char *names[]={"r_ssgi","r_dlightShadowStrength","r_dwCasStrength","r_dwLutStrength","r_lightmap","r_forceSun","r_volumetricSun"'
    assert s.count(old)==1,"Proof CVar logger anchor drift"
    p.write_text(s.replace(old,new,1))
    print("CRYPT1_CLOSEUP_TESTLAB_INSTRUMENTATION_PASS",flush=True)

def map_data(retail):
    for p in sorted(retail.glob("*.pk3")):
        with zipfile.ZipFile(p) as z:
            names=[x for x in z.namelist() if x.lower()=="maps/crypt1.bsp"]
            if names:return z.read(names[0])
    raise RuntimeError("No Crypt1 BSP")

def validate_cameras(retail):
    world=geom.World(map_data(retail))
    start=[-192.,1664.,512.125]
    for name,eye,_ in VIEWS:
        assert not world.solid(eye),(name,"solid eye")
        for offset in ((0,8,0),(0,-8,0),(0,0,-16),(8,0,0),(-8,0,0)):
            assert not world.solid([eye[i]+offset[i] for i in range(3)]),(name,"near solid",offset)
        hit=world.trace(start,eye)
        assert not hit or hit.get("fraction",1)>=.999,(name,"BSP obstacle",hit)
    print("CRYPT1_CLOSEUP_BSP_CAMERA_PROBES_PASS",len(VIEWS),flush=True)

def capture(source,retail,out):
    from PIL import Image,ImageDraw
    import numpy as np
    out.mkdir(parents=True,exist_ok=True)
    validate_cameras(retail)
    build=source/"SP/build/release-linux-x86_64"
    runtime,main=lab.prepare(build,retail)
    scenario="CRYPT1_GRATE_CLOSEUP_AB.cfg"
    commands=["set cg_draw2D 0","set cg_drawGun 0","set con_notifytime -1",
       "set cg_bobup 0","set cg_bobpitch 0","set cg_bobroll 0",
       "set r_autoExposure 0","set r_forceAutoExposure 0",
       "set r_forceSunPause 1","god","notarget","wait 18"]
    shots=[]
    idx=0
    for name,eye,angles in VIEWS:
        commands+=["set dw_proofFreeze 0","proofView "+" ".join(f"{x:.6f}" for x in eye+angles),
                   "wait 36","set dw_proofFreeze 1","wait 4"]
        for variant,shadow,ssgi,cas,a2c,lightmap in MODES:
            idx+=1
            shot=f"crypt1_{name}_{variant}"
            commands += [
                f"set r_dlightShadowStrength {shadow}",
                f"set r_forceSun {ssgi}",
                f"set r_dwCasStrength {cas}",
                f"set r_dwLutStrength {a2c}",
                f"set r_lightmap {lightmap}",
                "wait 35",f"set dw_proofShot {idx}","wait 5",f"screenshot {shot}","wait 3"]
            shots.append(dict(id=idx,view=name,variant=variant,eye=eye,angles=angles,shot=shot,
                              cvars=dict(zip(FIELDS,(shadow,ssgi,cas,a2c,lightmap)))))
    commands+=["set dw_proofFreeze 0","echo CRYPT1_GRATE_CLOSEUP_AB_COMPLETE","quit"]
    (main/scenario).write_text("\n".join(commands)+"\n")
    (out/"CRYPT1_GRATE_CLOSEUP_SCENARIO.txt").write_text("\n".join(commands)+"\n")
    setup=["set r_mode -1","set r_customwidth 1280","set r_customheight 720",
      "set r_fullscreen 0","set r_renderer rend2","set cl_renderer rend2",
      "set r_hdr 1","set r_postProcess 1","set r_bloom 1","set r_bloomMode 2",
      "set r_dwCas 1","set r_dwCasStrength 0.55","set r_dwA2C 1",
      "set r_dwLut 1","set r_dwLutMode 1","set r_dwLutStrength 0.80",
      "set r_ssgi 1","set r_forceSun 1","set r_sunShadows 1","set r_dlightMode 2",
      "set r_dlightShadowStrength 0.88","set r_dlightShadowFilter 2",
      "set r_dlightShadowMapSize 2048","set r_lightmap 0",
      "set r_dwTextureFidelity 1","set r_dwMaterialFidelity 1",
      "set r_volumetricSun 1","set r_volumetricLocal 1","set r_volumetricFire 1",
      "set r_ext_framebuffer_multisample 4","set r_picmip 0","set r_picmip2 0",
      "set s_initsound 0","set r_swapInterval 0","set fixedtime 100",
      "set cg_draw2D 0","set con_notifytime -1"]
    if os.getenv("DW_FIDELITY_OFF") == "1":
        setup += ["set r_dwTextureFidelity 0",
                  "set r_dwMaterialFidelity 0",
                  "set r_dwAdaptiveUpsample 0",
                  "set r_dwCutoutMip 0"]
    if os.getenv("DW_MSAA_OFF") == "1":
        setup += ["set r_ext_framebuffer_multisample 0"]
    cfg="CRYPT1_GRATE_CLOSEUP_SETUP.cfg"
    (main/cfg).write_text("\n".join(setup)+"\n")
    (out/"CRYPT1_GRATE_CLOSEUP_SETUP.txt").write_text("\n".join(setup)+"\n")
    (out/"TEST_VARIANT_ENV.json").write_text(json.dumps({"DW_FIDELITY_OFF":os.getenv("DW_FIDELITY_OFF","0"),"DW_MSAA_OFF":os.getenv("DW_MSAA_OFF","0")},indent=2))
    home=runtime/"home";home.mkdir(exist_ok=True)
    exe=next((p for p in runtime.iterdir() if p.name.lower().startswith("iowolfsp")),None)
    assert exe and exe.exists()
    exe.chmod(0o755)
    cmd=["xvfb-run","-a","-s","-screen 0 1600x900x24",str(exe),
      "+safe","+set","fs_basepath",str(runtime),"+set","fs_homepath",str(home),
      "+set","com_introplayed","1","+set","com_recommendedSet","1",
      "+set","logfile","2","+set","dw_proofAutomation","1",
      "+set","r_renderer","rend2","+set","cl_renderer","rend2",
      "+exec",cfg,"+vid_restart","+set","dw_proofScenario",scenario,"+spdevmap","crypt1"]
    env={k:v for k,v in os.environ.items() if not any(w in k.upper() for w in ("TOKEN","SECRET","PASSWORD","CREDENTIAL"))}
    env.update(LIBGL_ALWAYS_SOFTWARE="1",LP_NUM_THREADS="2",SDL_AUDIODRIVER="dummy")
    with (out/"crypt1-closeup-stdout.log").open("w") as log:
        p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try:exitcode=p.wait(timeout=720)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait();exitcode=124
    combined=[]
    for j,p in enumerate(sorted(home.rglob("*console*.log"))):
        data=p.read_text(errors="replace");combined.append(data)
        (out/f"crypt1-closeup-console-{j}.log").write_text(data)
    joined="\n".join(combined)
    camera={}
    for m in re.finditer(r"PROOF_VIEW shot=(\d+) time=\d+ eye=([^ ]+) forward=([^ ]+) weapon=(\d+)",joined):
        camera[int(m[1])]=dict(eye=m[2],forward=m[3],weapon=int(m[4]))
    cvars={}
    for m in re.finditer(r"PROOF_CVAR shot=(\d+) name=([^\s]+) value=([^\s]+)",joined):
        cvars.setdefault(int(m[1]),{})[m[2]]=m[3]
    for shot in shots:
        found=list(home.rglob(shot["shot"]+".tga"))
        if len(found)==1:
            f=found[0]; im=Image.open(f).convert("RGB")
            shot["png"]=shot["shot"]+".png"
            im.save(out/shot["png"])
    ready="PROOF_READY" in joined
    complete="CRYPT1_GRATE_CLOSEUP_AB_COMPLETE" in joined
    report=dict(name="Crypt1 user-near-closeup geometry/shadow/SSGI/CAS/A2C/lightmap A/B",
        map="crypt1",source="FourWeek Master SourceDefaultsON + accepted LUT V05",
        environment="Linux Mesa llvmpipe (not NVIDIA RTX 3060Ti Windows)",
        camera_bsp_collision_validated=True,renderer_source_unchanged=True,
        origin_player_spawn=[-192.,1664.,512.125],
        exitcode=exitcode,ready=ready,complete=complete,views=VIEWS,
        expected_shots=len(shots),saved_shots=sum("png" in s for s in shots),
        shots=shots,camera=camera,cvars=cvars)
    (out/"CRYPT1_GRATE_CLOSEUP_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
    if exitcode!=0 or not ready or not complete or report["saved_shots"]!=len(shots):
        raise RuntimeError("Real-game close-up capture failed: "+str({k:report[k] for k in ("exitcode","ready","complete","saved_shots")}))
    assert len(camera)==len(shots),(len(camera),len(shots),"missing camera logs")
    for view in VIEWS:
        v=[camera[s["id"]] for s in shots if s["view"]==view[0]]
        assert len({x["eye"] for x in v})==1 and len({x["forward"] for x in v})==1,(view,"camera drift")
    for shot in shots:
        measured=cvars.get(shot["id"],{})
        for k,want in shot["cvars"].items():
            assert k in measured and float(measured[k])==float(want),(shot["shot"],k,measured.get(k),want)
    data=[]
    for name,eye,angles in VIEWS:
        a={s["variant"]:s for s in shots if s["view"]==name}
        baseline=np.asarray(Image.open(out/a["baseline"]["png"]).convert("RGB"),dtype=np.int16)
        repeat=np.asarray(Image.open(out/a["baseline_repeat"]["png"]).convert("RGB"),dtype=np.int16)
        assert np.array_equal(baseline,repeat),("Non deterministic baseline",name)
        for variant,*_ in MODES[1:]:
            image=np.asarray(Image.open(out/a[variant]["png"]).convert("RGB"),dtype=np.int16)
            d=np.abs(image-baseline)
            roi=(slice(int(d.shape[0]*.34),int(d.shape[0]*.93)),
                 slice(int(d.shape[1]*.10),int(d.shape[1]*.90)))
            data.append(dict(view=name,variant=variant,changed_pixels=int(np.any(d>0,axis=2).sum()),
                             change_pct=round(float(np.mean(np.any(d>0,axis=2))*100),3),
                             mean_abs_rgb_delta=round(float(d.mean()),5),
                             lower_grate_roi_delta=round(float(d[roi].mean()),5)))
    (out/"CRYPT1_GRATE_CLOSEUP_PIXEL_DIFF.json").write_text(json.dumps(data,indent=2)+"\n")
    for name,eye,angles in VIEWS:
        group={s["variant"]:s for s in shots if s["view"]==name}
        thumb_w,thumb_h=500,282
        sheet=Image.new("RGB",(thumb_w*4,(thumb_h+33)*2),(18,18,18))
        draw=ImageDraw.Draw(sheet)
        for k,(variant,*_) in enumerate(MODES):
            col=k%4;row=k//4
            img=Image.open(out/group[variant]["png"]).convert("RGB")
            img.thumbnail((thumb_w,thumb_h))
            x=col*thumb_w;y=row*(thumb_h+33)
            draw.text((x+9,y+8),name+" | "+variant,fill="white")
            sheet.paste(img,(x,y+30))
        sheet.save(out/(name+"_A2C_CAS_SHADOW_SSGI_AB.png"))
    print("CRYPT1_GRATE_REAL_CLOSEUP_AB_PASS",len(shots),"identical_repeat=True",flush=True)

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    subs=p.add_subparsers(dest="cmd",required=True)
    s=subs.add_parser("instrument");s.add_argument("source",type=Path)
    s=subs.add_parser("capture");s.add_argument("source",type=Path);s.add_argument("retail",type=Path);s.add_argument("out",type=Path)
    a=p.parse_args()
    instrument(a.source) if a.cmd=="instrument" else capture(a.source,a.retail,a.out)
