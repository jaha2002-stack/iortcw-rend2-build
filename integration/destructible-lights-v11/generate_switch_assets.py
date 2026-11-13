#!/usr/bin/env python3
from pathlib import Path
import math, struct, zipfile, sys

out=Path(sys.argv[1] if len(sys.argv)>1 else "dist_assets/zz_DW_Destructible_Switches_V11.pk3")
out.parent.mkdir(parents=True,exist_ok=True)

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
    def quad(self,a,b,c,d,n,uv=((0,0),(1,0),(1,1),(0,1))):
        base=len(self.v)
        self.v += [a,b,c,d]
        self.st += list(uv)
        self.norm += [n,n,n,n]
        self.tri += [(base,base+1,base+2),(base,base+2,base+3)]
    def box(self,c,size,rot_y=0,rot_x=0):
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
        # rotate normals as directions
        def nf(n):
            x,y,z=n
            x,z=x*math.cos(ry)+z*math.sin(ry),-x*math.sin(ry)+z*math.cos(ry)
            y,z=y*math.cos(rx)-z*math.sin(rx),y*math.sin(rx)+z*math.cos(rx)
            return (x,y,z)
        for a,b,c_,d,n in faces: self.quad(P[a],P[b],P[c_],P[d],nf(n))
    def cyl_x(self,c,length,radius,segments=12):
        cx,cy,cz=c; x0=cx-length/2; x1=cx+length/2
        for i in range(segments):
            a=2*math.pi*i/segments; b=2*math.pi*(i+1)/segments
            ya,za=cy+radius*math.cos(a),cz+radius*math.sin(a)
            yb,zb=cy+radius*math.cos(b),cz+radius*math.sin(b)
            n=(0,math.cos((a+b)/2),math.sin((a+b)/2))
            self.quad((x0,ya,za),(x1,ya,za),(x1,yb,zb),(x0,yb,zb),n)
        # caps
        for x,nx in ((x0,-1),(x1,1)):
            center=len(self.v)
            self.v.append((x,cy,cz)); self.st.append((.5,.5)); self.norm.append((nx,0,0))
            ring=[]
            for i in range(segments):
                a=2*math.pi*i/segments
                ring.append(len(self.v))
                self.v.append((x,cy+radius*math.cos(a),cz+radius*math.sin(a)))
                self.st.append((.5+.5*math.cos(a),.5+.5*math.sin(a)))
                self.norm.append((nx,0,0))
            for i in range(segments):
                j=(i+1)%segments
                self.tri.append((center,ring[j],ring[i]) if nx<0 else (center,ring[i],ring[j]))

def model(kind,on):
    m=Mesh()
    if kind=="toggle":
        m.box((1.0,0,0),(2.0,18,26))
        m.box((3.0,0,0),(4.0,8,9))
        ang=-34 if on else 34
        z=4.5 if on else -4.5
        m.box((8.0,0,z),(11,3.2,3.2),rot_y=ang)
    elif kind=="knife":
        m.box((1.0,0,0),(2.0,20,30))
        m.cyl_x((4.0,0,-7),5,3.2,10)
        m.cyl_x((4.0,0,8),5,3.2,10)
        ang=-55 if on else -10
        z=1.5 if on else -4.5
        m.box((7.0,0,z),(18,3.0,3.0),rot_y=ang)
        m.box((11.5,0,10.0 if on else 1.0),(5,5,4))
    elif kind=="rotary":
        m.box((1.0,0,0),(2.0,20,20))
        m.cyl_x((4.0,0,0),6,6.5,16)
        # pointer bar lies on knob face; rotate around X between vertical and diagonal
        m.box((8.0,0,0),(2.5,2.5,11),rot_x=(0 if on else 90))
    return m

