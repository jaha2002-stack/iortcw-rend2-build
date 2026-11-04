/* Actual own-policy tests, including T junctions that failed the first game run. */
static void TestSelfContact(void)
{
 srfBspSurface_t a,b;srfVert_t av[4],bv[4];glIndex_t ix[6]={0,1,2,0,2,3};int i;
 const float roof[4][3]={{0,0,0},{10,0,0},{10,10,0},{0,10,0}};
 const float bar[4][3]={{4,4,-10},{6,4,-10},{6,4,0},{4,4,0}};
 const float corner[4][3]={{10,10,0},{12,10,0},{12,10,-2},{10,10,-2}};
 memset(&a,0,sizeof(a));memset(&b,0,sizeof(b));memset(av,0,sizeof(av));memset(bv,0,sizeof(bv));
 a.numVerts=b.numVerts=4;a.numIndexes=b.numIndexes=6;a.indexes=b.indexes=ix;a.verts=av;b.verts=bv;
 for(i=0;i<4;++i){VectorCopy(roof[i],av[i].xyz);VectorCopy(bar[i],bv[i].xyz);}
 CHECK(!R_IFLC_FixtureAdjacent(&a,&b),"T junction lacks matching edge vertices");
 CHECK(R_IFLC_SelfContact(&a,&b),"bar terminates inside actual housing roof");
 CHECK(R_IFLC_SelfContact(&b,&a),"contact is symmetric");
 for(i=0;i<4;++i)bv[i].xyz[2]+=.3f;
 CHECK(!R_IFLC_SelfContact(&a,&b),"nearby bounds alone do not join body");
 for(i=0;i<4;++i)VectorCopy(corner[i],bv[i].xyz);
 CHECK(!R_IFLC_SelfContact(&a,&b),"single shared corner cannot join unrelated object");
}
static void TestSelfRule(const dlight_t *original, msurface_t *s)
{
    dlight_t dl=*original,other=*original; iflcProfile_t *p;int f,i,count;const char *why;
    iflcProfile_t parsed[IFLC_MAX_PROFILES];char text[512],path[128];testFile_t *file;
    int oldSort=s[0].shader->sort;s[0].shader->sort=SS_BLEND0;
    TestSelfContact();
    Q_strncpyz(s_iflcMap,testWorld.baseName,sizeof(s_iflcMap));
    Com_sprintf(path,sizeof(path),"firelights/%s.iflc",s_iflcMap);
    memset(s_iflcProfiles,0,sizeof(s_iflcProfiles));R_IFLC_ResetSelfFixtures();
    p=R_IFLC_ProfileForOwner(0,qtrue);p->selfShadow=1;p->enabled=0;
    f=R_IFLC_ShadowFixture(&dl);
    CHECK(f>IFLC_MAX_OWNERS,"explicit OFF identifies own body without enabling opt-in Direct");
    CHECK(s_iflcSelfFixtures[0].count>=3,"explicit own-body set populated");
    tr.currentEntityNum=REFENTITYNUM_WORLD;tr.viewParms.flags=VPF_SHADOWMAP|VPF_DEPTHSHADOW;
    tr.viewParms.iflcFixture=f;tr.viewParms.iflcFixtureKey=R_IFLC_FixturePolicyKey(f);
    CHECK(!R_IFLC_SuppressSelfCaster(&s[1]),"structural wall retained");
    CHECK(!R_IFLC_SuppressSelfCaster(&s[8]),"small coplanar wall tile retained");
    for(i=0;i<s_iflcSelfFixtures[0].count;++i)CHECK(R_IFLC_SuppressSelfCaster(&s[s_iflcSelfFixtures[0].surfaces[i]]),"own body suppressed only for own light");
    tr.viewParms.flags|=VPF_FIREVOL_SYNTHETIC_SHADOW;
    CHECK(R_IFLC_SuppressSelfCaster(&s[s_iflcSelfFixtures[0].surfaces[0]]),"synthetic own body policy");
    CHECK(R_IFLC_SurfaceSelfFixture(0)==f,"stable flame own policy");
    tr.viewParms.flags=0;CHECK(!R_IFLC_SuppressSelfCaster(&s[7]),"visible body retained");
    tr.viewParms.flags=VPF_SHADOWMAP|VPF_DEPTHSHADOW|VPF_ORTHOGRAPHIC;
    CHECK(!R_IFLC_SuppressSelfCaster(&s[7]),"sun caster retained");
    tr.viewParms.flags=VPF_SHADOWMAP|VPF_DEPTHSHADOW;tr.currentEntityNum=0;
    CHECK(!R_IFLC_SuppressSelfCaster(&s[7]),"door/entity retained");
    other.origin[0]+=100;CHECK(R_IFLC_ShadowFixture(&other)==0,"different light retains shadow");
    p->selfShadow=2;CHECK(R_IFLC_ShadowFixture(&dl)==0,"ON restores original shadow");
    p->selfShadow=0;CHECK(R_IFLC_ShadowFixture(&dl)==1,"AUTO restores accepted compact policy");
    p->selfShadow=1;p->selfSeedCount=1;p->selfSeeds[0]=2;R_IFLC_ResetSelfFixtures();
    CHECK(R_IFLC_ShadowFixture(&dl)>IFLC_MAX_OWNERS,"manual seed works");
    p->selfSeeds[0]=1;R_IFLC_ResetSelfFixtures();
    CHECK(R_IFLC_ShadowFixture(&dl)==0,"wall seed rejected");
    p->selfSeeds[0]=2;R_IFLC_ResetSelfFixtures();
    TestClearFiles();s_iflcDirty=qtrue;R_IFLC_Save_f();file=TestFindFile(path,qfalse);
    CHECK(file && strstr(file->contents,"DW_IFLC 2") && strstr(file->contents," self 1 1 2"),"versioned profile saved");
    if(file) {
        CHECK(R_IFLC_ParseProfile(file->contents,file->length,parsed,&count,&why),"profile parses");
        CHECK(count==1 && parsed[0].selfShadow==1 && parsed[0].selfSeedCount==1 && parsed[0].selfSeeds[0]==2,"new fields roundtrip");
        p->selfShadow=2;CHECK(R_IFLC_LoadProfile(qtrue),"saved self policy reloads");
        CHECK(s_iflcProfiles[0].selfShadow==1,"reload restores OFF");
    }
    Com_sprintf(text,sizeof(text),"DW_IFLC 2\nmap %s\nbsp %08x\ncount 1\nfixture %s 1 1 1 0 0 1 1 1 self 1 2 2 2\nend\n",s_iflcMap,s_iflcFingerprint,s_iflcOwners[0].key);
    CHECK(!R_IFLC_ParseProfile(text,strlen(text),parsed,&count,&why),"duplicate seed rejected");
    testControl.integer=0;CHECK(R_IFLC_SurfaceSelfFixture(0)==0,"master OFF bypasses own-volume policy");testControl.integer=1;
    memset(s_iflcProfiles,0,sizeof(s_iflcProfiles));R_IFLC_ResetSelfFixtures();TestClearFiles();s[0].shader->sort=oldSort;
}
