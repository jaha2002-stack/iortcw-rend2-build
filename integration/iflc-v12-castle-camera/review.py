#!/usr/bin/env python3
"""Additional Castle opening-room view, derived floor projection, same controls.
Changes neither production code nor any shadow policy. No game assets exported.
"""
import argparse,importlib.util,json,math,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('iflc12_runtime',ROOT/'integration/iflc-v12/runtime.py')
rt=importlib.util.module_from_spec(spec);spec.loader.exec_module(rt)
proof={}
def opening_view(data,mapname):
 assert mapname=='castle'
 world=rt.World(data)
 def lump(i):
  o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
 vv=list(struct.iter_unpack('<10f4B',lump(10)));ss=list(struct.iter_unpack('<12i12f2i',lump(13)))
 index=7730;s=ss[index];vertices=vv[s[3]:s[3]+s[4]]
 anchor=[sum(v[k] for v in vertices)/len(vertices) for k in range(3)]
 start=next(list(map(float,e['origin'].split())) for e in world.entities if e.get('classname')=='info_player_start')
 candidates=[]
 for dx in (-256,-224,-288):
  for dy in (0,-32,32):
   eye=[start[0]+dx,start[1]+dy,start[2]+24]
   hit=world.trace(eye,anchor)
   if world.solid(eye) or hit and (hit.get('startsolid') or hit.get('fraction',0)<.92):continue
   candidates.append((abs(dx+256)+abs(dy),eye,hit))
 assert candidates,'Opening-room camera is obstructed'
 _,eye,hit=min(candidates,key=lambda x:x[0])
 target=[anchor[0],anchor[1]+64,anchor[2]-80]
 direction=[eye[k]-anchor[k] for k in range(3)];norm=math.sqrt(sum(v*v for v in direction))
 probe=[anchor[k]+direction[k]*32/norm for k in range(3)]
 if world.solid(probe):probe=eye
 light=world.entities[349];assert light.get('classname')=='dlight'
 origin=list(map(float,light['origin'].split()))
 floor_from=[origin[0],origin[1],-200.0];floor_to=[origin[0],origin[1],-1200.0]
 floor=world.trace(floor_from,floor_to)
 assert floor and not floor.get('startsolid') and floor.get('normal',[0,0,0])[2]>.99
 bottom=set()
 for i in range(3672,3676):
  row=ss[i];bottom.update(tuple(v[:3]) for v in vv[row[3]:row[3]+row[4]])
 rim_z=max(v[2] for v in bottom);floor_z=floor['position'][2]
 points=[]
 for v in sorted(bottom):
  if abs(v[2]-rim_z)>.001:continue
  scale=(floor_z-origin[2])/(v[2]-origin[2]);points.append([origin[k]+scale*(v[k]-origin[k]) for k in range(3)])
 proof.update(native_ordinal=349,source_origin=origin,floor_collision=floor,bottom_rim_z=rim_z,
  projected_bottom_rim_on_floor=points,projected_bounds=[[min(v[k] for v in points) for k in range(3)],[max(v[k] for v in points) for k in range(3)]],
  camera_eye=eye,camera_flame_ray=hit,
  limitations='Geometric projection of solid bottom from native point source onto actual collision floor plane, before other casters/attenuation/PCF. Game screenshots and individual-caster bypasses supply the render evidence; this calculation is not itself a visual PASS.')
 return [{'surface':index,'anchor':anchor,'shader':world.shaders[s[0]][0].split(b'\0')[0].decode('latin1'),'eye':eye,'select_angles':rt.angles(eye,anchor),'angles':rt.angles(eye,target),'name':'castle_opening_7730','probe':probe}]
rt.discover=opening_view
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('retail',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 try:rt.capture(a.source.resolve(),a.retail.resolve(),a.output.resolve(),'castle')
 finally:
  a.output.mkdir(parents=True,exist_ok=True)
  (a.output/'CASTLE_POINT_PROJECTION.json').write_text(json.dumps(proof,indent=2)+'\n')
