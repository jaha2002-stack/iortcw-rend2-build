#!/usr/bin/env python3
from pathlib import Path
import math, struct, zipfile, sys, json, hashlib

out = Path(sys.argv[1] if len(sys.argv) > 1 else "dist_assets/zz_DW_Destructible_Switches_V12_RTCW_ArtPass.pk3")
out.parent.mkdir(parents=True, exist_ok=True)

# DarkWolf Destructible Lights V1.2 - RTCW visual art pass.
# Asset-only update: model qpaths stay identical to V1.1 so game code/binaries remain unchanged.
# +X is authored out from the wall, matching V1.1 surface-normal placement.

METAL   = (0.02, 0.02, 0.48, 0.48)
BAKELITE= (0.52, 0.02, 0.98, 0.48)
STEEL   = (0.02, 0.52, 0.48, 0.98)
DARK    = (0.52, 0.52, 0.98, 0.98)

def uvrect(rect):
    u0,v0,u1,v1 = rect
    return ((u0,v0),(u1,v0),(u1,v1),(u0,v1))

def normal_code(n):
    x,y,z=n
    l=math.sqrt(x*x+y*y+z*z) or 1.0
    x,y,z=x/l,y/l,z/l
    lat=math.acos(max(-1,min(1,z)))
    lng=math.atan2(y,x)
    if lng<0: lng+=2*math.pi
    return ((int(lat*255/(2*math.pi))&255)<<8) | (int(lng*255/(2*math.pi))&255)

class Mesh:
    def __init__(self):
        self.v=[]; self.st=[]; self.tri=[]; self.norm=[]
    def quad(self,a,b,c,d,n,uv=uvrect(METAL)):
        base=len(self.v)
        self.v += [a,b,c,d]
        self.st += list(uv)
        self.norm += [n,n,n,n]
        self.tri += [(base,base+1,base+2),(base,base+2,base+3)]
    def box(self,c,size,rot_y=0.0,rot_x=0.0,rect=METAL):
        cx,cy,cz=c; sx,sy,sz=[q/2 for q in size]
        pts=[(-sx,-sy,-sz),(-sx,sy,-sz),(-sx,sy,sz),(-sx,-sy,sz),
             (sx,-sy,-sz),(sx,sy,-sz),(sx,sy,sz),(sx,-sy,sz)]
        ry=math.radians(rot_y); rx=math.radians(rot_x)
        def xf(p):
            x,y,z=p
            x,z=x*math.cos(ry)+z*math.sin(ry),-x*math.sin(ry)+z*math.cos(ry)
            y,z=y*math.cos(rx)-z*math.sin(rx),y*math.sin(rx)+z*math.cos(rx)
            return (x+cx,y+cy,z+cz)
        P=list(map(xf,pts))
        faces=[
            (4,5,6,7,(1,0,0)), (1,0,3,2,(-1,0,0)),
            (5,1,2,6,(0,1,0)), (0,4,7,3,(0,-1,0)),
            (7,6,2,3,(0,0,1)), (0,1,5,4,(0,0,-1))
        ]
        def nf(n):
            x,y,z=n
            x,z=x*math.cos(ry)+z*math.sin(ry),-x*math.sin(ry)+z*math.cos(ry)
            y,z=y*math.cos(rx)-z*math.sin(rx),y*math.sin(rx)+z*math.cos(rx)
            return (x,y,z)
        uv=uvrect(rect)
        for a,b,c_,d,n in faces: self.quad(P[a],P[b],P[c_],P[d],nf(n),uv)
    def cyl_x(self,c,length,radius,segments=12,rect=STEEL):
        cx,cy,cz=c; x0=cx-length/2; x1=cx+length/2
        u0,v0,u1,v1=rect
        for i in range(segments):
            a=2*math.pi*i/segments; b=2*math.pi*(i+1)/segments
            ya,za=cy+radius*math.cos(a),cz+radius*math.sin(a)
            yb,zb=cy+radius*math.cos(b),cz+radius*math.sin(b)
            n=(0,math.cos((a+b)/2),math.sin((a+b)/2))
            ua=u0+(u1-u0)*i/segments; ub=u0+(u1-u0)*(i+1)/segments
            side=((ua,v0),(ua,v1),(ub,v1),(ub,v0))
            self.quad((x0,ya,za),(x1,ya,za),(x1,yb,zb),(x0,yb,zb),n,side)
        for x,nx in ((x0,-1),(x1,1)):
            center=len(self.v)
            self.v.append((x,cy,cz)); self.st.append(((u0+u1)/2,(v0+v1)/2)); self.norm.append((nx,0,0))
            ring=[]
            for i in range(segments):
                a=2*math.pi*i/segments
                ring.append(len(self.v))
                self.v.append((x,cy+radius*math.cos(a),cz+radius*math.sin(a)))
                self.st.append(((u0+u1)/2+(u1-u0)*.46*math.cos(a),
                                (v0+v1)/2+(v1-v0)*.46*math.sin(a)))
                self.norm.append((nx,0,0))
            for i in range(segments):
                j=(i+1)%segments
                self.tri.append((center,ring[j],ring[i]) if nx<0 else (center,ring[i],ring[j]))
    def screw(self,y,z,x=3.0,r=1.15):
        self.cyl_x((x,y,z),1.4,r,10,STEEL)

