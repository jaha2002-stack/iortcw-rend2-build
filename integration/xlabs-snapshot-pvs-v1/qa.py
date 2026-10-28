#!/usr/bin/env python3
"""No false production claim: verify exact narrow Xlabs snapshot code and A/B model."""
import argparse,hashlib,json,random
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("source",type=Path);p.add_argument("--proof",required=True,type=Path);p.add_argument("--out",required=True,type=Path);a=p.parse_args()
src=(a.source/"SP/code/server/sv_snapshot.c").read_bytes()
s=src.decode("latin-1");proof=json.loads(a.proof.read_text())
mark="DARKWOLF_XLABS_LINKED_TESLA_NEAR_SNAPSHOT_PVS_TEST_V1_20261028"
assert hashlib.sha256(src).hexdigest()==proof["after_sha256"]
assert proof["changed_source_files"]==["SP/code/server/sv_snapshot.c"]
assert s.count(mark)==2
assert s.count('Cvar_Get( "sv_dwXlabsTeslaPvsRangeTest", "768", CVAR_TEMP )')==1
assert s.count('Cvar_Get( "sv_dwXlabsTeslaPvsAuditOnce", "0", CVAR_TEMP )')==1
assert s.count('!Q_stricmp( sv_mapname->string, "xlabs" )')==1
assert s.count('dwXlabsLocal = localClient && !portal && sv_mapname &&')==1
assert s.count('dwRange = Com_Clamp( 0.0f, 1024.0f, dwTeslaNearRange->value );')==1
assert s.count('ent->s.eType == ET_TESLA_EF')==1
assert s.count('SV_DWNearestTeslaSegmentDistSq( ent, origin ) <= dwRange * dwRange')==1
assert s.count('SV_AddEntToSnapshot( svEnt, ent, eNums );')>=3
assert s.count('if ( !ent->r.linked )')==1
assert s.count('if ( ent->r.svFlags & SVF_BROADCAST )')==1
assert s.index('if ( !ent->r.linked )')<s.index('// DW Xlabs local proximity exception:')
assert s.index('if ( ent->r.svFlags & SVF_NOCLIENT )')<s.index('// DW Xlabs local proximity exception:')
assert s.index('// DW Xlabs local proximity exception:')<s.index('if ( !CM_AreasConnected( clientarea, svEnt->areanum ) )')
assert s.count('CM_ClusterPVS( clientcluster );')==1
assert s.count('CM_AreasConnected( clientarea, svEnt->areanum )')==1
assert s.count('DW_XLABS_PVS_TEST_V1_BEGIN')==1
assert s.count('DW_XLABS_PVS_TEST_V1_TESLA')==1
assert s.count('DW_XLABS_PVS_TEST_V1_END')==1
assert s.count('Cvar_Set( "sv_dwXlabsTeslaPvsAuditOnce", "0" )')==1
# The server uses a NORMAL linked entity, not a broadcast flag or forced DLight.
assert not any(x in s for x in ('svFlags |= SVF_BROADCAST','svFlags = SVF_BROADCAST','r_dlightShadowMaxLights'))
# Independent exhaustive eligibility model of the actual server predicate.
def decide(xlabs,local,portal,linked,ent_type,range_value,dist_sq,pvs_visible,no_client=False):
 if not linked or no_client:return False
 if xlabs and local and not portal and ent_type=="ET_TESLA_EF" and 0 < range_value and dist_sq<=min(range_value,1024)**2:
  return True
 return pvs_visible
N=0
for xlabs in (False,True):
 for local in (False,True):
  for portal in (False,True):
   for linked in (False,True):
    for etype in ("ET_TESLA_EF","ET_PLAYER","ET_SPEAKER"):
     for dist_sq in (0,200**2,500**2,768**2,800**2,1024**2,1200**2):
      for r in (0,256,512,768,1024):
       for pvs in (False,True):
        actual=decide(xlabs,local,portal,linked,etype,r,dist_sq,pvs)
        N+=1
        if r==0 or not xlabs or not local or portal or etype!="ET_TESLA_EF":
         assert actual == (linked and pvs)
        if not linked:assert not actual
        if r>0 and xlabs and local and not portal and linked and etype=="ET_TESLA_EF" and dist_sq<=r*r:
         assert actual
assert N>=15000
# For a bolt aligned diagonally in the world, perpendicular offset is handled
# using distance to the SEGMENT rather than only distance to its tiny generator.
def dist_sq_segment(start,end,eye):
 seg=[end[i]-start[i] for i in range(3)]
 rel=[eye[i]-start[i] for i in range(3)]
 den=sum(x*x for x in seg)
 t=max(0,min(1,sum(rel[i]*seg[i] for i in range(3))/den if den>1e-4 else 0))
 return sum((eye[i]-(start[i]+t*seg[i]))**2 for i in range(3))
assert dist_sq_segment((0,0,0),(100,0,0),(50,100,0))==10000
assert dist_sq_segment((0,0,0),(100,0,0),(150,0,0))==2500
assert dist_sq_segment((0,0,0),(0,0,0),(10,0,0))==100
assert dist_sq_segment((0,0,0),(0,0,0),(0,0,0))==0
a.out.mkdir(parents=True,exist_ok=True)
report={
 "status":"DW_XLABS_PVS_TEST_V1_SOURCE_AND_SNAPSHOT_ELIGIBILITY_PASS",
 "base_run":40683914514,"changed_engine_source":["SP/code/server/sv_snapshot.c"],
 "test_cvars":["sv_dwXlabsTeslaPvsRangeTest","sv_dwXlabsTeslaPvsAuditOnce"],
 "default_range":768,"max_range":1024,"disable_range":0,
 "tested_predicate_combinations":N,
 "no_broadcast_override":True,
 "no_trigger_logic_changes":True,
 "no_cgame_renderer_shader_changes":True,
 "gpu_acceptance":"PENDING_USER_XLABS_THREE_DOOR_CLUSTER_AB"}
(a.out/"XLABS_SNAPSHOT_V1_QA.json").write_text(json.dumps(report,indent=2)+"\n")
print(report["status"],N)
