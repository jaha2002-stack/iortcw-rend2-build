/* DarkWolf Original Texture Restoration V1.
 * Runtime surface pick -> offline 4x restoration -> instant A/B -> PK3 persistence. */
typedef struct {
    qboolean selected;
    qboolean previewBuilt;
    qboolean showingB;
    int surfaceIndex;
    shader_t *shader;
    shaderStage_t *stage;
    image_t *original;
    image_t *preview;
    byte *pixels;
    int width, height;
} dwtrState_t;

static dwtrState_t s_dwtr;

static unsigned int DWTR_HashPath(const char *s)
{
    unsigned int h = 2166136261u;
    while (s && *s) {
        unsigned char c = (unsigned char)*s++;
        if (c == '\\') c = '/';
        if (c >= 'A' && c <= 'Z') c = (unsigned char)(c - 'A' + 'a');
        h ^= c; h *= 16777619u;
    }
    return h;
}

static unsigned int DWTR_CRC32(const byte *data, int len)
{
    unsigned int crc = 0xffffffffu;
    int i, b;
    for (i = 0; i < len; ++i) {
        crc ^= data[i];
        for (b = 0; b < 8; ++b)
            crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}

static void DWTR_Put16(byte *p, unsigned int v) { p[0]=(byte)v; p[1]=(byte)(v>>8); }
static void DWTR_Put32(byte *p, unsigned int v) { p[0]=(byte)v; p[1]=(byte)(v>>8); p[2]=(byte)(v>>16); p[3]=(byte)(v>>24); }

static qboolean DWTR_RayTriangle(const vec3_t o, const vec3_t d,
                                const vec3_t a, const vec3_t b, const vec3_t c,
                                float *outT)
{
    vec3_t e1,e2,p,q,tv; float det,inv,u,v,t;
    VectorSubtract(b,a,e1); VectorSubtract(c,a,e2);
    CrossProduct(d,e2,p); det=DotProduct(e1,p);
    if (fabs(det) < 0.000001f) return qfalse;
    inv=1.0f/det; VectorSubtract(o,a,tv); u=DotProduct(tv,p)*inv;
    if (u < 0.0f || u > 1.0f) return qfalse;
    CrossProduct(tv,e1,q); v=DotProduct(d,q)*inv;
    if (v < 0.0f || u+v > 1.0f) return qfalse;
    t=DotProduct(e2,q)*inv;
    if (t <= 0.5f || t > 8192.0f) return qfalse;
    *outT=t; return qtrue;
}

static qboolean DWTR_RaySurface(const msurface_t *ms, const vec3_t o, const vec3_t d, float *best)
{
    const srfBspSurface_t *s;
    int i;
    qboolean hit=qfalse;
    if (!ms || !ms->data) return qfalse;
    if (*ms->data != SF_FACE && *ms->data != SF_TRIANGLES && *ms->data != SF_GRID) return qfalse;
    s=(const srfBspSurface_t*)ms->data;
    if (!s->verts || s->numVerts < 3) return qfalse;
    if (s->indexes && s->numIndexes >= 3) {
        for (i=0;i+2<s->numIndexes;i+=3) {
            int ia=s->indexes[i],ib=s->indexes[i+1],ic=s->indexes[i+2]; float t;
            if (ia<0||ib<0||ic<0||ia>=s->numVerts||ib>=s->numVerts||ic>=s->numVerts) continue;
            if (DWTR_RayTriangle(o,d,s->verts[ia].xyz,s->verts[ib].xyz,s->verts[ic].xyz,&t) && t<*best) {
                *best=t; hit=qtrue;
            }
        }
    } else {
        for (i=1;i+1<s->numVerts;++i) {
            float t;
            if (DWTR_RayTriangle(o,d,s->verts[0].xyz,s->verts[i].xyz,s->verts[i+1].xyz,&t) && t<*best) {
                *best=t; hit=qtrue;
            }
        }
    }
    return hit;
}

static shaderStage_t *DWTR_DiffuseStage(shader_t *sh, image_t **out)
{
    int i;
    if (out) *out=NULL;
    if (!sh) return NULL;
    if (sh->remappedShader) sh=sh->remappedShader;
    if (sh->isSky) return NULL;
    for (i=0;i<sh->numUnfoggedPasses && i<MAX_SHADER_STAGES;++i) {
        shaderStage_t *st=sh->stages[i];
        image_t *im;
        if (!st || !st->active || st->bundle[TB_DIFFUSEMAP].isLightmap) continue;
        im=st->bundle[TB_DIFFUSEMAP].image[0];
        if (!im || !im->imgName[0] || im->imgName[0]=='*' || im==tr.whiteImage || im==tr.defaultImage) continue;
        if (out) *out=im;
        return st;
    }
    return NULL;
}

static void DWTR_Show(qboolean b)
{
    if (!s_dwtr.selected || !s_dwtr.stage || !s_dwtr.original) return;
    if (b && s_dwtr.previewBuilt && s_dwtr.preview) {
        s_dwtr.stage->bundle[TB_DIFFUSEMAP].image[0]=s_dwtr.preview;
        s_dwtr.showingB=qtrue;
    } else {
        s_dwtr.stage->bundle[TB_DIFFUSEMAP].image[0]=s_dwtr.original;
        s_dwtr.showingB=qfalse;
    }
}

void R_DWTextureRestoreReset(void)
{
    DWTR_Show(qfalse);
    if (s_dwtr.pixels) ri.Free(s_dwtr.pixels);
    Com_Memset(&s_dwtr,0,sizeof(s_dwtr));
}

void R_DWTexturePick_f(void)
{
    int i,bestIndex=-1; float best=8192.0f;
    shader_t *shader=NULL; shaderStage_t *stage=NULL; image_t *image=NULL;
    vec3_t o,d;
    R_IssuePendingRenderCommands();
    if (!tr.world || !tr.world->surfaces || tr.world->numWorldSurfaces<=0) {
        ri.Printf(PRINT_WARNING,"DWTR: no world loaded.\n"); return;
    }
    VectorCopy(tr.refdef.vieworg,o); VectorCopy(tr.refdef.viewaxis[0],d);
    for (i=0;i<tr.world->numWorldSurfaces;++i) {
        float t=best;
        if (DWTR_RaySurface(&tr.world->surfaces[i],o,d,&t) && t<best) {
            shader_t *candidate=tr.world->surfaces[i].shader;
            image_t *candidateImage=NULL;
            shaderStage_t *candidateStage=DWTR_DiffuseStage(candidate,&candidateImage);
            if (candidateStage && candidateImage) {
                best=t; bestIndex=i; shader=candidate; stage=candidateStage; image=candidateImage;
            }
        }
    }
    if (bestIndex<0) { ri.Printf(PRINT_WARNING,"DWTR: no restorable world texture under crosshair.\n"); return; }
    R_DWTextureRestoreReset();
    s_dwtr.selected=qtrue; s_dwtr.surfaceIndex=bestIndex; s_dwtr.shader=shader;
    s_dwtr.stage=stage; s_dwtr.original=image;
    ri.Printf(PRINT_ALL,"DWTR: selected surface=%d shader=%s texture=%s source=%dx%d distance=%.1f\n",
              bestIndex,shader?shader->name:"?",image->imgName,image->width,image->height,best);
    ri.Printf(PRINT_ALL,"DWTR: use /dw_tex_restore, then /dw_tex_ab; /dw_tex_save persists B in an automatic PK3.\n");
}

void R_DWTextureRestore_f(void)
{
    if (!s_dwtr.selected || !s_dwtr.original) {
        ri.Printf(PRINT_WARNING,"DWTR: select a texture first with /dw_tex_pick.\n"); return;
    }
    R_IssuePendingRenderCommands();
    if (s_dwtr.previewBuilt) { DWTR_Show(qtrue); ri.Printf(PRINT_ALL,"DWTR: B restored preview active.\n"); return; }
    if (!R_DWTextureRestoreBuild(s_dwtr.original,&s_dwtr.preview,&s_dwtr.pixels,&s_dwtr.width,&s_dwtr.height)) {
        ri.Printf(PRINT_WARNING,"DWTR: 4x restore failed for %s.\n",s_dwtr.original->imgName); return;
    }
    s_dwtr.previewBuilt=qtrue; DWTR_Show(qtrue);
    ri.Printf(PRINT_ALL,"DWTR: B active %s -> %dx%d (4x, offline hybrid restoration).\n",
              s_dwtr.original->imgName,s_dwtr.width,s_dwtr.height);
}

void R_DWTextureAB_f(void)
{
    if (!s_dwtr.previewBuilt) { ri.Printf(PRINT_WARNING,"DWTR: build B first with /dw_tex_restore.\n"); return; }
    R_IssuePendingRenderCommands();
    DWTR_Show(s_dwtr.showingB?qfalse:qtrue);
    ri.Printf(PRINT_ALL,"DWTR: %s active for %s.\n",s_dwtr.showingB?"B RESTORED 4X":"A ORIGINAL",s_dwtr.original->imgName);
}

static byte *DWTR_EncodeTGA(const byte *rgba,int w,int h,int *outLen)
{
    int x,y; byte *buf,*p;
    *outLen=18+w*h*4; buf=(byte*)ri.Z_Malloc(*outLen); Com_Memset(buf,0,18);
    buf[2]=2; buf[12]=(byte)w; buf[13]=(byte)(w>>8); buf[14]=(byte)h; buf[15]=(byte)(h>>8); buf[16]=32; buf[17]=8;
    p=buf+18;
    for(y=h-1;y>=0;--y) for(x=0;x<w;++x) {
        const byte *s=rgba+(y*w+x)*4; *p++=s[2];*p++=s[1];*p++=s[0];*p++=s[3];
    }
    return buf;
}

static byte *DWTR_EncodeJPG(const byte *rgba,int w,int h,int *outLen)
{
    byte *rgb,*jpg; int i; size_t cap,got;
    rgb=(byte*)ri.Z_Malloc(w*h*3);
    for(i=0;i<w*h;++i){rgb[i*3]=rgba[i*4];rgb[i*3+1]=rgba[i*4+1];rgb[i*3+2]=rgba[i*4+2];}
    cap=(size_t)w*h*3; jpg=(byte*)ri.Z_Malloc((int)cap);
    got=RE_SaveJPGToBuffer(jpg,cap,96,w,h,rgb,0); ri.Free(rgb);
    if(!got){ri.Free(jpg);return NULL;} *outLen=(int)got; return jpg;
}

static qboolean DWTR_MakePK3(const char *internal,const byte *fileData,int fileLen,char *outName,int outNameSize)
{
    int nameLen=(int)strlen(internal),localSize,centralSize,total,off; byte *z,*p; unsigned int crc,hash;
    if(nameLen<=0||nameLen>MAX_QPATH||fileLen<=0)return qfalse;
    hash=DWTR_HashPath(internal); crc=DWTR_CRC32(fileData,fileLen);
    Com_sprintf(outName,outNameSize,"zz_dwtr_%08x.pk3",hash);
    localSize=30+nameLen+fileLen; centralSize=46+nameLen; total=localSize+centralSize+22;
    z=(byte*)ri.Z_Malloc(total);p=z;
    DWTR_Put32(p,0x04034b50);DWTR_Put16(p+4,20);DWTR_Put16(p+6,0);DWTR_Put16(p+8,0);
    DWTR_Put16(p+10,0);DWTR_Put16(p+12,0);DWTR_Put32(p+14,crc);DWTR_Put32(p+18,fileLen);DWTR_Put32(p+22,fileLen);
    DWTR_Put16(p+26,nameLen);DWTR_Put16(p+28,0);Com_Memcpy(p+30,internal,nameLen);Com_Memcpy(p+30+nameLen,fileData,fileLen);
    off=localSize;p=z+off;
    DWTR_Put32(p,0x02014b50);DWTR_Put16(p+4,20);DWTR_Put16(p+6,20);DWTR_Put16(p+8,0);DWTR_Put16(p+10,0);
    DWTR_Put16(p+12,0);DWTR_Put16(p+14,0);DWTR_Put32(p+16,crc);DWTR_Put32(p+20,fileLen);DWTR_Put32(p+24,fileLen);
    DWTR_Put16(p+28,nameLen);DWTR_Put16(p+30,0);DWTR_Put16(p+32,0);DWTR_Put16(p+34,0);DWTR_Put16(p+36,0);
    DWTR_Put32(p+38,0);DWTR_Put32(p+42,0);Com_Memcpy(p+46,internal,nameLen);
    p=z+localSize+centralSize;DWTR_Put32(p,0x06054b50);DWTR_Put16(p+4,0);DWTR_Put16(p+6,0);
    DWTR_Put16(p+8,1);DWTR_Put16(p+10,1);DWTR_Put32(p+12,centralSize);DWTR_Put32(p+16,localSize);DWTR_Put16(p+20,0);
    ri.FS_WriteFile(outName,z,total);ri.Free(z);return qtrue;
}

void R_DWTextureSave_f(void)
{
    char internal[MAX_QPATH],pk3[MAX_QPATH],manifest[MAX_QPATH+96],text[1024];
    const char *ext; byte *encoded=NULL; int encodedLen=0; unsigned int hash;
    if (!s_dwtr.previewBuilt || !s_dwtr.pixels || !s_dwtr.original) {
        ri.Printf(PRINT_WARNING,"DWTR: nothing restored to save.\n"); return;
    }
    Q_strncpyz(internal,s_dwtr.original->imgName,sizeof(internal));
    ext=strrchr(internal,'.');
    if (!ext) {
        if ((int)strlen(internal)+4>=MAX_QPATH) {ri.Printf(PRINT_WARNING,"DWTR: path too long.\n");return;}
        Q_strcat(internal,sizeof(internal),".tga"); ext=".tga";
    }
    if (!Q_stricmp(ext,".tga")) encoded=DWTR_EncodeTGA(s_dwtr.pixels,s_dwtr.width,s_dwtr.height,&encodedLen);
    else if (!Q_stricmp(ext,".jpg") || !Q_stricmp(ext,".jpeg")) encoded=DWTR_EncodeJPG(s_dwtr.pixels,s_dwtr.width,s_dwtr.height,&encodedLen);
    else {
        ri.Printf(PRINT_WARNING,"DWTR: persistent V1 supports TGA/JPG sources; %s preview remains available but was not saved.\n",ext);
        return;
    }
    if (!encoded || encodedLen<=0) {ri.Printf(PRINT_WARNING,"DWTR: encoder failed.\n");return;}
    if (!DWTR_MakePK3(internal,encoded,encodedLen,pk3,sizeof(pk3))) {ri.Free(encoded);ri.Printf(PRINT_WARNING,"DWTR: PK3 creation failed.\n");return;}
    ri.Free(encoded);
    hash=DWTR_HashPath(internal);
    Com_sprintf(manifest,sizeof(manifest),"texture_restoration/dwtr_%08x.txt",hash);
    Com_sprintf(text,sizeof(text),
      "DarkWolf Original Texture Restoration V1\nsource %s\nreplacement %s\nsize %d %d\nscale 4x\nmode offline_hybrid_fidelity\npk3 %s\nrestart persistent yes\n",
      s_dwtr.original->imgName,internal,s_dwtr.width,s_dwtr.height,pk3);
    ri.FS_WriteFile(manifest,text,(int)strlen(text));
    DWTR_Show(qtrue);
    ri.Printf(PRINT_ALL,"DWTR: SAVED %s containing %s. It will override the original after game restart.\n",pk3,internal);
    ri.Printf(PRINT_ALL,"DWTR: manifest %s. No internet or telemetry used.\n",manifest);
}

void R_DWTextureDiscard_f(void)
{
    R_DWTextureRestoreReset();
    ri.Printf(PRINT_ALL,"DWTR: preview discarded; original texture restored.\n");
}

void R_DWTextureInfo_f(void)
{
    if(!s_dwtr.selected){ri.Printf(PRINT_ALL,"DWTR: nothing selected. /dw_tex_pick\n");return;}
    ri.Printf(PRINT_ALL,"DWTR: surface=%d shader=%s texture=%s A=%dx%d B=%s showing=%s\n",
      s_dwtr.surfaceIndex,s_dwtr.shader?s_dwtr.shader->name:"?",s_dwtr.original?s_dwtr.original->imgName:"?",
      s_dwtr.original?s_dwtr.original->width:0,s_dwtr.original?s_dwtr.original->height:0,
      s_dwtr.previewBuilt?va("%dx%d",s_dwtr.width,s_dwtr.height):"not built",s_dwtr.showingB?"B":"A");
}

void R_DWTextureArtistic_f(void)
{
    ri.Printf(PRINT_ALL,"DWTR ARTISTIC: optional backend intentionally not enabled in V1. Original Restoration stays fully offline and authenticity-locked.\n");
}
