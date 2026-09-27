#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source")
CHECK_ONLY = "--check-only" in sys.argv[2:]
MARK = "DARKWOLF_AI_MATERIAL_LAB_V0_1"

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def write(rel, data):
    if not CHECK_ONLY:
        (ROOT / rel).write_text(data, encoding="utf-8", newline="\n")

def replace_once(data, old, new, label):
    count = data.count(old)
    if count != 1:
        raise SystemExit(f"ERROR: {label}: expected anchor exactly once, found {count}")
    return data.replace(old, new, 1)

main_rel = "SP/code/rend2/tr_main.c"
init_rel = "SP/code/rend2/tr_init.c"
main = read(main_rel)
init = read(init_rel)

if MARK in main or MARK in init:
    raise SystemExit("ERROR: DarkWolf AI Material Lab v0.1 already applied")

module = r'''
// DARKWOLF_AI_MATERIAL_LAB_V0_1
// Renderer-native material authoring foundation. Original shader text and source
// textures are never modified; edits stay reversible and persist by shader name.
#define MATERIAL_LAB_MAX_OVERRIDES 256
#define MATERIAL_LAB_PROFILE_VERSION 1
#define MATERIAL_LAB_EPSILON 0.0001f

typedef struct {
	qboolean inUse;
	qboolean enabled;
	qboolean baseCaptured;
	char shaderName[MAX_QPATH];
	shader_t *shader;
	vec4_t baseNormalScale[MAX_SHADER_STAGES];
	vec4_t baseSpecularScale[MAX_SHADER_STAGES];
	float roughness;
	float metallic;
	float specular;
	float normalScale;
	float parallaxScale;
	float lastRoughness;
	float lastMetallic;
	float lastSpecular;
	float lastNormalScale;
	float lastParallaxScale;
} materialLabOverride_t;

static materialLabOverride_t s_materialLabOverrides[MATERIAL_LAB_MAX_OVERRIDES];
static int s_materialLabSelected = -1;
static world_t *s_materialLabWorld = NULL;
static qboolean s_materialLabProfileLoaded = qfalse;
static qboolean s_materialLabRuntimeApplied = qfalse;
static char s_materialLabMapName[MAX_QPATH] = "";
static char s_materialLabProfilePath[MAX_OSPATH] = "";

static cvar_t *r_materialLab = NULL;
static cvar_t *r_materialLabAutoload = NULL;
static cvar_t *r_materialLabPick = NULL;
static cvar_t *r_materialLabRoughness = NULL;
static cvar_t *r_materialLabMetallic = NULL;
static cvar_t *r_materialLabSpecular = NULL;
static cvar_t *r_materialLabNormalScale = NULL;
static cvar_t *r_materialLabParallaxScale = NULL;

static float R_MaterialLabRoughnessToEncodedGloss(float roughness)
{
	float r = CLAMP(roughness, 0.02f, 1.0f);
	switch (r_glossType->integer)
	{
		case 1: return 1.0f - r;
		case 2: return r;
		case 3:
		{
			float r2 = r * r;
			float r4 = r2 * r2;
			return CLAMP((2.0f / r4 - 2.0f) / 8190.0f, 0.0f, 1.0f);
		}
		case 0:
		default: return CLAMP(log2f(1.0f / r) / 3.0f, 0.0f, 1.0f);
	}
}

static float R_MaterialLabEncodedGlossToRoughness(float gloss)
{
	float g = CLAMP(gloss, 0.0f, 1.0f);
	switch (r_glossType->integer)
	{
		case 1: return CLAMP(1.0f - g, 0.02f, 1.0f);
		case 2: return CLAMP(g, 0.02f, 1.0f);
		case 3: return CLAMP(powf(2.0f / (8190.0f * g + 2.0f), 0.25f), 0.02f, 1.0f);
		case 0:
		default: return CLAMP(exp2f(-3.0f * g), 0.02f, 1.0f);
	}
}

static shaderStage_t *R_MaterialLabReferenceStage(shader_t *shader)
{
	int i;
	shaderStage_t *fallback = NULL;
	if (!shader) return NULL;
	for (i = 0; i < shader->numUnfoggedPasses && i < MAX_SHADER_STAGES; ++i)
	{
		shaderStage_t *stage = shader->stages[i];
		if (!stage || !stage->active) continue;
		if (!fallback) fallback = stage;
		if (stage->glslShaderGroup == tr.lightallShader) return stage;
	}
	return fallback;
}

static void R_MaterialLabCaptureBase(materialLabOverride_t *entry)
{
	int i;
	if (!entry || entry->baseCaptured || !entry->shader) return;
	for (i = 0; i < MAX_SHADER_STAGES; ++i)
	{
		shaderStage_t *stage = entry->shader->stages[i];
		if (!stage) continue;
		Vector4Copy(stage->normalScale, entry->baseNormalScale[i]);
		Vector4Copy(stage->specularScale, entry->baseSpecularScale[i]);
	}
	entry->baseCaptured = qtrue;
}

static void R_MaterialLabRestoreEntry(materialLabOverride_t *entry)
{
	int i;
	if (!entry || !entry->baseCaptured || !entry->shader) return;
	if (Q_stricmp(entry->shader->name, entry->shaderName)) return;
	for (i = 0; i < MAX_SHADER_STAGES; ++i)
	{
		shaderStage_t *stage = entry->shader->stages[i];
		if (!stage) continue;
		Vector4Copy(entry->baseNormalScale[i], stage->normalScale);
		Vector4Copy(entry->baseSpecularScale[i], stage->specularScale);
	}
}

static void R_MaterialLabApplyEntry(materialLabOverride_t *entry)
{
	int i;
	float encodedGloss;
	if (!entry || !entry->inUse || !entry->enabled || !entry->shader) return;
	R_MaterialLabCaptureBase(entry);
	encodedGloss = R_MaterialLabRoughnessToEncodedGloss(entry->roughness);
	for (i = 0; i < MAX_SHADER_STAGES; ++i)
	{
		shaderStage_t *stage = entry->shader->stages[i];
		if (!stage || !stage->active) continue;
		Vector4Copy(entry->baseNormalScale[i], stage->normalScale);
		Vector4Copy(entry->baseSpecularScale[i], stage->specularScale);
		stage->normalScale[0] = entry->baseNormalScale[i][0] * entry->normalScale;
		stage->normalScale[1] = entry->baseNormalScale[i][1] * entry->normalScale;
		stage->normalScale[3] = entry->baseNormalScale[i][3] * entry->parallaxScale;
		if (r_pbr && r_pbr->integer)
		{
			stage->specularScale[0] = encodedGloss;
			stage->specularScale[1] = CLAMP(entry->metallic, 0.0f, 1.0f);
		}
		else
		{
			float f0 = CLAMP(entry->specular, 0.0f, 1.0f);
			stage->specularScale[0] = f0;
			stage->specularScale[1] = f0;
			stage->specularScale[2] = f0;
			stage->specularScale[3] = encodedGloss;
		}
	}
}

static void R_MaterialLabBindEntry(materialLabOverride_t *entry)
{
	shader_t *shader;
	if (!entry || !entry->inUse || !entry->shaderName[0]) return;
	if (entry->shader && !Q_stricmp(entry->shader->name, entry->shaderName)) return;
	shader = R_FindShaderByName(entry->shaderName);
	if (!shader || Q_stricmp(shader->name, entry->shaderName)) return;
	entry->shader = shader;
	entry->baseCaptured = qfalse;
	R_MaterialLabCaptureBase(entry);
	if (entry->enabled) R_MaterialLabApplyEntry(entry);
}

static int R_MaterialLabFindSlot(const char *shaderName)
{
	int i;
	for (i = 0; i < MATERIAL_LAB_MAX_OVERRIDES; ++i)
		if (s_materialLabOverrides[i].inUse && !Q_stricmp(s_materialLabOverrides[i].shaderName, shaderName))
			return i;
	return -1;
}

static int R_MaterialLabAllocSlot(const char *shaderName)
{
	int i = R_MaterialLabFindSlot(shaderName);
	if (i >= 0) return i;
	for (i = 0; i < MATERIAL_LAB_MAX_OVERRIDES; ++i)
	{
		materialLabOverride_t *entry = &s_materialLabOverrides[i];
		if (entry->inUse) continue;
		Com_Memset(entry, 0, sizeof(*entry));
		entry->inUse = qtrue;
		Q_strncpyz(entry->shaderName, shaderName, sizeof(entry->shaderName));
		entry->roughness = 0.55f;
		entry->metallic = 0.0f;
		entry->specular = 0.04f;
		entry->normalScale = 1.0f;
		entry->parallaxScale = 1.0f;
		return i;
	}
	return -1;
}

static void R_MaterialLabSeedConceptualFromShader(materialLabOverride_t *entry)
{
	shaderStage_t *stage;
	if (!entry || !entry->shader) return;
	stage = R_MaterialLabReferenceStage(entry->shader);
	if (!stage) return;
	if (r_pbr && r_pbr->integer)
	{
		entry->roughness = R_MaterialLabEncodedGlossToRoughness(stage->specularScale[0]);
		entry->metallic = CLAMP(stage->specularScale[1], 0.0f, 1.0f);
		entry->specular = 0.04f;
	}
	else
	{
		entry->roughness = R_MaterialLabEncodedGlossToRoughness(stage->specularScale[3]);
		entry->metallic = 0.0f;
		entry->specular = CLAMP((stage->specularScale[0] + stage->specularScale[1] + stage->specularScale[2]) / 3.0f, 0.0f, 1.0f);
	}
	entry->normalScale = 1.0f;
	entry->parallaxScale = 1.0f;
	entry->lastRoughness = entry->roughness;
	entry->lastMetallic = entry->metallic;
	entry->lastSpecular = entry->specular;
	entry->lastNormalScale = entry->normalScale;
	entry->lastParallaxScale = entry->parallaxScale;
}

static void R_MaterialLabPushEntryToCvars(materialLabOverride_t *entry)
{
	if (!entry) return;
	ri.Cvar_Set("r_materialLabRoughness", va("%.6f", entry->roughness));
	ri.Cvar_Set("r_materialLabMetallic", va("%.6f", entry->metallic));
	ri.Cvar_Set("r_materialLabSpecular", va("%.6f", entry->specular));
	ri.Cvar_Set("r_materialLabNormalScale", va("%.6f", entry->normalScale));
	ri.Cvar_Set("r_materialLabParallaxScale", va("%.6f", entry->parallaxScale));
}

static qboolean R_MaterialLabFloatChanged(float a, float b)
{
	return fabsf(a - b) > MATERIAL_LAB_EPSILON ? qtrue : qfalse;
}

static void R_MaterialLabPullSelectedCvars(qboolean forceEnable)
{
	materialLabOverride_t *entry;
	qboolean changed;
	if (s_materialLabSelected < 0 || s_materialLabSelected >= MATERIAL_LAB_MAX_OVERRIDES) return;
	entry = &s_materialLabOverrides[s_materialLabSelected];
	if (!entry->inUse) return;
	changed =
		R_MaterialLabFloatChanged(entry->lastRoughness, r_materialLabRoughness->value) ||
		R_MaterialLabFloatChanged(entry->lastMetallic, r_materialLabMetallic->value) ||
		R_MaterialLabFloatChanged(entry->lastSpecular, r_materialLabSpecular->value) ||
		R_MaterialLabFloatChanged(entry->lastNormalScale, r_materialLabNormalScale->value) ||
		R_MaterialLabFloatChanged(entry->lastParallaxScale, r_materialLabParallaxScale->value);
	if (!changed && !forceEnable) return;
	entry->roughness = CLAMP(r_materialLabRoughness->value, 0.02f, 1.0f);
	entry->metallic = CLAMP(r_materialLabMetallic->value, 0.0f, 1.0f);
	entry->specular = CLAMP(r_materialLabSpecular->value, 0.0f, 1.0f);
	entry->normalScale = CLAMP(r_materialLabNormalScale->value, 0.0f, 4.0f);
	entry->parallaxScale = CLAMP(r_materialLabParallaxScale->value, 0.0f, 4.0f);
	entry->lastRoughness = entry->roughness;
	entry->lastMetallic = entry->metallic;
	entry->lastSpecular = entry->specular;
	entry->lastNormalScale = entry->normalScale;
	entry->lastParallaxScale = entry->parallaxScale;
	entry->enabled = qtrue;
	R_MaterialLabBindEntry(entry);
	R_MaterialLabApplyEntry(entry);
	s_materialLabRuntimeApplied = qtrue;
}

static void R_MaterialLabRestoreAll(void)
{
	int i;
	for (i = 0; i < MATERIAL_LAB_MAX_OVERRIDES; ++i)
		if (s_materialLabOverrides[i].inUse && s_materialLabOverrides[i].baseCaptured)
			R_MaterialLabRestoreEntry(&s_materialLabOverrides[i]);
	s_materialLabRuntimeApplied = qfalse;
}

static void R_MaterialLabClearTable(qboolean restore)
{
	if (restore) R_MaterialLabRestoreAll();
	Com_Memset(s_materialLabOverrides, 0, sizeof(s_materialLabOverrides));
	s_materialLabSelected = -1;
	s_materialLabProfileLoaded = qfalse;
}

static qboolean R_MaterialLabAppend(char *buffer, int capacity, int *used, const char *fmt, ...)
{
	va_list ap;
	int written;
	if (!buffer || !used || *used < 0 || *used >= capacity) return qfalse;
	va_start(ap, fmt);
	written = Q_vsnprintf(buffer + *used, (size_t)(capacity - *used), fmt, ap);
	va_end(ap);
	if (written < 0 || written >= capacity - *used) return qfalse;
	*used += written;
	return qtrue;
}

static qboolean R_MaterialLabLoadInternal(qboolean autoload)
{
	void *fileData = NULL;
	char *copy = NULL;
	char *line;
	long len;
	int version = -1;
	char mapName[MAX_QPATH] = {0};
	qboolean sawEnd = qfalse;
	qboolean ok = qfalse;
	int loaded = 0;
	int i;

	if (!tr.world || !s_materialLabProfilePath[0]) return qfalse;
	len = ri.FS_ReadFile(s_materialLabProfilePath, &fileData);
	if (len < 0 || !fileData)
	{
		if (!autoload) ri.Printf(PRINT_ALL, "MATERIAL_LAB: profile not found: %s\n", s_materialLabProfilePath);
		return qfalse;
	}
	R_MaterialLabClearTable(qtrue);
	copy = ri.Z_Malloc((int)len + 1);
	Com_Memcpy(copy, fileData, (int)len);
	copy[len] = '\0';
	ri.FS_FreeFile(fileData);
	fileData = NULL;
	for (line = strtok(copy, "\r\n"); line; line = strtok(NULL, "\r\n"))
	{
		char shaderName[MAX_QPATH];
		int enabled;
		float roughness, metallic, specular, normalScale, parallaxScale;
		int slot;
		if (!line[0] || line[0] == '#') continue;
		if (sscanf(line, "version %d", &version) == 1) continue;
		if (sscanf(line, "map %63s", mapName) == 1) continue;
		if (!Q_stricmp(line, "end")) { sawEnd = qtrue; continue; }
		if (sscanf(line, "shader %63s %d %f %f %f %f %f", shaderName, &enabled,
			&roughness, &metallic, &specular, &normalScale, &parallaxScale) == 7)
		{
			slot = R_MaterialLabAllocSlot(shaderName);
			if (slot < 0) goto done;
			s_materialLabOverrides[slot].enabled = enabled ? qtrue : qfalse;
			s_materialLabOverrides[slot].roughness = CLAMP(roughness, 0.02f, 1.0f);
			s_materialLabOverrides[slot].metallic = CLAMP(metallic, 0.0f, 1.0f);
			s_materialLabOverrides[slot].specular = CLAMP(specular, 0.0f, 1.0f);
			s_materialLabOverrides[slot].normalScale = CLAMP(normalScale, 0.0f, 4.0f);
			s_materialLabOverrides[slot].parallaxScale = CLAMP(parallaxScale, 0.0f, 4.0f);
			s_materialLabOverrides[slot].lastRoughness = s_materialLabOverrides[slot].roughness;
			s_materialLabOverrides[slot].lastMetallic = s_materialLabOverrides[slot].metallic;
			s_materialLabOverrides[slot].lastSpecular = s_materialLabOverrides[slot].specular;
			s_materialLabOverrides[slot].lastNormalScale = s_materialLabOverrides[slot].normalScale;
			s_materialLabOverrides[slot].lastParallaxScale = s_materialLabOverrides[slot].parallaxScale;
			loaded++;
			continue;
		}
		goto done;
	}
	if (!sawEnd || version != MATERIAL_LAB_PROFILE_VERSION || Q_stricmp(mapName, s_materialLabMapName)) goto done;
	for (i = 0; i < MATERIAL_LAB_MAX_OVERRIDES; ++i)
	{
		materialLabOverride_t *entry = &s_materialLabOverrides[i];
		if (!entry->inUse) continue;
		R_MaterialLabBindEntry(entry);
		if (entry->enabled) R_MaterialLabApplyEntry(entry);
	}
	s_materialLabProfileLoaded = qtrue;
	s_materialLabRuntimeApplied = qtrue;
	ok = qtrue;
	ri.Printf(PRINT_ALL, "MATERIAL_LAB: loaded %s entries=%d\n", s_materialLabProfilePath, loaded);

done:
	if (!ok)
	{
		R_MaterialLabClearTable(qtrue);
		if (!autoload) ri.Printf(PRINT_WARNING, "MATERIAL_LAB: rejected profile %s\n", s_materialLabProfilePath);
	}
	if (copy) ri.Free(copy);
	return ok;
}

static void R_MaterialLabEnsureWorld(void)
{
	if (!tr.world || !tr.world->baseName[0]) return;
	if (s_materialLabWorld == tr.world) return;
	// Previous shader pointers belong to the old world; never dereference them here.
	Com_Memset(s_materialLabOverrides, 0, sizeof(s_materialLabOverrides));
	s_materialLabSelected = -1;
	s_materialLabRuntimeApplied = qfalse;
	s_materialLabProfileLoaded = qfalse;
	s_materialLabWorld = tr.world;
	Q_strncpyz(s_materialLabMapName, tr.world->baseName, sizeof(s_materialLabMapName));
	Com_sprintf(s_materialLabProfilePath, sizeof(s_materialLabProfilePath),
		"materiallab/%s.materials", s_materialLabMapName);
	if (r_materialLab && r_materialLab->integer && r_materialLabAutoload && r_materialLabAutoload->integer)
		R_MaterialLabLoadInternal(qtrue);
}

static void R_MaterialLabFrontEndTick(void)
{
	int i;
	R_MaterialLabEnsureWorld();
	if (!tr.world || !r_materialLab) return;
	if (!r_materialLab->integer)
	{
		if (s_materialLabRuntimeApplied) R_MaterialLabRestoreAll();
		return;
	}
	for (i = 0; i < MATERIAL_LAB_MAX_OVERRIDES; ++i)
	{
		materialLabOverride_t *entry = &s_materialLabOverrides[i];
		if (!entry->inUse) continue;
		R_MaterialLabBindEntry(entry);
		if (!s_materialLabRuntimeApplied && entry->enabled) R_MaterialLabApplyEntry(entry);
	}
	if (!s_materialLabRuntimeApplied) s_materialLabRuntimeApplied = qtrue;
	R_MaterialLabPullSelectedCvars(qfalse);
}

static qboolean R_MaterialLabShaderEligible(const shader_t *shader)
{
	int sort;
	if (!shader || shader->numUnfoggedPasses <= 0) return qfalse;
	sort = (int)(shader->sort + 0.5f);
	if (shader->isSky || shader->isPortal) return qfalse;
	if (sort == SS_ENVIRONMENT || sort == SS_PORTAL || sort == SS_FOG || sort == SS_UNDERWATER) return qfalse;
	return qtrue;
}

static void R_MaterialLabSelectShader(shader_t *shader, int entityNum, int surfaceIndex,
	const char *surfaceType, float distance)
{
	int slot;
	materialLabOverride_t *entry;
	if (!shader || !R_MaterialLabShaderEligible(shader)) return;
	R_MaterialLabEnsureWorld();
	slot = R_MaterialLabAllocSlot(shader->name);
	if (slot < 0)
	{
		ri.Printf(PRINT_WARNING, "MATERIAL_LAB: override table full (%d)\n", MATERIAL_LAB_MAX_OVERRIDES);
		return;
	}
	entry = &s_materialLabOverrides[slot];
	if (!entry->shader)
	{
		entry->shader = shader;
		R_MaterialLabCaptureBase(entry);
		if (!entry->enabled) R_MaterialLabSeedConceptualFromShader(entry);
	}
	s_materialLabSelected = slot;
	entry->lastRoughness = entry->roughness;
	entry->lastMetallic = entry->metallic;
	entry->lastSpecular = entry->specular;
	entry->lastNormalScale = entry->normalScale;
	entry->lastParallaxScale = entry->parallaxScale;
	R_MaterialLabPushEntryToCvars(entry);
	ri.Printf(PRINT_ALL,
		"MATERIAL_LAB: selected shader=%s entity=%d surface=%d type=%s distance=%.1f state=%s mode=%s\n",
		entry->shaderName, entityNum, surfaceIndex, surfaceType ? surfaceType : "unknown", distance,
		entry->enabled ? "OVERRIDE" : "ORIGINAL", (r_pbr && r_pbr->integer) ? "PBR" : "CLASSIC");
	ri.Printf(PRINT_ALL,
		"MATERIAL_LAB: roughness=%.3f metallic=%.3f specular=%.3f normal=%.3f parallax=%.3f (editing any value applies live)\n",
		entry->roughness, entry->metallic, entry->specular, entry->normalScale, entry->parallaxScale);
}

static void R_MaterialLabHelp_f(void)
{
	ri.Printf(PRINT_ALL, "DarkWolf AI Material Lab v0.1\n");
	ri.Printf(PRINT_ALL, "  materiallab_pick       - select exact supported material under crosshair\n");
	ri.Printf(PRINT_ALL, "  materiallab_status     - show current selection and values\n");
	ri.Printf(PRINT_ALL, "  materiallab_apply      - enable current values even if unchanged\n");
	ri.Printf(PRINT_ALL, "  materiallab_reset      - restore selected material original stage scales\n");
	ri.Printf(PRINT_ALL, "  materiallab_save/load  - persist/reload per-map overrides\n");
	ri.Printf(PRINT_ALL, "  materiallab_list       - list in-memory material overrides\n");
	ri.Printf(PRINT_ALL, "  materiallab_reset_all confirm - restore and clear all in-memory overrides\n");
	ri.Printf(PRINT_ALL, "  r_materialLabRoughness 0.02..1 | r_materialLabMetallic 0..1 | r_materialLabSpecular 0..1\n");
	ri.Printf(PRINT_ALL, "  r_materialLabNormalScale 0..4 | r_materialLabParallaxScale 0..4\n");
	ri.Printf(PRINT_ALL, "NOTE: true Rend2 PBR remains global/latched through r_pbr; with r_pbr=0 the editor uses classic F0/gloss semantics.\n");
}

static void R_MaterialLabPick_f(void)
{
	R_MaterialLabEnsureWorld();
	if (!tr.world) { ri.Printf(PRINT_WARNING, "MATERIAL_LAB: no world loaded\n"); return; }
	ri.Cvar_Set("r_materialLab", "1");
	ri.Cvar_Set("r_materialLabPick", "1");
	ri.Printf(PRINT_ALL, "MATERIAL_LAB: point crosshair at a surface; picking on next main view\n");
}

static void R_MaterialLabStatus_f(void)
{
	materialLabOverride_t *entry;
	R_MaterialLabEnsureWorld();
	if (s_materialLabSelected < 0 || s_materialLabSelected >= MATERIAL_LAB_MAX_OVERRIDES)
	{
		ri.Printf(PRINT_ALL, "MATERIAL_LAB: map=%s selected=<none> master=%d profile=%s\n",
			s_materialLabMapName[0] ? s_materialLabMapName : "<none>", r_materialLab ? r_materialLab->integer : 0,
			s_materialLabProfileLoaded ? "loaded" : "not-loaded");
		return;
	}
	R_MaterialLabPullSelectedCvars(qfalse);
	entry = &s_materialLabOverrides[s_materialLabSelected];
	ri.Printf(PRINT_ALL,
		"MATERIAL_LAB: map=%s shader=%s enabled=%d mode=%s roughness=%.3f metallic=%.3f specular=%.3f normal=%.3f parallax=%.3f profile=%s\n",
		s_materialLabMapName, entry->shaderName, entry->enabled, (r_pbr && r_pbr->integer) ? "PBR" : "CLASSIC",
		entry->roughness, entry->metallic, entry->specular, entry->normalScale, entry->parallaxScale,
		s_materialLabProfilePath);
}

static void R_MaterialLabApply_f(void)
{
	if (s_materialLabSelected < 0) { ri.Printf(PRINT_WARNING, "MATERIAL_LAB: pick a material first\n"); return; }
	R_MaterialLabPullSelectedCvars(qtrue);
	R_MaterialLabStatus_f();
}

static void R_MaterialLabReset_f(void)
{
	materialLabOverride_t *entry;
	if (s_materialLabSelected < 0) { ri.Printf(PRINT_WARNING, "MATERIAL_LAB: pick a material first\n"); return; }
	entry = &s_materialLabOverrides[s_materialLabSelected];
	R_MaterialLabRestoreEntry(entry);
	entry->enabled = qfalse;
	R_MaterialLabSeedConceptualFromShader(entry);
	R_MaterialLabPushEntryToCvars(entry);
	ri.Printf(PRINT_ALL, "MATERIAL_LAB: restored original material stage scales for %s\n", entry->shaderName);
}

static void R_MaterialLabSave_f(void)
{
	char *buffer;
	int capacity = 65536;
	int used = 0;
	int i, count = 0;
	qboolean ok = qtrue;
	void *verifyData = NULL;
	long verifyLen;
	R_MaterialLabEnsureWorld();
	if (!tr.world || !s_materialLabProfilePath[0]) { ri.Printf(PRINT_WARNING, "MATERIAL_LAB: no world loaded\n"); return; }
	R_MaterialLabPullSelectedCvars(qfalse);
	buffer = ri.Z_Malloc(capacity);
	buffer[0] = '\0';
	ok = ok && R_MaterialLabAppend(buffer, capacity, &used, "# DarkWolf AI Material Lab v0.1\n");
	ok = ok && R_MaterialLabAppend(buffer, capacity, &used, "version %d\n", MATERIAL_LAB_PROFILE_VERSION);
	ok = ok && R_MaterialLabAppend(buffer, capacity, &used, "map %s\n", s_materialLabMapName);
	for (i = 0; i < MATERIAL_LAB_MAX_OVERRIDES; ++i)
	{
		materialLabOverride_t *entry = &s_materialLabOverrides[i];
		if (!entry->inUse || !entry->enabled) continue;
		ok = ok && R_MaterialLabAppend(buffer, capacity, &used,
			"shader %s 1 %.6f %.6f %.6f %.6f %.6f\n",
			entry->shaderName, entry->roughness, entry->metallic, entry->specular,
			entry->normalScale, entry->parallaxScale);
		count++;
	}
	ok = ok && R_MaterialLabAppend(buffer, capacity, &used, "end\n");
	if (!ok) { ri.Printf(PRINT_WARNING, "MATERIAL_LAB: profile buffer overflow\n"); ri.Free(buffer); return; }
	ri.FS_WriteFile(s_materialLabProfilePath, buffer, used);
	verifyLen = ri.FS_ReadFile(s_materialLabProfilePath, &verifyData);
	if (verifyLen != used || !verifyData || memcmp(verifyData, buffer, used) != 0)
	{
		if (verifyData) ri.FS_FreeFile(verifyData);
		ri.Free(buffer);
		ri.Printf(PRINT_WARNING, "MATERIAL_LAB: SAVE VERIFY FAILED: %s\n", s_materialLabProfilePath);
		return;
	}
	ri.FS_FreeFile(verifyData);
	ri.Free(buffer);
	s_materialLabProfileLoaded = qtrue;
	ri.Printf(PRINT_ALL, "MATERIAL_LAB: SAVED+VERIFIED %s entries=%d bytes=%d\n", s_materialLabProfilePath, count, used);
}

static void R_MaterialLabLoad_f(void)
{
	R_MaterialLabEnsureWorld();
	R_MaterialLabLoadInternal(qfalse);
}

static void R_MaterialLabList_f(void)
{
	int i, count = 0;
	for (i = 0; i < MATERIAL_LAB_MAX_OVERRIDES; ++i)
	{
		materialLabOverride_t *entry = &s_materialLabOverrides[i];
		if (!entry->inUse) continue;
		ri.Printf(PRINT_ALL, "MATERIAL_LAB[%d]: enabled=%d bound=%d shader=%s R=%.3f M=%.3f S=%.3f N=%.3f P=%.3f\n",
			i, entry->enabled, entry->shader ? 1 : 0, entry->shaderName, entry->roughness,
			entry->metallic, entry->specular, entry->normalScale, entry->parallaxScale);
		count++;
	}
	ri.Printf(PRINT_ALL, "MATERIAL_LAB: entries=%d/%d\n", count, MATERIAL_LAB_MAX_OVERRIDES);
}

static void R_MaterialLabResetAll_f(void)
{
	if (ri.Cmd_Argc() < 2 || Q_stricmp(ri.Cmd_Argv(1), "confirm"))
	{
		ri.Printf(PRINT_ALL, "usage: materiallab_reset_all confirm (saved profile file is NOT deleted)\n");
		return;
	}
	R_MaterialLabClearTable(qtrue);
	ri.Printf(PRINT_ALL, "MATERIAL_LAB: all in-memory overrides restored and cleared; saved file untouched\n");
}

void R_MaterialLabRegister(void)
{
	r_materialLab = ri.Cvar_Get("r_materialLab", "0", CVAR_ARCHIVE);
	r_materialLabAutoload = ri.Cvar_Get("r_materialLabAutoload", "1", CVAR_ARCHIVE);
	r_materialLabPick = ri.Cvar_Get("r_materialLabPick", "0", 0);
	r_materialLabRoughness = ri.Cvar_Get("r_materialLabRoughness", "0.55", 0);
	r_materialLabMetallic = ri.Cvar_Get("r_materialLabMetallic", "0.0", 0);
	r_materialLabSpecular = ri.Cvar_Get("r_materialLabSpecular", "0.04", 0);
	r_materialLabNormalScale = ri.Cvar_Get("r_materialLabNormalScale", "1.0", 0);
	r_materialLabParallaxScale = ri.Cvar_Get("r_materialLabParallaxScale", "1.0", 0);
	ri.Cvar_CheckRange(r_materialLabRoughness, 0.02f, 1.0f, qfalse);
	ri.Cvar_CheckRange(r_materialLabMetallic, 0.0f, 1.0f, qfalse);
	ri.Cvar_CheckRange(r_materialLabSpecular, 0.0f, 1.0f, qfalse);
	ri.Cvar_CheckRange(r_materialLabNormalScale, 0.0f, 4.0f, qfalse);
	ri.Cvar_CheckRange(r_materialLabParallaxScale, 0.0f, 4.0f, qfalse);
	ri.Cmd_AddCommand("materiallab_help", R_MaterialLabHelp_f);
	ri.Cmd_AddCommand("materiallab_pick", R_MaterialLabPick_f);
	ri.Cmd_AddCommand("materiallab_status", R_MaterialLabStatus_f);
	ri.Cmd_AddCommand("materiallab_apply", R_MaterialLabApply_f);
	ri.Cmd_AddCommand("materiallab_reset", R_MaterialLabReset_f);
	ri.Cmd_AddCommand("materiallab_save", R_MaterialLabSave_f);
	ri.Cmd_AddCommand("materiallab_load", R_MaterialLabLoad_f);
	ri.Cmd_AddCommand("materiallab_list", R_MaterialLabList_f);
	ri.Cmd_AddCommand("materiallab_reset_all", R_MaterialLabResetAll_f);
}

void R_MaterialLabShutdown(void)
{
	ri.Cmd_RemoveCommand("materiallab_help");
	ri.Cmd_RemoveCommand("materiallab_pick");
	ri.Cmd_RemoveCommand("materiallab_status");
	ri.Cmd_RemoveCommand("materiallab_apply");
	ri.Cmd_RemoveCommand("materiallab_reset");
	ri.Cmd_RemoveCommand("materiallab_save");
	ri.Cmd_RemoveCommand("materiallab_load");
	ri.Cmd_RemoveCommand("materiallab_list");
	ri.Cmd_RemoveCommand("materiallab_reset_all");
	Com_Memset(s_materialLabOverrides, 0, sizeof(s_materialLabOverrides));
	s_materialLabSelected = -1;
	s_materialLabWorld = NULL;
	s_materialLabMapName[0] = '\0';
	s_materialLabProfilePath[0] = '\0';
	s_materialLabRuntimeApplied = qfalse;
	s_materialLabProfileLoaded = qfalse;
}

'''