def model(kind,on):
    m=Mesh()
    if kind=="toggle":
        # Compact cast-metal plate + rounded dark bakelite body.
        m.box((1.0,0,0),(2.0,20,27),rect=METAL)
        for y in (-7.5,7.5):
            for z in (-10.8,10.8): m.screw(y,z,2.5,1.0)
        m.cyl_x((4.1,0,0),4.2,6.4,18,BAKELITE)
        m.cyl_x((6.6,0,0),1.8,3.1,14,STEEL)
        # Short chunky toggle blade remains readable from the front in both states.
        ang=-32 if on else 32
        z=2.7 if on else -2.7
        m.box((9.0,0,z),(5.8,3.0,5.2),rot_y=ang,rect=STEEL)
        tipz=4.9 if on else -4.9
        m.cyl_x((11.8,0,tipz),2.4,1.75,12,BAKELITE)
        # Small recessed name/inspection plate keeps the silhouette RTCW-like.
        m.box((2.35,0,-9.0),(0.8,8.0,2.5),rect=DARK)

    elif kind=="knife":
        # Heavy industrial lever box for Factory/basement environments.
        m.box((1.2,0,0),(2.4,22,31),rect=METAL)
        for y in (-8.5,8.5):
            for z in (-12.0,12.0): m.screw(y,z,2.8,1.0)
        m.box((3.0,0,0),(1.5,14.5,23.0),rect=DARK)
        # Porcelain/metal stand-offs and copper contact blocks.
        m.cyl_x((5.0,0,-7.8),4.8,2.55,14,STEEL)
        m.cyl_x((5.0,0, 8.0),4.8,2.55,14,STEEL)
        m.box((7.0,0,-7.8),(2.0,5.2,3.4),rect=STEEL)
        m.box((7.0,0, 8.0),(2.0,5.2,3.4),rect=STEEL)
        # Blade rotates in the wall plane; ON = near vertical closed contact.
        a=0 if on else -34
        m.box((8.1,0,0.1),(2.4,3.0,17.0),rot_x=a,rect=STEEL)
        topy=-8.0*math.sin(math.radians(a))
        topz= 8.0*math.cos(math.radians(a))
        m.cyl_x((9.7,topy,topz),3.0,2.15,12,BAKELITE)
        # Bottom cable gland.
        m.cyl_x((3.0,0,-14.7),3.5,2.2,12,DARK)

    elif kind=="rotary":
        # Cast-metal selector with black phenolic dial.
        m.box((1.0,0,0),(2.0,22,22),rect=METAL)
        for y in (-8.0,8.0):
            for z in (-8.0,8.0): m.screw(y,z,2.5,0.95)
        m.cyl_x((3.7,0,0),3.0,8.0,20,STEEL)
        m.cyl_x((5.8,0,0),2.8,6.5,20,DARK)
        # Thick bakelite pointer: OFF vertical, ON rotated clockwise.
        a=-55 if on else 0
        m.box((8.0,0,0),(2.3,3.4,11.5),rot_x=a,rect=BAKELITE)
        m.cyl_x((9.4,0,0),1.5,1.2,10,STEEL)
        # Two tiny raised stop marks.
        m.box((7.0,-5.2,5.6),(1.2,1.2,2.8),rect=STEEL)
        m.box((7.0,-6.4,-1.6),(1.2,1.2,2.8),rot_x=-55,rect=STEEL)
    return m

def md3_bytes(name,shader,m):
    verts=m.v
    mins=[min(p[i] for p in verts) for i in range(3)]
    maxs=[max(p[i] for p in verts) for i in range(3)]
    radius=max(math.sqrt(sum(c*c for c in p)) for p in verts)
    frame=struct.pack("<3f3f3ff16s",*mins,*maxs,0,0,0,radius,b"frame0\0"+b"\0"*9)
    tri=b"".join(struct.pack("<3i",*t) for t in m.tri)
    sh=shader.encode("ascii")[:63]+b"\0"; sh+=b"\0"*(64-len(sh))
    shaders=struct.pack("<64si",sh,0)
    st=b"".join(struct.pack("<2f",u,v) for u,v in m.st)
    xyz=b""
    for p,n in zip(m.v,m.norm):
        q=[max(-32768,min(32767,int(round(c*64)))) for c in p]
        xyz += struct.pack("<3hH",q[0],q[1],q[2],normal_code(n))
    SH=108; ofs_tri=SH; ofs_shader=ofs_tri+len(tri); ofs_st=ofs_shader+len(shaders)
    ofs_xyz=ofs_st+len(st); ofs_end=ofs_xyz+len(xyz)
    surf_name=name.encode("ascii")[:63]+b"\0"; surf_name+=b"\0"*(64-len(surf_name))
    surf=struct.pack("<4s64s10i",b"IDP3",surf_name,0,1,1,len(m.v),len(m.tri),
                     ofs_tri,ofs_shader,ofs_st,ofs_xyz,ofs_end)+tri+shaders+st+xyz
    H=108; ofs_frames=H; ofs_tags=ofs_frames+len(frame); ofs_surfs=ofs_tags
    ofs_end_file=ofs_surfs+len(surf)
    nm=name.encode("ascii")[:63]+b"\0"; nm+=b"\0"*(64-len(nm))
    hdr=struct.pack("<4si64s9i",b"IDP3",15,nm,0,1,0,1,0,
                    ofs_frames,ofs_tags,ofs_surfs,ofs_end_file)
    return hdr+frame+surf

