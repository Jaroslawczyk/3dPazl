"""Runs inside Blender: report version and which bundled add-ons the workshops can use."""
import json

import addon_utils
import bpy

WANTED = ["rigify", "io_scene_gltf2", "io_scene_fbx", "io_anim_bvh", "pose_library"]
names = {m.__name__.split(".")[-1] for m in addon_utils.modules()}
print("PAZL_RESULT " + json.dumps({"version": bpy.app.version_string, "addons": {a: a in names for a in WANTED}}))
