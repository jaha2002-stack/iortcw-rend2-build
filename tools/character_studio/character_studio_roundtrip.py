#!/usr/bin/env python3
# DARKWOLF_RTCW_CHARACTER_STUDIO_V0_1
#
# Blender headless MDS round-trip validator for DarkWolfRTCW.
# Runs inside Blender 2.93.x with RtCW:ET Blender Model Tools on sys.path.

import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def studio_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    if len(argv) < 2:
        raise SystemExit(
            "usage: blender --background --python character_studio_roundtrip.py "
            "-- <input.mds> <output_dir> [bind_frame]"
        )
    return Path(argv[0]).resolve(), Path(argv[1]).resolve(), int(argv[2]) if len(argv) > 2 else 0


def install_addon_path():
    root = os.environ.get("REMT_REPO_ROOT", "")
    if not root:
        raise RuntimeError("REMT_REPO_ROOT is not set")
    addon_path = Path(root).resolve() / "src" / "addons"
    if not addon_path.is_dir():
        raise RuntimeError("RtCW:ET addon path not found: {}".format(addon_path))
    sys.path.insert(0, str(addon_path))
    return addon_path


def summarize(mdi):
    surfaces = len(mdi.surfaces)
    vertices = sum(len(s.vertices) for s in mdi.surfaces)
    triangles = sum(len(s.triangles) for s in mdi.surfaces)
    bones = len(mdi.skeleton.bones) if mdi.skeleton else 0
    tags = len(mdi.tags)
    frames = 0
    if mdi.skeleton and mdi.skeleton.bones:
        frames = len(mdi.skeleton.bones[0].locations)
    elif mdi.bounds and getattr(mdi.bounds, "aabbs", None):
        frames = len(mdi.bounds.aabbs)

    return {
        "name": mdi.name,
        "surfaces": surfaces,
        "vertices": vertices,
        "triangles": triangles,
        "bones": bones,
        "tags": tags,
        "frames": frames,
        "surface_names": [s.name for s in mdi.surfaces],
        "bone_names": [b.name for b in mdi.skeleton.bones] if mdi.skeleton else [],
        "tag_names": [t.name for t in mdi.tags],
    }


def recursive_layer_collection(layer_collection, target_collection):
    if layer_collection.collection == target_collection:
        return layer_collection
    for child in layer_collection.children:
        found = recursive_layer_collection(child, target_collection)
        if found:
            return found
    return None


def set_active_collection(collection):
    layer = recursive_layer_collection(bpy.context.view_layer.layer_collection, collection)
    if not layer:
        raise RuntimeError("Imported collection has no LayerCollection")
    bpy.context.view_layer.active_layer_collection = layer


def collection_bbox(collection):
    points = []
    for obj in collection.all_objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        raise RuntimeError("No mesh bounds available for preview")

    mins = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maxs = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return mins, maxs


