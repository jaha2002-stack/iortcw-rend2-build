#!/usr/bin/env python3
"""Diagnostic-only camera/provenance correction. Never edits clean sources."""
from pathlib import Path
import ast,json,sys
source=Path(sys.argv[1]).resolve()
runtime=Path(sys.argv[2]).resolve()
assert source.name=='linux-test', 'Only diagnostic copy may be changed'
p=source/'SP/code/rend2/tr_scene.c'
s=p.read_text()
a='if (!(fd->rdflags & RDF_NOWORLDMODEL) && step > 0 && step != lastStep)'
b='if (!(fd->rdflags & (RDF_NOWORLDMODEL | RDF_SKYBOXPORTAL)) && step > 0 && step != lastStep)'
assert s.count(a)==1, 'Exact diagnostic logger not found'
p.write_text(s.replace(a,b))
# Player origin = requested eye minus DEFAULT_VIEWHEIGHT (40), not 64.
# These eyes lie in non-solid volumes in the actual retail escape1 BSP.
changes={
 (-980,602,-90,25,180,0):(-1010,692,-90,22,180,0),
 (-1060,602,-90,35,180,0):(-1100,692,-90,40,180,0),
 (-1460,520,-90,0,20,0):(-1340,760,-50,7,306,0),
 (400,400,-600,-14,170,0):(120,560,-510,3,300,0),
 (328,448,-330,70,180,0):(328,448,-250,70,180,0),
 (100,580,-330,45,315,0):(328,580,-250,65,270,0),
 (480,600,-330,35,225,0):(120,560,-280,55,300,0),
}
t=runtime.read_text();lines=t.splitlines(keepends=True)
offsets=[0]
for line in lines: offsets.append(offsets[-1]+len(line))
edits=[];found=set()
for node in ast.walk(ast.parse(t)):
 if isinstance(node,(ast.Tuple,ast.List)):
  try: value=ast.literal_eval(node)
  except (ValueError,TypeError,SyntaxError): continue
  if not isinstance(value,(list,tuple)) or len(value)!=6 or not all(isinstance(x,(int,float)) for x in value):continue
  key=tuple(value)
  if key in changes:
   replacement=list(changes[key]) if isinstance(node,ast.List) else changes[key]
   edits.append((offsets[node.lineno-1]+node.col_offset,offsets[node.end_lineno-1]+node.end_col_offset,repr(replacement)))
   found.add(key)
assert found==set(changes), 'Camera literal coverage mismatch: '+repr(found)
for start,end,value in sorted(edits,reverse=True): t=t[:start]+value+t[end:]
# Logs remain in console-0.log but must not cover screenshot pixels.
assert 'set cg_draw2D 0' in t
t=t.replace('set cg_draw2D 0','set con_notifytime 0\\nset cg_draw2D 0')
ast.parse(t)
runtime.write_text(t)
Path('evidence/view-corrections.json').write_text(json.dumps({'scope':'diagnostic only','skybox_excluded':True,'player_viewheight':40,'camera_changes':[{'before':a,'after':b} for a,b in changes.items()]},indent=2))
print('DIAGNOSTIC_CAMERA_AND_LOGGER_CORRECTION_PASS',len(edits))
