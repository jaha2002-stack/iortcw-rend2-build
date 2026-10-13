#!/usr/bin/env python3
"""TESTLAB ONLY: enable stock AVI video/stopvideo commands in live SP.
No production executable, patch or preset is modified by this instrumentation.
Stock ioRTCW's console video command only permits demo playback.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1])
path=root/"SP/code/client/cl_main.c"
s=path.read_text()
old='''\tif( !clc.demoplaying )
\t{
\t\tCom_Printf( "The video command can only be used when playing back demos\\n" );
\t\treturn;
\t}'''
new='''\t// DARKWOLF_TESTLAB_LIVE_AVI_ONLY: production cl_main.c remains unchanged.
\t// The stock CL_OpenAVIForWriting and CL_CloseAVI produce real rendered AVI frames.
\t// Permit capture in a live single-player map only for this isolated TestLab build.
\tif( !clc.demoplaying && clc.state != CA_ACTIVE )
\t{
\t\tCom_Printf( "TESTLAB_LIVE_AVI requires an active SP map or demo playback\\n" );
\t\treturn;
\t}'''
assert s.count(old)==1,("live AVI diagnostic anchor",s.count(old))
path.write_text(s.replace(old,new,1))
print("TESTLAB_LIVE_AVI_INSTRUMENTED",str(path))
