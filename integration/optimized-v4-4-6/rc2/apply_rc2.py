from pathlib import Path
import re,sys,hashlib,json
root=Path(sys.argv[1])
lock=json.loads((Path(__file__).parent/'rc2-lock.json').read_text())
for name,h in lock['source_delta'].items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=h['before']:raise RuntimeError('RC1 input mismatch: '+name)
def read(p): return (root/p).read_bytes().decode('latin1')
def write(p,s): (root/p).write_bytes(s.encode('latin1'))
def once(s,a,b,n=1):
 assert s.count(a)==n,(a[:100],s.count(a),n)
 return s.replace(a,b)
# RC2-01: collect all radix byte histograms in one traversal, stable scatters.
p='SP/code/rend2/tr_main.c';s=read(p)
a=s.index('static ID_INLINE void R_Radix(');b=s.index('//==========================================================================================',a)
s=s[:a]+'''/* RC2-01: one histogram traversal, stable LSD order, no passes for constant bytes. */
static void R_RadixSort(drawSurf_t *source, int size)
{
    static drawSurf_t scratch[MAX_DRAWSURFS];
    int count[4][256] = {{0}};
    int index[256];
    int i, pass, bucket;
    drawSurf_t *from = source, *to = scratch, *swap;
    if (size < 2)
        return;
    for (i = 0; i < size; ++i)
    {
        unsigned int key = source[i].sort;
        ++count[0][key & 255u];
        ++count[1][(key >> 8) & 255u];
        ++count[2][(key >> 16) & 255u];
        ++count[3][(key >> 24) & 255u];
    }
    for (pass = 0; pass < 4; ++pass)
    {
        if (count[pass][(from[0].sort >> (pass * 8)) & 255u] == size)
            continue;
        index[0] = 0;
        for (bucket = 1; bucket < 256; ++bucket)
            index[bucket] = index[bucket - 1] + count[pass][bucket - 1];
        for (i = 0; i < size; ++i)
        {
            bucket = (from[i].sort >> (pass * 8)) & 255u;
            to[index[bucket]++] = from[i];
        }
        swap = from; from = to; to = swap;
    }
    if (from != source)
        Com_Memcpy(source, from, size * sizeof(*source));
}

''' +s[b:];write(p,s)
# RC2-02,03: backend owns rectangle/matrix caches; all context resets invalidate.
p='SP/code/rend2/tr_local.h';s=read(p)
s=once(s,'\tqboolean\tfinishCalled;','\tqboolean\tfinishCalled;\n\tqboolean viewportValid, scissorValid, matrixProductValid;\n\tint viewportRect[4], scissorRect[4];')
s=once(s,'void\tGL_SetDefaultState (void);','void\tGL_SetDefaultState (void);\nvoid GL_Viewport(GLint x, GLint y, GLsizei width, GLsizei height);\nvoid GL_Scissor(GLint x, GLint y, GLsizei width, GLsizei height);')
anchor='void\tGL_SetDefaultState (void);'
helper='''/* RC2-04: axial BSP planes need one subtraction; oblique planes stay unchanged. */
static ID_INLINE float R_PointPlaneDistance(const vec3_t point, const cplane_t *plane)
{
    return plane->type < 3 ? point[plane->type] - plane->dist
        : DotProduct(point, plane->normal) - plane->dist;
}

'''
s=once(s,anchor,helper+anchor);write(p,s)
p='SP/code/rend2/tr_init.c';s=read(p);s=once(s,'void GL_SetDefaultState( void ) {','void GL_SetDefaultState( void ) {\n\tglState.viewportValid = glState.scissorValid = qfalse;\n\tglState.matrixProductValid = qfalse;');write(p,s)
p='SP/code/rend2/tr_backend.c';s=read(p)
s=s.replace('qglViewport(', 'GL_Viewport(').replace('qglScissor(', 'GL_Scissor(')
helper='''/* RC2-02: all Rend2 rectangle-state writers go through these helpers. */
void GL_Viewport(GLint x, GLint y, GLsizei width, GLsizei height)
{
    int rect[4] = {x, y, width, height};
    if (width < 0 || height < 0)
    {
        qglViewport(x, y, width, height);
        glState.viewportValid = qfalse;
        return;
    }
    if (!glState.viewportValid || memcmp(rect, glState.viewportRect, sizeof(rect)))
    {
        qglViewport(x, y, width, height);
        memcpy(glState.viewportRect, rect, sizeof(rect));
        glState.viewportValid = qtrue;
    }
}

void GL_Scissor(GLint x, GLint y, GLsizei width, GLsizei height)
{
    int rect[4] = {x, y, width, height};
    if (width < 0 || height < 0)
    {
        qglScissor(x, y, width, height);
        glState.scissorValid = qfalse;
        return;
    }
    if (!glState.scissorValid || memcmp(rect, glState.scissorRect, sizeof(rect)))
    {
        qglScissor(x, y, width, height);
        memcpy(glState.scissorRect, rect, sizeof(rect));
        glState.scissorValid = qtrue;
    }
}

/* RC2-10: a pure cache keyed by all inputs, not by frame or map identity. */
static void RB_FarPlaneExtents(float zmax, float fovX, float fovY, float *xmax, float *ymax)
{
    static qboolean valid = qfalse;
    static float key[3], cachedX, cachedY;
    float input[3] = {zmax, fovX, fovY};
    if (!valid || memcmp(input, key, sizeof(input)))
    {
        cachedY = zmax * tan(fovY * M_PI / 360.0f);
        cachedX = zmax * tan(fovX * M_PI / 360.0f);
        memcpy(key, input, sizeof(input));
        valid = qtrue;
    }
    *xmax = cachedX;
    *ymax = cachedY;
}

'''
s=once(s,'void GL_SetProjectionMatrix(mat4_t matrix)',helper+'void GL_SetProjectionMatrix(mat4_t matrix)')
for name,field in [('Projection','projection'),('Modelview','modelview')]:
 a='void GL_Set'+name+'Matrix(mat4_t matrix)\n{\n'
 s=once(s,a,a+f'\t/* RC2-03: preserve bit identity, including signed zero. */\n\tif (glState.matrixProductValid && !memcmp(matrix, glState.{field}, sizeof(mat4_t)))\n\t\treturn;\n')
 a='Mat4Multiply(glState.projection, glState.modelview, glState.modelviewProjection);\t'
 s=once(s,a,'Mat4Multiply(glState.projection, glState.modelview, glState.modelviewProjection);\n\tglState.matrixProductValid = qtrue;',2) if name=='Projection' else s
