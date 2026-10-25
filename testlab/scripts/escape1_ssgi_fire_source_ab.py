#!/usr/bin/env python3
"""Source-locked real RTCW Escape1/Factory SSGI emitter regression.
Derive safe in-world camera locations from the legally owned map BSP.
Never upload or redistribute map/pak contents. All comparisons retain effects.
"""
from pathlib import Path
import argparse,json,math,re,zipfile,os,shutil,subprocess,signal,sys
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path("testlab/scripts").resolve()))
import crypt1_grate_shadow_ab_v05 as lab
from rc4_assault_camera import World

ESCAPE_FIXTURES=[
 ("furnace",[-1340.,692.,-36.],"stove"),
 ("fireplace_west",[-1776.,1088.,180.],"fireplace"),
 ("torch_north",[-2780.,1344.,204.],"torch"),
 ("torch_east",[-1212.,1492.,-140.],"torch"),
 ("torch_south",[-1920.,-64.,372.],"torch"),
 ("lamp_warm",[516.,468.,-284.],"lamp"),
 ("lamp_red",[-924.,444.,-300.],"lamp"),
 ("fire_secondary",[932.,160.,-476.],"fire")
]
FACTORY_VIEWS=[
 ("tunnel_lamp_start",[-368.,-1055.,-232.],[-34.,180.,0.]),
]
MODES=[("ssgi_off",0,2,0),("factory_guard_v03",1,2,0),
       ("fire_guard_v04",1,3,0),("fire_guard_repeat",1,3,0),
       ("baked_lightmap",1,3,1)]
def read_map(retail,level):
 for file in sorted(retail.glob("*.pk3")):
  with zipfile.ZipFile(file) as z:
   for name in z.namelist():
    if name.lower()=="maps/"+level+".bsp":return z.read(name)
 raise RuntimeError("Map not found in authorized retail assets: "+level)
def choose_views(world,level):
 if level=="factory":
  return [(name,eye,angles,{"method":"historical factory tunnel lamp near spawn"}) for name,eye,angles in FACTORY_VIEWS]
 chosen=[]
 for name,target,kind in ESCAPE_FIXTURES:
  if name=="furnace":
   eye=[-1340.,760.,-10.]
   if not world.solid(eye):
    chosen.append((name,eye,[21.,270.,0.],{"target":target,"kind":kind,"method":"historical in-room verified camera"}))
    continue
  candidates=[]
  for radius in (76.,112.,148.,192.):
   for deg in range(0,360,30):
    t=math.radians(deg)
    for dz in (4.,32.,56.,-16.):
     eye=[round(target[0]+math.cos(t)*radius,3),round(target[1]+math.sin(t)*radius,3),round(target[2]+dz,3)]
     if world.solid(eye):continue
     if world.leaf(eye)[0]<0:continue
     if any(world.solid([eye[0]+dx,eye[1]+dy,eye[2]+zz]) for dx,dy,zz in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-12))):continue
     hit=world.trace(eye,target)
     fraction=1. if not hit else float(hit.get("fraction",1.))
     if fraction<0.82:continue
     yaw=math.degrees(math.atan2(target[1]-eye[1],target[0]-eye[0]))%360.
     pitch=-math.degrees(math.atan2(target[2]-eye[2],radius))
     score=fraction-0.0005*radius-0.002*abs(dz-16)
     candidates.append((score,eye,[pitch,yaw,0.],fraction))
  if not candidates:
   print("NO_SAFE_VIEW",level,name,flush=True)
   continue
  candidates.sort(reverse=True,key=lambda x:x[0])
  _,eye,angles,fraction=candidates[0]
  chosen.append((name,eye,angles,{"target":target,"kind":kind,"trace_fraction":fraction,"candidate_count":len(candidates)}))
 assert len(chosen)>=5,(level,len(chosen))
 return chosen

def instrument(src):
 lab.instrument(src)
 p=src/"SP/code/cgame/cg_view.c"
 s=p.read_text()
 old='static const char *names[]={"r_ssgi","r_dlightShadowStrength","r_volumetricSun"'
 new='static const char *names[]={"r_ssgi","r_ssgiBrightSourceFix","r_lightmap","r_dlightShadowStrength","r_volumetricSun"'
 assert s.count(old)==1
 p.write_text(s.replace(old,new,1))
 print("SSGI_ESCAPE1_PROOF_CAMERA_INSTRUMENTED",flush=True)

