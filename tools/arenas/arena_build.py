"""Procedural Ugandan buildings and props for ChezaDodge arenas."""
import math
import random
from mathutils import Vector
import arena_lib as L


def gable_roof(name, w, d, h, overhang, mat, z):
    """Pitched roof with ridge along X."""
    hw, hd = w / 2 + overhang, d / 2 + overhang
    v = [(-hw, -hd, z), (hw, -hd, z), (hw, 0, z + h), (-hw, 0, z + h),
         (-hw, hd, z), (hw, hd, z)]
    f = [(0, 1, 2, 3), (3, 2, 5, 4)]
    return L.mesh_obj(name, v, f, mat)


def mono_roof(name, w, d, z_low, z_high, overhang, mat):
    hw, hd = w / 2 + overhang, d / 2 + overhang
    v = [(-hw, -hd, z_low), (hw, -hd, z_low), (hw, hd, z_high), (-hw, hd, z_high)]
    return L.mesh_obj(name, v, [(0, 1, 2, 3)], mat)


def house(name, mats, w=7.0, d=5.0, h=2.8, roof="gable", seed=0, door_side=-1):
    """Rural / suburban house: walls, iron-sheet roof, door, windows, gable ends."""
    rnd = random.Random(seed)
    parts = [L.box(name + "W", (w, d, h), (0, 0, h / 2), mats["wall"])]
    parts.append(L.box(name + "Plinth", (w + 0.1, d + 0.1, 0.35), (0, 0, 0.175), mats["plinth"]))
    if roof == "gable":
        rh = d * 0.28
        parts.append(gable_roof(name + "R", w, d, rh, 0.45, mats["roof"], h))
        # gable end infill
        for s in (-1, 1):
            v = [(s * w / 2, -d / 2, h), (s * w / 2, d / 2, h), (s * w / 2, 0, h + rh)]
            parts.append(L.mesh_obj(name + "G", v, [(0, 1, 2)], mats["wall"]))
    else:
        parts.append(mono_roof(name + "R", w, d, h + 0.1, h + 0.7, 0.4, mats["roof"]))
    y = door_side * (d / 2 + 0.02)
    parts.append(L.box(name + "Door", (0.95, 0.06, 2.05), (rnd.uniform(-w / 4, w / 4), y, 1.03), mats["door"]))
    for x in (-w / 2 + 1.1, w / 2 - 1.1):
        parts.append(L.box(name + "Win", (1.0, 0.06, 1.0), (x, y, 1.6), mats["window"]))
        parts.append(L.box(name + "Sill", (1.15, 0.12, 0.08), (x, y * 1.01, 1.06), mats["plinth"]))
    return L.join(parts, name)


def shop_row(name, mats, units=4, unit_w=4.0, d=6.0, h=3.4, seed=0, paints=None):
    """Kampala-style row of shops: painted fronts, verandah on poles, roller shutters."""
    rnd = random.Random(seed)
    parts = []
    w = units * unit_w
    parts.append(L.box(name + "Body", (w, d, h), (0, 0, h / 2), mats["wall"]))
    parts.append(L.box(name + "Parapet", (w, 0.25, 0.9), (0, -d / 2 - 0.1, h + 0.45), mats["wall"]))
    parts.append(mono_roof(name + "Roof", w, d, h + 0.2, h + 0.6, 0.1, mats["roof"]))
    # verandah slab + roof + poles
    parts.append(L.box(name + "Slab", (w, 2.2, 0.25), (0, -d / 2 - 1.1, 0.125), mats["slab"]))
    parts.append(mono_roof(name + "VRoof", w, 2.3, h - 0.35, h - 0.05, 0.0, mats["roof"]))
    parts[-1].location.y = -d / 2 - 1.15
    for i in range(units + 1):
        x = -w / 2 + i * unit_w
        parts.append(L.cylinder(name + "Pole", 0.06, 0.06, h - 0.35, (x, -d / 2 - 2.1, 0.25), mats["metal"], seg=6))
    paints = paints or [(0.85, 0.75, 0.2), (0.75, 0.15, 0.1), (0.2, 0.45, 0.7), (0.9, 0.9, 0.85), (0.3, 0.6, 0.3)]
    for i in range(units):
        x = -w / 2 + unit_w * (i + 0.5)
        pc = paints[rnd.randrange(len(paints))]
        pm = L.noisy(f"{name}Paint{i}", pc, tuple(c * 0.82 for c in pc), scale=3.0, rough=0.8, bump=0.1)
        parts.append(L.box(name + "Front", (unit_w - 0.1, 0.05, h - 0.1), (x, -d / 2 - 0.02, h / 2), pm))
        open_shop = rnd.random() < 0.6
        sh = mats["shop_dark"] if open_shop else mats["shutter"]
        parts.append(L.box(name + "Shutter", (unit_w * 0.62, 0.08, 2.4), (x, -d / 2 - 0.05, 1.45), sh))
        # signboard band above the opening (plain colour, no brands)
        sc = paints[rnd.randrange(len(paints))]
        parts.append(L.box(name + "Sign", (unit_w * 0.85, 0.1, 0.55), (x, -d / 2 - 0.08, h - 0.6),
                           L.flat(f"{name}Sign{i}", sc, rough=0.6)))
        if open_shop:
            # goods / crates in front
            for k in range(rnd.randint(1, 3)):
                parts.append(L.box(name + "Crate", (0.5, 0.4, 0.35),
                                   (x + rnd.uniform(-1.2, 1.2), -d / 2 - 0.7 - rnd.uniform(0, 0.8), 0.43),
                                   mats["crate"]))
    return L.join(parts, name)