def patch_color(kind, patch):
    palettes={
      "toggle":{
        0:(69,72,64),   # aged field-gray/olive metal
        1:(55,36,27),   # dark brown bakelite
        2:(99,96,84),  # dark dull nickel/steel
        3:(31,32,29),   # near-black enamel
      },
      "knife":{
        0:(74,78,67),
        1:(49,32,24),
        2:(105,99,82),
        3:(39,42,36),
      },
      "rotary":{
        0:(65,69,64),
        1:(48,34,27),
        2:(96,94,84),
        3:(27,29,28),
      }
    }
    return palettes[kind][patch]

def tga(kind):
    w=h=128
    hdr=bytearray(18); hdr[2]=2; hdr[12]=w&255; hdr[13]=w>>8
    hdr[14]=h&255; hdr[15]=h>>8; hdr[16]=24; hdr[17]=0x20
    pix=bytearray()
    seed={"toggle":11,"knife":23,"rotary":37}[kind]
    for y in range(h):
        for x in range(w):
            patch=(1 if x>=64 else 0) + (2 if y>=64 else 0)
            base=list(patch_color(kind,patch))
            lx=x%64; ly=y%64
            # Low-frequency mottling and restrained RTCW-style grime.
            grain=((x*17+y*31+seed*13)%17)-8
            grime=((x*7+y*11+seed)%29)==0
            edge=min(lx,ly,63-lx,63-ly)
            if edge<3:
                base=[min(255,int(v*1.10)+6) for v in base]
            elif edge<7:
                base=[max(0,int(v*0.94)) for v in base]
            # Worn scratches, sparse and directional, not procedural noise soup.
            scratch=((x*5+y*3+seed)%97==0) or ((x+2*y+seed)%131==0)
            if scratch:
                base=[min(255,int(v*1.18)+5) for v in base]
            if grime:
                base=[max(0,int(v*0.82)) for v in base]
            base=[max(0,min(255,v+grain//2)) for v in base]
            pix.extend((base[2],base[1],base[0]))
    return bytes(hdr)+bytes(pix)

files={}
shader_lines=[]
stats={}
for kind in ("toggle","knife","rotary"):
    shader=f"models/darkwolf/switches/{kind}"
    shader_lines += [
        shader,
        "{",
        "    cull disable",
        "    {",
        f"        map models/darkwolf/switches/{kind}.tga",
        "        rgbGen lightingDiffuse",
        "    }",
        "}",
        ""
    ]
    files[f"models/darkwolf/switches/{kind}.tga"]=tga(kind)
    stats[kind]={}
    for state in ("on","off"):
        m=model(kind,state=="on")
        data=md3_bytes(f"dw_{kind}_{state}",shader,m)
        files[f"models/darkwolf/switches/{kind}_{state}.md3"]=data
        stats[kind][state]={"verts":len(m.v),"triangles":len(m.tri),"bytes":len(data)}

files["scripts/dw_destructible_switches_v12.shader"]=("\n".join(shader_lines)+"\n").encode("ascii")
manifest={
  "feature":"DarkWolf Destructible Lights V1.2.1 RTCW Art Pass Visibility Fix",
  "base_mechanics":"V1.1 Run #43347815867 unchanged",
  "asset_only":True,
  "texture_size":"128x128",
  "palette":"muted RTCW field-gray/olive, dark bakelite, dull steel",
  "model_qpaths_unchanged":True,
  "shader_visibility_fix":"valid nested stage + lightingDiffuse + cull disable",
  "stats":stats
}
files["docs/DW_SWITCHES_V12_MANIFEST.json"]=(json.dumps(manifest,indent=2)+"\n").encode("utf-8")

with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(files.items()):
        z.writestr(name,data)

with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    names=set(z.namelist())
    assert "scripts/dw_destructible_switches_v12.shader" in names
    for kind in ("toggle","knife","rotary"):
        tb=z.read(f"models/darkwolf/switches/{kind}.tga")
        assert len(tb)>128*128*3
        assert struct.unpack_from("<H",tb,12)[0]==128
        assert struct.unpack_from("<H",tb,14)[0]==128
        for state in ("on","off"):
            b=z.read(f"models/darkwolf/switches/{kind}_{state}.md3")
            assert b[:4]==b"IDP3"
            assert struct.unpack_from("<i",b,4)[0]==15
            assert len(b)>1500

print("DW_SWITCH_MODELS_V12_RTCW_ARTPASS_GENERATED",out,len(files))
print(json.dumps(manifest,sort_keys=True))
print("SHA256",hashlib.sha256(out.read_bytes()).hexdigest())
