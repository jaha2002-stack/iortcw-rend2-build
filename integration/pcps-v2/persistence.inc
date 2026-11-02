/* DARKWOLF_PCPS_PERSISTENCE_V2_20261102
 * Human-readable, per-BSP, versioned rule files in writable FS homepath.
 * A/B journal keeps the last complete file when an I/O write is interrupted.
 * Files contain light identity (NOT transient dlight index) and exact BSP
 * surface signatures. Never execute these files as console scripts.
 * All filesystem access is through renderer imports, from the main thread.
 * Renderer backend only consumes validated, map-local in-memory rules.
 */
#define DWPS_PERSIST_MAX_BYTES (256*1024)
#define DWPS_PERSIST_MAX_LINE 384
static unsigned int dwpsPersistMapHash=0;
static int dwpsPersistGeneration=0,dwpsPersistSlot=-1;
static dwpsRule_t dwpsPersistScratch[DWPS_MAX_RULES];
static dwpsRule_t dwpsPersistBest[DWPS_MAX_RULES];
static char dwpsPersistBuffer[DWPS_PERSIST_MAX_BYTES];

static unsigned int DWPS_FnvUpdate(unsigned int h,const void *data,size_t n)
{
    const unsigned char *b=(const unsigned char*)data;
    size_t i;
    for(i=0;i<n;i++){h^=b[i];h*=16777619u;}
    return h;
}
static unsigned int DWPS_Fnv(const void *data,size_t n)
{
    return DWPS_FnvUpdate(2166136261u,data,n);
}
static unsigned int DWPS_MapHash(void)
{
    unsigned int hash=2166136261u;
    int i;
    const world_t *w=tr.world;
    if(!w || !w->surfaces || w->numWorldSurfaces<1 ||
       w->numWorldSurfaces>w->numsurfaces || w->numWorldSurfaces>200000)
        return 0;
    hash=DWPS_FnvUpdate(hash,w->name,strlen(w->name));
    hash=DWPS_FnvUpdate(hash,&w->dataSize,sizeof(w->dataSize));
    hash=DWPS_FnvUpdate(hash,&w->numWorldSurfaces,sizeof(w->numWorldSurfaces));
    hash=DWPS_FnvUpdate(hash,&w->numsurfaces,sizeof(w->numsurfaces));
    for(i=0;i<w->numWorldSurfaces;i++)
    {
        const msurface_t *s=&w->surfaces[i];
        int type=s->data?(int)(*s->data):-1;
        hash=DWPS_FnvUpdate(hash,&type,sizeof(type));
        hash=DWPS_FnvUpdate(hash,&s->cullinfo.type,sizeof(s->cullinfo.type));
        if(s->shader)
            hash=DWPS_FnvUpdate(hash,s->shader->name,strlen(s->shader->name));
        else
            hash=DWPS_FnvUpdate(hash,"-",1);
        if(s->cullinfo.type&CULLINFO_BOX)
            hash=DWPS_FnvUpdate(hash,s->cullinfo.bounds,sizeof(s->cullinfo.bounds));
    }
    return hash?hash:1u;
}
static void DWPS_FilePath(int slot,char *out,int n)
{
    char name[MAX_QPATH];
    int i;
    if(!tr.world){if(n>0)out[0]=0;return;}
    Q_strncpyz(name,tr.world->baseName,sizeof(name));
    for(i=0;name[i];i++)
    {
        unsigned char c=(unsigned char)name[i];
        if(c>='A' && c<='Z')name[i]=(char)(c+('a'-'A'));
        else if(!((c>='a'&&c<='z') ||(c>='0'&&c<='9') ||
                  c=='_'||c=='-'))name[i]='_';
    }
    if(!name[0])Q_strncpyz(name,"unnamed",sizeof(name));
    snprintf(out,(size_t)n,"dw_pcps_%s_%c.dat",name,slot==0?'a':'b');
}
static qboolean DWPS_ValidFinite(float x)
{
    return (x==x && x>-100000000.0f && x<100000000.0f)?qtrue:qfalse;
}
static qboolean DWPS_ValidMaterialToken(const char *s)
{
    int i;
    if(!s || !s[0] || strlen(s)>=MAX_QPATH)return qfalse;
    for(i=0;s[i];i++)
    {
        unsigned char c=(unsigned char)s[i];
        if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||
             (c>='0'&&c<='9')||c=='/'||c=='_'||c=='-'||c=='.'))
            return qfalse;
    }
    return qtrue;
}
static qboolean DWPS_FileReadLine(const char **cursor,char *out,int cap)
{
    const char *s=*cursor,*e;
    size_t n;
    if(!s || !*s)return qfalse;
    e=strchr(s,'\n');
    if(!e)return qfalse;
    n=(size_t)(e-s);
    if(n && s[n-1]=='\r')n--;
    if(n>=(size_t)cap)return qfalse;
    memcpy(out,s,n);
    out[n]=0;
    *cursor=e+1;
    return qtrue;
}
/* Read and verify a complete journal slot without changing active PCPS rules.
 * 0 => missing/invalid; 1 => entire file valid and scratch contains rules.
 */
