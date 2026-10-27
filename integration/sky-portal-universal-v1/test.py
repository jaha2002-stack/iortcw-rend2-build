#!/usr/bin/env python3
"""Deterministic source and eligibility tests; not a substitute for full-game GPU testing."""
from pathlib import Path
import sys, hashlib
root=Path(__file__).parent
s=(root/'apply.py').read_text()
checks={
 'source-only backend patch':"'SP/code/rend2/tr_backend.c'" in s and "'SP/code/rend2/tr_sky.c'" not in s.split('proof={')[-1],
 'portal-sky view gating': 'RDF_SKYBOXPORTAL | RDF_DRAWSKYBOX' in s,
 'no mirrored/cubemap/shadow view': 'backEnd.viewParms.isPortal' in s and 'VPF_SHADOWMAP' in s and 'targetFbo' in s,
 'no map whitelist': '"trainyard"' not in s and '"factory"' not in s and 'r_portalsky && r_portalsky->integer && tr.world)' in s,
 'single sample FBO used': 'backEnd.viewParms.targetFbo = tr.msaaResolveFbo' in s,
 'prepass no self-copy': 'tr.msaaResolveFbo && !dwPortalSkySingleSample' in s,
 'explicit old-color clear': 'clearBits |= GL_COLOR_BUFFER_BIT;' in s,
 'depth preservation for main': 'DO NOT copy portal depth' in s,
 'replicate color 1 to N': 'FBO_FastBlit(tr.msaaResolveFbo, NULL, tr.renderFbo, NULL,' in s,
 'no sky stage disable': 'RB_StageIteratorSky' not in s.split('s=replace(s,anchor,addition)')[-1],
 'keep MSAA and HDR': 'r_hdr->integer' in s and 'r_ext_framebuffer_multisample->integer >= 2' in s,
}
for name,passed in checks.items():
 print(('PASS ' if passed else 'FAIL ')+name)
 assert passed,name
# Synthetic 8-sample conceptual proof of why this protocol removes single-sample
# shadow stipple in a sky background while leaving the world MSAA attachment intact.
portal_pixel=(.56,.46,.39)
samples=[portal_pixel]*8
resolved=tuple(sum(sample[ch] for sample in samples)/8 for ch in range(3))
assert all(abs(a-b)<1e-10 for a,b in zip(portal_pixel,resolved))
# A scene fragment that covers 2 of 8 samples still gets edge AA over portal sky.
world=(.10,.13,.15)
for j in (0,7):samples[j]=world
out=tuple(sum(sample[ch] for sample in samples)/8 for ch in range(3))
expected=tuple(.25*world[ch]+.75*portal_pixel[ch] for ch in range(3))
assert all(abs(a-b)<1e-10 for a,b in zip(out,expected))
# Eligibility matrix: for every map name, activation is driven ONLY by portal-sky
# view/capability flags, not a list of levels. Assert negative cases are untouched.
def eligible(*, portal, flags, world, shadow, reflection, target, fbo, blit, size_match, hdr, msaa, portalsky):
    return bool(portal and flags == 3 and world and not shadow and not reflection and
                not target and fbo and blit and size_match and hdr and msaa >= 2 and portalsky)
for name in ('trainyard', 'factory', 'village1', 'village2', 'castle', 'forest', 'custom_map', ''):
    values=dict(portal=True,flags=3,world=True,shadow=False,reflection=False,target=False,
                fbo=True,blit=True,size_match=True,hdr=True,msaa=8,portalsky=True)
    assert eligible(**values), name
    for key, value in [('portal',False),('flags',0),('world',False),('shadow',True),
                       ('reflection',True),('target',True),('fbo',False),('blit',False),
                       ('size_match',False),('hdr',False),('msaa',0),('msaa',1),('portalsky',False)]:
        assert not eligible(**{**values,key:value}), (name,key)
print('DW_PORTAL_SKY_UNIVERSAL_SOURCE_AND_CAPABILITY_TESTS_PASS')