def md3_bytes(name,shader,m):
    verts=m.v
    mins=[min(p[i] for p in verts) for i in range(3)]
    maxs=[max(p[i] for p in verts) for i in range(3)]
    radius=max(math.sqrt(sum(c*c for c in p)) for p in verts)
    frame=struct.pack("<3f3f3ff16s",*mins,*maxs,0,0,0,radius,b"frame0\0"+b"\0"*9)

    tri=b"".join(struct.pack("<3i",*t) for t in m.tri)
    sh=shader.encode("ascii")[:63]+b"\0"
    sh=sh+b"\0"*(64-len(sh))
    shaders=struct.pack("<64si",sh,0)
    st=b"".join(struct.pack("<2f",u,v) for u,v in m.st)
    xyz=b""
    for p,n in zip(m.v,m.norm):
        q=[max(-32768,min(32767,int(round(c*64)))) for c in p]
        xyz += struct.pack("<3hH",q[0],q[1],q[2],normal_code(n))

    SH=108
    ofs_tri=SH
    ofs_shader=ofs_tri+len(tri)
    ofs_st=ofs_shader+len(shaders)
    ofs_xyz=ofs_st+len(st)
    ofs_end=ofs_xyz+len(xyz)
    surf_name=name.encode("ascii")[:63]+b"\0"
    surf_name+=b"\0"*(64-len(surf_name))
    surf=struct.pack("<4s64s10i",b"IDP3",surf_name,0,1,1,len(m.v),len(m.tri),
                     ofs_tri,ofs_shader,ofs_st,ofs_xyz,ofs_end)+tri+shaders+st+xyz

    H=108
    ofs_frames=H
    ofs_tags=ofs_frames+len(frame)
    ofs_surfs=ofs_tags
    ofs_end_file=ofs_surfs+len(surf)
    nm=name.encode("ascii")[:63]+b"\0"; nm+=b"\0"*(64-len(nm))
    hdr=struct.pack("<4si64s9i",b"IDP3",15,nm,0,1,0,1,0,
                    ofs_frames,ofs_tags,ofs_surfs,ofs_end_file)
    return hdr+frame+surf

def tga(base,border,accent):
    w=h=64
    hdr=bytearray(18); hdr[2]=2; hdr[12]=w&255; hdr[13]=w>>8; hdr[14]=h&255; hdr[15]=h>>8; hdr[16]=24; hdr[17]=0x20
    pix=bytearray()
    for y in range(h):
        for x in range(w):
            c=list(base)
            if x<5 or y<5 or x>=59 or y>=59: c=list(border)
            if (x-10)**2+(y-10)**2<9 or (x-53)**2+(y-10)**2<9 or (x-10)**2+(y-53)**2<9 or (x-53)**2+(y-53)**2<9:
                c=list(accent)
            grain=((x*17+y*31)%13)-6
            c=[max(0,min(255,v+grain)) for v in c]
            pix.extend((c[2],c[1],c[0]))
    return bytes(hdr)+bytes(pix)

types={
    "toggle":((78,58,40),(32,27,22),(185,170,135)),
    "knife":((150,142,112),(52,48,40),(190,70,45)),
    "rotary":((42,47,49),(18,20,21),(210,195,145)),
}
shader_lines=[]
files={}
for kind,(base,border,accent) in types.items():
    shader=f"models/darkwolf/switches/{kind}"
    shader_lines += [shader,"{",f"    map models/darkwolf/switches/{kind}.tga","    rgbGen identity","}",""]
    files[f"models/darkwolf/switches/{kind}.tga"]=tga(base,border,accent)
    for state in ("on","off"):
        m=model(kind,state=="on")
        files[f"models/darkwolf/switches/{kind}_{state}.md3"]=md3_bytes(f"dw_{kind}_{state}",shader,m)

files["scripts/dw_destructible_switches_v11.shader"]=("\n".join(shader_lines)+"\n").encode("ascii")
with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(files.items()):
        z.writestr(name,data)

# self-verification
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for kind in types:
        for state in ("on","off"):
            b=z.read(f"models/darkwolf/switches/{kind}_{state}.md3")
            assert b[:4]==b"IDP3"
            assert struct.unpack_from("<i",b,4)[0]==15
print("DW_SWITCH_MODELS_V11_GENERATED",out,len(files))
