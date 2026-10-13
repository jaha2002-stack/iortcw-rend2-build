#!/usr/bin/env python3
"""Locate actual furnace-room BSP walls, not guessed compass facades.

Collision uses opaque (CONTENTS_SOLID) world brushes from original escape1 BSP.
Reports wall intersection, free camera origin, and downward ground collision.
No copyrighted map geometry leaves the CI runner.
"""
import json,math,struct,sys,zipfile
from pathlib import Path

retail=Path(sys.argv[1]); out=Path(sys.argv[2])
out.parent.mkdir(parents=True,exist_ok=True)
pak=next((x for x in retail.iterdir() if x.name.lower()=='pak0.pk3'),None)
assert pak is not None
with zipfile.ZipFile(pak) as z:
    bsp=z.read('maps/escape1.bsp')
magic,version=struct.unpack_from('<4si',bsp,0)
assert magic==b'IBSP' and version==47,(magic,version)
lumps=[struct.unpack_from('<ii',bsp,8+8*i) for i in range(17)]
def lump(i,n):
    o,length=lumps[i]
    assert length%n==0,(i,length,n)
    return [bsp[o+j:o+j+n] for j in range(0,length,n)]
shaders=[struct.unpack('<64sii',b) for b in lump(1,72)]
planes=[struct.unpack('<4f',b) for b in lump(2,16)]
nodes=[struct.unpack('<9i',b) for b in lump(3,36)]
leafs=[struct.unpack('<12i',b) for b in lump(4,48)]
brushsides=[struct.unpack('<ii',b) for b in lump(9,8)]
raw_brushes=[struct.unpack('<iii',b) for b in lump(8,12)]
solid=[]
for bi,(first,num,shader) in enumerate(raw_brushes):
    if shader<0 or shader>=len(shaders) or not(shaders[shader][2]&1):continue
    # Weapon-only collision brushes are not opaque visual walls and often
    # enclose the stove entity. Exclude them from architectural BSP traces.
    name=shaders[shader][0].split(b'\\0')[0].decode('latin1').lower()
    if name.startswith('textures/common/') and any(k in name for k in ('clip', 'trigger', 'nodraw', 'hint', 'skip', 'origin')):continue
    sides=[planes[brushsides[k][0]] for k in range(first,first+num)]
    if not sides:continue
    minimum=[-1e12]*3; maximum=[1e12]*3
    for normalx,normaly,normalz,dist in sides:
        normal=(normalx,normaly,normalz)
        for ax in range(3):
            other=sorted(abs(normal[q]) for q in range(3) if q!=ax)
            if abs(abs(normal[ax])-1.0)<1e-4 and all(t<1e-4 for t in other):
                if normal[ax]>0:maximum[ax]=min(maximum[ax],dist)
                else:minimum[ax]=max(minimum[ax],-dist)
    solid.append((bi,sides,minimum,maximum,shaders[shader][0].split(b'\0')[0].decode('latin1')))
print('STOVE_BSP_PARSE',json.dumps(dict(version=version,brushes=len(raw_brushes),solid=len(solid),planes=len(planes),leafs=len(leafs))))
def leafat(pt):
    node=0
    for _ in range(100):
        if node<0:
            l=leafs[-1-node];return {'leaf':-1-node,'cluster':l[0],'area':l[1]}
        plane,front,back,*_=nodes[node]
        a,b,c,d=planes[plane]
        signed=a*pt[0]+b*pt[1]+c*pt[2]-d
        node=front if signed>=0 else back
    raise RuntimeError('BSP node cycle')
def dot(v,n):
    return v[0]*n[0]+v[1]*n[1]+v[2]*n[2]
def overlaps(minimum,maximum,start,end):
    return all(not (max(start[i],end[i])<minimum[i]-0.1 or min(start[i],end[i])>maximum[i]+0.1) for i in range(3))
def trace(start,end):
    winner=None;best=1.001
    for idx,sides,minimum,maximum,shname in solid:
        if not overlaps(minimum,maximum,start,end):continue
        enter=-1.0;leave=2.0;normalhit=None;start_inside=True;reject=False
        for x,y,z,d in sides:
            n=(x,y,z)
            ds=dot(start,n)-d;de=dot(end,n)-d
            if ds>0:start_inside=False
            if ds>0 and de>0:reject=True;break
            if ds<=0 and de<=0:continue
            if abs(ds-de)<1e-8:continue
            f=ds/(ds-de)
            if ds>de and f>enter:enter=f;normalhit=n
            elif ds<de and f<leave:leave=f
            if enter>leave:reject=True;break
        if reject:continue
        if start_inside:
            # A ray starting inside a solid brush cannot define a real exterior wall.
            return {'fraction':0,'hit':list(start),'normal':None,'brush':idx,'shader':shname,'start_solid':True}
        if 0<=enter<=1 and enter<=leave and enter<best:
            best=enter
            winner={'fraction':round(enter,5),'hit':[round(start[k]+(end[k]-start[k])*enter,2) for k in range(3)],
                    'normal':[round(t,3) for t in normalhit] if normalhit else None,
                    'brush':idx,'shader':shname,'start_solid':False}
    return winner
furnace=[-1226.,602.,-48.]
rays=[]
for i in range(32):
    ang=i*2*math.pi/32
    vx,vy=math.cos(ang),math.sin(ang)
    start=furnace
    end=[furnace[0]+vx*560, furnace[1]+vy*560, furnace[2]]
    wall=trace(start,end)
    row={'index':i,'angle_deg':round(i*11.25,2),'wall':wall}
    if wall is not None and not wall.get('start_solid') and wall['fraction']*560<420:
        hit=wall['hit']
        row['furnace_to_wall_units']=round(math.dist(start,hit),1)
        possible=[]
        for offset in (80.,100.,118.):
            xx=hit[0]+vx*offset; yy=hit[1]+vy*offset
            floor=trace([xx,yy,300.],[xx,yy,-400.])
            if floor is None or floor.get('start_solid'):continue
            ground_z=floor['hit'][2]
            if not (-500<ground_z<200):continue
            eye=[round(xx,2),round(yy,2),round(ground_z+58,2)]
            check=trace(eye,hit)
            ground_below=trace([xx,yy,ground_z+58],[xx,yy,ground_z-10])
            possible.append(dict(offset=offset,camera=eye,ground_z=ground_z,
                                 floor_shader=floor['shader'],floor_normal=floor['normal'],
                                 camera_leaf=leafat(eye),towards_stove=check,
                                 downtrace=ground_below))
        row['exterior_camera_options']=possible
    rays.append(row)
result={'schema':1,'map':'escape1','model':'models/mapobjects/furniture/furnace.md3',
        'model_origin':[-1226,602,-64],'source_point':furnace,
        'scale_note':'80-118 BSP units are approximately 2-3m if 1 unit is 1 inch',
        'furnace_leaf':leafat(furnace),'rays':rays}
out.write_text(json.dumps(result,indent=2)+'\n')
print('STOVE_BSP_FACADE_CANDIDATES',json.dumps([
 {'deg':r['angle_deg'],'dist':r.get('furnace_to_wall_units'),
  'wall':r.get('wall'),'cam':r.get('exterior_camera_options',[None])[0]}
 for r in rays if r.get('exterior_camera_options')
],separators=(',',':'))[:27000])
