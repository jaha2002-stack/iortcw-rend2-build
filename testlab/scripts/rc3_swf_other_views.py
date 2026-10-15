#!/usr/bin/env python3
"""Capture other SWF locations using unchanged RC3 graphics and private retail assets.
Only camera control/observability comes from the existing isolated Linux TestLab.
No retail assets, engine binaries, generated pictures or changed presets are published.
"""
from pathlib import Path
import datetime, hashlib, json, math, os, re, shutil, signal, struct, subprocess, sys, time, zipfile
from PIL import Image
import numpy as np

EXPECTED_TREE = '921a3d2a339d3a670c098a777c4c7896d987efe8'
ORIGINAL = (1456.0, -1824.0, 280.0)

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class BSP:
    def __init__(self, data):
        if data[:4] != b'IBSP' or struct.unpack_from('<i', data, 4)[0] not in (46, 47):
            raise ValueError('Unsupported SWF BSP format')
        def lump(i):
            offset, size = struct.unpack_from('<ii', data, 8 + 8*i)
            if offset < 0 or size < 0 or offset + size > len(data):
                raise ValueError('Invalid BSP lump')
            return data[offset:offset+size]
        def rows(i, fmt):
            return list(struct.iter_unpack(fmt, lump(i)))
        self.entities = [dict(re.findall(r'"([^"\n]+)"\s*"([^"\n]*)"', b)) for b in re.findall(r'\{([^{}]*)\}', lump(0).decode('latin1'))]
        self.shaders = rows(1, '<64sii')
        self.planes = rows(2, '<4f')
        self.nodes = rows(3, '<9i')
        self.leaves = rows(4, '<12i')
        self.leafbrushes = [r[0] for r in rows(6, '<i')]
        self.brushes = rows(8, '<3i')
        self.sides = rows(9, '<2i')
    def leaf(self, p):
        n = 0
        while n >= 0:
            node = self.nodes[n]
            plane = self.planes[node[0]]
            n = node[1 if sum(p[i]*plane[i] for i in range(3)) >= plane[3] else 2]
        return self.leaves[-1-n]
    def solid(self, p):
        leaf = self.leaf(p)
        if leaf[0] < 0:
            return True
        for b in self.leafbrushes[leaf[10]:leaf[10]+leaf[11]]:
            first, count, shader = self.brushes[b]
            if not self.shaders[shader][2] & 1:
                continue
            if all(sum(p[i]*self.planes[self.sides[s][0]][i] for i in range(3)) <= self.planes[self.sides[s][0]][3] + 0.05 for s in range(first, first+count)):
                return True
        return False
    def ray(self, p, yaw):
        a = math.radians(yaw)
        for d in range(24, 769, 24):
            if self.solid((p[0]+d*math.cos(a), p[1]+d*math.sin(a), p[2])):
                return d
        return 768

def positions(bsp):
    origins = []
    for index, ent in enumerate(bsp.entities):
        try:
            p = tuple(map(float, ent.get('origin', '').split()))
        except ValueError:
            continue
        if len(p) != 3:
            continue
        cls = ent.get('classname', '')
        if cls.startswith(('ai_', 'weapon_', 'item_', 'info_player')):
            origins.append((index, cls, p))
    candidates = []
    for index, cls, p in origins:
        top = (p[0], p[1], p[2]+32)
        if bsp.solid(top):
            continue
        floor = None
        for dz in range(4, 257, 4):
            if bsp.solid((top[0], top[1], top[2]-dz)):
                floor = top[2]-dz+4
                break
        if floor is None:
            continue
        body = (p[0], p[1], floor+24)
        eye = (p[0], p[1], floor+88)
        if math.dist(body, ORIGINAL) < 500:
            continue
        if any(bsp.solid((eye[0]+dx, eye[1]+dy, eye[2]+dz)) for dx,dy,dz in [(0,0,0),(20,0,0),(-20,0,0),(0,20,0),(0,-20,0),(0,0,16)]):
            continue
        if any(math.dist(body, c['origin']) < 180 for c in candidates):
            continue
        options = []
        for yaw in range(0, 360, 30):
            distances = [bsp.ray(eye, yaw+d) for d in (-30,0,30)]
            options.append((min(distances) + sum(distances)/4, yaw, distances))
        score, yaw, distances = max(options)
        if min(distances) < 120:
            continue
        candidates.append({'origin':body,'angles':(-5.0,float(yaw),0.0),'entity_index':index,'entity_class':cls,'cluster':bsp.leaf(eye)[0],'clearance_score':score,'forward_clearances':distances})
    selected = []
    for c in sorted(candidates, key=lambda x:x['clearance_score'], reverse=True):
        if all(math.dist(c['origin'], q['origin']) >= 650 for q in selected):
            selected.append(c)
        if len(selected) == 4:
            break
    if len(selected) < 2:
        raise RuntimeError('Fewer than two separated valid gameplay camera locations')
    return selected, len(candidates)

