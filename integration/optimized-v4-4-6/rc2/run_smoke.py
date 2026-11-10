#!/usr/bin/env python3
"""Reuse known six-map TestLab smoke with observable progress, not an FPS test."""
from pathlib import Path
import hashlib,sys
original=Path(__file__).resolve().parent.parent/'runtime.py'
s=original.read_text()
if hashlib.sha256(original.read_bytes()).hexdigest()!='92d1cc06c25a2b050235f967ad07ddc06277f6cbc7ef6684de3da22473a65cdd':
    raise RuntimeError('Original runtime.py hash changed; review adapter before running')
def once(old,new):
    global s
    if s.count(old)!=1:raise RuntimeError('Unexpected runtime adapter anchor: '+old[:80])
    s=s.replace(old,new)
once(' started=time.time()', ' print("SMOKE_START",tag,flush=True)\n started=time.time()')
once('  try:rc=proc.wait(timeout=240)', '''  try:
   while True:
    try:
     rc=proc.wait(timeout=20)
     break
    except subprocess.TimeoutExpired:
     elapsed=time.time()-started
     print('SMOKE_PROGRESS',tag,'elapsed_seconds',round(elapsed),
           'screenshots',len(list(home.rglob('*.tga'))),
           'console_bytes',sum(p.stat().st_size for p in home.rglob('*console*.log')),flush=True)
     if elapsed>=240:raise''')
once("  im=Image.open(shots[-1]).convert('RGB');im.save(out/(tag+'.png'));pixels=list(im.getdata());n=len(pixels)",
     "  shutil.copy2(shots[-1],out/(tag+'.tga'))\n  im=Image.open(shots[-1]).convert('RGB');im.save(out/(tag+'.png'));pixels=list(im.getdata());n=len(pixels)")
once(" rows.append(row);(out/'runtime-results.json').write_text(json.dumps(rows,indent=2)+'\\n')", " rows.append(row);(out/'runtime-results.json').write_text(json.dumps(rows,indent=2)+'\\n')\n print('SMOKE_END',tag,row['status'],round(row['elapsed_seconds']),flush=True)\n if row['status']!='SMOKE_PASS':raise SystemExit('Fail-fast on '+tag+'; actual logs preserved')")
exec(compile(s,str(original),'exec'),{'__file__':str(original),'__name__':'__main__'})
