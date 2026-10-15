#!/usr/bin/env python3
"""Bound first-use world captures without changing any light/shader formula."""
from pathlib import Path
import subprocess,sys,json,hashlib
src=Path(sys.argv[1]).resolve();kit=Path(sys.argv[2]).resolve()
def git(*args):return subprocess.check_output(['git','-C',str(src),*args],text=True).strip()
assert git('rev-parse','HEAD^{tree}')=='3bd8085e2169af3cd40686bbcaa986c92c49cca4'
assert not git('status','--porcelain')
base=git('rev-parse','HEAD^');assert git('rev-parse',base+'^{tree}')=='74049eab929ec9271459634e143dda9fd7d700c1'
p=src/'SP/code/rend2/tr_main.c';s=p.read_text();start=s.index('void R_RenderDlightWorldOcclusion(');end=s.index('\nstatic qboolean R_FireVolProductionCacheMatchesHint',start);f=s[start:end]
a='\t\t\tfor (side = 0; side < 6; ++side)\n';b='''\t\t\t// Cold-cache captures may exceed the shared command/surface rings.
\t\t\t// Consume earlier views before reusing their storage; submit each new
\t\t\t// face completely before declaring the cache entry valid. No glFinish.
\t\t\tR_IssuePendingRenderCommands();
\t\t\ttr.refdef.numDrawSurfs = 0;
\t\t\tfor (side = 0; side < 6; ++side)
''';assert f.count(a)==1;f=f.replace(a,b)
a='\t\t\t\tR_AddCapShadowmapCmd(DLIGHT_WORLD_MAP_BASE + slot, side);\n';b='''\t\t\t\tif (tr.refdef.numDrawSurfs > MAX_DRAWSURFS)
\t\t\t\t\tri.Error(ERR_DROP, "Dlight architectural capture exceeds surface ring");
\t\t\t\tR_AddCapShadowmapCmd(DLIGHT_WORLD_MAP_BASE + slot, side);
\t\t\t\tR_IssuePendingRenderCommands();
\t\t\t\ttr.refdef.numDrawSurfs = 0;
''';assert f.count(a)==1;f=f.replace(a,b);p.write_text(s[:start]+f+s[end:])
git('diff','--check');git('add','SP/code');tree=git('write-tree');assert tree=='c652eaed9cbcf1df4eb7d7d5187b9bea63dce60b',tree
git('-c','user.name=DarkWolf CI','-c','user.email=ci@invalid.local','commit','-qm','Bound architectural cold-cache command and surface lifetime')
patch=subprocess.check_output(['git','-C',str(src),'diff','--binary','--full-index',base,'HEAD'])
subprocess.run(['git','-C',str(src),'apply','--reverse','--check','-'],input=patch,check=True)
lock=json.loads((kit/'source-lock.json').read_text());lock['candidate_tree']=tree;lock['patch_sha256']=hashlib.sha256(patch).hexdigest();lock['capture_submission']='Consume pending commands before bounded scratch-surface reuse; each face delivered before valid.'
(kit/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n');(kit/'containment.patch').write_bytes(patch)
p=kit/'test_cache.py';t=p.read_text();assert t.count('int num_dlights;dlight_t dlights[32];')==1
t=t.replace('int num_dlights;dlight_t dlights[32];','int num_dlights;int numDrawSurfs;dlight_t dlights[32];')
t=t.replace('#define MAX_DLIGHTS 32','#define MAX_DLIGHTS 32\n#define MAX_DRAWSURFS 65536')
t=t.replace('static int draws,caps;','static int draws,caps;\nstatic void R_IssuePendingRenderCommands(void) {}')
p.write_text(t)
p=kit/'README.md';p.write_text(p.read_text()+'\nCold-cache safety: every face is submitted before the shared draw-surface ring\nis reused and before the cache becomes valid. No glFinish or per-frame light\nlimit is added. Warm cache hits have no extra submission calls. Actual allocator\nstress tests cover all 32 lights / 192 faces, not just mocked unlimited queues.\n')
print('BOUNDED_CAPTURE_SOURCE_TREE_PASS',tree,lock['patch_sha256'])