s=once(s,'DotProduct(point, node->plane->normal) - node->plane->dist','R_PointPlaneDistance(point, node->plane)')
s=once(s,'ymax = zmax * tan(backEnd.viewParms.fovY * M_PI / 360.0f);\n\txmax = zmax * tan(backEnd.viewParms.fovX * M_PI / 360.0f);','RB_FarPlaneExtents(zmax, backEnd.viewParms.fovX, backEnd.viewParms.fovY, &xmax, &ymax);',2)
s,n=re.subn(r'float ymax = zmax \* tan\(backEnd.viewParms.fovY \* M_PI / 360\.0f\);\n([\t ]*)float xmax = zmax \* tan\(backEnd.viewParms.fovX \* M_PI / 360\.0f\);',r'float ymax, xmax;\n\1RB_FarPlaneExtents(zmax, backEnd.viewParms.fovX, backEnd.viewParms.fovY, &xmax, &ymax);',s);assert n==2
write(p,s)
p='SP/code/rend2/tr_fbo.c';s=read(p).replace('qglViewport(', 'GL_Viewport(').replace('qglScissor(', 'GL_Scissor(');write(p,s)
p='SP/code/rend2/tr_world.c';s=read(p)
for a,b in [('DotProduct( p,plane->normal ) - plane->dist','R_PointPlaneDistance(p, plane)'),('DotProduct( dl->origin, node->plane->normal ) - node->plane->dist','R_PointPlaneDistance(dl->origin, node->plane)'),('DotProduct( shadow->lightOrigin, node->plane->normal ) - node->plane->dist','R_PointPlaneDistance(shadow->lightOrigin, node->plane)')]: s=once(s,a,b)
write(p,s)
p='SP/code/rend2/tr_scene.c';s=once(read(p),'DotProduct(point, plane->normal) - plane->dist','R_PointPlaneDistance(point, plane)');write(p,s)
# RC2-05: preserve insertion/search precedence and case semantics; index only this call.
p='SP/code/qcommon/files.c';s=read(p)
s=once(s,'#define MAX_FOUND_FILES 0x1000','#define MAX_FOUND_FILES 0x1000\n#define FILELIST_HASH_SIZE 1024')
a=s.index('static int FS_AddFileToList('); b=s.index('\n/*',a)
s=s[:a]+'''/* RC2-05: Q_stricmp-compatible ASCII folding; do not fold path separators. */
static unsigned int FS_FileListHash(const char *name)
{
    unsigned int hash = 2166136261u;
    unsigned char c;
    while ((c = (unsigned char)*name++) != 0)
    {
        if (c >= 'a' && c <= 'z') c -= 'a' - 'A';
        hash = (hash ^ c) * 16777619u;
    }
    return hash & (FILELIST_HASH_SIZE - 1);
}

static int FS_AddFileToList(char *name, char *list[MAX_FOUND_FILES], int nfiles,
    int *heads, int *links)
{
    int i;
    unsigned int hash;
    if (nfiles == MAX_FOUND_FILES - 1)
        return nfiles;
    hash = FS_FileListHash(name);
    for (i = heads[hash]; i >= 0; i = links[i])
        if (!Q_stricmp(name, list[i]))
            return nfiles;
    list[nfiles] = CopyString(name);
    links[nfiles] = heads[hash];
    heads[hash] = nfiles;
    return nfiles + 1;
}
''' +s[b:]
s=once(s,'\tchar            *list[MAX_FOUND_FILES];','\tchar            *list[MAX_FOUND_FILES];\n\tint fileListHeads[FILELIST_HASH_SIZE], fileListLinks[MAX_FOUND_FILES];')
s=once(s,"if ( path[pathLength - 1] == '\\\\' || path[pathLength - 1] == '/' ) {","if ( pathLength > 0 && ( path[pathLength - 1] == '\\\\' || path[pathLength - 1] == '/' ) ) {")
s=once(s,'\tnfiles = 0;\n\tFS_ReturnPath( path, zpath, &pathDepth );','\tnfiles = 0;\n\tfor (i = 0; i < FILELIST_HASH_SIZE; ++i) fileListHeads[i] = -1;\n\tFS_ReturnPath( path, zpath, &pathDepth );')
s=once(s,'FS_AddFileToList( name, list, nfiles )','FS_AddFileToList( name, list, nfiles, fileListHeads, fileListLinks )',2)
s=once(s,'FS_AddFileToList( name + temp, list, nfiles )','FS_AddFileToList( name + temp, list, nfiles, fileListHeads, fileListLinks )')
write(p,s)
# RC2-06: recompute before every invocation, not time keyed.
p='SP/code/cgame/cg_particles.c';s=read(p)
s=once(s,'void CG_AddParticleToScene( cparticle_t *p, vec3_t org, float alpha ) {','static vec3_t particleViewAngles; /* RC2-06: current CG_AddParticles invocation only. */\n\nvoid CG_AddParticleToScene( cparticle_t *p, vec3_t org, float alpha ) {')
s=once(s,'\t\t\tvectoangles( cg.refdef.viewaxis[0], rotate_ang );','\t\t\tVectorCopy(particleViewAngles, rotate_ang);',3)
s=once(s,'\tvectoangles( cg.refdef.viewaxis[0], rotate_ang );\n\troll +=','\tvectoangles( cg.refdef.viewaxis[0], particleViewAngles );\n\tVectorCopy(particleViewAngles, rotate_ang);\n\troll +=')
write(p,s)
# RC2-07: repeat-texture trails use stored sTex, never the summed length.
p='SP/code/cgame/cg_trails.c';s=once(read(p),'if ( j->nextJunc ) {\n\t\t\t\tsInc += VectorDistance','if ( j->nextJunc && trail->sType != STYPE_REPEAT ) {\n\t\t\t\t/* RC2-07: repeat trails do not consume total length. */\n\t\t\t\tsInc += VectorDistance');write(p,s)
# RC2-08: same formula, no approximation.
p='SP/code/rend2/glsl/volumetriclocal_fp.glsl';s=read(p)
a='''    float guardWidth = max(lightRadius * plumeRadius * mix(1.06, 0.50, z01), 1.0);
    float guardR = length(rel.xy - bend) / guardWidth;
    float lateralGuard = 1.0 - smoothstep(0.70, 1.06, guardR);
'''
s=once(s,a,'')
s=once(s,'    vec2 flutter;','''    // RC2-08: outside the tapered guard the original final product is exactly zero.
'''+a+'''    if (lateralGuard <= 0.0)
        return 0.0;

    vec2 flutter;''')
