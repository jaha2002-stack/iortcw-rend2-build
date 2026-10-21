#!/usr/bin/env python3
"""Targeted non-A/B Assault camera gallery using original BSP entity metadata.
Do not put BSP or commercially licensed PK3 files in artifacts.
"""
import sys, json, math, struct, importlib.util
from pathlib import Path
from PIL import Image, ImageDraw

s=Path('integration/cas-a2c-lut/game_ab.py').read_text()
assert 'set r_dwCasStrength 0.35' in s and 'set r_dwLutStrength 0.35' in s
s=s.replace('set r_dwCasStrength 0.35','set r_dwCasStrength 0.55')
s=s.replace('set r_dwLutStrength 0.35','set r_dwLutStrength 0.80')
# Use the real production High Quality exposure instead of forcing a dark frame.
s=s.replace('set r_autoExposure 0','set r_autoExposure 1')
s=s.replace('"wait 14","set dw_proofFreeze 1"','"wait 65","set dw_proofFreeze 1"')
p=Path('integration/cas-a2c-lut/.assault_gate_tmp.py')
p.write_text(s)
spec=importlib.util.spec_from_file_location('assault_gallery_g',p)
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
g.MAPS=('assault',)
g.PROFILE={'ALL3':('1','1','1')}
from rc4_assault_camera import World,select_views