def main():
    src, retail, out = map(lambda s:Path(s).resolve(), sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    repo = Path.cwd()
    kit = repo/'integration/optimized-v4-4-6'
    clean_tree = subprocess.check_output(['git','-C',str(repo/'source'),'rev-parse','HEAD^{tree}'], text=True).strip()
    if clean_tree != EXPECTED_TREE:
        raise RuntimeError('Unexpected clean RC3 source tree: '+clean_tree)
    build = src/'SP/build/release-linux-x86_64'
    runtime = repo/'private-swf-rc3-capture'
    (runtime/'main').mkdir(parents=True, exist_ok=True)
    for p in build.iterdir():
        if p.is_file():
            shutil.copy2(p, runtime/p.name)
    for p in (build/'main').glob('*.so'):
        shutil.copy2(p, runtime/'main'/p.name)
    bsp_data = None
    for p in sorted(retail.iterdir()):
        if p.suffix.lower() != '.pk3':
            continue
        (runtime/'main'/p.name.lower()).symlink_to(p)
        with zipfile.ZipFile(p) as z:
            for name in z.namelist():
                if name.replace('\\','/').lower() == 'maps/swf.bsp':
                    bsp_data = z.read(name)
    if bsp_data is None:
        raise RuntimeError('Retail SWF map not available')
    bsp = BSP(bsp_data)
    views, valid_count = positions(bsp)
    for i,v in enumerate(views,1):
        v.update(name=f'swf_other_{i:02d}', index=i)
    views.insert(0, {'name':'swf_original_control','index':0,'origin':ORIGINAL,'angles':(-28.0,0.0,0.0)})
    preset = kit/'PRODUCTION_HIGH_QUALITY.cfg'
    shutil.copy2(preset, runtime/'main'/preset.name)
    shutil.copy2(kit/'payload/Main/darkwolf_ignition_rc_v0_6.pk3',runtime/'main/darkwolf_ignition_rc_v0_6.pk3')
    scenario = ['set cg_draw2D 0']
    for v in views:
        scenario += ['dw_testView '+' '.join(str(x) for x in (*v['origin'],*v['angles'])), 'wait 50', f'dw_testViewState {v["index"]}', f'set r_testlabCaptureIndex {v["index"]}', 'wait 5', 'viewpos', f'screenshot {v["name"]}', 'wait 8']
    scenario += ['quit']
    (runtime/'main/SWF_RC3_OTHER_VIEWS.cfg').write_text('\n'.join(scenario)+'\n')
    shutil.copy2(runtime/'main/SWF_RC3_OTHER_VIEWS.cfg',out/'SWF_RC3_OTHER_VIEWS.cfg')
    (out/'camera-plan.json').write_text(json.dumps({'valid_candidates':valid_count,'views':views},indent=2)+'\n')
    print('SWF_CAMERA_PLAN', json.dumps(views),flush=True)
    exe = runtime/'iowolfsp.x86_64'
    home = runtime/'capture-home'
    home.mkdir(exist_ok=True)
    cmd = [str(exe),'+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+safe','+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_testAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec',preset.name,'+set','r_mode','-1','+set','r_customwidth','640','+set','r_customheight','480','+set','r_fullscreen','0','+set','r_forceSun','1','+set','s_initsound','0','+vid_restart','+set','dw_testlabSmokeCapture','swf-other-views','+set','dw_testlabScenario','SWF_RC3_OTHER_VIEWS.cfg','+spdevmap','swf']
    start = time.monotonic()
    with (out/'stdout.log').open('w') as log:
        proc = subprocess.Popen(['xvfb-run','-a',*cmd],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'LIBGL_ALWAYS_SOFTWARE':'1'},start_new_session=True)
        while True:
            try:
                rc = proc.wait(timeout=20)
                break
            except subprocess.TimeoutExpired:
                print('SWF_CAPTURE_PROGRESS',round(time.monotonic()-start),'seconds',len(list(home.rglob('*.tga'))),'screenshots',flush=True)
                if time.monotonic()-start > 360:
                    os.killpg(proc.pid,signal.SIGKILL)
                    proc.wait()
                    rc = 124
                    break
    logs = list(home.rglob('*console*.log'))
    for i,p in enumerate(logs):
        shutil.copy2(p,out/f'console-{i}.log')
    text = '\n'.join(p.read_text(errors='replace') for p in logs)
    ready = 'TESTLAB_FRAME_STATE stage=READY map=swf' in text and 'TESTLAB_GAMEPLAY_START requested=1' in text and bool(re.search(r'TESTLAB_CAPTURE_READY frames=\d+ fadeRate=0',text))
    actual = dict(re.findall(r'TESTLAB_CVAR name=(\w+) value=([^\s]+)',text))
    expected = dict(re.findall(r'seta ([^ ]+) "([^" ]+)"',preset.read_text()))
    expected['r_forceSun'] = '1'
    mismatch = {k:{'expected':expected.get(k),'actual':v} for k,v in actual.items() if expected.get(k)!=v}
    results = []
    for v in views:
        files = list(home.rglob(v['name']+'.tga'))
        row = dict(v)
        if len(files) != 1:
            row['status'] = 'MISSING_CAPTURE'
        else:
            tga = out/(v['name']+'.tga')
            shutil.copy2(files[0],tga)
            im = Image.open(tga).convert('RGB')
            png = out/(v['name']+'.png')
            im.save(png)
            a = np.array(im)
            white_rows = np.all(a == 255, axis=(1,2))
            bottom = 0
            for white in white_rows[::-1]:
                if not white:break
                bottom += 1
            row.update(status='CAPTURED', size=list(im.size), tga_sha256=digest(tga), png_sha256=digest(png), bottom_all_white_rows=bottom, full_width_white_rows=int(white_rows.sum()), white_fraction=float(np.all(a>247,axis=2).mean()), black_fraction=float(np.all(a<8,axis=2).mean()), server_camera_confirmed=f'TESTLAB_VIEW_STATE index={v["index"]} ' in text, renderer_camera_confirmed=f'TESTLAB_RENDER_VIEW index={v["index"]} ' in text)
        print('SWF_CAPTURE_RESULT',json.dumps(row),flush=True)
        results.append(row)
    passed = rc == 0 and ready and len(actual)==11 and not mismatch and all(r['status']=='CAPTURED' and r['server_camera_confirmed'] and r['renderer_camera_confirmed'] for r in results)
    report = {'status':'CAPTURE_INTEGRITY_PASS' if passed else 'CAPTURE_FAIL','timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'github_run_id':os.environ.get('GITHUB_RUN_ID'),'builder_sha':os.environ.get('GITHUB_SHA'),'clean_rc3_source_tree':clean_tree,'base_release_run':38692442439,'base_game_zip_sha256':'fc45bbeb642cc07692ad10ee6758343712bcb155fca282557cbdb6c5d2932814','hardware':'Linux Mesa llvmpipe; software rasterizer; not Windows GPU validation','resolution':[640,480],'preset_sha256':digest(preset),'actual_cvars':actual,'cvar_mismatches':mismatch,'exit_code':rc,'gameplay_ready':ready,'images_unretouched':True,'production_source_changed':False,'views':results,'command':cmd,'test_binary_sha256':{p.name:digest(p) for p in build.iterdir() if p.is_file()},'view_state_log':[s for s in text.splitlines() if 'TESTLAB_RENDER_VIEW' in s or 'TESTLAB_VIEW_STATE' in s]}
    (out/'capture-results.json').write_text(json.dumps(report,indent=2)+'\n')
    sums = ''.join(f'{digest(p)}  {p.name}\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt')
    (out/'SHA256SUMS.txt').write_text(sums)
    if not passed:
        raise SystemExit('Capture integrity check failed; inspect preserved evidence')

if __name__ == '__main__':
    main()
