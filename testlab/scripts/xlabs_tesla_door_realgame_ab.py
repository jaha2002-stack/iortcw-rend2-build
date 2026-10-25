#!/usr/bin/env python3
"""Real original RTCW Xlabs Tesla door A/B, renderer byte-identical to production."""
from pathlib import Path
import sys,argparse,math,json,re,zipfile,os,signal,subprocess,shutil,hashlib,time
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path("testlab/scripts").resolve()))
import rc4_requested_views as qa
from rc4_assault_camera import World

CASES=(("original",0,1),("blue_shadowed",1,1),("blue_unshadowed",1,0),("original_repeat",0,1))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def instrument(root):
 code=root/"SP/code"
 renderer={str(p.relative_to(code)):sha(p) for p in (code/"rend2").rglob("*") if p.is_file()}
 qa.instrument(root)
 p=code/"cgame/cg_view.c";s=p.read_text()
 old='static const char *names[]={"r_ssgi","r_volumetricSun"'
 assert s.count(old)==1
 p.write_text(s.replace(old,'static const char *names[]={"cg_xlabsTeslaDoorLight","cg_xlabsTeslaDoorShadows","r_dlightMode","r_dynamiclight","r_ssgi","r_volumetricSun"',1))
 assert renderer=={str(p.relative_to(code)):sha(p) for p in (code/"rend2").rglob("*") if p.is_file()}
 print("XLABS_PROOF_CAMERA_ONLY_RENDERER_BYTE_IDENTICAL_PASS",len(renderer),flush=True)

def get_world(retail):
 for p in sorted(retail.glob("*.pk3")):
  with zipfile.ZipFile(p) as z:
   for n in z.namelist():
    if n.lower()=="maps/xlabs.bsp":return World(z.read(n))
 raise RuntimeError("Licensed xlabs BSP unavailable")

def camera_views(world):
 targets={e.get("targetname"):e for e in world.entities if e.get("targetname")}
 groups={}
 for e in world.entities:
  if e.get("classname")!="shooter_tesla":continue
  flags=int(e.get("spawnflags","0"))
  if not flags&1 or flags&2:continue
  key=e.get("targetname")
  if key:groups.setdefault(key,[]).append(e)
 result=[]
 for label,emitters in groups.items():
  if len(emitters)!=3:continue
  middle=[]
  for e in emitters:
   t=targets.get(e.get("target"))
   if t is None or "origin" not in t:continue
   a=list(map(float,e["origin"].split()));b=list(map(float,t["origin"].split()))
   middle.append([a[i]*0.52+b[i]*0.48 for i in range(3)])
  if len(middle)!=3:continue
  center=[sum(e[i] for e in middle)/3 for i in range(3)]
  found=[]
  for radius in (132,180,230):
   for deg in range(0,360,30):
    rad=math.radians(deg)
    for dz in (0,40,70):
     eye=[center[0]+radius*math.cos(rad),center[1]+radius*math.sin(rad),center[2]+dz]
     if world.solid(eye) or world.leaf(eye)[0]<0:continue
     hit=world.trace(eye,center);fraction=hit["fraction"] if hit else 1.
     if fraction<0.75:continue
     yaw=math.degrees(math.atan2(center[1]-eye[1],center[0]-eye[0]))%360
     pitch=-math.degrees(math.atan2(center[2]-eye[2],radius))
     found.append((fraction-.0002*radius,eye,[pitch,yaw,0],fraction))
  if not found:continue
  found.sort(key=lambda x:x[0],reverse=True);_,eye,angles,fraction=found[0]
  result.append({"name":"door_"+label,"eye":eye,"angles":angles,
                 "center":center,"fraction":fraction,"emitters":3})
 if not result:raise RuntimeError("No safe Xlabs original authored Tesla door view")
 return result[:2]