def views(retail,name):
    world=World(g.maps_from(retail,name))
    gates=[]
    for idx,e in enumerate(world.entities):
        if e.get('classname')=='script_mover' and 'gate' in e.get('targetname','').lower() and 'origin' in e:
            gates.append((idx,e,[float(x) for x in e['origin'].split()[:3]]))
    if not gates:raise RuntimeError('authored big_gate not found in Assault')
    _,entity,origin=gates[0]
    print('ASSAULT_GATE_ENTITY',entity.get('targetname'),origin,flush=True)
    # Brush model bounds are local to the script_mover origin.
    model=entity.get('model','')
    center=origin[:]
    if model.startswith('*'):
        mo,ml=struct.unpack_from('<ii',world.data,8+7*8)
        bid=int(model[1:])
        if 0<=bid<ml//40:
            rec=struct.unpack_from('<6f4i',world.data,mo+40*bid)
            local=[0.5*(rec[k]+rec[k+3]) for k in range(3)]
            center=[origin[k]+local[k] for k in range(3)]
            print('GATE_BRUSH_LOCAL_CENTER',local,'WORLD_CENTER',center,flush=True)

    # Locate *rendered fence geometry*, not only mapper entity names.
    vo,vl=struct.unpack_from('<ii',world.data,8+10*8)
    so,sl=struct.unpack_from('<ii',world.data,8+13*8)
    fence_surfaces=[]
    if vl%44==0 and sl%104==0:
        for sid in range(sl//104):
            shader, fog, surface_type, first, count=struct.unpack_from('<5i',world.data,so+104*sid)
            if shader<0 or shader>=len(world.shaders) or count<3 or count>2000 or first<0 or first+count>vl//44:continue
            name=world.shaders[shader][0].split(bytes([0]))[0].decode('latin1','replace').lower()
            if 'fence' not in name and 'grate' not in name and 'grill' not in name:continue
            # Actual draw-vertex world positions (not BSP brush clipping hulls).
            sampled=[struct.unpack_from('<3f',world.data,vo+(first+k)*44) for k in range(0,count,max(1,count//70))]
            spans=[max(p[k] for p in sampled)-min(p[k] for p in sampled) for k in range(3)]
            lengths=sorted(spans,reverse=True)
            area=lengths[0]*lengths[1]
            if area<1000 or max(abs(q) for p in sampled for q in p)>150000:continue
            target=[sum(p[k] for p in sampled)/len(sampled) for k in range(3)]
            nx=[0.,0.,0.]
            for k in range(0,count,max(1,count//70)):
                row=struct.unpack_from('<3f',world.data,vo+(first+k)*44+28)
                for t in range(3):nx[t]+=row[t]
            norm=math.sqrt(sum(v*v for v in nx))
            if norm>0.01:nx=[v/norm for v in nx]
            else:
                thin=spans.index(min(spans));nx=[float(i==thin) for i in range(3)]
            if abs(nx[2])>0.75:continue
            fence_surfaces.append({'sid':sid,'shader':name,'center':target,'normal':nx,'area':area,'spans':spans})
    fence_surfaces.sort(key=lambda d:-d['area'])
    selected=[]
    for surf in fence_surfaces:
        if any(sum((surf['center'][i]-p['center'][i])**2 for i in range(3))<150**2 for p in selected):continue
        selected.append(surf)
        if len(selected)>=10:break
    print('AUTHORED_FENCE_SURFACES',len(fence_surfaces),'DISTINCT',len(selected),flush=True)
    print('FENCE_TARGETS',[(a['sid'],a['shader'],[round(x,1) for x in a['center']],round(a['area'])) for a in selected],flush=True)
    (Path('evidence')/'assault_fence_targets.json').write_text(json.dumps(selected,indent=2)+'\\n')
    views=[]
    def add(label,eye,target,kind):
        if world.solid(eye):return False
        d=[target[k]-eye[k] for k in range(3)]
        if sum(x*x for x in d)<2500:return False
        hit=world.trace(eye,target)
        if hit and (hit.get('startsolid') or hit.get('fraction',1.)<0.72):return False
        pitch=-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1])))
        yaw=math.degrees(math.atan2(d[1],d[0]))%360.
        views.append({'name':label,'eye':eye,'angles':[pitch,yaw,0.],'aim':target,'geometry':kind})
        return True
    # Prioritize actual fence mesh surfaces in disparate map regions.
    for surf in selected:
        if len(views)>=15:break
        target=surf['center'];n=surf['normal']
        for sign in (1.,-1.):
            for dist in (160.,260.,110.,360.):
                eye=[target[k]+n[k]*sign*dist for k in range(3)]
                eye[2]+=30
                if add('meshfence_%d_%s_%du'%(surf['sid'],'front' if sign>0 else 'back',int(dist)),eye,target,surf['shader']):break
            if len(views)>=15:break
    # Add real midpoint views across the BIG_GATE axis at standing height.
    for sign in (-1.,1.):
        for offset in (-230.,0.,230.):
            if len(views)>=20:break
            eye=[center[0]+sign*240,center[1]+offset,center[2]+15.]
            add('big_gate_mid_%s_%s'%('A' if sign<0 else 'B',str(int(offset)).replace('-','m')),eye,center,'big_gate')
    if len(views)<3:raise RuntimeError('insufficient validated mesh/gate viewpoints')
    print('VISIBLE_FENCE_CAMERA_CANDIDATES',len(views),flush=True)
    return views[:20]

def compare(out,maps,results):
    shots=[];preview=[]
    for mapname,views in maps.items():
        result=results[mapname]['ALL3']
        assert result['ready'] and result['complete'] and len(result['images'])==len(views)
        for v in views:
            file=out/result['images'][v['name']]
            im=Image.open(file).convert('RGB')
            shots.append({'name':v['name'],'image':file.name,'eye':v['eye'],'aim':v.get('aim'),
                          'reference_only_not_gate':v.get('reference_only_not_gate',False)})
            preview.append((v['name'],im))
    (out/'GATE_CANDIDATES_MANIFEST.json').write_text(json.dumps({'all3':True,'CAS':0.55,'LUT':0.80,'A2C':1,
                 'note':'Real fence mesh targets, camera candidates; visually inspect screenshots before declaring success',
                 'shots':shots},indent=2)+'\n')
    thumb=(480,270)
    canvas=Image.new('RGB',(960,((len(preview)+1)//2)*310),(14,16,20))
    d=ImageDraw.Draw(canvas)
    for i,(name,im) in enumerate(preview):
        x=i%2*480;y=i//2*310
        d.text((x+6,y+8),name,fill='white')
        canvas.paste(im.resize(thumb),(x,y+36))
    canvas.save(out/'ASSAULT_FENCE_VISIBLE_ALL3_AUTO_EXPOSURE.png')
    print('ASSAULT_FENCE_RETAKE_COMPLETE',len(shots),flush=True)

g.camera_views=views
g.compare=compare
g.main()
