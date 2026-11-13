#!/usr/bin/env python3
from pathlib import Path
import sys

src=Path(sys.argv[1] if len(sys.argv)>1 else "source")
cg=src/"SP"/"code"/"cgame"/"cg_ents.c"
if not cg.exists():
    raise SystemExit("missing cg_ents.c")
c=cg.read_text()


# Cache whether each state uses our compact custom model or a large stock fallback.
old_decl="static qboolean s_dwDlv14SwitchModelTried[3][2];\n"
new_decl="static qboolean s_dwDlv14SwitchModelTried[3][2];\nstatic qboolean s_dwDlv16SwitchUsesCustom[3][2];\n"
if old_decl not in c:
    raise SystemExit("V1.6 custom-cache declaration anchor missing")
c=c.replace(old_decl,new_decl,1)

old=r'''static qhandle_t CG_DLV14_GetSwitchModel(int type, int on)
{
    int ti, si;
    const char *path;
    if (type < 1 || type > 3) type = 1;
    ti = type - 1;
    si = on ? 1 : 0;
    if (!s_dwDlv14SwitchModelTried[ti][si]) {
        s_dwDlv14SwitchModelTried[ti][si] = qtrue;
        path = CG_DLV14_SwitchModelPath(type,on);
        s_dwDlv14SwitchModel[ti][si] = trap_R_RegisterModel(path);
        CG_Printf("DW_DLV14 SWITCH_MODEL path=%s handle=%d\n",
            path,(int)s_dwDlv14SwitchModel[ti][si]);
    }
    return s_dwDlv14SwitchModel[ti][si];
}

static qhandle_t CG_DLV14_GetLampOffShader(void)
{
    if (!s_dwDlv14LampOffShaderTried) {
        s_dwDlv14LampOffShaderTried = qtrue;
        s_dwDlv14LampOffShader = trap_R_RegisterShader("darkwolf/dlv14_lamp_off");
        CG_Printf("DW_DLV14 LAMP_OFF_SHADER handle=%d\n",(int)s_dwDlv14LampOffShader);
    }
    return s_dwDlv14LampOffShader;
}
'''

new=r'''static int CG_DLV16_VfsBytes(const char *path)
{
    fileHandle_t f = 0;
    int len;
    if (!path || !path[0]) return -1;
    len = trap_FS_FOpenFile(path,&f,FS_READ);
    if (f) trap_FS_FCloseFile(f);
    return len;
}

static const char *CG_DLV16_StockSwitchFallback(int type)
{
    switch (type) {
    default:
    case 1: return "models/mapobjects/electronics/alarmbox.md3";
    case 2: return "models/mapobjects/electronics/phone.md3";
    case 3: return "models/mapobjects/electronics/loudspeaker2.md3";
    }
}

static qhandle_t CG_DLV14_GetSwitchModel(int type, int on)
{
    int ti, si, bytes;
    const char *path;
    if (type < 1 || type > 3) type = 1;
    ti = type - 1;
    si = on ? 1 : 0;
    if (!s_dwDlv14SwitchModelTried[ti][si]) {
        const char *fallback;
        qhandle_t h;
        s_dwDlv14SwitchModelTried[ti][si] = qtrue;
        path = CG_DLV14_SwitchModelPath(type,on);
        bytes = CG_DLV16_VfsBytes(path);
        h = trap_R_RegisterModel(path);
        s_dwDlv16SwitchUsesCustom[ti][si] = h ? qtrue : qfalse;
        CG_Printf("DW_DLV16 SWITCH_ASSET path=%s vfsBytes=%d handle=%d\n",
            path,bytes,(int)h);

        if (!h) {
            fallback = CG_DLV16_StockSwitchFallback(type);
            h = trap_R_RegisterModel(fallback);
            s_dwDlv16SwitchUsesCustom[ti][si] = qfalse;
            CG_Printf("DW_DLV16 SWITCH_STOCK_FALLBACK path=%s handle=%d\n",
                fallback,(int)h);
        }
        s_dwDlv14SwitchModel[ti][si] = h;
    }
    return s_dwDlv14SwitchModel[ti][si];
}

static qhandle_t CG_DLV14_GetLampOffShader(void)
{
    if (!s_dwDlv14LampOffShaderTried) {
        int bytes;
        s_dwDlv14LampOffShaderTried = qtrue;
        bytes = CG_DLV16_VfsBytes("gfx/darkwolf/dlv14_lamp_off.tga");

        s_dwDlv14LampOffShader = trap_R_RegisterShader("darkwolf/dlv14_lamp_off");
        if (!s_dwDlv14LampOffShader) {
            s_dwDlv14LampOffShader =
                trap_R_RegisterShaderNoMip("gfx/darkwolf/dlv14_lamp_off.tga");
        }

        CG_Printf("DW_DLV16 LAMP_OFF_ASSET vfsBytes=%d handle=%d\n",
            bytes,(int)s_dwDlv14LampOffShader);
    }
    return s_dwDlv14LampOffShader;
}
'''
if old not in c:
    raise SystemExit("V1.6 switch/lamp loader anchor missing")