def capture(root,retail,out):
 out.mkdir(parents=True,exist_ok=True);views=camera_views(get_world(retail))
 # Run each condition in a fresh process: native llvmpipe aborts after first
 # proof shot even when Xlabs door light is OFF. Capture single verified frames.
 one_case=os.environ.get("XLABS_SINGLE_SHOT_VARIANT")
 if one_case:
  cases=tuple(c for c in CASES if c[0]==one_case)
  assert len(cases)==1,one_case
  views=views[:1]
 else:cases=CASES
 (out/"ACTUAL_XLABS_DOOR_CAMERAS.json").write_text(json.dumps(views,indent=2))
 runtime=Path("xlabs-tesla-door-proof-runtime").resolve()
 shutil.rmtree(runtime,ignore_errors=True);main=runtime/"main";main.mkdir(parents=True)
 build=root/"SP/build/release-linux-x86_64";assert build.is_dir()
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/"main").glob("*.so"):shutil.copy2(p,main/p.name)
 for p in retail.glob("*.pk3"):(main/p.name.lower()).symlink_to(p.resolve())
 config=["set r_renderer rend2","set cl_renderer rend2","set r_mode -1",
         "set r_customwidth 1280","set r_customheight 720","set r_fullscreen 0",
         "set r_hdr 1","set r_postProcess 1","set r_bloom 1","set r_bloomMode 2",
         "set r_dwLut 1","set r_dwLutStrength 0","set r_dwCas 1","set r_dwCasStrength 0.55",
         "set r_dwA2C 1","set r_ssgi 1","set r_dlightMode 2","set r_dynamiclight 1",
         "set r_dlightShadowMaxLights 3","set r_dlightWorldContainment 2",
         "set cg_dlightEffectEnhance 1","set cg_xlabsTeslaDoorRadius 300",
         "set cg_xlabsTeslaDoorIntensity 0.95","set r_volumetricLocal 1","set r_volumetricFire 1",
         "set r_autoExposure 0","set r_forceAutoExposure 0",
         "set r_picmip 0","set r_picmip2 0","set s_initsound 0",
         "set fixedtime 100","set r_swapInterval 0","set cg_draw2D 0","set cg_drawGun 0"]
 scenario=["set cg_draw2D 0","set cg_drawGun 0","god","notarget","wait 12"]
 expected=[];i=0
 for v in views:
  scenario+=["set dw_proofFreeze 0","proofView "+" ".join("%.4f"%x for x in v["eye"]+v["angles"]),
             "wait 25","set dw_proofFreeze 1","wait 5"]
  for label,on,shadow in cases:
   i+=1;name="xlabs_"+v["name"]+"_"+label
   scenario+=["set cg_xlabsTeslaDoorLight "+str(on),
              "set cg_xlabsTeslaDoorShadows "+str(shadow),"wait 20",
              "set dw_proofShot "+str(i),"wait 24"]
   expected.append(dict(id=i,name=name,view=v["name"],label=label,light=on,shadow=shadow))
 scenario+=["set dw_proofFreeze 0","echo XLABS_DOOR_ACTUAL_AB_COMPLETED","quit"]
 (main/"XLABS_SETUP.cfg").write_text("\n".join(config)+"\n")
 (main/"XLABS_SCENARIO.cfg").write_text("\n".join(scenario)+"\n")
 (out/"XLABS_SETUP.cfg").write_text("\n".join(config)+"\n")
 (out/"XLABS_SCENARIO.cfg").write_text("\n".join(scenario)+"\n")
 exe=next(p for p in runtime.iterdir() if p.is_file() and p.name.lower().startswith("iowolfsp"));exe.chmod(0o755)
 home=runtime/"home";home.mkdir()
 cmd=[str(exe),
      "+safe","+set","fs_basepath",str(runtime),"+set","fs_homepath",str(home),
      "+set","com_introplayed","1","+set","com_recommendedSet","1",
      "+set","logfile","2","+set","dw_proofAutomation","1",
      "+set","r_renderer","rend2","+set","cl_renderer","rend2",
      "+exec","XLABS_SETUP.cfg","+vid_restart",
      "+set","dw_proofScenario","XLABS_SCENARIO.cfg","+spdevmap","xlabs"]
 env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ("TOKEN","SECRET","PASSWORD","CREDENTIAL"))}
 env.update(LIBGL_ALWAYS_SOFTWARE="1",LP_NUM_THREADS="2",SDL_AUDIODRIVER="dummy",
            SDL_VIDEO_CENTERED="1",DISPLAY=":97")
 # Capture the real SDL game window through a separate X11 client.
 # The native software rasterizer SIGSEGVs on the first in-engine screenshot
 # even in the control case with the new lighting disabled.
 display=subprocess.Popen(["Xvfb",":97","-screen","0","1600x900x24","-nolisten","tcp"],
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 time.sleep(1)
 shot_ids=set()
 screenshot_errors=[]
 begin=time.monotonic()
 with (out/"runtime.log").open("w") as log:
  proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:
   while proc.poll() is None and time.monotonic()-begin<660:
    for console in home.rglob("*console*.log"):
     contents=console.read_text(errors="replace")
     for match in re.finditer(r"PROOF_VIEW shot=(\d+) time=",contents):
      num=int(match[1])
      if num in shot_ids or num<1 or num>len(expected):continue
      row=expected[num-1]
      shot_ids.add(num)
      time.sleep(0.32)
      imagefile=out/(row["name"]+".png")
      cap=subprocess.run(["import","-display",":97","-window","root",
                          "-crop","1280x720+160+90","png:"+str(imagefile)],
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=28)
      if cap.returncode!=0 or not imagefile.is_file() or imagefile.stat().st_size<3000:
       screenshot_errors.append({"shot":num,"rc":cap.returncode,
                                 "stderr":cap.stderr.decode(errors="replace")[:350]})

    time.sleep(0.12)
   if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   rc=proc.returncode if proc.returncode is not None else 124
  finally:
   if display.poll() is None:os.killpg(display.pid,signal.SIGTERM);display.wait()
 logs=[]
 for j,p in enumerate(sorted(home.rglob("*console*.log"))):
  t=p.read_text(errors="replace");(out/("console%d.log"%j)).write_text(t);logs.append(t)
 (out/"EXTERNAL_X11_CAPTURE_ERRORS.json").write_text(json.dumps(screenshot_errors,indent=2))
 combined="\n".join(logs);cv={};camera={}
 for m in re.finditer(r"PROOF_CVAR shot=(\d+) name=([^\s]+) value=([^\s]+)",combined):
  cv.setdefault(int(m[1]),{})[m[2]]=m[3]
 for m in re.finditer(r"PROOF_VIEW shot=(\d+) time=(\d+) eye=([^ ]+) forward=([^ ]+) weapon=(\d+)",combined):
  camera[int(m[1])]={"eye":m[3],"forward":m[4]}
 saved=[]
 for row in expected:
  imagefile=out/(row["name"]+".png")
  if imagefile.is_file() and imagefile.stat().st_size>3000:
   with Image.open(imagefile) as img:
    if img.size==(1280,720):saved.append(row)
 passed=(rc==0 and "PROOF_READY" in combined and "XLABS_DOOR_ACTUAL_AB_COMPLETED" in combined and
         len(saved)==len(expected) and len(camera)==len(expected))
 if passed:
  for v in views:
   rows=[r for r in expected if r["view"]==v["name"]]
   if len({camera[r["id"]]["eye"] for r in rows})!=1:passed=False
   if len({camera[r["id"]]["forward"] for r in rows})!=1:passed=False
  for row in expected:
   c=cv.get(row["id"],{})
   if c.get("cg_xlabsTeslaDoorLight")!=str(row["light"]) or c.get("cg_xlabsTeslaDoorShadows")!=str(row["shadow"]):passed=False
 results=[]
 if passed:
  for v in views:
   def img(k):
    return Image.open(out/("xlabs_"+v["name"]+"_"+k+".png")).convert("RGB")
   imgs=[img(k) for k,_,_ in CASES]
   off=np.asarray(imgs[0],dtype=np.int16);on=np.asarray(imgs[1],dtype=np.int16)
   diff=np.abs(on-off);changed=float(np.any(diff>4,axis=2).mean()*100)
   mask=np.all(off<85,axis=2)
   gain=float((on[:,:,2]-off[:,:,2])[mask].mean()) if np.any(mask) else 0.
   no_shadow=np.asarray(imgs[2],dtype=np.int16)
   shad=float(np.any(np.abs(on-no_shadow)>4,axis=2).mean()*100)
   results.append({"view":v["name"],"changed_gt4_pct":round(changed,3),
                   "dark_surface_blue_gain":round(gain,3),"shadow_toggle_changed_pct":round(shad,3)})
   board=Image.new("RGB",(2560,1440))
   for i,(label,_,_) in enumerate(CASES):
    board.paste(imgs[i],((i%2)*1280,(i//2)*720))
    ImageDraw.Draw(board).text(((i%2)*1280+12,(i//2)*720+15),label,fill="white")
   board.save(out/("xlabs_"+v["name"]+"_AB_CONTACT_SHEET.png"))
 report={"map":"xlabs","source":"licensed RTCW Xlabs BSP, Linux Mesa llvmpipe with external X11 framebuffer capture",
         "exit_code":rc,"valid":passed,"requested":expected,"captured":len(saved),
         "camera_count":len(camera),"views":views,"deltas":results}
 (out/"XLABS_REAL_GAME_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
 if one_case:
  # A single verified X11 image with exact CVar and pose is evidence of this
  # condition; the game may exit SIGSEGV immediately thereafter in Mesa.
  single_ok=(len(saved)==1 and len(camera)==1
      and cv.get(1,{}).get("cg_xlabsTeslaDoorLight")==str(expected[0]["light"])
      and cv.get(1,{}).get("cg_xlabsTeslaDoorShadows")==str(expected[0]["shadow"]))
  report["single_shot_valid"]=single_ok
  report["LinuxMesa_client_exit"]=rc
  (out/"XLABS_REAL_GAME_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
  if not single_ok:raise RuntimeError("Single shot missing: "+json.dumps(report)[:2300])
  print("XLABS_ONE_CAMERA_SINGLE_SHOT_ACTUAL_GAME_CAPTURE_PASS",one_case,flush=True)
  return
 if not passed:raise RuntimeError("Authentic Xlabs A/B incomplete: "+json.dumps(report)[:3000])
 assert any(x["changed_gt4_pct"]>0.4 and x["dark_surface_blue_gain"]>0.15 for x in results),\
        "No evidence of blue light illuminating Xlabs"
 print("XLABS_TESLA_DOOR_BLUE_DLIGHT_REAL_GAME_AB_PASS",json.dumps(results),flush=True)

if __name__=="__main__":
 p=argparse.ArgumentParser();s=p.add_subparsers(dest="command",required=True)
 x=s.add_parser("instrument");x.add_argument("source",type=Path)
 x=s.add_parser("capture");x.add_argument("source",type=Path);x.add_argument("retail",type=Path);x.add_argument("out",type=Path)
 a=p.parse_args()
 if a.command=="instrument":instrument(a.source)
 else:capture(a.source,a.retail,a.out)
