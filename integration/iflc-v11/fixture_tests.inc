static void TestFixturePolicy(void) {
    static msurface_t s[10]; static srfBspSurface_t b[10];
    static srfVert_t v[10][6]; static glIndex_t ix[10][12]; static shader_t sh[10];
    static const float xyz[9][6][3] = {
      {{-8,1,0},{7,16,0},{7,16,48},{-8,1,48}},
      {{-64,0,-100},{64,0,-100},{64,0,100},{-64,0,100}},
      {{8,12,-12},{-8,12,-12},{-8,0,-12},{8,0,-12}},
      {{-12,4,0},{-12,16,0},{12,16,0},{12,4,0},{12,0,0},{-12,0,0}},
      {{8,12,-12},{8,0,-12},{12,0,0},{12,4,0},{12,16,0}},
      {{-8,0,-12},{-8,12,-12},{-12,16,0},{-12,4,0},{-12,0,0}},
      {{12,4,0},{12,0,0},{12,0,20},{12,4,20}},
      {{-12,4,0},{12,4,0},{12,4,20},{6,4,28},{-6,4,28},{-12,4,20}},
      {{-10,0,10},{10,0,10},{10,0,40},{-10,0,40}}
    };
    const int nv[9]={4,4,4,6,5,5,4,6,4};
    int i,j,k,turn;
    dlight_t dl;
    for(turn=0;turn<4;++turn) {
      float angle=turn*0.71f; float cs=cosf(angle),sn=sinf(angle);
      TestReadyScene(); R_IFLC_ResetFixtures();
      memset(s,0,sizeof(s));memset(b,0,sizeof(b));memset(v,0,sizeof(v));memset(sh,0,sizeof(sh));
      memset(s_iflcOwners,0,sizeof(s_iflcOwners));memset(s_iflcSurfaces,0,sizeof(s_iflcSurfaces));
      testWorld.surfaces=s;testWorld.numWorldSurfaces=testWorld.numsurfaces=9;
      Q_strncpyz(testWorld.baseName,turn ? "arbitrary_map" : "fixture_test",sizeof(testWorld.baseName));
      for(i=0;i<9;++i) {
        b[i].surfaceType=SF_FACE;b[i].numVerts=nv[i];b[i].numIndexes=(nv[i]-2)*3;b[i].verts=v[i];b[i].indexes=ix[i];
        for(j=0;j<nv[i];++j) { float x=xyz[i][j][0],y=xyz[i][j][1];
          VectorSet(v[i][j].xyz,x*cs-y*sn+turn*300,y*cs+x*sn-turn*170,xyz[i][j][2]+turn*25);
        }
        for(j=0;j<nv[i]-2;++j) {ix[i][3*j]=0;ix[i][3*j+1]=j+1;ix[i][3*j+2]=j+2;}
        s[i].data=(surfaceType_t*)&b[i];s[i].shader=&sh[i];sh[i].sort=SS_OPAQUE;
        Q_strncpyz(sh[i].name,i?"opaque/common_stone":"fx/flame",sizeof(sh[i].name));
      }
      s_iflcReady=qtrue;s_iflcCatalogOverflow=qfalse;s_iflcOwnerCount=s_iflcSurfaceCount=1;
      s_iflcOwners[0].kind=IFLC_SURFACE;s_iflcOwners[0].surfaceCount=1;
      VectorSet(s_iflcOwners[0].origin,-.5f*cs-8.5f*sn+turn*300,8.5f*cs-.5f*sn-turn*170,24+turn*25);
      Q_strncpyz(s_iflcOwners[0].key,"surface:test",sizeof(s_iflcOwners[0].key));
      s_iflcSurfaces[0].owner=0;s_iflcSurfaces[0].surfaceIndex=0;
      memset(&dl,0,sizeof(dl));dl.iflcOptIn=qtrue;VectorCopy(s_iflcOwners[0].origin,dl.origin);
      CHECK(R_IFLC_ShadowFixture(&dl)==1,"geometry qualified mount independent of map and rotation");
      CHECK(s_iflcFixtures[0].count==6,"exact six connected local fixture faces classified");
      CHECK(s_iflcFixtures[0].policyKey!=0,"nonzero geometry policy cache key");
      tr.currentEntityNum=REFENTITYNUM_WORLD;
      tr.viewParms.flags=VPF_DEPTHSHADOW|VPF_SHADOWMAP;
      tr.viewParms.iflcFixture=1;tr.viewParms.iflcFixtureKey=R_IFLC_FixturePolicyKey(1);
      CHECK(!R_IFLC_SuppressSelfCaster(&s[1]),"large structural wall retained");
      CHECK(!R_IFLC_SuppressSelfCaster(&s[8]),"small coplanar wall tile retained");
      for(i=2;i<=7;++i)CHECK(R_IFLC_SuppressSelfCaster(&s[i]),"each local fixture caster excluded for own direct light");
      tr.viewParms.flags|=VPF_FIREVOL_SYNTHETIC_SHADOW;
      CHECK(!R_IFLC_SuppressSelfCaster(&s[7]),"FireVol synthetic shadows unchanged");
      tr.viewParms.flags=VPF_DEPTHSHADOW|VPF_ORTHOGRAPHIC;
      CHECK(!R_IFLC_SuppressSelfCaster(&s[7]),"CSM shadows unchanged");
      tr.viewParms.flags=0;CHECK(!R_IFLC_SuppressSelfCaster(&s[7]),"visible geometry unchanged");
      tr.viewParms.flags=VPF_DEPTHSHADOW|VPF_SHADOWMAP;tr.viewParms.iflcFixtureKey^=1;
      CHECK(!R_IFLC_SuppressSelfCaster(&s[7]),"mismatched policy cannot suppress a surface");
      tr.viewParms.iflcFixtureKey=R_IFLC_FixturePolicyKey(1);tr.currentEntityNum=0;
      CHECK(!R_IFLC_SuppressSelfCaster(&s[7]),"brush models doors and entities unchanged");
      dl.iflcOptIn=qfalse;CHECK(R_IFLC_ShadowFixture(&dl)==0,"native promoted and other lights retain fixture shadows");
      dl.iflcOptIn=qtrue;dl.origin[0]+=100;dl.origin[1]+=100;
      CHECK(R_IFLC_ShadowFixture(&dl)==0,"nearby different light cannot inherit caster exclusions");
      VectorCopy(s_iflcOwners[0].origin,dl.origin);
      R_IFLC_ResetFixtures();sh[1].sort=SS_SEE_THROUGH;
      CHECK(R_IFLC_ShadowFixture(&dl)==0,"no structural backing wall means fail closed");
      sh[1].sort=SS_OPAQUE;R_IFLC_ResetFixtures();s_iflcOwners[0].ambiguous=qtrue;
      CHECK(R_IFLC_ShadowFixture(&dl)==0,"ambiguous source retains all casters");
    }
    printf("CHECKED V1.1 fixture geometry: rotation/translation, local component, architecture, non-owner shadows, FireVol/CSM, ambiguity\n");
}