static int DWPS_ReadSlot(int slot,int *generation,int *numRules)
{
    char path[128],line[DWPS_PERSIST_MAX_LINE],mapName[MAX_QPATH];
    char *sumBegin;
    const char *cursor;
    void *fileData=NULL;
    long size;
    unsigned int gotHash=0,storedSum=0,gotSum,expectedMapHash;
    int i,j,count=0,gen=0;
    DWPS_FilePath(slot,path,sizeof(path));
    size=ri.FS_ReadFile(path,&fileData);
    if(size<=0 || !fileData)
    {
        if(fileData)ri.FS_FreeFile(fileData);
        return 0;
    }
    if(size>=(long)sizeof(dwpsPersistBuffer))
    {
        ri.FS_FreeFile(fileData);
        ri.Printf(PRINT_WARNING,"PCPS V2: file %s too large; ignored\n",path);
        return 0;
    }
    memcpy(dwpsPersistBuffer,fileData,(size_t)size);
    dwpsPersistBuffer[size]=0;
    ri.FS_FreeFile(fileData);
    /* Strict whole-file checksum. Any truncation / partial write fails closed. */
    sumBegin=strstr(dwpsPersistBuffer,"\nCHECKSUM ");
    if(!sumBegin || strstr(sumBegin+1,"\nCHECKSUM "))
        goto invalid;
    gotSum=DWPS_Fnv(dwpsPersistBuffer,(size_t)((sumBegin+1)-dwpsPersistBuffer));
    if(sscanf(sumBegin+1,"CHECKSUM %x",&storedSum)!=1 ||
       storedSum!=gotSum || strchr(sumBegin+1,'\n')==NULL ||
       strchr(sumBegin+1,'\n')[1]!=0)
        goto invalid;

    cursor=dwpsPersistBuffer;
    if(!DWPS_FileReadLine(&cursor,line,sizeof(line)) || strcmp(line,"DWPCPS_V2"))
        goto invalid;
    if(!DWPS_FileReadLine(&cursor,line,sizeof(line)) ||
       sscanf(line,"MAP %63s",mapName)!=1 ||
       Q_stricmp(mapName,tr.world->name))
        goto invalid;
    if(!DWPS_FileReadLine(&cursor,line,sizeof(line)) ||
       sscanf(line,"SIGNATURE %x",&expectedMapHash)!=1 ||
       expectedMapHash!=dwpsPersistMapHash)
        goto invalid;
    if(!DWPS_FileReadLine(&cursor,line,sizeof(line)) ||
       sscanf(line,"GENERATION %d",&gen)!=1 ||
       gen<1 || gen>2000000000)
        goto invalid;
    if(!DWPS_FileReadLine(&cursor,line,sizeof(line)) ||
       sscanf(line,"RULES %d",&count)!=1 ||
       count<0 || count>DWPS_MAX_RULES)
        goto invalid;
    Com_Memset(dwpsPersistScratch,0,sizeof(dwpsPersistScratch));
    for(i=0;i<count;i++)
    {
        dwpsRule_t *r=&dwpsPersistScratch[i];
        int enabled,casters;
        if(!DWPS_FileReadLine(&cursor,line,sizeof(line)) ||
           sscanf(line,"SOURCE %f %f %f %f %d %d %d %d",
             &r->origin[0],&r->origin[1],&r->origin[2],&r->radius,
             &r->sourceClass,&r->fixtureId,&enabled,&casters)!=8 ||
           !DWPS_ValidFinite(r->origin[0]) ||
           !DWPS_ValidFinite(r->origin[1]) ||
           !DWPS_ValidFinite(r->origin[2]) ||
           !DWPS_ValidFinite(r->radius) ||
           r->radius<=0 || r->radius>1000000.0f ||
           r->sourceClass<0 || r->sourceClass>255 ||
           r->fixtureId< -1 || r->fixtureId>1000000 ||
           (enabled!=0 && enabled!=1) ||
           casters<0 || casters>DWPS_MAX_CASTERS)
            goto invalid;
        r->shadowOff=enabled?qtrue:qfalse;
        r->numCasters=casters;
        for(j=0;j<casters;j++)
        {
            dwpsCaster_t *c=&r->casters[j];
            const msurface_t *ms;
            if(!DWPS_FileReadLine(&cursor,line,sizeof(line)) ||
               sscanf(line,"CASTER %d %63s %f %f %f %f %f %f",
                 &c->id,c->material,
                 &c->bounds[0][0],&c->bounds[0][1],&c->bounds[0][2],
                 &c->bounds[1][0],&c->bounds[1][1],&c->bounds[1][2])!=8 ||
               !DWPS_ValidMaterialToken(c->material) ||
               c->id<0 || c->id>=tr.world->numWorldSurfaces)
                goto invalid;
            if(!DWPS_ValidFinite(c->bounds[0][0]) ||
               !DWPS_ValidFinite(c->bounds[0][1]) ||
               !DWPS_ValidFinite(c->bounds[0][2]) ||
               !DWPS_ValidFinite(c->bounds[1][0]) ||
               !DWPS_ValidFinite(c->bounds[1][1]) ||
               !DWPS_ValidFinite(c->bounds[1][2]))
                goto invalid;
            ms=&tr.world->surfaces[c->id];
            c->surface=ms->data;
            if(!DWPS_CasterValid(c))goto invalid;
        }
    }
    if(!DWPS_FileReadLine(&cursor,line,sizeof(line)) ||
       strcmp(line,"END") || cursor!=(sumBegin+1))
        goto invalid;
    if(!DWPS_FileReadLine(&cursor,line,sizeof(line)) ||
       sscanf(line,"CHECKSUM %x",&gotHash)!=1 ||
       gotHash!=storedSum || *cursor!=0)
        goto invalid;
    *generation=gen;
    *numRules=count;
    return 1;
invalid:
    ri.Printf(PRINT_WARNING,
       "PCPS V2: rejected invalid or map-incompatible file %s; no rules from it applied\n",
       path);
    return 0;
}
static void DWPS_LoadCurrentMap(void)
{
    int slot,bestGen=-1,bestSlot=-1,bestNum=0;
    int gen=0,n=0;
    char pathA[128],pathB[128];
    dwpsNumRules=0;
    dwpsSelected=-1;
    dwpsLastSurface=-1;
    dwpsPersistGeneration=0;
    dwpsPersistSlot=-1;
    if(!tr.world || !tr.world->surfaces)return;
    dwpsPersistMapHash=DWPS_MapHash();
    if(!dwpsPersistMapHash)
    {
        ri.Printf(PRINT_WARNING,"PCPS V2: invalid BSP signature; persistence disabled for this map\n");
        return;
    }
    DWPS_FilePath(0,pathA,sizeof(pathA));
    DWPS_FilePath(1,pathB,sizeof(pathB));
    for(slot=0;slot<2;slot++)
        if(DWPS_ReadSlot(slot,&gen,&n) &&
           (bestSlot<0 || gen>bestGen))
        {
            bestGen=gen;
            bestSlot=slot;
            bestNum=n;
            memcpy(dwpsPersistBest,dwpsPersistScratch,sizeof(dwpsPersistBest));
        }
    if(bestSlot>=0)
    {
        memcpy(dwpsRules,dwpsPersistBest,sizeof(dwpsRules));
        dwpsNumRules=bestNum;
        dwpsPersistGeneration=bestGen;
        dwpsPersistSlot=bestSlot;
        ri.Printf(PRINT_ALL,
          "PCPS V2: AUTO-LOADED %d rules for %s (generation %d; %s)\n",
          bestNum,tr.world->name,bestGen,bestSlot==0?pathA:pathB);
    }
    else
        ri.Printf(PRINT_ALL,
          "PCPS V2: no valid saved profile for %s (new rules will autosave)\n",
          tr.world->name);
}
static qboolean DWPS_SaveCurrentMap(void)
{
    size_t used=0;
    char path[128];
    void *checkData=NULL;
    long checkLen;
    int slot,i,j,storedCount=0,nextGen;
    unsigned int sum;
    if(!tr.world || !tr.world->surfaces || !dwpsPersistMapHash)
    {
        ri.Printf(PRINT_WARNING,"PCPS V2: no valid map; cannot save\n");
        return qfalse;
    }
    for(i=0;i<dwpsNumRules;i++)
        if(dwpsRules[i].shadowOff || dwpsRules[i].numCasters)
            storedCount++;
    nextGen=dwpsPersistGeneration+1;
    if(nextGen<=0 || nextGen>2000000000)
    {
        ri.Printf(PRINT_WARNING,"PCPS V2: journal generation exhausted\n");
        return qfalse;
    }
    slot=(dwpsPersistSlot==0)?1:0;
    DWPS_FilePath(slot,path,sizeof(path));
    /* snprintf bound-checked appends; never emit truncated or partial records. */
#define DWPS_EMIT(...) do { \
    int nn=snprintf(dwpsPersistBuffer+used,sizeof(dwpsPersistBuffer)-used,__VA_ARGS__); \
    if(nn<0 || (size_t)nn>=sizeof(dwpsPersistBuffer)-used)goto failed; \
    used+=(size_t)nn; \
} while(0)
    DWPS_EMIT("DWPCPS_V2\nMAP %s\nSIGNATURE %08X\nGENERATION %d\nRULES %d\n",
      tr.world->name,dwpsPersistMapHash,nextGen,storedCount);
    for(i=0;i<dwpsNumRules;i++)
    {
        const dwpsRule_t *r=&dwpsRules[i];
        if(!r->shadowOff && !r->numCasters)continue;
        if(!DWPS_ValidFinite(r->radius) || r->radius<=0.0f ||
           !DWPS_ValidFinite(r->origin[0]) ||
           !DWPS_ValidFinite(r->origin[1]) ||
           !DWPS_ValidFinite(r->origin[2]))
            goto failed;
        DWPS_EMIT("SOURCE %.6f %.6f %.6f %.6f %d %d %d %d\n",
          r->origin[0],r->origin[1],r->origin[2],r->radius,
          r->sourceClass,r->fixtureId,r->shadowOff?1:0,r->numCasters);
        for(j=0;j<r->numCasters;j++)
        {
            const dwpsCaster_t *c=&r->casters[j];
            if(!DWPS_CasterValid(c) || !DWPS_ValidMaterialToken(c->material))
                goto failed;
            DWPS_EMIT("CASTER %d %s %.6f %.6f %.6f %.6f %.6f %.6f\n",
               c->id,c->material,
               c->bounds[0][0],c->bounds[0][1],c->bounds[0][2],
               c->bounds[1][0],c->bounds[1][1],c->bounds[1][2]);
        }
    }
    DWPS_EMIT("END\n");
    sum=DWPS_Fnv(dwpsPersistBuffer,used);
    DWPS_EMIT("CHECKSUM %08X\n",sum);
