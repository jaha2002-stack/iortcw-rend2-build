#!/usr/bin/env python3
"""Actual Escape1 / Xlabs rendered A/B of 0/1/2 selective containment modes.
Source-only diagnostic camera and Tesla activation; renderer remains production
byte-identical to the Win64 candidate. Uses legally supplied testlab pk3 only.
"""
from pathlib import Path
import argparse,os,re,math,signal,subprocess,shutil,sys,zipfile,json,hashlib
from PIL import Image,ImageDraw
import numpy as np
sys.path.insert(0,str(Path("testlab/scripts").resolve()))
import rc4_requested_views as proof
from rc4_assault_camera import World

MAPS=("escape1","xlabs")
MODES=(("original_0",0),("fire_only_1",1),("fire_tesla_2",2),("original_repeat_0",0))
ESCAPE_POSES=[
 ("stove_interior",[-1340.,760.,-50.],[7.,306.,0.],"fire"),
 ("stove_exterior",[-1100.,692.,-90.],[40.,180.,0.],"wall-leak"),
 ("tesla_room",[120.,560.,-510.],[3.,300.,0.],"tesla")
]
def checksum(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def edit(path,old,new):
 s=path.read_text()
 assert s.count(old)==1,(str(path),"expected unique anchor",s.count(old))
 path.write_text(s.replace(old,new,1))

def instrument(root):
 code=root/"SP/code"
 before={str(p.relative_to(code)):checksum(p) for p in (code/"rend2").rglob("*") if p.is_file()}
 proof.instrument(root)
 g=code/"game/g_cmds.c"
 helper=r'''
/* TESLA_FIRE_HARMONY_TESTLAB_ONLY: authored trigger, never a synthetic light. */
static void Cmd_DWProofActivateTesla_f(gentity_t *ent) {
    int i,count=0;
    if (!g_cheats.integer || !ent || !ent->client) return;
    for (i=0;i<level.num_entities;i++) {
        gentity_t *e=&g_entities[i];
        if (!e->inuse || !e->classname || Q_stricmp(e->classname,"shooter_tesla") || !e->use || e->r.linked)
            continue;
        e->use(e,ent,ent);
        count++;
    }
    G_Printf("TESLA_PROOF_ACTIVATE_REAL_SHOOTERS count=%d\n",count);
}
static void Cmd_DWProofUseTarget_f(gentity_t *ent) {
    char name[MAX_TOKEN_CHARS];gentity_t *e=NULL;int count=0;
    if (!g_cheats.integer || trap_Argc()!=2) return;
    trap_Argv(1,name,sizeof(name));
    while ((e=G_Find(e,FOFS(targetname),name))!=NULL) {
        if (e->use && !e->r.linked) { e->use(e,ent,ent);count++; }
    }
    G_Printf("TESLA_PROOF_TARGET_USE name=%s count=%d\n",name,count);
}
'''
 edit(g,"static void Cmd_ProofView_f(gentity_t *ent) {",helper+"static void Cmd_ProofView_f(gentity_t *ent) {")
 a='} else if ( Q_stricmp( cmd, "proofView" ) == 0 ) {'
 b='} else if ( Q_stricmp( cmd, "proofActivateTesla" ) == 0 ) {\n        Cmd_DWProofActivateTesla_f(ent);\n    } else if ( Q_stricmp( cmd, "proofUseTarget" ) == 0 ) {\n        Cmd_DWProofUseTarget_f(ent);\n    '+a
 edit(g,a,b)
 # Force deterministic client effect pseudo-randomness on the *same* frozen time.
 cg=code/"cgame/cg_view.c"
 old='CG_AddPacketEntities();         // adter calcViewValues, so predicted player state is correct'
 if cg.read_text().count(old)==1:
  edit(cg,old,'{ char frozen[16]; trap_Cvar_VariableStringBuffer("dw_proofFreeze",frozen,sizeof(frozen)); if (atoi(frozen)) srand((unsigned int)cg.time); }\n        '+old)
 edit(cg,'static const char *names[]={"r_ssgi","r_volumetricSun"',
      'static const char *names[]={"r_dlightWorldContainment","r_ssgi","r_volumetricSun"')
 after={str(p.relative_to(code)):checksum(p) for p in (code/"rend2").rglob("*") if p.is_file()}
 assert before==after,"TestLab touched renderer, invalid production proof"
 print("SELECTIVE_CONTAINMENT_TESTLAB_SOURCE_INSTRUMENTED_RENDERER_UNCHANGED",len(before),flush=True)

def retail_map(retail,name):
 for pk3 in sorted(retail.glob("*.pk3")):
  with zipfile.ZipFile(pk3) as z:
   for key in z.namelist():
    if key.lower()=="maps/"+name+".bsp":return z.read(key)
 raise RuntimeError("Missing licensed retail map "+name)

def pick_xlabs(world):
 teslas=[]
 for e in world.entities:
  typ=e.get("classname","").lower()
  if "tesla" not in typ or "origin" not in e:continue
  try:xyz=[float(x) for x in e["origin"].split()]
  except ValueError:continue
  if len(xyz)!=3:continue
  teslas.append((typ,xyz))
 if not teslas:
  raise RuntimeError("Xlabs has no source-verified Tesla BSP entity; cannot claim Tesla screenshot")
 locations=[]
 for typ,tar in teslas:
  for rad in (92.,128.,164.,220.):
   for angle in range(0,360,30):
    ang=math.radians(angle)
    for dz in (12.,36.,-12.):
     eye=[round(tar[0]+rad*math.cos(ang),3),round(tar[1]+rad*math.sin(ang),3),round(tar[2]+dz,3)]
     if world.solid(eye):continue
     hit=world.trace(eye,tar)
     visible=1.0 if hit is None else float(hit["fraction"])
     if visible<0.9:continue
     yaw=math.degrees(math.atan2(tar[1]-eye[1],tar[0]-eye[0]))%360
     pitch=-math.degrees(math.atan2(tar[2]-eye[2],rad))
     score=(visible-0.001*rad)
     locations.append((score,typ,eye,[pitch,yaw,0.],tar))
 if not locations:raise RuntimeError("Xlabs Tesla exists but no safe visible proof camera")
 locations.sort(key=lambda x:x[0],reverse=True)
 x=locations[0]
 return [("xlabs_tesla_fixture",x[2],x[3],x[1])],teslas

def game_capture(src,retail,out,mapname):
 out.mkdir(parents=True,exist_ok=True)
 data=retail_map(retail,mapname);w=World(data)
 if mapname=="escape1":poses=ESCAPE_POSES;teslas=[(e.get("classname"),e.get("origin")) for e in w.entities if "tesla" in e.get("classname","").lower()]
 else:poses,teslas=pick_xlabs(w)
 (out/"TESLA_MAP_FIXTURES.json").write_text(json.dumps({"map":mapname,"Tesla_entities":teslas,"views":poses},indent=2))
 runtime=Path("harmony-runtime-"+mapname).resolve()
 shutil.rmtree(runtime,ignore_errors=True)
 main=runtime/"main";main.mkdir(parents=True)
 build=src/"SP/build/release-linux-x86_64"
 assert build.is_dir() and (build/"main").is_dir(),str(build)
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/"main").glob("*.so"):shutil.copy2(p,main/p.name)
 for pk3 in retail.glob("*.pk3"):
  (main/pk3.name.lower()).symlink_to(pk3.resolve())
 setup=[
 "set r_renderer rend2","set cl_renderer rend2","set r_mode -1","set r_customwidth 1280","set r_customheight 720","set r_fullscreen 0",
 "set r_postProcess 1","set r_hdr 1","set r_bloom 1","set r_bloomMode 2",
 "set r_dwCas 1","set r_dwCasStrength 0.55","set r_dwLut 1","set r_dwLutStrength 0",
 "set r_dwA2C 1","set r_dwTextureFidelity 1","set r_dwMaterialFidelity 1",
 "set r_ssgi 1","set r_ssgiBrightSourceFix 2","set r_forceSun 1","set r_sunShadows 1","set r_dlightMode 2",
 "set r_volumetricSun 1","set r_volumetricLocal 1","set r_volumetricFire 1",
 "set r_dlightShadowMaxLights 3","set r_dlightWorldContainment 0",
 "set r_autoExposure 0","set r_forceAutoExposure 0","set r_picmip 0","set r_picmip2 0",
 "set s_initsound 0","set r_swapInterval 0","set fixedtime 100",
 "set cg_draw2D 0","set cg_drawGun 0","set con_notifytime -1",
 ]
 scenario=["set cg_draw2D 0","set cg_drawGun 0","set con_notifytime -1",
           "set cg_bobup 0","set cg_bobpitch 0","set cg_bobroll 0",
           "god","notarget","wait 16","proofActivateTesla",
           "proofUseTarget t1055","proofUseTarget t1012","proofUseTarget t1008","wait 30"]
 shots=[]
 counter=0
 for name,eye,angles,category in poses:
  scenario+=["set dw_proofFreeze 0","proofView "+" ".join(f"{x:.4f}" for x in eye+angles),
             "wait 28","set dw_proofFreeze 1","wait 5"]
  for variant,mode in MODES:
   counter+=1
   shot=mapname+"_"+name+"_"+variant
   scenario+=["set r_dlightWorldContainment "+str(mode),"wait 16",
              "set dw_proofShot "+str(counter),"wait 4","screenshot "+shot,"wait 3"]
   shots.append({"name":shot,"view":name,"mode":mode,"category":category,"id":counter})
 scenario+=["set dw_proofFreeze 0","echo FIRE_TESLA_SELECTIVE_REALGAME_COMPLETED","quit"]
 (main/"HARMONY_SETUP.cfg").write_text("\n".join(setup)+"\n")
 (main/"HARMONY_SCENARIO.cfg").write_text("\n".join(scenario)+"\n")
 (out/"SCENARIO.cfg").write_text("\n".join(scenario)+"\n")
 (out/"SETUP.cfg").write_text("\n".join(setup)+"\n")
 exe=next(x for x in runtime.iterdir() if x.name.lower().startswith("iowolfsp") and x.is_file())
 exe.chmod(0o755)
 home=runtime/"home";home.mkdir()
 cmd=["xvfb-run","-a","-s","-screen 0 1600x900x24",str(exe),
      "+safe","+set","fs_basepath",str(runtime),"+set","fs_homepath",str(home),
      "+set","com_introplayed","1","+set","com_recommendedSet","1",
      "+set","logfile","2","+set","dw_proofAutomation","1",
      "+set","r_renderer","rend2","+set","cl_renderer","rend2",
      "+exec","HARMONY_SETUP.cfg","+vid_restart",
      "+set","dw_proofScenario","HARMONY_SCENARIO.cfg","+spdevmap",mapname]
 env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ("TOKEN","PASSWORD","CREDENTIAL","SECRET"))}
 env.update(LIBGL_ALWAYS_SOFTWARE="1",LP_NUM_THREADS="2",SDL_AUDIODRIVER="dummy")
 with (out/"stdout.log").open("w") as log:
  proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:exit_code=proc.wait(timeout=900)
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGKILL);proc.wait();exit_code=124
 logs=[]
 for i,p in enumerate(sorted(home.rglob("*console*.log"))):
  t=p.read_text(errors="replace")
  (out/("console_"+str(i)+".log")).write_text(t)
  logs.append(t)
 combined="\n".join(logs)
 cvar={}
 poses_actual={}
 for m in re.finditer(r"PROOF_CVAR shot=(\d+) name=([^\s]+) value=([^\s]+)",combined):
  cvar.setdefault(int(m[1]),{})[m[2]]=m[3]
 for m in re.finditer(r"PROOF_VIEW shot=(\d+) time=(\d+) eye=([^ ]+) forward=([^ ]+) weapon=(\d+)",combined):
  poses_actual[int(m[1])]=dict(time=int(m[2]),eye=m[3],forward=m[4])
 captured=[]
 for shot in shots:
  paths=list(home.rglob(shot["name"]+".tga"))
  if len(paths)!=1:continue
  img=Image.open(paths[0]).convert("RGB")
  img.save(out/(shot["name"]+".png"))
  captured.append({**shot,"pixels":list(img.size)})
 ready="PROOF_READY" in combined and "FIRE_TESLA_SELECTIVE_REALGAME_COMPLETED" in combined
 passed=exit_code==0 and ready and len(captured)==len(shots) and len(poses_actual)==len(shots)
 evidence={"map":mapname,"exit":exit_code,"ready":ready,"expected":len(shots),
           "captured":captured,"poses":poses_actual,"cvars":cvar,
           "real_retail":True,"renderer_source_unmodified_by_testlab":True,
           "sdl":"Linux Mesa llvmpipe and Xvfb; not Windows GPU"}
 for shot in shots:
  if str(cvar.get(shot["id"],{}).get("r_dlightWorldContainment",""))!=str(shot["mode"]):passed=False
 for name,*_ in poses:
  views=[a for a in shots if a["view"]==name]
  if len({poses_actual.get(a["id"],{}).get("eye") for a in views})!=1:passed=False
  if len({poses_actual.get(a["id"],{}).get("forward") for a in views})!=1:passed=False
 deltas=[]
 if passed:
  for name,*_ in poses:
   a={x["mode"]:None for x in shots if x["view"]==name}
   grouping={x["name"].split(name+"_")[-1]:x["name"] for x in shots if x["view"]==name}
   names=["original_0","fire_only_1","fire_tesla_2","original_repeat_0"]
   imgs=[Image.open(out/(mapname+"_"+name+"_"+variant+".png")).convert("RGB") for variant in names]
   base=np.asarray(imgs[0],dtype=np.int16)
   values={}
   for k,other in zip(names[1:],imgs[1:]):
    diff=np.abs(base-np.asarray(other,dtype=np.int16))
    values[k]={"mean_abs_rgb":float(diff.mean()),"pixel_changed_over4_percent":float(np.any(diff>4,axis=2).mean()*100)}
   deltas.append({"view":name,**values})
   sheet=Image.new("RGB",(1280*2,720*2))
   for i,img in enumerate(imgs):
    sheet.paste(img,((i%2)*1280,(i//2)*720))
    ImageDraw.Draw(sheet).text(((i%2)*1280+14,(i//2)*720+15),names[i],fill="white")
   sheet.save(out/(mapname+"_"+name+"_AB_CONTACT_SHEET.png"))
 evidence["valid"]=passed;evidence["differences"]=deltas
 (out/"REALGAME_RESULT.json").write_text(json.dumps(evidence,indent=2)+"\n")
 if not passed:raise RuntimeError("Real game capture incomplete "+json.dumps({"map":mapname,"exit":exit_code,"ready":ready,"captured":len(captured),"expected":len(shots),"proof_views":len(poses_actual)},sort_keys=True))
 print("TESLA_FIRE_REAL_RETAIL_MODE_0_1_2_AB_CAPTURE_PASS",mapname,len(shots),len(poses),flush=True)

if __name__=="__main__":
 p=argparse.ArgumentParser()
 sub=p.add_subparsers(dest="cmd",required=True)
 sub.add_parser("instrument").add_argument("source",type=Path)
 x=sub.add_parser("capture")
 x.add_argument("source",type=Path);x.add_argument("retail",type=Path)
 x.add_argument("out",type=Path);x.add_argument("map",choices=MAPS)
 a=p.parse_args()
 if a.cmd=="instrument":instrument(a.source)
 else:game_capture(a.source,a.retail,a.out,a.map)
