#!/usr/bin/env python3
"""Compile the exact in-tree V6.1 C preview with narrow-LM-chart mock host."""
import sys
import subprocess
from pathlib import Path
src = Path(sys.argv[1]).read_text()
a = src.index('static void DWPS6_BakedPreview_f(void)\n{')
b = src.index('\nstatic void DWPS6_BakedCancel_f(void)', a)
preview = src[a:b]
assert 'DARKWOLF_UNIFIED_PCPS_V61_BAKED_ADAPTIVE_REFERENCE' in src[a-700:a]
header = r'''
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define Com_Memcpy memcpy
#define PRINT_WARNING 1
#define PRINT_ALL 0
#define GL_RGBA8 0x8058
#define GL_RGBA16 0x805B
typedef unsigned char byte;
typedef int qboolean;
static float Com_Clamp(float l,float h,float v){return v<l?l:v>h?h:v;}
typedef struct {int dummy;} msurface_t;
typedef struct {int width,height;} image_t;
typedef struct {msurface_t *surfaces;int numWorldSurfaces;} world_t;
static world_t world;
static msurface_t surfaces[1];
static image_t image;
static image_t*images[1];
static struct {world_t *world;int numLightmaps,fatLightmapCols,fatLightmapRows;image_t**lightmaps;}tr;
static byte srcPixel[128*128*8],gpu[128*128*8],dwps6Scratch[128*128*8];
static int dwps6TileSize=128,dwps6TileCount=1,dwps6PixelStride=4,dwps6BakedSelected=0;
static int dwps6BakedSurface=0,dwps6PreviewTile=-1,dwps6PreviewReady=0;
static float dwps6BakedUV[2]={49.5f,73.5f};
static byte *dwps6Base[1],*dwps6Work[1];
static int writes=0;
static void MockPrintf(int level,const char *fmt,...){(void)level;va_list ap;va_start(ap,fmt);vprintf(fmt,ap);va_end(ap);}
static int MockArgc(void){return 3;}
static const char*MockArgv(int i){return i==1?"7":i==2?"0.4":"dw_ps_baked_preview";}
static struct {int(*Cmd_Argc)(void);const char*(*Cmd_Argv)(int);void(*Printf)(int,const char*,...);} ri={MockArgc,MockArgv,MockPrintf};
static void DWPS_CheckWorld(void){}
static int DWPS6_Bytes(void){return dwps6TileSize*dwps6TileSize*dwps6PixelStride;}
static const byte*DWPS6_Current(int tile){return tile==0?srcPixel:NULL;}
static void DWPS6_BakedDiscardPreview(void){dwps6PreviewTile=-1;dwps6PreviewReady=0;}
static qboolean DWPS6_UvCovered(const msurface_t *s,float u,float v){
 (void)s;
 return u>49.0f/128 && u<50.0f/128 && v>73.0f/128 && v<74.0f/128;
}
static qboolean DWPS6_BakedUpload(int tile,const byte *data){
 if(tile!=0)return 0;
 memcpy(gpu,data,(size_t)DWPS6_Bytes());writes++;return 1;
}
'''
footer = r'''
int main(void){
 int i,p=(73*128+49)*4,q=(73*128+50)*4;
 tr.world=&world;tr.numLightmaps=1;tr.lightmaps=images;
 world.numWorldSurfaces=1;world.surfaces=surfaces;
 image.width=image.height=128;images[0]=&image;dwps6Base[0]=srcPixel;
 for(i=0;i<128*128;i++){srcPixel[4*i]=40;srcPixel[4*i+1]=30;srcPixel[4*i+2]=20;srcPixel[4*i+3]=255;}
 DWPS6_BakedPreview_f();
 if(!dwps6PreviewReady || writes!=1 || gpu[p]<=srcPixel[p])return 11;
 if(gpu[q]!=srcPixel[q] || gpu[q+1]!=srcPixel[q+1])return 12;
 puts("PASS V61_CRYPT1_NARROW_RGBA8_PREVIEW_AND_ATLAS_ISOLATION");
 dwps6PreviewTile=-1;dwps6PreviewReady=0;
 dwps6PixelStride=8;p=(73*128+49)*8;q=(73*128+50)*8;
 for(i=0;i<128*128;i++){
  unsigned short *t=(unsigned short*)(srcPixel+i*8);
  t[0]=4000;t[1]=3500;t[2]=2500;t[3]=65535;
 }
 DWPS6_BakedPreview_f();
 if(!dwps6PreviewReady || writes!=2 || ((unsigned short*)(gpu+p))[0]<=4000)return 13;
 if(((unsigned short*)(gpu+q))[0]!=4000)return 14;
 puts("PASS V61_CRYPT1_NARROW_RGBA16_PREVIEW_AND_ATLAS_ISOLATION");
 return 0;
}
'''
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
fp=out/'v61_native_exact.c';fp.write_text(header+preview+footer)
exe=out/'v61_native_exact'
subprocess.run(['gcc','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-Wno-unused-variable',str(fp),'-lm','-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