#undef DWPS_EMIT
    /* Alternating slots keep previous valid generation intact on I/O crash.
       Read back the new slot before declaring persistence successful. */
    ri.FS_WriteFile(path,dwpsPersistBuffer,(int)used);
    checkLen=ri.FS_ReadFile(path,&checkData);
    if(checkLen!=(long)used || !checkData ||
       memcmp(checkData,dwpsPersistBuffer,used)!=0)
    {
        if(checkData)ri.FS_FreeFile(checkData);
        ri.Printf(PRINT_WARNING,
          "PCPS V2: WRITE VERIFY FAILED for %s (current session change still active)\n",
          path);
        return qfalse;
    }
    ri.FS_FreeFile(checkData);
    dwpsPersistGeneration=nextGen;
    dwpsPersistSlot=slot;
    ri.Printf(PRINT_ALL,
       "PCPS V2: SAVED %d persistent rules to %s (generation %d)\n",
       storedCount,path,nextGen);
    return qtrue;
failed:
    ri.Printf(PRINT_WARNING,"PCPS V2: failed to serialize rules; NOT saved\n");
    return qfalse;
}
static void DWPS_PersistAfterChange(void)
{
    if(!DWPS_SaveCurrentMap())
        ri.Printf(PRINT_WARNING,
          "PCPS V2: WARNING change applies for this session only; file NOT updated\n");
}
static void DWPS_Save_f(void)
{
    DWPS_CheckWorld();
    DWPS_SaveCurrentMap();
}
static void DWPS_Reload_f(void)
{
    DWPS_CheckWorld();
    if(tr.world)DWPS_LoadCurrentMap();
}
static void DWPS_File_f(void)
{
    char a[128],b[128];
    DWPS_CheckWorld();
    if(!tr.world){ri.Printf(PRINT_ALL,"PCPS V2: no active BSP\n");return;}
    DWPS_FilePath(0,a,sizeof(a));
    DWPS_FilePath(1,b,sizeof(b));
    ri.Printf(PRINT_ALL,
       "PCPS V2: map=%s signature=%08X, rules=%d, generation=%d, activeSlot=%d\n"
       "PCPS V2: files in writable Main: %s , %s\n"
       "PCPS V2: current launcher fs_homepath controls physical file location\n",
       tr.world->name,dwpsPersistMapHash,dwpsNumRules,
       dwpsPersistGeneration,dwpsPersistSlot,a,b);
}
