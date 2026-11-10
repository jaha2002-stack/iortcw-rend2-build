#!/usr/bin/env python3
"""Crypt1 BSP near-spawn grate: collision-safe camera probes + authored mesh facts.
Licensed retail PK3 stays only on temporary runner; emit derived metadata.
"""
from pathlib import Path
import json,zipfile,struct,math,re,sys
sys.path.insert(0,str(Path("testlab/scripts").resolve()))
from rc4_assault_camera import World

SPAWN_EYE=[-192.,1664.,512.125]
DIRECTION=[-1.,0.,0.]
def get_bsp(retail):
    for p in sorted(retail.glob("*.pk3")):
        with zipfile.ZipFile(p) as z:
            names=[s for s in z.namelist() if s.lower()=="maps/crypt1.bsp"]
            if names:return z.read(names[0]),p.name
    raise RuntimeError("Retail crypt1 map not found")
def near(point, bbox,rad):
    return all(bbox[i]-rad <= point[i] <= bbox[i+3]+rad for i in range(3))
def main():
    retail=Path(sys.argv[1]); output=Path(sys.argv[2])
    data,origin=get_bsp(retail); world=World(data)
    def lump(i):
        pos,n=struct.unpack_from('<ii',data,8+i*8)
        return data[pos:pos+n]
    verts=lump(10);surfs=lump(13)
    assert len(verts)%44==0 and len(surfs)%104==0
    def vertex_xyz(i):
        return struct.unpack_from('<3f',verts,i*44)
    materials=[s[0].split(b'\0')[0].decode('latin-1') for s in world.shaders]
    extracted=[]
    # Geometry gate region: strip 300+ units along -X behind initial player.
    for idx in range(len(surfs)//104):
        vals=struct.unpack_from('<12i12f2i',surfs,idx*104)
        sh,fog,typ,fv,nv,fi,ni,lm=vals[:8]
        if not (0<=sh<len(materials)) or not (0<=fv<len(verts)//44) or nv<1 or nv>10000:continue
        loc=[vertex_xyz(i) for i in range(fv,fv+nv)]
        lo=[min(v[i] for v in loc) for i in range(3)]
        hi=[max(v[i] for v in loc) for i in range(3)]
        # Include any geometry within a 400u box of spawn or spanning the grate plane.
        bbox=lo+hi
        if not near(SPAWN_EYE,bbox,425):continue
        center=[(lo[i]+hi[i])/2 for i in range(3)]
        d=math.dist(center,SPAWN_EYE)
        extracted.append(dict(index=idx,shader=materials[sh],type=typ,vertices=nv,triangles=ni//3,
                              lightmap=lm,min_xyz=[round(x,2) for x in lo],max_xyz=[round(x,2) for x in hi],
                              center_distance=round(d,2)))
    extracted.sort(key=lambda d:d["center_distance"])
    names=("gate","grate","fence","bar","iron","metal","crypt","spike","portcullis")
    likely=sorted(extracted,key=lambda d:(not any(x in d["shader"].lower() for x in names),d["center_distance"]))
    objects=[]
    for index,obj in enumerate(world.entities):
        pos=obj.get("origin","")
        try:
            xyz=list(map(float,pos.split()))
            if len(xyz)!=3:continue
        except (ValueError,TypeError):continue
        dist=math.dist(xyz,SPAWN_EYE)
        if dist>650:continue
        objects.append(dict(index=index,classname=obj.get("classname"),model=obj.get("model"),
                            model2=obj.get("model2"),origin=xyz,angles=obj.get("angles"),
                            targetname=obj.get("targetname"),distance=round(dist,1)))
    objects.sort(key=lambda x:x["distance"])
    selected=[]
    trace_by_z={}
    for zoff in (0,-24,-48,24):
        start=[SPAWN_EYE[0],SPAWN_EYE[1],SPAWN_EYE[2]+zoff]
        end=[start[0]-425,start[1],start[2]]
        hit=world.trace(start,end)
        trace_by_z[str(zoff)]=hit
    for units in (0,12,24,36,48,60,72,88,104,120,144,168,192):
        p=[SPAWN_EYE[0]-units,SPAWN_EYE[1],SPAWN_EYE[2]]
        checks=[[0,0,0],[8,0,0],[-8,0,0],[0,8,0],[0,-8,0],[0,0,-16]]
        if any(world.solid([p[i]+offset[i] for i in range(3)]) for offset in checks):continue
        if units>0:
            hit=world.trace(SPAWN_EYE,p)
            if hit and hit.get("fraction",1.0)<0.999:continue
        # Actual player eye offset is 40 in TestLab.
        selected.append(dict(eye=p,offset_from_spawn=units,cluster=world.leaf(p)[0],
                             direction_behind_spawn="negative-X",allowed=True))
    if not selected:raise RuntimeError("No non-solid near-grate camera candidates")
    result=dict(schema=1,map="crypt1",source_pk3=origin,spawn_eye=SPAWN_EYE,
        backwards_yaw=180,collision_trace=trace_by_z,collision_valid_cameras=selected,
        nearby_bsp_surfaces=extracted[:220],surface_count_nearby=len(extracted),
        prioritized_grate_materials=likely[:80],nearby_entities=objects[:140],
        num_entities=len(world.entities),num_bsp_surfaces=len(surfs)//104,num_bsp_verts=len(verts)//44,
        limitations="BSP surface index, material and collision metadata only; MD3 model topology and authored shader stages are not inferred.")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ["source_pk3","spawn_eye","collision_trace","collision_valid_cameras","surface_count_nearby","num_bsp_surfaces"]},indent=2),flush=True)
    print("CRYPT1_GRATE_BSP_COLLISION_AND_SURFACE_INVENTORY_PASS",len(selected),len(extracted),len(objects),flush=True)
if __name__=="__main__":main()
