#!/usr/bin/env python3
"""Rend2 Hybrid Relight V2 integration, exact #41019985033 source lineage.
Never modifies game BSP, GLSL, sun, shadow, bloom, particles or SSGI.
"""
import argparse, hashlib, json
from pathlib import Path
MARK='DARKWOLF_HYBRID_RELIGHT_V2_NATIVE_41019985033'
ANCHOR='#define\tDEFAULT_LIGHTMAP_SIZE\t128\nstatic\tvoid R_LoadLightmaps( lump_t *l, lump_t *surfs ) {'
HELPERS=r'''/* DARKWOLF_HYBRID_RELIGHT_V2_NATIVE_41019985033
 * Default OFF. Input source-BSP fingerprint and all source image texels must
 * validate before ANY atlas is replaced. Does not recover the historical
 * RTCW direct / indirect decomposition from the original RGB lightmap.
 */
#define DW_HYBRID_V2_PIXELS (128 * 128)
#define DW_HYBRID_V2_HDR_HEAD "#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 128 +X 128\n"
static unsigned long long s_dwHybridBspHash, s_dwHybridBspSize;
static unsigned long long DW_HybridV2_Fnv64(const byte *src, int len) {
    unsigned long long h=14695981039346656037ULL;
    int n; for(n=0;n<len;n++){h^=(unsigned long long)src[n];h*=1099511628211ULL;}
    return h;
}
static qboolean DW_HybridV2_ValidateAtlas(const byte *data,int bytes,
                                     const byte *stockRGB,float minRetain) {
    const int head=(int)(sizeof(DW_HYBRID_V2_HDR_HEAD)-1);
    const int expect=head+DW_HYBRID_V2_PIXELS*12;
    int i,c;
    if(!data || bytes!=expect || memcmp(data,DW_HYBRID_V2_HDR_HEAD,head))
        return qfalse;
    for(i=0;i<DW_HYBRID_V2_PIXELS;i++)for(c=0;c<3;c++){
        float f, original=(float)stockRGB[i*3+c];
        memcpy(&f,data+head+(i*3+c)*4,4);f=LittleFloat(f);
        if(!(f>=original*minRetain-0.0005f && f<=original+0.0005f))
            return qfalse;
    }
    return qtrue;
}
static qboolean DW_HybridV2_Preflight(const byte *lightmaps,int count,float retain){
    char file[MAX_QPATH],expected[160];
    char *manifest=NULL;int bytes,i;
    const int atlasBytes=DW_HYBRID_V2_PIXELS*3;
    Com_sprintf(file,sizeof(file),"maps/%s/dwrl_v2.manifest",s_worldData.baseName);
    bytes=ri.FS_ReadFile(file,(void **)&manifest);
    Com_sprintf(expected,sizeof(expected),"DWHR2V1 %u %08x%08x %d\n",
        (unsigned int)s_dwHybridBspSize,
        (unsigned int)(s_dwHybridBspHash>>32),
        (unsigned int)s_dwHybridBspHash,count);
    if(bytes!=(int)strlen(expected) || !manifest ||
       memcmp(manifest,expected,(size_t)bytes)){
       if(manifest)ri.FS_FreeFile(manifest);
       ri.Printf(PRINT_WARNING,"DW_HYBRID_V2: map=%s manifest mismatch; full stock fallback\n",s_worldData.baseName);
       return qfalse;
    }
    ri.FS_FreeFile(manifest);
    for(i=0;i<count;i++){
        byte *data=NULL;int size;
        Com_sprintf(file,sizeof(file),"maps/%s/dwrl_%04d.hdr",s_worldData.baseName,i);
        size=ri.FS_ReadFile(file,(void **)&data);
        if(!DW_HybridV2_ValidateAtlas(data,size,lightmaps+i*atlasBytes,retain)){
            if(data)ri.FS_FreeFile(data);
            ri.Printf(PRINT_WARNING,"DW_HYBRID_V2: map=%s atlas=%d invalid; full stock fallback\n",
                s_worldData.baseName,i);
            return qfalse;
        }
        ri.FS_FreeFile(data);
    }
    return qtrue;
}
'''
def one(text,old,new,what):
    if text.count(old)!=1:raise ValueError(what+': source anchor count '+str(text.count(old)))
    return text.replace(old,new,1)
