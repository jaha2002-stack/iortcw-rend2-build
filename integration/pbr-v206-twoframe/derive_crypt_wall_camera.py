#!/usr/bin/env python3
import sys, zipfile, struct, math, re, pathlib, json

root = pathlib.Path(sys.argv[1])
out_json = pathlib.Path(sys.argv[2])
out_env = pathlib.Path(sys.argv[3])

bsp = None
source_pk3 = None
for pk3 in sorted(root.glob("*.pk3")):
    try:
        with zipfile.ZipFile(pk3) as z:
            for n in z.namelist():
                if n.lower() == "maps/crypt1.bsp":
                    bsp = z.read(n)
                    source_pk3 = pk3.name
                    break
    except zipfile.BadZipFile:
        continue
    if bsp:
        break

if not bsp or bsp[:4] != b"IBSP":
    raise SystemExit("crypt1.bsp not found or invalid")

lumps = [struct.unpack_from("<ii", bsp, 8 + i * 8) for i in range(17)]
def lump(i):
    off, length = lumps[i]
    return bsp[off:off + length]

entity_text = lump(0).split(b"\0", 1)[0].decode("latin1", "ignore")
fires = []
for block in re.findall(r"\{([^}]*)\}", entity_text, re.S):
    kv = dict(re.findall(r'"([^"]+)"\s+"([^"]*)"', block))
    if "origin" not in kv:
        continue
    hay = " ".join((
        kv.get("classname", ""),
        kv.get("model", ""),
        kv.get("targetname", ""),
        kv.get("scriptName", ""),
    )).lower()
    if not any(k in hay for k in ("torch", "fire", "flame")):
        continue
    try:
        origin = [float(x) for x in kv["origin"].split()[:3]]
    except Exception:
        continue
    if len(origin) == 3:
        fires.append(origin)

shaders = lump(1)
verts = lump(10)
surfaces = lump(13)

shader_names = []
for off in range(0, len(shaders), 72):
    if off + 72 <= len(shaders):
        shader_names.append(shaders[off:off + 64].split(b"\0", 1)[0].decode("latin1").lower())

target = "textures/crypt/crypt_wall_03"
if target not in shader_names:
    raise SystemExit(f"shader missing from crypt1 BSP: {target}")
shader_index = shader_names.index(target)

candidates = []
for off in range(0, len(surfaces), 104):
    if off + 104 > len(surfaces):
        break
    s = struct.unpack_from("<12i3f9f2i", surfaces, off)
    if s[0] != shader_index:
        continue

    first_vert, num_verts = s[3], s[4]
    points, normals = [], []
    for j in range(num_verts):
        vo = (first_vert + j) * 44
        if vo + 44 > len(verts):
            break
        v = struct.unpack_from("<3f2f2f3f4B", verts, vo)
        points.append(v[:3])
        normals.append(v[7:10])
    if not points:
        continue

    center = [sum(p[k] for p in points) / len(points) for k in range(3)]
    normal = [sum(n[k] for n in normals) / len(normals) for k in range(3)]
    length = math.sqrt(sum(x * x for x in normal)) or 1.0
    normal = [x / length for x in normal]
    if abs(normal[2]) >= 0.65:
        continue

    fire_distance = min(
        (math.sqrt(sum((center[k] - f[k]) ** 2 for k in range(3))) for f in fires),
        default=999999.0,
    )
    candidates.append({
        "center": center,
        "normal": normal,
        "numVerts": num_verts,
        "numIndexes": s[6],
        "fireDistance": fire_distance,
    })

if not candidates:
    raise SystemExit("no vertical crypt_wall_03 surfaces found")

near = [c for c in candidates if c["fireDistance"] < 700.0] or candidates
selected = min(near, key=lambda c: (c["fireDistance"], -c["numVerts"], -c["numIndexes"]))
c = selected["center"]
n = selected["normal"]

camera = [c[0] + n[0] * 105.0, c[1] + n[1] * 105.0, c[2] + n[2] * 105.0 + 8.0]
yaw = math.degrees(math.atan2(c[1] - camera[1], c[0] - camera[0]))
if yaw < 0:
    yaw += 360.0

result = {
    "map": "crypt1",
    "shader": target,
    "sourcePk3": source_pk3,
    "fireEntityCount": len(fires),
    **selected,
    "camera": camera,
    "yaw": yaw,
}
out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
out_env.write_text(
    f"CRYPT_X={camera[0]:.3f}\n"
    f"CRYPT_Y={camera[1]:.3f}\n"
    f"CRYPT_Z={camera[2]:.3f}\n"
    f"CRYPT_YAW={yaw:.3f}\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2))
