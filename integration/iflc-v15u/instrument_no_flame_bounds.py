#!/usr/bin/env python3
"""Test-only: force AUTO flame-bounds discovery to fail.
A successful MANUAL dw_fl_self_pick then proves production manual mode no longer
relies on flame bounds. Never used by the Win64 packaging job.
"""
from pathlib import Path
import sys
src=Path(sys.argv[1]).resolve()
p=src/'SP/code/rend2/tr_iflc_self.inc';s=p.read_text()
needle='''static qboolean R_IFLC_SelfBounds(int ownerIndex, vec3_t lo, vec3_t hi, vec3_t anchor)
{
    int i,j,count=0;
'''
repl='''static qboolean R_IFLC_SelfBounds(int ownerIndex, vec3_t lo, vec3_t hi, vec3_t anchor)
{
    int i,j,count=0;
    return qfalse; /* IFLC15U TEST ONLY: simulate missing/ambiguous flame geometry */
'''
assert s.count(needle)==1;s=s.replace(needle,repl);p.write_text(s)
print('IFLC15U_TEST_FORCED_NO_FLAME_BOUNDS')
