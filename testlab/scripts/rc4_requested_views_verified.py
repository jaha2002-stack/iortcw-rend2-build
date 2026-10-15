#!/usr/bin/env python3
"""Correct only capture controls; use the existing auditable camera driver.

The sun master is latched. Its strength is a live uniform, so the attribution
frame uses strength=0 while all delivered ON frames retain strength=0.72.
Never modify the candidate renderer, its settings profile, or image pixels.
"""
from pathlib import Path

original = Path(__file__).with_name('rc4_requested_views.py')
text = original.read_text()
replacements = [
    ("'set com_fixedtime 100'", "'set fixedtime 100'"),
    ("'set r_forceSunPause 1','give all','wait 5','weapon 3','wait 35'",
     "'set r_forceSunPause 1','set fixedtime 100','god','notarget','give all','wait 3','weapon 3','wait 15'"),
    ("'wait 30','set dw_proofFreeze 1','wait 3'",
     "'wait 8','set dw_proofFreeze 1','wait 3'"),
    ("'set r_volumetricSun '+('0' if map_name=='assault' and mode=='off' else '1'),",
     "'set r_volumetricSun 1',\n                     'set r_volumetricSunStrength '+('0' if map_name=='assault' and mode=='off' else '0.72'),"),
    ("f'set dw_proofShot {index}','wait 5',f'screenshot {name}','wait 3'",
     "f'set dw_proofShot {index}','wait 3',f'screenshot {name}','wait 1'"),
    ("timeout=900", "timeout=600"),
]
anchor = "    assert renderer == {str(p.relative_to(code)): digest(p) for p in (code/'rend2').rglob('*') if p.is_file()}"
idle = """    # Isolated photo-mode pose lock, not a change to game rendering.
    edit('cgame/cg_weapons.c', '\\tfracsin = sin( cg.time * 0.001 );', r'''
    fracsin = sin(cg.time * 0.001);
    { char proof[16];
      trap_Cvar_VariableStringBuffer("dw_proofAutomation",proof,sizeof(proof));
      if(atoi(proof)) fracsin=0.0f; }
''')
"""
replacements.append((anchor, idle + anchor))
for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'Capture driver drift: expected one anchor, got {count}: {old!r}')
    text = text.replace(old, new)
exec(compile(text, str(original), 'exec'), {'__name__': '__main__', '__file__': str(original)})
