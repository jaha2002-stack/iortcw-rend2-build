#!/usr/bin/env python3
"""Test-only SP server snapshot exception for local, linked ET_TESLA_EF on Xlabs.

Exact predecessor: DarkWolf Clean Production GitHub Actions #40683914514.
NO changes to BSP visibility, renderer, CGame, QGame, Tesla triggers or
shadow selection. Only client snapshot eligibility for locally-near active
electric bolt segments. A live test CVar gives 0/768/1024 A/B with no reload.
"""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess

MARK="DARKWOLF_XLABS_LINKED_TESLA_NEAR_SNAPSHOT_PVS_TEST_V1_20261028"
SOURCE="SP/code/server/sv_snapshot.c"
H=lambda b:hashlib.sha256(b).hexdigest()
p=argparse.ArgumentParser()
p.add_argument("root",type=Path)
p.add_argument("--proof",type=Path,required=True)
p.add_argument("--patch",type=Path,required=True)
a=p.parse_args()
f=a.root/SOURCE
original=f.read_bytes()
assert MARK.encode() not in original,"PATCH_ALREADY_PRESENT"
s=original.decode("latin-1")

def replace_once(anchor,replacement,step):
 global s
 assert s.count(anchor)==1,(step,"ANCHOR_COUNT",s.count(anchor))
 s=s.replace(anchor,replacement,1)

helpers=r'''
/*
 * DARKWOLF_XLABS_LINKED_TESLA_NEAR_SNAPSHOT_PVS_TEST_V1_20261028
 *
 * LOCAL TEST ONLY. The active Tesla's visible bolt may cross a BSP cluster
 * boundary while the small shooter_tesla origin is classified outside PVS.
 * Include only linked, ordinary ET_TESLA_EF entities on map "xlabs"
 * when the local SP player's eye is near any point of their bolt segment.
 * Do NOT broadcast every Tesla across the map; do NOT defeat renderer PVS.
 * Range cvar 0 restores exact original server snapshot behavior at runtime.
 */
static float SV_DWNearestTeslaSegmentDistSq( const sharedEntity_t *ent, const vec3_t eye ) {
	vec3_t segment, startToEye, nearest, distance;
	float segmentSq, t;
	VectorSubtract( ent->s.origin2, ent->s.origin, segment );
	VectorSubtract( eye, ent->s.origin, startToEye );
	segmentSq = DotProduct( segment, segment );
	t = ( segmentSq > 0.0001f )
		? DotProduct( startToEye, segment ) / segmentSq : 0.0f;
	t = Com_Clamp( 0.0f, 1.0f, t );
	VectorMA( ent->s.origin, t, segment, nearest );
	VectorSubtract( eye, nearest, distance );
	return DotProduct( distance, distance );
}
'''
anchor="/*\n===============\nSV_AddEntitiesVisibleFromPoint\n===============\n*/"
replace_once(anchor,helpers+"\n"+anchor,"HELPER_BEFORE_SNAPSHOT")

vars_anchor="\tbyte    *bitvector;\n\n\t// during an error shutdown message"
vars=r'''\tbyte    *bitvector;
	// DARKWOLF_XLABS_LINKED_TESLA_NEAR_SNAPSHOT_PVS_TEST_V1_20261028:
	// No effect outside local SP snapshots of Xlabs.
	static cvar_t *dwTeslaNearRange = NULL;
	static cvar_t *dwTeslaAuditOnce = NULL;
	qboolean dwXlabsLocal = qfalse;
	float dwRange = 0.0f;

	// during an error shutdown message'''.replace("\\t","\t")
replace_once(vars_anchor,vars,"SNAPSHOT_LOCAL_VARS")

init_anchor="\tplayerEnt = SV_GentityNum( frame->ps.clientNum );\n\n\tfor ( e = 0 ; e < sv.num_entities ; e++ ) {"
init=r'''\tplayerEnt = SV_GentityNum( frame->ps.clientNum );

	// No global PVS override, no map-independent option, no multiplayer effect.
	dwXlabsLocal = localClient && !portal && sv_mapname &&
		!Q_stricmp( sv_mapname->string, "xlabs" );
	if ( dwXlabsLocal ) {
		if ( !dwTeslaNearRange )
			dwTeslaNearRange = Cvar_Get( "sv_dwXlabsTeslaPvsRangeTest", "768", CVAR_TEMP );
		if ( !dwTeslaAuditOnce )
			dwTeslaAuditOnce = Cvar_Get( "sv_dwXlabsTeslaPvsAuditOnce", "0", CVAR_TEMP );
		dwRange = Com_Clamp( 0.0f, 1024.0f, dwTeslaNearRange->value );
	}

	for ( e = 0 ; e < sv.num_entities ; e++ ) {'''.replace("\\t","\t")
replace_once(init_anchor,init,"XLABS_LOCAL_MAP_TEST_CVARS")

# Insert immediately before the existing area-visibility gate. This is a
# stable semantic location in the accepted September/October server snapshot,
# regardless of extra code that precedes the original SVF_BROADCAST handler.
branch_anchor="\t\tif ( !CM_AreasConnected( clientarea, svEnt->areanum ) ) {"
branch=r'''		// DW Xlabs local proximity exception: only linked, client-visible
		// active Tesla bolt emitters. Unlinked/trigger-OFF entities were
		// rejected above. Every other entity stays PVS-bound.
		if ( dwXlabsLocal && dwRange > 0.0f &&
			ent->s.eType == ET_TESLA_EF &&
			SV_DWNearestTeslaSegmentDistSq( ent, origin ) <= dwRange * dwRange ) {
			SV_AddEntToSnapshot( svEnt, ent, eNums );
			continue;
		}

		if ( !CM_AreasConnected( clientarea, svEnt->areanum ) ) {'''
