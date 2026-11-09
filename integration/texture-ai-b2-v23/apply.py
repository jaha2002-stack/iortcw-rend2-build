#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve(); ev.mkdir(parents=True,exist_ok=True)
code=src/"SP/code/rend2"
qcommon=src/"SP/code/qcommon"
here=Path(__file__).resolve().parent
MARK="DARKWOLF_TEXTURE_AI_B2_V23"

def edit(path, fn, label):
    p=path
    before=p.read_text()
    assert MARK not in before, label+" already patched"
    after=fn(before)
    assert after != before, label+" unchanged"
    p.write_text(after)
    return {
      "file":str(p.relative_to(src)).replace("\\","/"),
      "before":hashlib.sha256(before.encode()).hexdigest(),
      "after":hashlib.sha256(after.encode()).hexdigest()
    }

shutil.copy2(here/"tr_texture_ai_b2_v23.inc", code/"tr_texture_ai_b2_v23.inc")
changes=[]

def local_patch(s):
    anchor="void R_DWTextureInfoV22_f(void);\n"
    assert s.count(anchor)==1, ("local anchor",s.count(anchor))
    return s.replace(anchor,anchor+"""/* DARKWOLF_TEXTURE_AI_B2_V23 */
void R_DWTextureSaveV23_f(void);
""",1)
changes.append(edit(code/"tr_local.h",local_patch,"tr_local.h"))

def world_patch(s):
    return s + "\n/* "+MARK+": single cumulative PK3 persistence */\n#include \"tr_texture_ai_b2_v23.inc\"\n"
changes.append(edit(code/"tr_world.c",world_patch,"tr_world.c"))

def init_patch(s):
    old='\tri.Cmd_AddCommand( "dw_tex_save", R_DWTextureSaveV2_f );\n'
    assert s.count(old)==1, ("save registration",s.count(old))
    return s.replace(old,
      '\t/* DARKWOLF_TEXTURE_AI_B2_V23 */\n'
      '\tri.Cmd_AddCommand( "dw_tex_save", R_DWTextureSaveV23_f );\n',1)
changes.append(edit(code/"tr_init.c",init_patch,"tr_init.c"))