anchor = "static void R_DlightMaterialProbeDrawSurfs(drawSurf_t *drawSurfs, int numDrawSurfs)\n{"
main = replace_once(main, anchor, module + anchor, "tr_main material lab module insertion")

old_sort = "\tR_DlightMaterialSortHits(hits, hitCount);\n\treport[0] = '\\0';"
new_sort = r'''\tR_DlightMaterialSortHits(hits, hitCount);

\t// DARKWOLF_AI_MATERIAL_LAB_V0_1: use the shared exact center-ray hits.
\tif (r_materialLabPick && r_materialLabPick->integer)
\t{
\t\tint materialHit = -1;
\t\tfor (drawIndex = 0; drawIndex < hitCount; ++drawIndex)
\t\t{
\t\t\tif (R_MaterialLabShaderEligible(hits[drawIndex].shader))
\t\t\t{
\t\t\t\tmaterialHit = drawIndex;
\t\t\t\tbreak;
\t\t\t}
\t\t}
\t\tif (materialHit >= 0)
\t\t{
\t\t\tdlightMaterialRayHit_t *hit = &hits[materialHit];
\t\t\tR_MaterialLabSelectShader(hit->shader, hit->entityNum, hit->surfaceIndex,
\t\t\t\tR_DlightMaterialSurfaceTypeName(*hit->draw->surface), sqrt(hit->distanceSquared));
\t\t}
\t\telse
\t\t{
\t\t\tri.Printf(PRINT_ALL,
\t\t\t\t"MATERIAL_LAB: MISS - no supported editable BSP/MDV material on center ray; unsupportedModelDrawSurfs=%d\\n",
\t\t\t\tunsupportedModelDrawSurfs);
\t\t}
\t\tri.Cvar_Set("r_materialLabPick", "0");
\t\tif (!r_dlightMaterialProbe || !r_dlightMaterialProbe->integer)
\t\t\treturn;
\t}

\treport[0] = '\\0';'''
new_sort = new_sort.replace("\\t", "\t")
main = replace_once(main, old_sort, new_sort, "tr_main probe material selection hook")

