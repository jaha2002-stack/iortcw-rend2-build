#!/usr/bin/env python3
"""Select in-world, directly sun-exposed views using the actual Assault BSP.
Only camera validation metadata is exported. Retail bytes remain local.
"""
from pathlib import Path
import math, re, struct, zipfile

class World:
    def __init__(self, data):
        if data[:4] != b'IBSP':
            raise ValueError('Expected an IBSP map')
        self.data=data
        def lump(i):
            offset,length=struct.unpack_from('<ii',data,8+i*8)
            return data[offset:offset+length]
        self.entities=[dict(re.findall(r'"([^"\n]+)"\s*"([^"\n]*)"',x)) for x in re.findall(r'\{([^{}]*)\}',lump(0).decode('latin1'))]
        self.shaders=list(struct.iter_unpack('<64sii',lump(1)))
        self.planes=list(struct.iter_unpack('<4f',lump(2)))
        self.nodes=list(struct.iter_unpack('<9i',lump(3)))
        self.leaves=list(struct.iter_unpack('<12i',lump(4)))
        self.leafbrush=[x[0] for x in struct.iter_unpack('<i',lump(6))]
        self.brushes=list(struct.iter_unpack('<3i',lump(8)))
        self.sides=list(struct.iter_unpack('<2i',lump(9)))
        self.bounds=struct.unpack_from('<6f',lump(7))
    @staticmethod
    def distance(p, plane):
        return p[0]*plane[0]+p[1]*plane[1]+p[2]*plane[2]-plane[3]
    def leaf(self,p):
        n=0
        while n>=0:
            row=self.nodes[n];n=row[1 if self.distance(p,self.planes[row[0]])>=0 else 2]
        return self.leaves[-n-1]
    def solid(self,p):
        leaf=self.leaf(p)
        if leaf[0]<0: return True
        for j in range(leaf[10],leaf[10]+leaf[11]):
            first,count,shader=self.brushes[self.leafbrush[j]]
            if not self.shaders[shader][2]&1:continue
            if all(self.distance(p,self.planes[self.sides[k][0]]) < -0.05 for k in range(first,first+count)):
                return True
        return False
    def trace(self,a,b):
        todo=[(0,0.0,1.0)];brush_ids=set();direction=[b[k]-a[k] for k in range(3)]
        while todo:
            node,t0,t1=todo.pop()
            if node<0:
                leaf=self.leaves[-node-1]
                brush_ids.update(self.leafbrush[leaf[10]:leaf[10]+leaf[11]])
                continue
            row=self.nodes[node];plane=self.planes[row[0]]
            p0=[a[k]+direction[k]*t0 for k in range(3)];p1=[a[k]+direction[k]*t1 for k in range(3)]
            d0=self.distance(p0,plane);d1=self.distance(p1,plane)
            if d0>=0 and d1>=0:todo.append((row[1],t0,t1))
            elif d0<0 and d1<0:todo.append((row[2],t0,t1))
            else:
                t=t0+(t1-t0)*(d0/(d0-d1))
                near,far=(row[1],row[2]) if d0>=0 else (row[2],row[1])
                todo.append((far,t,t1));todo.append((near,t0,t))
        nearest=None
        for bid in brush_ids:
            first,count,shader=self.brushes[bid]
            if not self.shaders[shader][2]&1:continue
            enter=-1.0;leave=1.0;hit_side=None;outside=False;miss=False
            for k in range(first,first+count):
                pi,si=self.sides[k];plane=self.planes[pi]
                da=self.distance(a,plane);db=self.distance(b,plane)
                if da>0:outside=True
                if da>0 and db>0:miss=True;break
                if da<=0 and db<=0:continue
                t=da/(da-db)
                if da>db:
                    if t>enter:enter=t;hit_side=(pi,si)
                else:leave=min(leave,t)
            if miss:continue
            if not outside:return {'fraction':0.0,'startsolid':True,'sky':False}
            if enter<leave and 0<=enter<=1 and hit_side and (nearest is None or enter<nearest['fraction']):
                pi,si=hit_side
                nearest={'fraction':enter,'startsolid':False,'sky':bool(self.shaders[si][1]&4),
                         'normal':list(self.planes[pi][:3]),'position':[a[k]+direction[k]*enter for k in range(3)],
                         'material':self.shaders[si][0].split(b'\0')[0].decode('latin1')}
        return nearest


