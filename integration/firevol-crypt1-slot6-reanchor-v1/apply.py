#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1])
p=root/"tr_backend.c"
s=p.read_text()

old='''static qboolean RB_FireV07NameLooksFire(const char *name)
{
	static const char *tokens[] = {
		"fire", "flame", "torch", "blaze", "burn", "ember", "flamethrower", NULL
	};
	int i;
	if (!name || !name[0])
		return qfalse;
	if (RB_FireV085NameLooksWeaponStream(name))
		return qfalse;
	for (i = 0; tokens[i]; ++i)
		if (RB_FireV07ContainsToken(name, tokens[i]))
			return qtrue;
	return qfalse;
}
'''

new='''// DARKWOLF_FIREVOL_CRYPT1_SLOT6_REANCHOR_V1
// Burn/scorch decals are evidence of past impact/heat on geometry, not a physical flame fixture.
// Production already rejected them for synthetic/fallback admission, but positive native DLight
// owners could still bind to the nearest semanticFire anchor because generic "burn" was accepted
// by RB_FireV07NameLooksFire(). This caused Crypt1 surface 9035 / pool 52 to anchor FireVol to
// textures/decals/burnm_01a instead of the actual flame fixture.
static qboolean RB_FireV07NameLooksBurnScorchDecal(const char *name)
{
	qboolean decalFamily;
	if (!name || !name[0])
		return qfalse;
	decalFamily = RB_FireV07ContainsToken(name, "/decals/") ||
		RB_FireV07ContainsToken(name, "decals/");
	if (!decalFamily)
		return qfalse;
	return (RB_FireV07ContainsToken(name, "burn") ||
		RB_FireV07ContainsToken(name, "scorch")) ? qtrue : qfalse;
}

static qboolean RB_FireV07NameLooksFire(const char *name)
{
	static const char *tokens[] = {
		"fire", "flame", "torch", "blaze", "burn", "ember", "flamethrower", NULL
	};
	int i;
	if (!name || !name[0])
		return qfalse;
	if (RB_FireV085NameLooksWeaponStream(name))
		return qfalse;
	// V1 targeted ownership correction: a decal can never become a FireVol flame anchor.
	if (RB_FireV07NameLooksBurnScorchDecal(name))
		return qfalse;
	for (i = 0; tokens[i]; ++i)
		if (RB_FireV07ContainsToken(name, tokens[i]))
			return qtrue;
	return qfalse;
}
'''

if old not in s:
    raise SystemExit("RB_FireV07NameLooksFire anchor not found")
s=s.replace(old,new,1)

p.write_text(s)
print("PASS Crypt1 Slot6 Reanchor V1 patch: burn/scorch decals excluded from flame-anchor evidence")
