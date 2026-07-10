#!/usr/bin/env python3
# Kit E v2: separate RGBA linear-distance cubemap shadows.
# This patch runs after Kit D v1.2 and redirects dynamic-light shadow sampling to
# tr.dlightDistanceCubemaps instead of tr.shadowCubemaps.

from pathlib import Path
import re
import shutil

SETS = [
    {
        "name": "SP",
        "tr_init": Path("SP/code/rend2/tr_init.c"),
        "tr_local": Path("SP/code/rend2/tr_local.h"),
        "tr_image": Path("SP/code/rend2/tr_image.c"),
        "tr_backend": Path("SP/code/rend2/tr_backend.c"),
        "tr_shade": Path("SP/code/rend2/tr_shade.c"),
        "dlight_fp": Path("SP/code/rend2/glsl/dlight_fp.glsl"),
        "shadowfill_fp": Path("SP/code/rend2/glsl/shadowfill_fp.glsl"),
    },
    {
        "name": "MP",
        "tr_init": Path("MP/code/rend2/tr_init.c"),
        "tr_local": Path("MP/code/rend2/tr_local.h"),
        "tr_image": Path("MP/code/rend2/tr_image.c"),
        "tr_backend": Path("MP/code/rend2/tr_backend.c"),
        "tr_shade": Path("MP/code/rend2/tr_shade.c"),
        "dlight_fp": Path("MP/code/rend2/glsl/dlight_fp.glsl"),
        "shadowfill_fp": Path("MP/code/rend2/glsl/shadowfill_fp.glsl"),
    },
]

ASSET_DIR = Path("kit_e_v2_assets")

CVAR_NAMES = [
    "r_dlightDistanceMapSize",
    "r_dlightDistanceColorTest",
    "r_dlightDistanceSkipGeometry",
    "r_dlightDistanceDebug",
    "r_dlightDistanceBias",
    "r_dlightDistanceStrength",
]

REGISTER_LINES = [
    'r_dlightDistanceMapSize = ri.Cvar_Get( "r_dlightDistanceMapSize", "256", CVAR_ARCHIVE | CVAR_LATCH );',
    'r_dlightDistanceColorTest = ri.Cvar_Get( "r_dlightDistanceColorTest", "0", CVAR_ARCHIVE | CVAR_LATCH );',
    'r_dlightDistanceSkipGeometry = ri.Cvar_Get( "r_dlightDistanceSkipGeometry", "0", CVAR_ARCHIVE | CVAR_LATCH );',
    'r_dlightDistanceDebug = ri.Cvar_Get( "r_dlightDistanceDebug", "1", CVAR_ARCHIVE );',
    'r_dlightDistanceBias = ri.Cvar_Get( "r_dlightDistanceBias", "0.020", CVAR_ARCHIVE | CVAR_LATCH );',
    'r_dlightDistanceStrength = ri.Cvar_Get( "r_dlightDistanceStrength", "0.90", CVAR_ARCHIVE | CVAR_LATCH );',
]

def read(path):
    return path.read_text(encoding="utf-8", errors="replace")

def save(path, text):
    path.write_text(text, encoding="utf-8")

def ensure_cvars(init_path, local_path):
    local = read(local_path)

    for name in CVAR_NAMES:
        local = re.sub(
            rf"(?m)^\s*(?:extern\s+)?cvar_t\s*\*\s*{re.escape(name)}\s*;\s*$",
            f"extern cvar_t *{name};",
            local,
        )

    missing = [name for name in CVAR_NAMES if f"extern cvar_t *{name};" not in local]
    if missing:
        block = "\n".join([f"extern cvar_t *{name};" for name in missing]) + "\n"
        if "extern cvar_t *r_dlightMode;" in local:
            local = local.replace("extern cvar_t *r_dlightMode;", "extern cvar_t *r_dlightMode;\n" + block, 1)
        else:
            local += "\n" + block

    save(local_path, local)

    init = read(init_path)
    for name in CVAR_NAMES:
        init = re.sub(rf"(?m)^\s*(?:extern\s+)?cvar_t\s*\*\s*{re.escape(name)}\s*;\s*$", "", init)

    defs = "\n".join([f"cvar_t *{name};" for name in CVAR_NAMES]) + "\n"
    if "cvar_t *r_dlightDistanceMapSize;" not in init:
        if "cvar_t *r_dlightMode;" in init:
            init = init.replace("cvar_t *r_dlightMode;", "cvar_t *r_dlightMode;\n" + defs, 1)
        else:
            init = defs + "\n" + init

    if 'ri.Cvar_Get( "r_dlightDistanceMapSize"' not in init:
        register = "\n\t" + "\n\t".join(REGISTER_LINES)
        marker = 'r_dlightMode = ri.Cvar_Get( "r_dlightMode", "0", CVAR_ARCHIVE | CVAR_LATCH );'
        if marker in init:
            init = init.replace(marker, marker + register, 1)
        else:
            m = re.search(r'r_dlightMode\s*=\s*ri\.Cvar_Get\s*\([^;]+;', init)
            if not m:
                raise SystemExit(f"Could not find r_dlightMode registration in {init_path}")
            init = init[:m.end()] + register + init[m.end():]

    save(init_path, init)
    print(f"patched cvars: {init_path}, {local_path}")