def capture(src,retail,out,level):
 out.mkdir(parents=True,exist_ok=True)
 world=World(read_map(retail,level))
 selected=choose_views(world,level)
 (out/"CAMERAS.json").write_text(json.dumps([
   {"name":n,"eye":p,"angles":a,**meta} for n,p,a,meta in selected],indent=2)+"\n")
 runtime,main=lab.prepare(src/"SP/build/release-linux-x86_64",retail)
 setup=["set r_renderer rend2","set cl_renderer rend2","set r_mode -1",
        "set r_customwidth 1280","set r_customheight 720","set r_fullscreen 0",
        "set r_hdr 1","set r_postProcess 1","set r_bloom 1","set r_bloomMode 2",
        "set r_dwCas 1","set r_dwCasStrength 0.55","set r_dwA2C 1",
        "set r_dwLut 1","set r_dwLutMode 1","set r_dwLutStrength 0.80",
        "set r_ssgi 1","set r_ssgiBrightSourceFix 2",
        "set r_ssgiResolveMode 2","set r_ssgiEntityGuardMode 2",
        "set r_forceSun 1","set r_sunShadows 1","set r_dlightMode 2",
        "set r_volumetricSun 1","set r_volumetricLocal 1","set r_volumetricFire 1",
        "set r_dwTextureFidelity 1","set r_dwMaterialFidelity 1",
        "set r_ext_framebuffer_multisample 4","set r_picmip 0","set r_picmip2 0",
        "set r_swapInterval 0","set s_initsound 0","set fixedtime 100"]
 scenario=["set cg_draw2D 0","set cg_drawGun 0","set con_notifytime -1",
           "set cg_bobup 0","set cg_bobpitch 0","set cg_bobroll 0",
           "set r_autoExposure 0","set r_forceAutoExposure 0",
           "set r_forceSunPause 1","god","notarget","wait 15"]
 shots=[];idx=0
 for name,eye,angles,_ in selected:
  scenario+=["set dw_proofFreeze 0","proofView "+" ".join("%.5f"%v for v in eye+angles),
             "wait 36","set dw_proofFreeze 1","wait 5"]
  for mode,ssgi,bright,lightmap in MODES:
   idx+=1
   filename=level+"_"+name+"_"+mode
   scenario += ["set r_ssgi "+str(ssgi),"set r_ssgiBrightSourceFix "+str(bright),
                "set r_lightmap "+str(lightmap),"wait 42",
                "set dw_proofShot "+str(idx),"wait 6","screenshot "+filename,"wait 3"]
   shots.append({"shot_id":idx,"scene":name,"mode":mode,"file":filename+".png",
                 "cvars":{"r_ssgi":ssgi,"r_ssgiBrightSourceFix":bright,"r_lightmap":lightmap}})
 scenario+=["set dw_proofFreeze 0","echo ESCAPE1_SSGI_SOURCE_TEST_COMPLETE","quit"]
 (main/"ESCAPE1_SSGI_SETUP.cfg").write_text("\n".join(setup)+"\n")
 (main/"ESCAPE1_SSGI_SCENARIO.cfg").write_text("\n".join(scenario)+"\n")
 (out/"ESCAPE1_SSGI_SETUP.cfg").write_text("\n".join(setup)+"\n")
 (out/"ESCAPE1_SSGI_SCENARIO.cfg").write_text("\n".join(scenario)+"\n")
 home=runtime/"home";home.mkdir(exist_ok=True)
 exe=next(p for p in runtime.iterdir() if p.name.lower().startswith("iowolfsp"))
 cmd=["xvfb-run","-a","-s","-screen 0 1600x900x24",str(exe),
      "+safe","+set","fs_basepath",str(runtime),"+set","fs_homepath",str(home),
      "+set","com_introplayed","1","+set","com_recommendedSet","1",
      "+set","logfile","2","+set","dw_proofAutomation","1",
      "+set","r_renderer","rend2","+set","cl_renderer","rend2",
      "+exec","ESCAPE1_SSGI_SETUP.cfg","+vid_restart",
      "+set","dw_proofScenario","ESCAPE1_SSGI_SCENARIO.cfg","+spdevmap",level]
 env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ("TOKEN","PASSWORD","CREDENTIAL","SECRET"))}
 env.update(LIBGL_ALWAYS_SOFTWARE="1",LP_NUM_THREADS="2",SDL_AUDIODRIVER="dummy")
 with (out/"runtime.log").open("w") as log:
  proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:rc=proc.wait(timeout=1150)
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGKILL);proc.wait();rc=124
 logs=[]
 for i,p in enumerate(sorted(home.rglob("*console*.log"))):
  t=p.read_text(errors="replace")
  logs.append(t)
  (out/("console_%d.log"%i)).write_text(t)
 joined="\n".join(logs)
 camera={int(m[1]):(m[2],m[3]) for m in re.finditer(r"PROOF_VIEW shot=(\d+) time=\d+ eye=([^ ]+) forward=([^ ]+)",joined)}
 cv={}
 for m in re.finditer(r"PROOF_CVAR shot=(\d+) name=([^\s]+) value=([^\s]+)",joined):
  cv.setdefault(int(m[1]),{})[m[2]]=m[3]
 for row in shots:
  match=list(home.rglob(Path(row["file"]).stem+".tga"))
  if len(match)==1: Image.open(match[0]).convert("RGB").save(out/row["file"])
 capture_ok=rc==0 and "ESCAPE1_SSGI_SOURCE_TEST_COMPLETE" in joined and len(camera)==len(shots) and all((out/x["file"]).is_file() for x in shots)
 if capture_ok:
  for scene,_,_,_ in selected:
   frames=[x for x in shots if x["scene"]==scene]
   assert len(set(camera[x["shot_id"]][0] for x in frames))==1,("camera moved",scene)
   for x in frames:
    for key,want in x["cvars"].items():
     assert key in cv.get(x["shot_id"],{}) and float(cv[x["shot_id"]][key])==float(want),(scene,x["mode"],key,cv.get(x["shot_id"]))
  for name,eye,angle,_ in selected:
   imgs={x["mode"]:Image.open(out/x["file"]).convert("RGB") for x in shots if x["scene"]==name}
   a=np.asarray(imgs["factory_guard_v03"],dtype=np.int16)
   b=np.asarray(imgs["fire_guard_v04"],dtype=np.int16)
   delta=np.abs(a-b)
   assert np.array_equal(np.asarray(imgs["fire_guard_v04"]),np.asarray(imgs["fire_guard_repeat"])),("non deterministic",name)
   board=Image.new("RGB",(1280*2,720*2),(16,16,16))
   for i,key in enumerate(("ssgi_off","factory_guard_v03","fire_guard_v04","baked_lightmap")):
    x=(i%2)*1280;y=(i//2)*720
    board.paste(imgs[key],(x,y))
    ImageDraw.Draw(board).text((x+20,y+15),level+" "+name+" "+key,fill="white")
   board.save(out/(level+"_"+name+"_ATLAS.png"))
   metric={"scene":name,"full_mean_abs_rgb":round(float(delta.mean()),5),
          "changed_gt4_pct":round(float(np.any(delta>4,axis=2).mean()*100),4),
          "bright_core_v02_to_v03_changed":int(np.any(delta>4,axis=2).sum())}
   print("SSGI_FIXTURE_METRIC",json.dumps(metric),flush=True)
 summary={"map":level,"exit":rc,"views":selected,"shots":shots,"saved":sum((out/x["file"]).is_file() for x in shots),
          "camera_count":len(camera),"success":capture_ok}
 (out/"RESULT.json").write_text(json.dumps(summary,indent=2)+"\n")
 if not capture_ok:raise RuntimeError("SSGI FIRE ACTUAL GAME CAPTURE FAILED "+str((rc,len(camera),summary["saved"],len(shots))))
 print("ESCAPE1_FACTORY_SSGI_REALGAME_FIXTURE_PASS",level,len(shots),len(selected),flush=True)

if __name__=="__main__":
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest="action",required=True)
 x=sub.add_parser("instrument");x.add_argument("source",type=Path)
 x=sub.add_parser("capture");x.add_argument("source",type=Path);x.add_argument("retail",type=Path);x.add_argument("out",type=Path);x.add_argument("level",choices=["escape1","factory"])
 a=p.parse_args()
 if a.action=="instrument":instrument(a.source)
 else:capture(a.source,a.retail,a.out,a.level)