def transform(text):
    if MARK in text:raise ValueError('already patched')
    text=one(text,ANCHOR,HELPERS+'\n'+ANCHOR,'R_LoadLightmaps')
    text=one(text,'\tint\t\t\tnumLightmapsPerPage = 16;',
       '\tint\t\t\tnumLightmapsPerPage = 16;\n'
       '\tcvar_t *hybrid = ri.Cvar_Get("r_dwHybridRelight","0",CVAR_ARCHIVE);\n'
       '\tcvar_t *strength = ri.Cvar_Get("r_dwHybridRelightStrength","1.0",CVAR_ARCHIVE);\n'
       '\tqboolean hybridActive = qfalse;\n\tfloat hybridMix = 0.0f;',
       'cvars')
    a='\tif (tr.worldDeluxeMapping)\n\t\tnumLightmaps >>= 1;'
    b=a+'''
    // DARKWOLF_HYBRID_RELIGHT_V2_NATIVE_41019985033
    hybridMix = strength ? strength->value : 1.0f;
    if(hybridMix<0.0f)hybridMix=0.0f;
    if(hybridMix>1.0f)hybridMix=1.0f;
    if(hybrid && hybrid->integer && hybridMix>0.0f && r_hdr->integer &&
       !tr.worldDeluxeMapping)
        hybridActive=DW_HybridV2_Preflight(buf,numLightmaps,0.82f);
    if(hybrid && hybrid->integer)
        ri.Printf(PRINT_ALL,"DW_HYBRID_V2: map=%s active=%d strength=%.3f atlases=%d (reload map to change)\\n",
                  s_worldData.baseName,(int)hybridActive,hybridMix,numLightmaps);
'''
    text=one(text,a,b,'map-load gate')
    text=one(text,'\ttextureInternalFormat = GL_RGBA8;\n\tif (r_hdr->integer)',
       '\ttextureInternalFormat = GL_RGBA8;\n\tif(hybridActive)\n\t\ttextureInternalFormat=GL_RGBA16;\n\telse if (r_hdr->integer)',
       'HDR format')
    a='\t\t\t\tCom_sprintf( filename, sizeof( filename ), "maps/%s/lm_%04d.hdr", s_worldData.baseName, i * (tr.worldDeluxeMapping ? 2 : 1) );'
    text=one(text,a,
       '\t\t\t\tif(hybridActive)\n'
       '\t\t\t\t\tCom_sprintf(filename,sizeof(filename),"maps/%s/dwrl_%04d.hdr",s_worldData.baseName,i);\n'
       '\t\t\t\telse\n'+a,'custom input')
    a='\t\t\t\tsize = ri.FS_ReadFile(filename, (void **)&hdrLightmap);'
    text=one(text,a,a+'''
                if(hybridActive && !hdrLightmap)
                    ri.Error(ERR_DROP,"DW_HYBRID_V2: atlas disappeared after preflight");''',
       'validation race')
    a='\t\t\t\t\tcolor[2] = LittleFloat(color[2]);'
    text=one(text,a,a+'''
                    if(hybridActive) {
                        const byte *stock = buf+(i*DW_HYBRID_V2_PIXELS+j)*3;
                        color[0]=stock[0]+hybridMix*(color[0]-stock[0]);
                        color[1]=stock[1]+hybridMix*(color[1]-stock[1]);
                        color[2]=stock[2]+hybridMix*(color[2]-stock[2]);
                    }''','runtime blending')
    a='    ri.FS_ReadFile( name, &buffer.v );'
    text=one(text,a,
      '    {\n'
      '        int length=ri.FS_ReadFile(name,&buffer.v);\n'
      '        s_dwHybridBspSize=(length>0)?(unsigned long long)length:0ULL;\n'
      '        s_dwHybridBspHash=(length>0 && buffer.b)?DW_HybridV2_Fnv64(buffer.b,length):0ULL;\n'
      '    }','source BSP provenance')
    if text.count('DW_HybridV2_Preflight(')!=2:raise AssertionError('incomplete')
    return text
def main():
    p=argparse.ArgumentParser()
    p.add_argument('source',type=Path)
    p.add_argument('--check-only',action='store_true')
    p.add_argument('--proof',type=Path)
    a=p.parse_args()
    f=a.source/'SP/code/rend2/tr_bsp.c'
    old=f.read_text();new=transform(old)
    if not a.check_only:f.write_text(new)
    evidence={'base_run':41019985033,'old_sha256':hashlib.sha256(old.encode()).hexdigest(),
        'new_sha256':hashlib.sha256(new.encode()).hexdigest(),'modified_files':['SP/code/rend2/tr_bsp.c'],
        'default_off':True,'cvars':['r_dwHybridRelight','r_dwHybridRelightStrength'],
        'new_GLSL':False,'check_only':a.check_only}
    if a.proof:a.proof.write_text(json.dumps(evidence,indent=2)+'\n')
    print('DW_HYBRID_NATIVE_SOURCE_APPLY_PASS')
if __name__=='__main__':main()
