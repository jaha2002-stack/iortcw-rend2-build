#!/usr/bin/env python3
"""Render the published candidate at validated, directly sunlit Assault views."""
import argparse, inspect
from pathlib import Path
import rc4_requested_views as driver

source=inspect.getsource(driver.capture)
changes=[
    ("'set com_fixedtime 100'", "'set fixedtime 100'"),
    ("'set r_forceSunPause 1','give all','wait 5','weapon 3','wait 35'",
     "'set r_forceSunPause 1','set fixedtime 100','god','notarget','give all','wait 3','weapon 3','wait 15'"),
    ("'wait 30','set dw_proofFreeze 1','wait 3'", "'wait 8','set dw_proofFreeze 1','wait 3'"),
    ("'set r_volumetricSun '+('0' if map_name=='assault' and mode=='off' else '1'),",
     "'set r_volumetricSun 1',\n                     'set r_volumetricSunStrength '+('0' if mode=='off' else '0.72'),"),
    ("f'set dw_proofShot {index}','wait 5',f'screenshot {name}','wait 3'",
     "f'set dw_proofShot {index}','wait 3',f'screenshot {name}','wait 1'"),
    ("timeout=900", "timeout=600"),
    ("    vv=views(map_name)", """    from rc4_assault_camera import select_views
    vv,validation=select_views(retail)
    (output/'assault-camera-validation.json').write_text(json.dumps(validation,indent=2)+'\\n')
    print(json.dumps(validation,indent=2),flush=True)"""),
]
for old,new in changes:
    if source.count(old)!=1:raise RuntimeError('Capture source drift: '+repr(old))
    source=source.replace(old,new)
namespace=driver.__dict__.copy()
exec(compile(source,__file__,'exec'),namespace)
ap=argparse.ArgumentParser()
for name in ('source','retail','release','output'):ap.add_argument(name,type=Path)
ap.add_argument('variant',choices=('base','candidate'))
args=ap.parse_args()
namespace['capture'](args.source,args.retail,args.release,args.output,args.variant,'assault')