def files_patch(s):
    anchor='''static int QDECL paksort( const void *a, const void *b ) {
\tchar    *aa, *bb;

\taa = *(char **)a;
\tbb = *(char **)b;

\treturn FS_PathCmp( aa, bb );
}
'''
    assert s.count(anchor)==1, ("paksort anchor",s.count(anchor))
    helper=r'''
/* DARKWOLF_TEXTURE_AI_B2_V23
 * A cumulative texture pack may be mounted for the whole session, so the
 * renderer stages updates as .pending. Promote before this directory is
 * scanned and before any PK3 handle is opened. */
#define DWTR_V23_PACK_FILE "zzzzzz_DW_TextureRestoration.pk3"
#define DWTR_V23_PENDING_FILE "zzzzzz_DW_TextureRestoration.pk3.pending"
#define DWTR_V23_BACKUP_FILE "zzzzzz_DW_TextureRestoration.pk3.backup"

static qboolean FS_DWTRV23_FileExistsOS( const char *path ) {
	FILE *f = fopen( path, "rb" );
	if ( !f ) {
		return qfalse;
	}
	fclose( f );
	return qtrue;
}

static qboolean FS_DWTRV23_IsLegacyPakName( const char *name ) {
	int z = 0;
	const char *p = name;

	if ( !name || !name[0] ) {
		return qfalse;
	}

	while ( (*p == 'z' || *p == 'Z') && z < 11 ) {
		++p;
		++z;
	}

	if ( z < 2 || z > 10 ) {
		return qfalse;
	}
	if ( Q_stricmpn( p, "_dwtr_", 6 ) ) {
		return qfalse;
	}
	return qtrue;
}

static void FS_DWTRV23_DeleteLegacyPaks( const char *path, const char *dir ) {
	char curpath[MAX_OSPATH + 1];
	char **pakfiles;
	int numfiles = 0;
	int i;

	Q_strncpyz( curpath, FS_BuildOSPath( path, dir, "" ), sizeof(curpath) );
	curpath[strlen(curpath) - 1] = '\0';

	pakfiles = Sys_ListFiles( curpath, ".pk3", NULL, &numfiles, qfalse );
	for ( i = 0; i < numfiles; ++i ) {
		if ( pakfiles && FS_DWTRV23_IsLegacyPakName( pakfiles[i] ) ) {
			char ospath[MAX_OSPATH + 1];
			Q_strncpyz( ospath,
			            FS_BuildOSPath( path, dir, pakfiles[i] ),
			            sizeof(ospath) );
			if ( remove( ospath ) == 0 ) {
				Com_Printf( "DWTR B2 V2.3: removed migrated legacy pack %s\n", ospath );
			}
		}
	}
	Sys_FreeFileList( pakfiles );
}

static void FS_DWTRV23_PromotePendingPack( const char *path, const char *dir ) {
	char finalPath[MAX_OSPATH + 1];
	char pendingPath[MAX_OSPATH + 1];
	char backupPath[MAX_OSPATH + 1];
	qboolean hadFinal;

	Q_strncpyz( finalPath,
	            FS_BuildOSPath( path, dir, DWTR_V23_PACK_FILE ),
	            sizeof(finalPath) );
	Q_strncpyz( pendingPath,
	            FS_BuildOSPath( path, dir, DWTR_V23_PENDING_FILE ),
	            sizeof(pendingPath) );
	Q_strncpyz( backupPath,
	            FS_BuildOSPath( path, dir, DWTR_V23_BACKUP_FILE ),
	            sizeof(backupPath) );

	if ( FS_DWTRV23_FileExistsOS( pendingPath ) ) {
		hadFinal = FS_DWTRV23_FileExistsOS( finalPath );
		remove( backupPath );

		if ( hadFinal && rename( finalPath, backupPath ) != 0 ) {
			Com_Printf( "DWTR B2 V2.3: pending pack promotion postponed; could not backup %s\n",
			            finalPath );
			return;
		}

		if ( rename( pendingPath, finalPath ) != 0 ) {
			Com_Printf( "DWTR B2 V2.3: pending pack promotion failed; preserving previous cumulative pack\n" );
			if ( hadFinal ) {
				rename( backupPath, finalPath );
			}
			return;
		}

		if ( hadFinal ) {
			remove( backupPath );
		}
		Com_Printf( "DWTR B2 V2.3: promoted cumulative texture pack %s\n",
		            finalPath );
	}

	/* If our cumulative pack exists, legacy one-texture DWTR packs have
	 * already been merged by the renderer writer and are now redundant. */
	if ( FS_DWTRV23_FileExistsOS( finalPath ) ) {
		FS_DWTRV23_DeleteLegacyPaks( path, dir );
	}
}
'''
    s=s.replace(anchor,anchor+helper,1)

    call_anchor='''\tQ_strncpyz(curpath, FS_BuildOSPath(path, dir, ""), sizeof(curpath));
\tcurpath[strlen(curpath) - 1] = '\\0';\t// strip the trailing slash
'''
    assert s.count(call_anchor)==1, ("addgamedir anchor",s.count(call_anchor))
    s=s.replace(call_anchor,call_anchor+
'''\n\t/* DARKWOLF_TEXTURE_AI_B2_V23: promote staged cumulative pack before
\t * Sys_ListFiles sees PK3s and before FS_LoadZipFile opens any handle. */
\tFS_DWTRV23_PromotePendingPack( path, dir );
''',1)
    return s
changes.append(edit(qcommon/"files.c",files_patch,"files.c"))

proof={
 "version":"DarkWolf Local AI Texture Restoration B2 V2.3",
 "base_clean_production_run":42198541106,
 "inherits_b2_v22_run":42580281924,
 "persistence":{
   "single_pack":"zzzzzz_DW_TextureRestoration.pk3",
   "first_save":"creates the single cumulative PK3",
   "later_new_texture":"adds/rebuilds same cumulative archive",
   "same_texture":"replaces same qpath entry inside cumulative archive",
   "mounted_pack_safety":"updates .pending; qcommon promotes before PK3 scan next startup",
   "legacy_migration":"merge old 2..10-z per-texture DWTR packs, delete only after cumulative pack exists",
   "atomic":"temp write + flush + rename/replace; startup backup/restore on promotion failure"
 },
 "picker_preserved":"B2 V2.2 WORLD + MOD_BRUSH",
 "variants_preserved":["FAITHFUL","BALANCED","STRONG"],
 "network_at_runtime":False,
 "telemetry":False,
 "changes":changes
}
(ev/"DW_TEXTURE_AI_B2_V23_SOURCE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n")
print(json.dumps(proof,indent=2))