write(p,s)
# RC2-09: max of bounded [0,1] masks cannot rise above 1.
p='SP/code/rend2/glsl/ssgi_fp.glsl';s=read(p);a=s.index('float SsgiSceneEntityGuardMask(');b=s.index('\nfloat SsgiEdgeStabilityAt',a);part=s[a:b]
lines=part.splitlines();out=[]
for l in lines:
 out.append(l)
 if 'float m = SsgiSceneEntityMask(uv);' in l or 'm = max(m, SsgiSceneEntityMask(' in l:
  out.extend(['\t// RC2-09: saturated maximum; later taps cannot change this value.','\tif (m >= 1.0) return 1.0;'])
assert sum('if (m >= 1.0)' in l for l in out)==13
s=s[:a]+'\n'.join(out)+'\n'+s[b:];write(p,s)
# Exact reviewed formatting is part of the locked source identity.
p='SP/code/rend2/glsl/ssgi_fp.glsl';s=read(p)
needle='\t// RC2-09: saturated maximum; later taps cannot change this value.\n\tif (m >= 1.0) return 1.0;'
start=s.index(needle)+len(needle)
s=s[:start]+s[start:].replace(needle,'\t\tif (m >= 1.0) return 1.0;');write(p,s)
p='SP/code/rend2/tr_backend.c';s=read(p)
s=s.replace('GL_Viewport( backEnd.viewParms.viewportX, backEnd.viewParms.viewportY, \n','GL_Viewport( backEnd.viewParms.viewportX, backEnd.viewParms.viewportY,\n')
s=s.replace('GL_Scissor( backEnd.viewParms.viewportX, backEnd.viewParms.viewportY, \n','GL_Scissor( backEnd.viewParms.viewportX, backEnd.viewParms.viewportY,\n');write(p,s)
for name,h in lock['source_delta'].items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=h['after']:raise RuntimeError('RC2 output mismatch: '+name)
print('APPLIED 10 SOURCE-BASED OPTIMIZATIONS')
