#!/usr/bin/env python3
"""Floating-point arithmetic checks; not equivalent to GPU image/performance validation."""
import json, math, random, struct, sys
from pathlib import Path
def f(x): return struct.unpack('f', struct.pack('f', x))[0]
def test():
    rng=random.Random(44620261011); max_fire=0.0; max_sun=0.0
    for _ in range(20000):
        x=f(rng.uniform(-150,150));y=f(rng.uniform(-150,150));w=f(rng.uniform(1,250));k=rng.choice((3.1,4.6,6.5))
        radius=f(f(math.sqrt(f(f(x*x)+f(y*y))))/w)
        old=f(math.exp(f(-k*f(radius*radius))))
        r2=f(f(f(x*x)+f(y*y))/f(w*w));new=f(math.exp(f(-k*r2)))
        max_fire=max(max_fire,abs(old-new))
        if abs(old-new)>2e-6: raise AssertionError(('fire',old,new))
    for _ in range(3000):
        count=rng.randint(4,64);depth=f(rng.uniform(0.01,1));ray=f(rng.uniform(100,8000));density=f(rng.uniform(0.000001,0.014))
        step=f(depth/float(count));world=f(ray*step);jitter=f(rng.uniform(-0.25,0.25))
        t=f(math.exp(f(-density*f(world*f(0.5+jitter)))));decay=f(math.exp(f(-density*world)))
        for i in range(count):
            sample=f(step*f(i+f(0.5+jitter)));sample=f(min(max(sample,0),depth))
            old=f(math.exp(f(-density*f(ray*sample))))
            max_sun=max(max_sun,abs(t-old))
            if abs(t-old)>2e-5: raise AssertionError(('sun',i,t,old))
            t=f(t*decay)
    return {'status':'ARITHMETIC_SMOKE_PASS','fire_cases':20000,'sun_ray_cases':3000,
            'fire_max_abs_error':max_fire,'sun_max_abs_error':max_sun,'GPU_VALIDATION':'NOT_RUN'}
if __name__=='__main__':
    z=test();print(json.dumps(z,indent=2))
    if len(sys.argv)>1: Path(sys.argv[1]).write_text(json.dumps(z,indent=2)+'\n')