c=c.replace(old,new,1)

old=r'''            ent.radius = (s1->effect1Time == 3) ? 9.0f :
                         (s1->effect1Time == 2) ? 8.0f : 7.0f;
            ent.customShader = sh ? sh : cgs.media.smokePuffShader;
            ent.shaderRGBA[0]=255;
            ent.shaderRGBA[1]=255;
            ent.shaderRGBA[2]=255;
            ent.shaderRGBA[3]=255;
'''
new=r'''            ent.radius = (s1->effect1Time == 3) ? 12.0f :
                         (s1->effect1Time == 2) ? 10.0f : 10.0f;
            /*
             * Preferred path is the loose/PK3 dark circular TGA.  If that
             * somehow fails too, use a dark-tinted stock smoke shader rather
             * than a white/emissive fallback.
             */
            ent.customShader = sh ? sh : cgs.media.smokePuffShader;
            if (sh) {
                ent.shaderRGBA[0]=255;
                ent.shaderRGBA[1]=255;
                ent.shaderRGBA[2]=255;
                ent.shaderRGBA[3]=255;
            } else {
                ent.shaderRGBA[0]=22;
                ent.shaderRGBA[1]=20;
                ent.shaderRGBA[2]=18;
                ent.shaderRGBA[3]=240;
            }
'''
if old not in c:
    raise SystemExit("V1.6 lamp mask render anchor missing")
c=c.replace(old,new,1)

# If the custom model still cannot load, stock models are much larger than our
# hand-authored switches, so use a smaller scale for stock handles. We identify
# this by VFS availability: custom model bytes > 0 means custom; <=0 means stock.
old=r'''        if (h) {
            ent.reType=RT_MODEL;
            ent.hModel=h;
            AnglesToAxis(cent->lerpAngles,ent.axis);
            /* Slight readability scale; no change to server collision. */
            VectorScale(ent.axis[0],1.15f,ent.axis[0]);
            VectorScale(ent.axis[1],1.15f,ent.axis[1]);
            VectorScale(ent.axis[2],1.15f,ent.axis[2]);
            ent.nonNormalizedAxes=qtrue;
            trap_R_AddRefEntityToScene(&ent);
'''
new=r'''        if (h) {
            float visualScale;
            int ti = s1->effect1Time;
            int si = s1->effect2Time ? 1 : 0;
            if (ti < 1 || ti > 3) ti = 1;
            visualScale = s_dwDlv16SwitchUsesCustom[ti-1][si] ? 1.15f : 0.34f;

            ent.reType=RT_MODEL;
            ent.hModel=h;
            AnglesToAxis(cent->lerpAngles,ent.axis);
            VectorScale(ent.axis[0],visualScale,ent.axis[0]);
            VectorScale(ent.axis[1],visualScale,ent.axis[1]);
            VectorScale(ent.axis[2],visualScale,ent.axis[2]);
            ent.nonNormalizedAxes=qtrue;
            trap_R_AddRefEntityToScene(&ent);
'''
if old not in c:
    raise SystemExit("V1.6 switch render scale anchor missing")
c=c.replace(old,new,1)

cg.write_text(c)
print("DW_DESTRUCTIBLE_LIGHTS_V16_ASSET_VFS_APPLY_PASS")
