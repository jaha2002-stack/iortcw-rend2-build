#!/usr/bin/env python3
from pathlib import Path
import argparse

ap=argparse.ArgumentParser()
ap.add_argument("source")
args=ap.parse_args()
p=Path(args.source)/"SP/code/rend2/tr_shader.c"
s=p.read_text()
old='''				specularImg = R_FindImageFile(specularName, IMGTYPE_COLORALPHA, specularFlags | IMGFLAG_PBRDATA);
				if (specularImg)
				{
					VectorSet4(diffuse->specularScale, 1.0f, 1.0f, -1.0f, 1.0f);
					pbrOrm = qtrue;
				}
'''
new='''				specularImg = R_FindImageFile(specularName, IMGTYPE_COLORALPHA, specularFlags | IMGFLAG_PBRDATA);
				if (specularImg)
				{
					ri.Printf( PRINT_ALL, "DW_PBR_ORM_LOADED path=%s\\n", specularName );
					VectorSet4(diffuse->specularScale, 1.0f, 1.0f, -1.0f, 1.0f);
					pbrOrm = qtrue;
				}
'''
if s.count(old)!=1:
    raise SystemExit(f"ORM trace anchor count={s.count(old)}")
p.write_text(s.replace(old,new,1))
print("DW_PBR_TESTLAB_ORM_TRACE_APPLIED")
