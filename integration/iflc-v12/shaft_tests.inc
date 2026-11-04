/* Synthetic geometry regression, independent of any retail map/material. */
static void TestSlenderTorch(void) {
    static msurface_t s[8]; static srfBspSurface_t b[8];
    static srfVert_t v[8][4]; static glIndex_t ix[8][6]; static shader_t sh[8];
    const float wallSlope = 1.0f/24.0f;
    static const float xyz[8][4][3] = {
      {{12,-6,32},{24,6,32},{24,6,64},{12,-6,64}},
      {{-4,-80,-64},{4,-80,128},{4,80,128},{-4,80,-64}},
      {{1,-1,1},{3,-1,1},{16,-1,30},{14,-1,31}},
      {{1,1,1},{14,1,31},{16,1,30},{3,1,1}},
      {{1,-1,1},{14,-1,31},{14,1,31},{1,1,1}},
      {{3,-1,1},{3,1,1},{16,1,30},{16,-1,30}},
      {{0,-10,0},{0,10,0},{0,10,20},{0,-10,20}},
      {{10,22,3},{12,22,3},{24,22,31},{22,22,31}}
    };
    int i,j,turn; dlight_t dl;
    for(turn=0;turn<8;++turn) {
      float a=turn*.77f,cs=cosf(a),sn=sinf(a);
      TestReadyScene();R_IFLC_ResetFixtures();memset(s,0,sizeof(s));memset(b,0,sizeof(b));memset(v,0,sizeof(v));memset(sh,0,sizeof(sh));
      memset(s_iflcOwners,0,sizeof(s_iflcOwners));memset(s_iflcSurfaces,0,sizeof(s_iflcSurfaces));
      testWorld.surfaces=s;testWorld.numWorldSurfaces=testWorld.numsurfaces=8;
      for(i=0;i<8;++i) {
        s[i].data=(surfaceType_t*)&b[i];s[i].shader=&sh[i];sh[i].sort=SS_OPAQUE;
        Q_strncpyz(sh[i].name,i?"opaque/any_material":"fx/flame",sizeof(sh[i].name));
        b[i].surfaceType=SF_FACE;b[i].numVerts=4;b[i].numIndexes=6;b[i].verts=v[i];b[i].indexes=ix[i];
        for(j=0;j<4;++j) {float z=xyz[i][j][2],x=xyz[i][j][0],y=xyz[i][j][1];
          if(i==1 || i==6)x=z*wallSlope;
          VectorSet(v[i][j].xyz,x*cs-y*sn+turn*200,y*cs+x*sn-turn*125,z+turn*15);
        }
        ix[i][0]=0;ix[i][1]=1;ix[i][2]=2;ix[i][3]=0;ix[i][4]=2;ix[i][5]=3;
      }
      s_iflcReady=qtrue;s_iflcCatalogOverflow=qfalse;s_iflcOwnerCount=s_iflcSurfaceCount=1;
      s_iflcOwners[0].kind=IFLC_SURFACE;s_iflcOwners[0].surfaceCount=1;
      Q_strncpyz(s_iflcOwners[0].key,"surface:synthetic_shaft",sizeof(s_iflcOwners[0].key));
      VectorSet(s_iflcOwners[0].origin,18*cs+turn*200,18*sn-turn*125,48+turn*15);
      s_iflcSurfaces[0].owner=0;s_iflcSurfaces[0].surfaceIndex=0;
      memset(&dl,0,sizeof(dl));dl.iflcOptIn=qtrue;VectorCopy(s_iflcOwners[0].origin,dl.origin);
      CHECK(R_IFLC_ShadowFixture(&dl)==1,"slender tilted-wall torch recognised after arbitrary rotation/translation");
      CHECK(s_iflcFixtures[0].count==4,"only four connected shaft faces selected");
      tr.currentEntityNum=REFENTITYNUM_WORLD;tr.viewParms.flags=VPF_DEPTHSHADOW|VPF_SHADOWMAP;
      tr.viewParms.iflcFixture=1;tr.viewParms.iflcFixtureKey=R_IFLC_FixturePolicyKey(1);
      CHECK(!R_IFLC_SuppressSelfCaster(&s[1]),"sloped column remains a blocker");
      CHECK(!R_IFLC_SuppressSelfCaster(&s[6]),"small coplanar architecture fragment remains a blocker");
      CHECK(!R_IFLC_SuppressSelfCaster(&s[7]),"disconnected nearby geometry retained");
      for(i=2;i<=5;++i)CHECK(R_IFLC_SuppressSelfCaster(&s[i]),"own shaft face excluded");
      dl.iflcOptIn=qfalse;CHECK(R_IFLC_ShadowFixture(&dl)==0,"no native/promoted policy expansion");
      dl.iflcOptIn=qtrue;R_IFLC_ResetFixtures();sh[1].sort=SS_SEE_THROUGH;sh[6].sort=SS_SEE_THROUGH;
      CHECK(R_IFLC_ShadowFixture(&dl)==0,"suspended object without backing wall rejected");
      sh[1].sort=sh[6].sort=SS_OPAQUE;R_IFLC_ResetFixtures();s_iflcOwners[0].ambiguous=qtrue;
      CHECK(R_IFLC_ShadowFixture(&dl)==0,"ambiguous shaft rejected");
    }
    printf("CHECKED V1.2 slender torch: 8 transforms, slope, wall tile, unrelated geometry, hanging/native isolation\n");
}