replace_once(branch_anchor,branch,"BEFORE_AREA_AND_CLUSTER_PVS")

audit_anchor="\t}\n}\n\n/*\n=============\nSV_BuildClientSnapshot"
audit=r'''\t}
	// One-shot test audit, disabled by default. Record true snapshot inclusion
	// (not merely the predicted nearby state). No console spam per frame.
	if ( dwXlabsLocal && dwTeslaAuditOnce && dwTeslaAuditOnce->integer ) {
		int total = 0, linked = 0, sent = 0, near = 0;
		Com_Printf( "DW_XLABS_PVS_TEST_V1_BEGIN cluster=%d area=%d range=%.1f snapshot=%d\n",
			clientcluster, clientarea, dwRange, eNums->numSnapshotEntities );
		for ( e = 0; e < sv.num_entities; ++e ) {
			int found = 0, k;
			float d2;
			ent = SV_GentityNum( e );
			if ( ent->s.eType != ET_TESLA_EF )
				continue;
			++total;
			if ( ent->r.linked ) ++linked;
			d2 = SV_DWNearestTeslaSegmentDistSq( ent, origin );
			if ( ent->r.linked && d2 <= dwRange * dwRange ) ++near;
			for ( k = 0; k < eNums->numSnapshotEntities; ++k ) {
				if ( eNums->snapshotEntities[k] == e ) {
					found = 1;
					break;
				}
			}
			if ( found ) ++sent;
			Com_Printf(
				"DW_XLABS_PVS_TEST_V1_TESLA ent=%d linked=%d sent=%d inRange=%d d2=%.0f from=%.0f,%.0f,%.0f to=%.0f,%.0f,%.0f\n",
				e, (int)ent->r.linked, found,
				(int)(dwRange > 0.0f && d2 <= dwRange * dwRange),
				d2, ent->s.origin[0], ent->s.origin[1], ent->s.origin[2],
				ent->s.origin2[0], ent->s.origin2[1], ent->s.origin2[2] );
		}
		Com_Printf( "DW_XLABS_PVS_TEST_V1_END linked=%d total=%d sent=%d near=%d\n",
			linked, total, sent, near );
		Cvar_Set( "sv_dwXlabsTeslaPvsAuditOnce", "0" );
	}
}

/*
=============
SV_BuildClientSnapshot'''.replace("\\t","\t")
replace_once(audit_anchor,audit,"ONE_SHOT_TRUE_SNAPSHOT_AUDIT")

modified=s.encode("latin-1")
assert modified!=original
assert modified.count(MARK.encode())==2
assert modified.count(b'Com_Printf( "DW_XLABS_PVS_TEST_V1_BEGIN')==1
assert modified.count(b'SV_DWNearestTeslaSegmentDistSq( ent, origin ) <= dwRange * dwRange')==1
assert modified.count(b'sv_dwXlabsTeslaPvsRangeTest')==1
assert modified.count(b'sv_dwXlabsTeslaPvsAuditOnce')==2
assert modified.count(b'if ( !ent->r.linked )')==original.count(b'if ( !ent->r.linked )')
assert modified.count(b'SVF_BROADCAST')==original.count(b'SVF_BROADCAST')
assert modified.count(b'CM_AreasConnected(')==original.count(b'CM_AreasConnected(')
assert modified.count(b'CM_ClusterPVS(')==original.count(b'CM_ClusterPVS(')
assert modified.count(b'SVF_NOCLIENT')==original.count(b'SVF_NOCLIENT')
assert modified.count(b'ET_TESLA_EF')==original.count(b'ET_TESLA_EF')+3
assert len(modified)-len(original)<6000
f.write_bytes(modified)
diff="".join(difflib.unified_diff(
    original.decode("latin-1").splitlines(keepends=True),
    modified.decode("latin-1").splitlines(keepends=True),
    fromfile="a/"+SOURCE,tofile="b/"+SOURCE))
a.patch.parent.mkdir(parents=True,exist_ok=True)
a.patch.write_bytes(diff.encode("latin-1"))
proof={
 "marker":MARK,"source_base_run":40683914514,
 "changed_source_files":[SOURCE],
 "before_sha256":H(original),"after_sha256":H(modified),
 "delta_patch_sha256":H(a.patch.read_bytes()),
 "test_cvars_non_archived":{
     "sv_dwXlabsTeslaPvsRangeTest":{"default":768,"off":0,"maximum":1024},
     "sv_dwXlabsTeslaPvsAuditOnce":{"default":0,"one_shot":1}},
 "local_loopback_only":True,"xlabs_only":True,"linked_only":True,
 "server_broadcast_unchanged":True,"renderer_pvs_unchanged":True,
 "trigger_link_unlink_unchanged":True,
 "no_renderer_or_cgame_changes":True,
 "runtime_gpu_and_pvs_verification":"PENDING_USER_A_B"}
a.proof.write_text(json.dumps(proof,indent=2)+"\n")
print("DW_XLABS_LINKED_TESLA_NEAR_SNAPSHOT_PVS_TEST_V1_SOURCE_PASS",
      H(original),H(modified),H(a.patch.read_bytes()))