old_hook = r'''\t// REND2_DLIGHT_MATERIAL_LOCK_DIAG_V8_6_5: one-shot exact center-ray material probe.
\tif (r_dlightMaterialProbe && r_dlightMaterialProbe->integer
\t\t&& !(tr.viewParms.flags & (VPF_SHADOWMAP | VPF_DEPTHSHADOW))
\t\t&& !tr.viewParms.isPortal && !(tr.refdef.rdflags & RDF_NOWORLDMODEL))
\t{
\t\tR_DlightMaterialProbeDrawSurfs(drawSurfs, numDrawSurfs);
\t}
'''
old_hook = old_hook.replace("\\t", "\t")
new_hook = r'''\t// DARKWOLF_AI_MATERIAL_LAB_V0_1: live update only from the main front-end view.
\tif (!(tr.viewParms.flags & (VPF_SHADOWMAP | VPF_DEPTHSHADOW))
\t\t&& !tr.viewParms.isPortal && !(tr.refdef.rdflags & RDF_NOWORLDMODEL))
\t{
\t\tR_MaterialLabFrontEndTick();
\t}

\t// Existing diagnostic and Material Lab share the exact center-ray geometry pass.
\tif (((r_dlightMaterialProbe && r_dlightMaterialProbe->integer) ||
\t\t (r_materialLabPick && r_materialLabPick->integer))
\t\t&& !(tr.viewParms.flags & (VPF_SHADOWMAP | VPF_DEPTHSHADOW))
\t\t&& !tr.viewParms.isPortal && !(tr.refdef.rdflags & RDF_NOWORLDMODEL))
\t{
\t\tR_DlightMaterialProbeDrawSurfs(drawSurfs, numDrawSurfs);
\t}
'''
new_hook = new_hook.replace("\\t", "\t")
main = replace_once(main, old_hook, new_hook, "tr_main sort hook")
write(main_rel, main)

