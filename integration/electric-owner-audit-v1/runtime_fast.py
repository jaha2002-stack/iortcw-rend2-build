#!/usr/bin/env python3
from pathlib import Path
import argparse,sys,json
sys.path.insert(0,str(Path(__file__).resolve().parent))
import runtime_lab as lab

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('retail',type=Path)
    ap.add_argument('out',type=Path)
    a=ap.parse_args()
    original=lab.choose_eyes
    lab.choose_eyes=lambda world,target,count=4: original(world,target,1)
    report=lab.lab(a.retail.resolve(),a.out.resolve(),'escape1')
    print('EPOA_FAST_RESULT',json.dumps({
        'native':report['native']['summary_max'],
        'controlled':report['controlled']['summary_max'] if report.get('controlled') else None,
        'delta':report.get('delta'),
        'selected_fixture':report.get('selected_fixture'),
        'suspicious':len(report['controlled']['suspicious_near_pairs']) if report.get('controlled') else None
    },sort_keys=True))

# rerun with delivered-owner selection