def patch_trglobals(local_path):
    s = read(local_path)
    if "dlightDistanceCubemaps" not in s:
        old = "image_t *shadowCubemaps[MAX_DLIGHTS];"
        new = old + " image_t *dlightDistanceCubemaps[MAX_DLIGHTS]; image_t *dlightDistanceDepthImage;"
        if old not in s:
            raise SystemExit(f"Could not find shadowCubemaps field in {local_path}")
        s = s.replace(old, new, 1)
    save(local_path, s)
    print(f"patched trGlobals fields: {local_path}")

def patch_image_alloc(image_path):
    s = read(image_path)

    if "dlightdistancecubemap" not in s:
        pattern = r'(tr\.shadowCubemaps\[x\]\s*=\s*R_CreateImage\s*\(\s*va\s*\(\s*"\*shadowcubemap%i"\s*,\s*x\s*\)\s*,\s*NULL\s*,\s*PSHADOW_MAP_SIZE\s*,\s*PSHADOW_MAP_SIZE\s*,\s*IMGTYPE_COLORALPHA\s*,\s*IMGFLAG_CLAMPTOEDGE\s*\|\s*IMGFLAG_CUBEMAP\s*,\s*0\s*\)\s*;)'
        replacement = (
            r'\1\n'
            '            tr.dlightDistanceCubemaps[x] = R_CreateImage(va("*dlightdistancecubemap%i", x), NULL,\n'
            '                r_dlightDistanceMapSize ? r_dlightDistanceMapSize->integer : 256,\n'
            '                r_dlightDistanceMapSize ? r_dlightDistanceMapSize->integer : 256,\n'
            '                IMGTYPE_COLORALPHA,\n'
            '                IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE | IMGFLAG_CUBEMAP,\n'
            '                GL_RGBA8);'
        )
        s, n = re.subn(pattern, replacement, s, count=1)
        if n == 0:
            raise SystemExit(f"Could not patch dlight distance cubemap allocation in {image_path}")

    if "dlightDistanceDepth" not in s:
        insert = (
            '\n    tr.dlightDistanceDepthImage = R_CreateImage("*dlightDistanceDepth", NULL,\n'
            '        r_dlightDistanceMapSize ? r_dlightDistanceMapSize->integer : 256,\n'
            '        r_dlightDistanceMapSize ? r_dlightDistanceMapSize->integer : 256,\n'
            '        IMGTYPE_COLORALPHA,\n'
            '        IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE,\n'
            '        GL_DEPTH_COMPONENT24);\n'
        )
        marker = "// with overbright bits active"
        if marker in s:
            s = s.replace(marker, insert + "\n" + marker, 1)
        else:
            s = s.replace("tr.renderDepthImage = R_CreateImage", insert + "\n tr.renderDepthImage = R_CreateImage", 1)

    save(image_path, s)
    print(f"patched image allocation: {image_path}")