old_decl = "extern void R_CropImages_f( void );\n\n/*\n===============\nR_Register"
new_decl = "extern void R_CropImages_f( void );\n\n// DARKWOLF_AI_MATERIAL_LAB_V0_1\nvoid R_MaterialLabRegister( void );\nvoid R_MaterialLabShutdown( void );\n\n/*\n===============\nR_Register"
init = replace_once(init, old_decl, new_decl, "tr_init forward declarations")

old_register = "\tr_highQualityVideo = ri.Cvar_Get( \"r_highQualityVideo\", \"1\", CVAR_ARCHIVE );\n\t// make sure all the commands added here are also"
new_register = "\tr_highQualityVideo = ri.Cvar_Get( \"r_highQualityVideo\", \"1\", CVAR_ARCHIVE );\n\n\t// DARKWOLF_AI_MATERIAL_LAB_V0_1\n\tR_MaterialLabRegister();\n\n\t// make sure all the commands added here are also"
init = replace_once(init, old_register, new_register, "tr_init registration call")

old_shutdown = "void RE_Shutdown( qboolean destroyWindow ) {\n\n\tri.Printf( PRINT_ALL, \"RE_Shutdown( %i )\\n\", destroyWindow );\n"
new_shutdown = "void RE_Shutdown( qboolean destroyWindow ) {\n\n\tri.Printf( PRINT_ALL, \"RE_Shutdown( %i )\\n\", destroyWindow );\n\n\t// DARKWOLF_AI_MATERIAL_LAB_V0_1\n\tR_MaterialLabShutdown();\n"
init = replace_once(init, old_shutdown, new_shutdown, "tr_init shutdown call")
write(init_rel, init)

print("DARKWOLF_AI_MATERIAL_LAB_V0_1_PATCH_OK" + ("_CHECK_ONLY" if CHECK_ONLY else ""))