def select_views(retail: Path):
    bsp=None;scripts={}
    for p in sorted(retail.iterdir()):
        if p.suffix.lower()!='.pk3':continue
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                key=n.lower()
                if key=='maps/assault.bsp':bsp=z.read(n)
                elif key.startswith('scripts/') and key.endswith('.shader'):
                    scripts[key]=z.read(n).decode('latin1')
    if bsp is None:raise RuntimeError('Assault map not present')
    world=World(bsp)
    sun=[]
    for name,flags,_ in world.shaders:
        if not flags&4:continue
        name=name.split(b'\0')[0].decode('latin1')
        for file,text in scripts.items():
            text=re.sub(r'/\*.*?\*/','',text,flags=re.S)
            text=re.sub(r'//[^\n]*','',text)
            m=re.search(r'(?m)^\s*'+re.escape(name)+r'\s*\{',text,re.I)
            if not m:continue
            start=m.end();i=start;depth=1
            while i<len(text) and depth:
                if text[i]=='{':depth+=1
                elif text[i]=='}':depth-=1
                i+=1
            body=text[start:i-1]
            match=re.search(r'\b(?:q3map_sunExt|q3map_sun|q3gl2_sun)\s+([^\n\r{}]+)',body,re.I)
            if match:
                values=[float(v) for v in match.group(1).split()[:6]]
                if len(values)==6:sun.append({'material':name,'yaw':values[4],'elevation':values[5]})
    if not sun:raise RuntimeError('No authored sun direction found for the actual sky')
    s=sun[-1];yaw=s['yaw'];az=math.radians(yaw);el=math.radians(s['elevation'])
    direction=[math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)]
    starts=[e for e in world.entities if e.get('classname')=='info_player_start' and 'origin' in e]
    if not starts:starts=[e for e in world.entities if e.get('classname','').startswith('info_player') and 'origin' in e]
    if not starts:raise RuntimeError('No player starts in map')
    start=list(map(float,starts[0]['origin'].split()))
    tested=0;valid=[]
    offsets=sorted(((x,y) for x in range(-1536,1537,192) for y in range(-1536,1537,192)),key=lambda p:p[0]*p[0]+p[1]*p[1])
    def exposed(point):
        hit=world.trace(point,[point[k]+direction[k]*32768 for k in range(3)])
        return bool(hit and hit.get('sky') and not hit.get('startsolid'))
    for dx,dy in offsets:
        for height in (64,256,512,1024):
            probe=[start[0]+dx,start[1]+dy,start[2]+height]
            if world.solid(probe):continue
            floor=world.trace(probe,[probe[0],probe[1],probe[2]-2048])
            if not floor or floor.get('sky') or floor.get('startsolid') or floor['normal'][2]<0.7:continue
            eye=[probe[0],probe[1],floor['position'][2]+64]
            tested+=1
            if world.solid(eye) or any(world.solid([eye[0]+a,eye[1]+b,eye[2]+c]) for a,b,c in [(16,0,0),(-16,0,0),(0,16,0),(0,-16,0),(0,0,-16)]):continue
            if not exposed(eye):continue
            for heading in (yaw+180,yaw+90):
                angle=math.radians(heading);fwd=[math.cos(angle),math.sin(angle),0]
                right=[math.sin(angle),-math.cos(angle),0]
                gun=[eye[k]+fwd[k]*32+right[k]*8 for k in range(3)];gun[2]-=8
                if world.solid(gun) or not exposed(gun):continue
                valid.append({'eye':eye,'angles':[8.0,heading%360,0.0],
                              'floor':floor['position'],'leaf_cluster':world.leaf(eye)[0],
                              'weapon_probe':gun,'camera_and_weapon_sun_ray_hit_sky':True})
            if len(valid)>=2:break
        if len(valid)>=2:break
    if len(valid)<2:raise RuntimeError(f'Insufficient proven sunlit camera positions: {len(valid)}, tested {tested}')
    result=[]
    for name,v in zip(('assault_mp40_sun_front','assault_mp40_sun_side'),valid[:2]):
        result.append({'name':name,'eye':v['eye'],'angles':v['angles']})
    return result,{'map':'assault','start':start,'world_bounds':list(world.bounds),'sky_sun_candidates':sun,
                   'selected_sun_direction':direction,'tested_positions':tested,'validated_views':valid[:2],
                   'method':'BSP segment traversal, solid convex brush clipping; positive PVS cluster; sun rays from camera and weapon probe must hit authored sky'}
