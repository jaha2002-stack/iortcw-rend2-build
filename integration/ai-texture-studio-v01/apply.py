#!/usr/bin/env python3
"""Apply opt-in Texture Studio prototype to the reconstructed, accepted Rend2 source."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INC = (ROOT / "studio.c.inc").read_text()
START = "/* DARKWOLF_AI_TEXTURE_STUDIO_V01_BEGIN */"
END = "/* DARKWOLF_AI_TEXTURE_STUDIO_V01_END */"

def replace_once(path, before, after, check):
    data = path.read_text()
    if data.count(before) != 1:
        raise RuntimeError(f"{path}: anchor count {data.count(before)}, expected exactly 1")
    if START in data and (not check):
        raise RuntimeError(f"{path}: already patched")
    new = data.replace(before, after, 1)
    if not check:
        path.write_text(new)
    return {"path":str(path),"sha256_before":hashlib.sha256(data.encode()).hexdigest(),
            "sha256_after":hashlib.sha256(new.encode()).hexdigest()}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("source",type=Path)
    a.add_argument("--check-only",action="store_true")
    a.add_argument("--proof",type=Path)
    o=a.parse_args()
    p=o.source/"SP/code/rend2"
    tr_image=p/"tr_image.c"
    tr_init=p/"tr_init.c"
    tr_cmds=p/"tr_cmds.c"
    tr_local=p/"tr_local.h"
    header="\n/* DARKWOLF_AI_TEXTURE_STUDIO_V01 */\nvoid R_DWTextureStudio_Init( void );\nvoid R_DWTextureStudio_Shutdown( void );\nvoid R_DWTextureStudio_Tick( void );\n"
    results=[
      replace_once(tr_local,"void\tR_ImageList_f( void );",
         "void\tR_ImageList_f( void );"+header,o.check_only),
      replace_once(tr_image,"void R_DeleteTextures( void ) {",
         START+"\n"+INC+"\n"+END+"\n\nvoid R_DeleteTextures( void ) {",o.check_only),
      replace_once(tr_init,'\tri.Cmd_AddCommand( "imagelist", R_ImageList_f );',
         '\tR_DWTextureStudio_Init();\n\tri.Cmd_AddCommand( "imagelist", R_ImageList_f );',
         o.check_only),
      replace_once(tr_init,'\tri.Cmd_RemoveCommand( "imagelist" );',
         '\tR_DWTextureStudio_Shutdown();\n\tri.Cmd_RemoveCommand( "imagelist" );',
         o.check_only),
      replace_once(tr_cmds,'\ttr.frameCount++;\n\ttr.frameSceneNum = 0;',
         '\tR_DWTextureStudio_Tick();\n\ttr.frameCount++;\n\ttr.frameSceneNum = 0;',
         o.check_only),
    ]
    proof={"base_run":41408153237,"base_commit":"6fd61c7bd4e6a1c23c549c93d237f2204c9d3d89",
           "dry_run":o.check_only,"changes":results,"feature_default":"OFF",
           "scope":"BSP world surface pick and staged PNG GPU replacement only",
           "limitations":["no real AI worker bundled","not yet build-tested","not GPU or in-game tested",
             "no occlusion-aware visibility gate","no per-surface override for shared images"]}
    if o.proof:o.proof.write_text(json.dumps(proof,indent=2)+"\n")
    print("DW_AI_TEXTURE_STUDIO_V01_"+("PREFLIGHT" if o.check_only else "APPLIED"))

if __name__=="__main__":
    main()
