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
p=Path('integration/cas-a2c-lut/.assault_gate_tmp.py')
p.write_text(s)
spec=importlib.util.spec_from_file_location('assault_gallery_g',p)
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
g.MAPS=('assault',)
g.PROFILE={'ALL3':('1','1','1')}
from rc4_assault_camera import World,select_views

def views(retail,name):
    world=World(g.maps_from(retail,name));views=[]
    gates=[]
    for idx,e in enumerate(world.entities):
        if e.get('classname')=='script_mover' and 'gate' in str(e.get('targetname','')).lower():
            if 'origin' in e:
                gates.append((idx,e,[float(x) for x in e['origin'].split()[:3]]))
    if not gates:raise RuntimeError('No scripted iron gate found in authored Assault entities')
    _,entity,origin=gates[0]
    candidates=[('gate_entity_center',origin)]
    # BSP submodels may use local or world coordinates.
    model=entity.get('model','')
    if model.startswith('*'):
        raw=world.data
        off,length=struct.unpack_from('<ii',raw,8+7*8)
        index=int(model[1:]);sz=40
        if 0<=index<length//sz:
            rec=struct.unpack_from('<6f4i',raw,off+index*sz)
            center=[(rec[i]+rec[i+3])*0.5 for i in range(3)]
            if max(abs(center[k]-origin[k]) for k in range(3))<650:
                candidates.append(('gate_brush_center',center))
            if max(abs(center[k]) for k in range(3))<650:
                candidates.append(('gate_relative_center',[center[k]+origin[k] for k in range(3)]))
            print('GATE_MODEL_BOUNDS',model,[round(x,1) for x in rec[:6]],flush=True)
    print('ASSAULT_GATES',[(idx,e.get('targetname'),origin) for idx,e,origin in gates],flush=True)
    def add(label,eye,target):
        if world.solid(eye):return False
        d=[target[k]-eye[k] for k in range(3)]
        if sum(x*x for x in d)<1600:return False
        hit=world.trace(eye,target)
        if hit and (hit.get('startsolid') or hit.get('fraction',1.)<0.83):return False
        pitch=-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1])))
        yaw=math.degrees(math.atan2(d[1],d[0]))%360.
        views.append({'name':label,'eye':eye,'angles':[pitch,yaw,0.],
                      'target_entity':entity.get('targetname'),'aim':target})
        return True
    for label,target in candidates:
        if len(views)>=11:break
        for degrees in (0,60,120,180,240,300):
            if len(views)>=11:break
            a=math.radians(degrees)
            for radius in (260.,420.,160.,540.):
                for height in (120.,200.,0.,-50.,360.):
                    eye=[target[0]+radius*math.cos(a),target[1]+radius*math.sin(a),target[2]+height]
                    if add(f'{label}_{degrees}deg_{int(radius)}u_{int(height)}z',eye,target):break
                else:continue
                break
    # Proven sunlight references only; not claimed to show the gate.
    sun,proof=select_views(retail)
    for n,v in enumerate(sun):
        if len(views)>=13:break
        views.append({'name':'assault_sunlit_reference'+str(n+1),'eye':v['eye'],'angles':v['angles'],
                      'aim':None,'reference_only_not_gate':True})
    if len(views)<5:raise RuntimeError('Insufficient camera candidates for gate gallery')
    print('ASSAULT_GATE_VIEWPOINTS',len(views),flush=True)
    return views

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
                 'note':'Camera positions are candidates; visible iron gate must be inspected manually',
                 'shots':shots},indent=2)+'\n')
    thumb=(480,270)
    canvas=Image.new('RGB',(960,((len(preview)+1)//2)*310),(14,16,20))
    d=ImageDraw.Draw(canvas)
    for i,(name,im) in enumerate(preview):
        x=i%2*480;y=i//2*310
        d.text((x+6,y+8),name,fill='white')
        canvas.paste(im.resize(thumb),(x,y+36))
    canvas.save(out/'ASSAULT_GATE_RETAKE_ALL3.png')
    print('ASSAULT_GATE_RETAKE_COMPLETE',len(shots),flush=True)

g.camera_views=views
g.compare=compare
g.main()