def patch_backend(backend_path):
    s = read(backend_path)

    s = s.replace("tr.shadowCubemaps[lightIndex]", "tr.dlightDistanceCubemaps[lightIndex]")

    s = s.replace(
        "FBO_AttachImage( tr.renderCubeFbo, tr.dlightDistanceCubemaps[lightIndex], GL_DEPTH_ATTACHMENT_EXT, face );",
        "FBO_AttachImage( tr.renderCubeFbo, tr.dlightDistanceCubemaps[lightIndex], GL_COLOR_ATTACHMENT0_EXT, face );\n"
        "            if ( tr.dlightDistanceDepthImage )\n"
        "            {\n"
        "                FBO_AttachImage( tr.renderCubeFbo, tr.dlightDistanceDepthImage, GL_DEPTH_ATTACHMENT_EXT, 0 );\n"
        "            }\n"
        "            qglDrawBuffer( GL_COLOR_ATTACHMENT0_EXT );\n"
        "            qglReadBuffer( GL_COLOR_ATTACHMENT0_EXT );"
    )

    s = s.replace("qglColorMask( GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE );", "qglColorMask( GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE );")

    if "Kit E v2 face-color clear" not in s:
        s = s.replace(
            "qglClear( GL_DEPTH_BUFFER_BIT );",
            "/* Kit E v2 face-color clear: visible in r_dlightDistanceColorTest mode. */\n"
            "            switch ( face )\n"
            "            {\n"
            "                case 0: qglClearColor( 1.0f, 0.0f, 0.0f, 1.0f ); break;\n"
            "                case 1: qglClearColor( 0.0f, 1.0f, 0.0f, 1.0f ); break;\n"
            "                case 2: qglClearColor( 0.0f, 0.0f, 1.0f, 1.0f ); break;\n"
            "                case 3: qglClearColor( 1.0f, 1.0f, 0.0f, 1.0f ); break;\n"
            "                case 4: qglClearColor( 0.0f, 1.0f, 1.0f, 1.0f ); break;\n"
            "                default: qglClearColor( 1.0f, 0.0f, 1.0f, 1.0f ); break;\n"
            "            }\n"
            "            qglClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT );",
            1,
        )

    if "r_dlightDistanceSkipGeometry" not in s:
        s = s.replace(
            "RB_RenderDrawSurfList( drawSurfs, numDrawSurfs );",
            "if ( !r_dlightDistanceSkipGeometry || !r_dlightDistanceSkipGeometry->integer )\n"
            "            {\n"
            "                RB_RenderDrawSurfList( drawSurfs, numDrawSurfs );\n"
            "            }",
            1,
        )

    s = s.replace("CUBEDDBG", "LINEARCUBEDBG")
    s = s.replace("CUBEVIEWDBG", "LINEARCUBEDBG")

    save(backend_path, s)
    print(f"patched backend separate RGBA cubemap pass: {backend_path}")

def patch_shade(shade_path):
    s = read(shade_path)

    s = s.replace("tr.shadowCubemaps[l]", "tr.dlightDistanceCubemaps[l]")
    s = s.replace("hasCube", "hasDistanceCube")
    s = s.replace("DLIGHTSHADERDBG", "DLIGHTDISTDBG")

    s = s.replace(
        "vector[2] = r_dlightShadowShaderStrength ? r_dlightShadowShaderStrength->value : 0.85f;",
        "vector[2] = r_dlightDistanceStrength ? r_dlightDistanceStrength->value : (r_dlightShadowShaderStrength ? r_dlightShadowShaderStrength->value : 0.85f);",
    )
    s = s.replace(
        "GLSL_SetUniformFloat(sp, UNIFORM_DLIGHTSHADOWBIAS, r_dlightShadowShaderBias ? r_dlightShadowShaderBias->value : 0.010f);",
        "GLSL_SetUniformFloat(sp, UNIFORM_DLIGHTSHADOWBIAS, r_dlightDistanceBias ? r_dlightDistanceBias->value : (r_dlightShadowShaderBias ? r_dlightShadowShaderBias->value : 0.010f));",
    )

    save(shade_path, s)
    print(f"patched shade separate RGBA cubemap binding: {shade_path}")

def patch_shaders(dlight_fp_path, shadowfill_fp_path):
    shutil.copyfile(ASSET_DIR / "dlight_fp.glsl", dlight_fp_path)
    shutil.copyfile(ASSET_DIR / "shadowfill_fp.glsl", shadowfill_fp_path)
    print(f"replaced dlight/shadowfill shaders: {dlight_fp_path}, {shadowfill_fp_path}")

for item in SETS:
    ensure_cvars(item["tr_init"], item["tr_local"])
    patch_trglobals(item["tr_local"])
    patch_image_alloc(item["tr_image"])
    patch_backend(item["tr_backend"])
    patch_shade(item["tr_shade"])
    patch_shaders(item["dlight_fp"], item["shadowfill_fp"])

print("Kit E v2 separate RGBA distance cubemap patch completed.")