def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_preview_material():
    mat = bpy.data.materials.new("DarkWolf_CharacterStudio_Clay")
    mat.diffuse_color = (0.24, 0.27, 0.25, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.24, 0.27, 0.25, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.72
        bsdf.inputs["Specular"].default_value = 0.25
    return mat


def setup_preview_scene(collection, out_dir):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.025, 0.028, 0.03, 1.0)
        bg.inputs["Strength"].default_value = 0.7

    clay = make_preview_material()
    bpy.context.view_layer.material_override = clay

    mins, maxs = collection_bbox(collection)
    center = (mins + maxs) * 0.5
    size = max((maxs - mins).x, (maxs - mins).y, (maxs - mins).z)
    distance = max(64.0, size * 1.85)

    camera_data = bpy.data.cameras.new("CharacterStudioCamera")
    camera = bpy.data.objects.new("CharacterStudioCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 58

    key_data = bpy.data.lights.new("CharacterStudioKey", "AREA")
    key = bpy.data.objects.new("CharacterStudioKey", key_data)
    bpy.context.scene.collection.objects.link(key)
    key.location = center + Vector((-distance * 0.65, -distance * 0.7, distance * 0.9))
    key_data.energy = 1300
    key_data.size = max(32.0, size * 0.65)
    look_at(key, center)

    fill_data = bpy.data.lights.new("CharacterStudioFill", "AREA")
    fill = bpy.data.objects.new("CharacterStudioFill", fill_data)
    bpy.context.scene.collection.objects.link(fill)
    fill.location = center + Vector((distance * 0.75, -distance * 0.15, distance * 0.45))
    fill_data.energy = 650
    fill_data.size = max(32.0, size * 0.8)
    look_at(fill, center)

    rim_data = bpy.data.lights.new("CharacterStudioRim", "AREA")
    rim = bpy.data.objects.new("CharacterStudioRim", rim_data)
    bpy.context.scene.collection.objects.link(rim)
    rim.location = center + Vector((0.0, distance * 0.8, distance * 0.75))
    rim_data.energy = 1000
    rim_data.size = max(24.0, size * 0.55)
    look_at(rim, center)

    camera_positions = {
        "front": center + Vector((0.0, -distance, size * 0.10)),
        "back": center + Vector((0.0, distance, size * 0.10)),
        "left": center + Vector((-distance, 0.0, size * 0.10)),
        "three_quarter": center + Vector((-distance * 0.70, -distance * 0.70, size * 0.12)),
    }

    preview_dir = out_dir / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    for name, location in camera_positions.items():
        camera.location = location
        look_at(camera, center)
        scene.render.filepath = str(preview_dir / (name + ".png"))
        bpy.ops.render.render(write_still=True)


def compare_roundtrip(before, after):
    strict_keys = ("surfaces", "vertices", "triangles", "bones", "tags", "frames")
    mismatches = {}
    for key in strict_keys:
        if before[key] != after[key]:
            mismatches[key] = {"before": before[key], "after": after[key]}
    if before["surface_names"] != after["surface_names"]:
        mismatches["surface_names"] = {
            "before": before["surface_names"],
            "after": after["surface_names"],
        }
    if before["bone_names"] != after["bone_names"]:
        mismatches["bone_names"] = {
            "before": before["bone_names"],
            "after": after["bone_names"],
        }
    if before["tag_names"] != after["tag_names"]:
        mismatches["tag_names"] = {
            "before": before["tag_names"],
            "after": after["tag_names"],
        }
    return mismatches


def main():
    input_mds, out_dir, bind_frame = studio_args()
    if not input_mds.is_file():
        raise RuntimeError("Input MDS does not exist: {}".format(input_mds))
    out_dir.mkdir(parents=True, exist_ok=True)

    addon_path = install_addon_path()
    import rtcw_et_model_tools.common.reporter as reporter_m
    import rtcw_et_model_tools.mds.facade as mds_facade_m
    import rtcw_et_model_tools.blender.core.collection as collection_m

    reporter_m.init()
    bpy.ops.wm.read_factory_settings(use_empty=True)

    mdi_in = mds_facade_m.read(str(input_mds), bind_frame)
    before = summarize(mdi_in)
    if before["surfaces"] <= 0 or before["vertices"] <= 0:
        raise RuntimeError("Imported MDS has no renderable geometry")
    if before["bones"] <= 0 or before["frames"] <= 0:
        raise RuntimeError("Imported MDS has no usable skeleton/frames")

    collection = collection_m.write(mdi_in)
    set_active_collection(collection)

    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_end = max(0, before["frames"] - 1)
    scene.frame_set(min(bind_frame, scene.frame_end))

    # Save the unmodified imported working scene before any export.
    blend_path = out_dir / "roundtrip_work.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    # Export back through the exact MDI->MDS path.
    roundtrip_path = out_dir / "roundtrip_body.mds"
    mdi_from_blender, collapse_frame = collection_m.read(0)
    mds_facade_m.write(mdi_from_blender, str(roundtrip_path), collapse_frame)

    mdi_check = mds_facade_m.read(str(roundtrip_path), bind_frame)
    after = summarize(mdi_check)
    mismatches = compare_roundtrip(before, after)

    audit = {
        "studio": "DARKWOLF_RTCW_CHARACTER_STUDIO_V0_1",
        "blender": bpy.app.version_string,
        "addon_path": str(addon_path),
        "input_mds": str(input_mds),
        "bind_frame": bind_frame,
        "before": before,
        "after": after,
        "mismatches": mismatches,
        "roundtrip_pass": not bool(mismatches),
    }
    (out_dir / "roundtrip_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "DARKWOLF RTCW CHARACTER STUDIO V0.1",
        "====================================",
        "Blender: {}".format(bpy.app.version_string),
        "Input: {}".format(input_mds),
        "Surfaces: {} -> {}".format(before["surfaces"], after["surfaces"]),
        "Vertices: {} -> {}".format(before["vertices"], after["vertices"]),
        "Triangles: {} -> {}".format(before["triangles"], after["triangles"]),
        "Bones: {} -> {}".format(before["bones"], after["bones"]),
        "Tags: {} -> {}".format(before["tags"], after["tags"]),
        "Frames: {} -> {}".format(before["frames"], after["frames"]),
        "Result: {}".format("PASS" if not mismatches else "FAIL"),
    ]
    if mismatches:
        lines.append("Mismatches: {}".format(json.dumps(mismatches, ensure_ascii=False)))
    (out_dir / "ROUNDTRIP_AUDIT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Render only after the untouched geometry has already been exported.
    setup_preview_scene(collection, out_dir)

    if mismatches:
        raise RuntimeError("Strict MDS round-trip validation failed: {}".format(mismatches))

    print("DARKWOLF_CHARACTER_STUDIO_ROUNDTRIP_PASS")


if __name__ == "__main__":
    main()