def round_hut(name, wall, thatch, r=2.6, h=2.3, seed=0, door=None):
    parts = [L.cylinder(name + "W", r, r, h, (0, 0, 0), wall, seg=20)]
    cone = L.cylinder(name + "R", r + 0.7, 0.05, r * 1.15, (0, 0, h - 0.15), thatch, seg=20)
    parts.append(cone)
    if door:
        parts.append(L.box(name + "D", (0.9, 0.2, 1.8), (0, -r, 0.9), door))
    return L.join(parts, name)


def water_tank(name, tank_mat, metal, h_stand=0.0):
    parts = [L.cylinder(name, 0.85, 0.85, 1.9, (0, 0, h_stand), tank_mat, seg=20)]
    parts.append(L.cylinder(name + "Lid", 0.86, 0.3, 0.25, (0, 0, h_stand + 1.9), tank_mat, seg=20))
    if h_stand:
        for x, y in ((-0.6, -0.6), (0.6, -0.6), (0.6, 0.6), (-0.6, 0.6)):
            parts.append(L.box(name + "Leg", (0.08, 0.08, h_stand), (x, y, h_stand / 2), metal))
    return L.join(parts, name)


def power_pole(name, wood, height=9.0):
    parts = [L.cylinder(name, 0.13, 0.1, height, (0, 0, 0), wood, seg=8)]
    parts.append(L.box(name + "Arm", (1.6, 0.1, 0.1), (0, 0, height - 0.5), wood))
    return L.join(parts, name)


def wire(name, a, b, sag, mat, seg=16):
    """Cable between two points as a thin ribbon with catenary-ish sag."""
    a, b = Vector(a), Vector(b)
    v, f = [], []
    for i in range(seg + 1):
        t = i / seg
        p = a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))
        v.append(tuple(p + Vector((0, 0, 0.012))))
        v.append(tuple(p - Vector((0, 0, 0.012))))
    for i in range(seg):
        f.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    return L.mesh_obj(name, v, f, mat)


def boda(name, mats, seed=0):
    """Simple motorcycle taxi silhouette (frame, wheels, seat, tank)."""
    rnd = random.Random(seed)
    body = mats["body"][rnd.randrange(len(mats["body"]))]
    parts = []
    for y in (-0.65, 0.65):
        w = L.cylinder(name + "Wh", 0.32, 0.32, 0.1, (0.05, y, 0.32), mats["tyre"], seg=16,
                       rot=(0, math.radians(90), 0))
        w.location.x = -0.05
        parts.append(w)
    parts.append(L.box(name + "Frame", (0.12, 1.1, 0.12), (0, 0, 0.55), mats["metal"]))
    parts.append(L.box(name + "Tank", (0.3, 0.45, 0.25), (0, 0.2, 0.78), body))
    parts.append(L.box(name + "Seat", (0.3, 0.75, 0.12), (0, -0.3, 0.82), mats["seat"]))
    parts.append(L.box(name + "Fork", (0.06, 0.06, 0.65), (0, 0.62, 0.6), mats["metal"]))
    parts.append(L.box(name + "Bar", (0.7, 0.04, 0.04), (0, 0.55, 1.0), mats["metal"]))
    return L.join(parts, name)


def fence(name, pts, wood, rope, post_h=1.1, gap=3.0):
    """Wooden posts with a rope rail (as in the 0.7 arenas, but on the terrain)."""
    parts = []
    for i in range(len(pts) - 1):
        a, b = Vector(pts[i]), Vector(pts[i + 1])
        n = max(1, int((b - a).length / gap))
        for k in range(n):
            p = a.lerp(b, k / n)
            parts.append(L.cylinder(name + "P", 0.07, 0.06, post_h, tuple(p), wood, seg=6))
        top_a, top_b = a + Vector((0, 0, post_h * 0.85)), b + Vector((0, 0, post_h * 0.85))
        parts.append(wire(name + "Rope", top_a, top_b, 0.06, rope, seg=12))
    parts.append(L.cylinder(name + "P", 0.07, 0.06, post_h, tuple(pts[-1]), wood, seg=6))
    return L.join(parts, name)
