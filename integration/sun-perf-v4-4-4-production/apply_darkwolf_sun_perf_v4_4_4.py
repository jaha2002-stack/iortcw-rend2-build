#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source")
P = ROOT / "SP/code/rend2/tr_scene.c"
MARK = "DARKWOLF_FORCE_SUN_CSM_SMART_PRODUCTION_V444"

def rep(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ERROR {label}: expected 1 anchor, found {n}")
    return text.replace(old, new, 1)

s = P.read_text(encoding="utf-8")
if MARK in s:
    print("DarkWolf forceSun smart CSM v4.4.4 already applied")
    raise SystemExit(0)

for marker in [
    "R_VolumetricSunMapSourceValid",
    "R_VolumetricSunDirectionChanged",
    "R_VolumetricSunCommitCascade",
    "R_VolumetricSunRestoreCascade",
]:
    if marker not in s:
        raise SystemExit("ERROR parent smart-CSM contract missing: " + marker)

# Never build the primary-view sun CSM from a skybox portal scene.  Evidence in
# TestLab showed those scenes are auxiliary and duplicate the producer call.
s = rep(
    s,
    '''\tif(glRefConfig.framebufferObject && r_sunlightMode->integer && !( fd->rdflags & RDF_NOWORLDMODEL ) && (r_forceSun->integer || tr.sunShadows || volumetricSunCsmRequest))
{''',
    '''\tif(glRefConfig.framebufferObject && r_sunlightMode->integer && !( fd->rdflags & RDF_NOWORLDMODEL ) &&
\t\t(r_forceSun->integer || tr.sunShadows || volumetricSunCsmRequest) &&
\t\t!(fd->rdflags & RDF_SKYBOXPORTAL))
{''',
    "primary-view CSM guard",
)

anchor = '''static void R_VolumetricSunRestoreCascade(int cascade)
{
\tif (tr.volumetricSunCsmValid[cascade])
\t\tMat4Copy(tr.volumetricSunCsmMvp[cascade], tr.refdef.sunShadowMvp[cascade]);
}
'''
helper = anchor + '''
// DARKWOLF_FORCE_SUN_CSM_SMART_PRODUCTION_V444
// r_forceSun 1 is a static-direction sun.  Keep the near visible cascade live
// every frame and reuse the exact full-resolution CSM for only one/three
// intermediate frames in the middle/far cascades.  This changes update cadence
// only: map resolution, projection, PCF/filtering, caster selection and lighting
// remain the existing production path.
static int s_forceSunVisibleCsmActive = 0;

static qboolean R_ForceSunVisibleShouldUpdateCascade(int cascade)
{
\tif (!tr.volumetricSunCsmValid[cascade])
\t\treturn qtrue;
\tif (cascade <= 0)
\t\treturn qtrue;
\tif (cascade == 1)
\t\treturn (tr.frameCount & 1) == 0 ? qtrue : qfalse;
\tif (cascade == 2)
\t\treturn (tr.frameCount & 3) == 0 ? qtrue : qfalse;
\treturn qfalse;
}
'''
s = rep(s, anchor, helper, "install forceSun cadence helper")

old = '''\t\telse
\t\t{

\t\t\tif (r_shadowCascadeZFar->integer != 0)
'''
new = '''\t\telse if (r_forceSun->integer == 1)
\t\t{
\t\t\tqboolean sunChanged;
\t\t\tint cascade;

\t\t\tif (!s_forceSunVisibleCsmActive)
\t\t\t{
\t\t\t\tfor (cascade = 0; cascade < 4; ++cascade)
\t\t\t\t\ttr.volumetricSunCsmValid[cascade] = qfalse;
\t\t\t\ts_forceSunVisibleCsmActive = 1;
\t\t\t}

\t\t\tsunChanged = R_VolumetricSunDirectionChanged(tr.refdef.sunDir, tr.volumetricSunCsmSunDirection);

\t\t\tif (r_shadowCascadeZFar->integer != 0)
\t\t\t{
\t\t\t\tfor (cascade = 0; cascade < 3; ++cascade)
\t\t\t\t{
\t\t\t\t\tif (sunChanged || R_ForceSunVisibleShouldUpdateCascade(cascade))
\t\t\t\t\t{
\t\t\t\t\t\tR_RenderSunShadowMaps(fd, cascade);
\t\t\t\t\t\tR_VolumetricSunCommitCascade(cascade);
\t\t\t\t\t}
\t\t\t\t\telse
\t\t\t\t\t{
\t\t\t\t\t\tR_VolumetricSunRestoreCascade(cascade);
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t\telse
\t\t\t{
\t\t\t\tMat4Zero(tr.refdef.sunShadowMvp[0]);
\t\t\t\tMat4Zero(tr.refdef.sunShadowMvp[1]);
\t\t\t\tMat4Zero(tr.refdef.sunShadowMvp[2]);
\t\t\t}

\t\t\tif (sunChanged || !tr.volumetricSunCsmValid[3])
\t\t\t{
\t\t\t\tR_RenderSunShadowMaps(fd, 3);
\t\t\t\tR_VolumetricSunCommitCascade(3);
\t\t\t}
\t\t\telse
\t\t\t{
\t\t\t\tR_VolumetricSunRestoreCascade(3);
\t\t\t}

\t\t\tif (sunChanged)
\t\t\t\tVectorCopy(tr.refdef.sunDir, tr.volumetricSunCsmSunDirection);
\t\t}
\t\telse
\t\t{
\t\t\ts_forceSunVisibleCsmActive = 0;

\t\t\tif (r_shadowCascadeZFar->integer != 0)
'''
s = rep(s, old, new, "install forceSun production smart CSM path")

for forbidden in ["r_sunPerfLab", "r_sunPerfCandidate", "SUNPERF_", "qglFinish()"]:
    if forbidden in s:
        raise SystemExit("ERROR diagnostic symbol leaked into clean source: " + forbidden)

P.write_text(s, encoding="utf-8", newline="\n")
print("DARKWOLF_FORCE_SUN_CSM_SMART_PRODUCTION_V444_PATCH_OK")
