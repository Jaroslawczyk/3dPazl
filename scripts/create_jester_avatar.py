"""Build the jester avatar from the supplied multi-view design in 3dPazl projects/."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "projects" / "arlequin_roblox" / "export" / "arlequin_roblox.glb"
FACE = ROOT / "projects" / "arlequin_roblox" / "textures" / "face.png"

COLORS = {
    "skin": (239, 237, 232, 255), "hair": (30, 27, 29, 255),
    "red": (196, 34, 48, 255), "red_light": (229, 49, 60, 255),
    "blue": (37, 97, 181, 255), "blue_light": (55, 139, 232, 255),
    "gold": (245, 190, 28, 255), "gold_light": (255, 214, 52, 255),
    "white": (238, 240, 240, 255), "glove": (244, 244, 237, 255),
    "pink": (222, 90, 153, 255), "black": (20, 19, 21, 255),
}
scene = trimesh.Scene()


def add(mesh, color, name):
    mesh.visual.material = trimesh.visual.material.PBRMaterial(
        name=name, baseColorFactor=COLORS[color], metallicFactor=0.0, roughnessFactor=0.72
    )
    scene.add_geometry(mesh, geom_name=name, node_name=name)


def box(name, color, center, size):
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(center)
    add(mesh, color, name)


def ball(name, color, center, scale, subdivisions=2, rotation=None):
    mesh = trimesh.creation.icosphere(subdivisions=subdivisions, radius=1)
    mesh.apply_scale(scale)
    if rotation:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(rotation, (0, 0, 1)))
    mesh.apply_translation(center)
    add(mesh, color, name)


def rod(name, color, a, b, r0, r1=None, sides=10):
    a, b = np.asarray(a, float), np.asarray(b, float)
    axis = b - a
    length = np.linalg.norm(axis)
    if length < 1e-6:
        return
    unit = axis / length
    helper = np.array([0., 0., 1.]) if abs(unit[2]) < .9 else np.array([0., 1., 0.])
    u = np.cross(unit, helper); u /= np.linalg.norm(u)
    v = np.cross(unit, u)
    verts = []
    for p, r in ((a, r0), (b, r1 if r1 is not None else r0)):
        for i in range(sides):
            t = 2 * np.pi * i / sides
            verts.append(p + r * (np.cos(t) * u + np.sin(t) * v))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.extend(((i, j, sides + j), (i, sides + j, sides + i),
                      (0, j, (j + 1) % sides), (sides, sides + (j + 1) % sides, sides + j)))
    add(trimesh.Trimesh(vertices=verts, faces=faces, process=True), color, name)


def triangle(name, color, pts, z_front, depth=.012):
    # Flat, slightly raised costume/fur panels facing the character's front (+Z).
    v = np.asarray([[x, y, z_front] for x, y in pts] + [[x, y, z_front - depth] for x, y in pts], float)
    f = [(0, 1, 2), (5, 4, 3), (0, 3, 4), (0, 4, 1), (1, 4, 5), (1, 5, 2), (2, 5, 3), (2, 3, 0)]
    add(trimesh.Trimesh(vertices=v, faces=f, process=True), color, name)


def face_texture():
    im = Image.new("RGBA", (512, 512), (239, 237, 232, 255))
    d = ImageDraw.Draw(im)
    ink = (35, 32, 35, 255)
    # Large outlined eyes with a red/blue four-point jester-star in each iris.
    for cx in (153, 359):
        cy, rx, ry = 250, 96, 103
        d.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), fill=(250, 250, 246, 255), outline=ink, width=12)
        ir, iy = (cx + (5 if cx < 200 else -5)), cy + 6
        d.ellipse((ir-34, iy-36, ir+34, iy+36), fill=(34, 100, 183, 255), outline=ink, width=4)
        d.polygon([(ir,iy-42),(ir+13,iy-12),(ir+41,iy),(ir+13,iy+12),(ir,iy+42),(ir-13,iy+12),(ir-41,iy),(ir-13,iy-12)], fill=(213,44,58,255))
        d.ellipse((ir-8,iy-8,ir+8,iy+8), fill=(246,194,40,255))
        d.ellipse((cx-49,cy-60,cx-26,cy-37), fill=(255,255,255,255))
    # Slightly lowered eyelid on the right eye and worried brows.
    d.pieslice((281, 160, 438, 334), 195, 344, fill=(35,32,35,255))
    d.line([(80,150),(153,127),(218,148)], fill=ink, width=13)
    d.line([(297,147),(359,125),(435,152)], fill=ink, width=13)
    # Pink cheek circles and a tiny uncertain frown.
    d.ellipse((62, 345, 145, 399), fill=(225,104,163,225))
    d.ellipse((367, 345, 450, 399), fill=(225,104,163,225))
    d.arc((211, 365, 301, 445), 200, 340, fill=ink, width=11)
    FACE.parent.mkdir(parents=True, exist_ok=True)
    im.save(FACE)
    return im


def hat_half(side, color):
    # Slice one broad padded cap into clean left/right colour halves at its centre seam.
    source = trimesh.creation.icosphere(subdivisions=3, radius=1)
    source.apply_scale((.42, .29, .205))
    if side < 0:
        mesh = trimesh.intersections.slice_mesh_plane(source, [1, 0, 0], [0, 0, 0], cap=True)
    else:
        mesh = trimesh.intersections.slice_mesh_plane(source, [-1, 0, 0], [0, 0, 0], cap=True)
    mesh.apply_translation((0, 1.82, 0))
    add(mesh, color, f"jester_cap_{'left' if side < 0 else 'right'}")


# Body proportions follow the rounded, compact Roblox toy figure in the references.
# White block legs and mismatched shoes.
box("left_white_leg", "white", (-.135, .335, 0), (.225, .58, .27))
box("right_white_leg", "white", (.135, .335, 0), (.225, .58, .27))
box("left_knee_gold_band", "gold", (-.135, .405, .008), (.232, .075, .278))
box("right_knee_gold_band", "gold", (.135, .405, .008), (.232, .075, .278))
box("left_shin_white", "white", (-.135, .22, .006), (.215, .29, .263))
box("right_shin_white", "white", (.135, .22, .006), (.215, .29, .263))
box("left_ankle_gold", "gold", (-.135, .085, .01), (.222, .065, .275))
box("right_ankle_gold", "gold", (.135, .085, .01), (.222, .065, .275))
ball("left_blue_shoe", "blue", (-.135, .045, .035), (.13, .095, .17), 2)
ball("right_red_shoe", "red", (.135, .045, .035), (.13, .095, .17), 2)

# Two-tone puff shorts with gold hem and contrasting vertical panels.
box("shorts_left_blue", "blue", (-.13, .595, 0), (.26, .30, .32))
box("shorts_right_red", "red", (.13, .595, 0), (.26, .30, .32))
box("shorts_left_red_stripe", "red", (-.13, .585, .166), (.105, .27, .014))
box("shorts_right_blue_stripe", "blue", (.13, .585, .166), (.105, .27, .014))
box("shorts_gold_hem_left", "gold", (-.13, .45, .004), (.265, .045, .328))
box("shorts_gold_hem_right", "gold", (.13, .45, .004), (.265, .045, .328))

# Split jacket with central seam, gold collar and buttons.
box("jacket_left_blue", "blue", (-.132, .91, 0), (.264, .48, .31))
box("jacket_right_red", "red", (.132, .91, 0), (.264, .48, .31))
box("jacket_centre_seam", "gold", (0, .90, .162), (.018, .47, .018))
triangle("collar_left_gold", "gold", [(-.25,1.13),(-.015,1.07),(-.07,1.22)], .171)
triangle("collar_right_gold", "gold", [(.25,1.13),(.015,1.07),(.07,1.22)], .171)
for i, y in enumerate((.97, .77)):
    ball(f"gold_button_{i}", "gold_light", (0, y, .185), (.056, .056, .035), 3)
box("gold_waist_trim_left", "gold", (-.13, .677, .168), (.09, .035, .016))
box("gold_waist_trim_right", "gold", (.13, .677, .168), (.09, .035, .016))

# Two-colour sleeves, white forearms, gold cuffs, and simple open mitten hands.
for side, upper, cuff in ((-1, "blue", "blue"), (1, "red", "red")):
    shoulder = (side*.285, 1.075, 0)
    elbow = (side*.405, .905, 0)
    wrist = (side*.565, .705, 0)
    ball(f"shoulder_puff_{side}", upper, shoulder, (.145, .15, .145), 2, rotation=side*.22)
    rod(f"sleeve_upper_{side}", upper, shoulder, elbow, .105, .083)
    # Narrow opposite-colour stripe on each puff.
    rod(f"sleeve_stripe_{side}", "red" if side < 0 else "blue",
        (side*.32, 1.025, .018), (side*.38, .945, .018), .032, .029, 8)
    rod(f"forearm_{side}", "white", elbow, wrist, .083, .065)
    ball(f"gold_cuff_{side}", "gold", wrist, (.077, .047, .077), 1)
    hand = (side*.60, .635, .005)
    ball(f"glove_palm_{side}", "glove", hand, (.095, .09, .07), 1)
    # C-shaped hand: two curved fingers and an inward thumb leave a visible opening.
    for finger, dy in (("top", .055), ("bottom", -.055)):
        start = (side*.63, .64+dy, .04)
        mid = (side*.68, .635+dy*.55, .04)
        end = (side*.67, .60, .04)
        rod(f"glove_{finger}_finger_{side}", "glove", start, mid, .029, .027, 7)
        rod(f"glove_{finger}_tip_{side}", "glove", mid, end, .027, .021, 7)
    rod(f"glove_thumb_{side}", "glove", (side*.55,.60,.05), (side*.61,.595,.05), .03, .024, 7)

# Head and face texture card, framed by dark bobbed hair.
ball("hair_back", "hair", (0, 1.40, -.055), (.30, .31, .235), 3)
ball("head", "skin", (0, 1.40, .015), (.285, .30, .235), 3)
face = face_texture()
# A radial UV patch hugs the rounded head instead of floating as a square card.
rx, ry, rz, rings, sectors = .238, .235, .235, 18, 64
vertices, uvs, faces = [[0., 1.40, .015 + rz + .004]], [[.5, .5]], []
for ri in range(1, rings + 1):
    radius = ri / rings
    for si in range(sectors):
        theta = 2 * np.pi * si / sectors
        x, y = rx * radius * np.cos(theta), ry * radius * np.sin(theta)
        z = .015 + rz * np.sqrt(max(0., 1 - radius * radius)) + .004
        vertices.append([x, 1.40 + y, z])
        uvs.append([(x / rx + 1) / 2, (1 - y / ry) / 2])
for si in range(sectors):
    faces.append((0, 1 + si, 1 + (si + 1) % sectors))
for ri in range(1, rings):
    inner, outer = 1 + (ri - 1) * sectors, 1 + ri * sectors
    for si in range(sectors):
        sj = (si + 1) % sectors
        faces.extend(((inner + si, outer + si, outer + sj), (inner + si, outer + sj, inner + sj)))
face_mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
face_mesh.visual = trimesh.visual.texture.TextureVisuals(
    uv=np.asarray(uvs, dtype=float),
    material=trimesh.visual.material.PBRMaterial(name="painted_face", baseColorTexture=face, metallicFactor=0, roughnessFactor=.9)
)
scene.add_geometry(face_mesh, geom_name="painted_face", node_name="painted_face")
# Raised eye shapes keep the oversized cartoon expression legible on the curved head.
for side in (-1, 1):
    eye_x = side * .095
    ball(f"eye_outline_{side}", "hair", (eye_x,1.43,.251), (.112,.117,.012), 2)
    ball(f"eye_white_{side}", "white", (eye_x,1.43,.260), (.098,.103,.012), 2)
    ball(f"eye_iris_{side}", "blue", (eye_x,1.425,.271), (.044,.052,.009), 2)
    ball(f"eye_star_red_{side}", "red", (eye_x,1.425,.278), (.023,.032,.006), 1)
    ball(f"eye_glint_{side}", "white", (eye_x-.013,1.448,.281), (.012,.014,.005), 1)
    ball(f"cheek_{side}", "pink", (side*.19,1.335,.245), (.062,.031,.012), 2)
rod("worried_mouth_left", "black", (-.033,1.245,.251), (0,1.231,.251), .008, .008, 6)
rod("worried_mouth_right", "black", (0,1.231,.251), (.033,1.245,.251), .008, .008, 6)
for side in (-1, 1):
    triangle(f"bob_side_lock_{side}", "hair", [(side*.17,1.58),(side*.28,1.56),(side*.26,1.20)], .252, .05)
triangle(f"bang_{side}_outer", "hair", [(side*.07,1.61),(side*.20,1.62),(side*.16,1.49)], .246)
triangle(f"bang_{side}_inner", "hair", [(side*.01,1.61),(side*.11,1.62),(side*.04,1.52)], .248)

# Oversized split jester cap, drooping red/blue tails, gold brow band and pom-poms.
hat_half(-1, "blue_light")
hat_half(1, "red_light")
for side, col in ((-1,"red_light"),(1,"blue_light")):
    ball(f"hat_flop_{side}", col, (side*.34,1.72,.01), (.13,.24,.16), 2, rotation=side*.48)
    rod(f"hat_droop_{side}", col, (side*.36,1.74,.02), (side*.43,1.61,.02), .105, .075, 10)
    ball(f"hat_pom_{side}", "gold_light", (side*.435,1.57,.025), (.068,.068,.068), 3)
for i, (x0,y0,x1,y1) in enumerate(((-.34,1.59,-.27,1.66),(-.27,1.66,-.15,1.70),(-.15,1.70,0,1.705),(0,1.705,.15,1.70),(.15,1.70,.27,1.66),(.27,1.66,.34,1.59))):
    rod(f"gold_hat_band_{i}", "gold_light", (x0,y0,.205), (x1,y1,.205), .033, .033, 10)

OUT.parent.mkdir(parents=True, exist_ok=True)
scene.export(OUT, file_type="glb")
check = trimesh.load(OUT, force="scene")
tris = sum(len(m.faces) for m in check.geometry.values())
print(f"Wrote {OUT}: {tris:,} triangles, height {check.bounds[1,1]-check.bounds[0,1]:.3f} units")
