#!/usr/bin/env python3
"""Real RTCW screenshots, v03 all 3 effects on, no A/B or synthetic views."""
import math, json, sys, importlib.util
from pathlib import Path
from PIL import Image,ImageDraw

base=Path("integration/cas-a2c-lut/game_ab.py")
s=base.read_text()
assert '"set r_dwCasStrength 0.35"' in s and '"set r_dwLutStrength 0.35"' in s
s=s.replace('"set r_dwCasStrength 0.35"','"set r_dwCasStrength 0.55"')
s=s.replace('"set r_dwLutStrength 0.35"','"set r_dwLutStrength 0.80"')
patched=Path("integration/cas-a2c-lut/.gallery_runtime.py")
patched.write_text(s)
spec=importlib.util.spec_from_file_location("gallery_runtime",patched)
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
g.PROFILE={"ALL3":("1","1","1")}
g.MAPS=("factory","escape1","assault","crypt1","church","boss1","swf","crypt2","village1","forest")
from rc4_assault_camera import World

def camera_views(retail,name):
    world=World(g.maps_from(retail,name))
    groups={"fire":("torch","fire","flame","candle","burn","brazier","stove","furnace"),
            "lamp":("lamp","light"),"gate":("gate","iron","fence","grate","grill","door")}
    targets=[]
    starts=[]
    for idx,e in enumerate(world.entities):
        raw=e.get("origin")
        if not raw:continue
        try:target=[float(x) for x in raw.split()[:3]]
        except (ValueError,TypeError):continue
        if len(target)!=3:continue
        cls=e.get("classname","").lower()
        if cls.startswith("info_player"):starts.append(target)
        info=" ".join(str(x) for k,x in e.items() if k!="message").lower()
        category=next((key for key,words in groups.items() if any(w in info for w in words)),None)
        if not category and cls=="light":category="lamp"
        if category:targets.append((category,idx,target))
    views=[]
    def aim(label,target):
        for radius in (100.,165.,240.,320.):
            for dz in (0.,48.,-48.,96.):
                for deg in range(0,360,30):
                    a=math.radians(deg)
                    eye=[target[0]+radius*math.cos(a),target[1]+radius*math.sin(a),target[2]+dz]
                    if world.solid(eye):continue
                    if any(world.solid([eye[0]+dx,eye[1]+dy,eye[2]]) for dx,dy in ((12,0),(-12,0),(0,12),(0,-12))):continue
                    hit=world.trace(eye,target)
                    if hit and (hit.get("startsolid") or hit.get("fraction",1)<0.90):continue
                    d=[target[i]-eye[i] for i in range(3)]
                    pitch=-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1])))
                    yaw=math.degrees(math.atan2(d[1],d[0]))%360
                    views.append({"name":label,"eye":eye,"angles":[pitch,yaw,0.],"target":target})
                    return True
        return False
    if name=="factory":
        for view in g.photo.views("factory"):
            if not world.solid(view["eye"]):views.append(dict(view))
    if name=="assault": priority=("gate","lamp","fire")
    else: priority=("fire","lamp","gate")
    targets.sort(key=lambda v:(priority.index(v[0]),v[1]))
    counts={"fire":0,"lamp":0,"gate":0}
    for group,idx,point in targets:
        if len(views)>=5:break
        if counts[group]>=2:continue
        if aim(f"{name}_{group}_entity{idx}",point):counts[group]+=1
    for idx,point in enumerate(starts[:6]):
        if len(views)>=3:break
        aim(f"{name}_spawn{idx}",point)
    if not views:raise RuntimeError("NO_VALID_CAMERA "+name)
    return views[:5]

def compare(out,maps,results):
    items=[]
    canvas_shots=[]
    for mapname,views in maps.items():
        report=results[mapname]["ALL3"]
        assert report["ready"] and report["complete"] and len(report["images"])==len(views)
        for view in views:
            path=out/report["images"][view["name"]]
            img=Image.open(path).convert("RGB")
            items.append({"map":mapname,"name":view["name"],"file":path.name,
                          "size":list(img.size),"eye":view["eye"],"angles":view["angles"]})
            canvas_shots.append((mapname,view["name"],img))
    count=len(canvas_shots)
    assert count>=15
    (out/"GALLERY_MANIFEST.json").write_text(json.dumps(
        {"mode":"ALL3 ONLY","CAS":0.55,"LUT":0.80,"A2C":1,"MSAA":4,
         "maps":sorted(maps),"shots":items,"source":"actual game runtime under Mesa GL",
         "no_AB":True,"windows_fps":"NOT_RUN"},indent=2)+"\n")
    thumb=(480,270);canvas=Image.new("RGB",(960,310*((count+1)//2)),(18,18,18))
    draw=ImageDraw.Draw(canvas)
    for i,(m,name,img) in enumerate(canvas_shots):
        x=(i%2)*480;y=(i//2)*310
        draw.text((x+6,y+7),name,fill="white")
        canvas.paste(img.resize(thumb),(x,y+34))
    canvas.save(out/"GALLERY_ALL3_MONTAGE.png")
    print("GALLERY_ALL3_VERIFIED",count,flush=True)

g.camera_views=camera_views
g.compare=compare
g.main()
