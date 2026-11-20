"""Procedural East African plants for ChezaDodge arenas.

Foliage is built from alpha-masked leaf cards (see arena_lib.leaf_card) placed in
clump volumes around branch tips, with a dark core blob so crowns read as dense.
Each builder returns one joined object (a template); place copies with
arena_lib.instance() so the mesh is shared.
"""
import math
import random
from mathutils import Vector
import arena_lib as L

UP = Vector((0, 0, 1))


def _orient(ob, a, b):
    ob.rotation_euler = UP.rotation_difference((b - a).normalized()).to_euler()


def limb(name, a, b, r0, r1, mat, seg=7):
    a, b = Vector(a), Vector(b)
    ob = L.cylinder(name, r0, r1, (b - a).length, tuple(a), mat, seg=seg)
    _orient(ob, a, b)
    return ob


def leaf_cloud(name, clumps, n, mat, size=(0.5, 0.35), hang=0.0, flat=0.0, seed=0, shell=0.55):
    """Cards scattered in ellipsoid clumps [(centre, radii), ...].

    hang: 0 random orientation .. 1 cards hang straight down (eucalyptus).
    flat: 0 random .. 1 cards lie horizontal (acacia layers)."""
    rnd = random.Random(seed)
    vols = [r.x * r.y * r.z for _, r in clumps]
    tot = sum(vols)
    verts, faces, uvs = [], [], []
    for k in range(n):
        pick = rnd.uniform(0, tot)
        for (c, r), vol in zip(clumps, vols):
            pick -= vol
            if pick <= 0:
                break
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
        rr = shell + (1 - shell) * rnd.random() ** 0.5
        p = c + Vector((d.x * r.x, d.y * r.y, d.z * r.z)) * rr
        down = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
        if hang > 0:
            down = down.lerp(Vector((d.x * 0.3, d.y * 0.3, -1)).normalized(), hang).normalized()
        if flat > 0:
            down = down.lerp(Vector((d.x, d.y, 0)).normalized(), flat).normalized()
        side = down.cross(Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))))
        if flat > 0:
            side = side.lerp(down.cross(UP), flat)
        side.normalize()
        s = rnd.uniform(0.75, 1.25)
        ln, wd = size[0] * s, size[1] * s * 0.5
        a = p - side * wd
        b = p + side * wd
        i = len(verts)
        verts += [tuple(a), tuple(b), tuple(b + down * ln), tuple(a + down * ln)]
        faces.append((i, i + 1, i + 2, i + 3))
        uvs += [(0, 1), (1, 1), (1, 0), (0, 0)]
    ob = L.mesh_obj(name, verts, faces, mat)
    uvl = ob.data.uv_layers.new(name="UVMap")
    for li, loop in enumerate(ob.data.loops):
        uvl.data[li].uv = uvs[loop.vertex_index]
    return ob


def core(name, clumps, mat, scale=0.55, seed=0):
    return [L.blob(name, 1.0, tuple(c), mat, squash=tuple(r * scale), rough=0.3, seed=seed + i, subdiv=2)
            for i, (c, r) in enumerate(clumps)]


def eucalyptus(name, bark, cards, inner, height=22.0, seed=0, n_cards=1600):
    rnd = random.Random(seed)
    parts = []
    lean = Vector((rnd.uniform(-0.08, 0.08), rnd.uniform(-0.08, 0.08), 1)).normalized()
    pts = [Vector((0, 0, 0))]
    for s in range(5):
        step = lean * (height * 0.8 / 5)
        pts.append(pts[-1] + step + Vector((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), 0)))
    r = 0.30
    for a, b in zip(pts, pts[1:]):
        parts.append(limb(name + "T", a, b, r, r * 0.8, bark, seg=10))
        r *= 0.8
    clumps = []
    for k in range(9):
        t = rnd.uniform(0.45, 1.0)
        idx = min(4, int(t * 5))
        start = pts[idx].lerp(pts[idx + 1], t * 5 - idx)
        ang = rnd.uniform(0, 2 * math.pi)
        ln = rnd.uniform(2.0, 4.5) * (1.15 - t * 0.5)
        tip = start + Vector((math.cos(ang) * ln, math.sin(ang) * ln, ln * rnd.uniform(0.6, 1.1)))
        parts.append(limb(name + "B", start, tip, 0.1 * (1.2 - t * 0.5), 0.035, bark, seg=6))
        clumps.append((tip + Vector((0, 0, -0.6)), Vector((1, 1, 1.25)) * rnd.uniform(1.5, 2.3)))
    clumps.append((pts[-1] + Vector((0, 0, 1.0)), Vector((1.8, 1.8, 2.6))))
    parts += core(name + "C", clumps, inner, 0.32, seed)
    parts.append(leaf_cloud(name + "L", clumps, n_cards, cards, size=(0.6, 0.5), hang=0.55, seed=seed))
    return L.join(parts, name)


def banana(name, stem_mat, leaf_mat, height=2.6, leaves=8, seed=0):
    rnd = random.Random(seed)
    parts = [L.cylinder(name + "S", 0.14, 0.10, height, (0, 0, 0), stem_mat, seg=10)]
    for i in range(leaves):
        a = 2 * math.pi * i / leaves + rnd.uniform(-0.3, 0.3)
        out = Vector((math.cos(a), math.sin(a), 0))
        length = rnd.uniform(1.8, 2.5)
        rise = rnd.uniform(0.6, 1.3)
        pts, wid = [], []
        n = 10
        for k in range(n + 1):
            t = k / n
            p = Vector((0, 0, height - 0.15)) + out * (t * length) + \
                Vector((0, 0, rise * math.sin(t * math.pi * 0.85) - t * t * 0.9))
            pts.append(p)
            wid.append(0.28 * math.sin(math.pi * min(1, t * 1.15 + 0.06)) + 0.01)
        side = out.cross(UP).normalized()
        v, f = [], []
        for k, p in enumerate(pts):
            w = wid[k]
            v += [tuple(p - side * w + UP * 0.07 * w * 4), tuple(p), tuple(p + side * w + UP * 0.07 * w * 4)]
        for k in range(n):
            j = 3 * k
            f += [(j, j + 3, j + 4, j + 1), (j + 1, j + 4, j + 5, j + 2)]
        parts.append(L.mesh_obj(name + "L", v, f, leaf_mat, smooth=True))
    return L.join(parts, name)


def borassus(name, bark, frond_mat, height=15.0, seed=0):
    """Borassus aethiopum: straight grey trunk with an upper bulge, fan-leaf crown."""
    rnd = random.Random(seed)
    parts = []
    seg_n = 10
    z = 0.0

    def rad(t):
        return 0.36 + 0.16 * math.exp(-((t - 0.68) / 0.12) ** 2) - 0.06 * t
    for s in range(seg_n):
        t0, t1 = s / seg_n, (s + 1) / seg_n
        h = height / seg_n
        parts.append(L.cylinder(name + "T", rad(t0), rad(t1), h, (0, 0, z), bark, seg=10, cap=False))
        z += h
    crown = Vector((0, 0, height))
    for i in range(44):
        a = rnd.uniform(0, 2 * math.pi)
        pitch = rnd.uniform(-0.7, 1.2)
        d = Vector((math.cos(a) * math.cos(pitch), math.sin(a) * math.cos(pitch), math.sin(pitch)))
        pet = rnd.uniform(1.2, 1.9)
        hub = crown + d * pet
        parts.append(limb(name + "P", crown, hub, 0.045, 0.03, frond_mat, seg=5))
        side = d.cross(UP)
        if side.length < 0.1:
            side = Vector((1, 0, 0))
        side.normalize()
        up = side.cross(d).normalized()
        R = rnd.uniform(1.7, 2.3)
        rays = 26
        v = [tuple(hub)]
        for k in range(rays + 1):
            th = math.pi * (0.08 + 0.84 * k / rays) - math.pi / 2
            pleat = 0.10 if k % 2 else -0.10
            dirv = (d * math.cos(th) + side * math.sin(th)).normalized()
            p = hub + dirv * R + up * pleat - Vector((0, 0, 0.25 * R * abs(math.sin(th))))
            v.append(tuple(p))
        f = [(0, k + 1, k + 2) for k in range(rays)]
        parts.append(L.mesh_obj(name + "F", v, f, frond_mat))
    return L.join(parts, name)


def acacia(name, bark, cards, inner, height=7.0, spread=5.0, seed=0, n_cards=1800):
    """Umbrella acacia: short trunk splitting into spreading limbs, flat layered crown."""
    rnd = random.Random(seed)
    parts = []
    fork = Vector((0, 0, height * 0.38))
    parts.append(limb(name + "T", (0, 0, 0), fork, 0.24, 0.18, bark, seg=8))
    clumps = []
    limbs = rnd.randint(3, 5)
    for i in range(limbs):
        a = 2 * math.pi * i / limbs + rnd.uniform(-0.4, 0.4)
        mid = fork + Vector((math.cos(a) * spread * 0.25, math.sin(a) * spread * 0.25, height * 0.3))
        tip = fork + Vector((math.cos(a) * spread * 0.5, math.sin(a) * spread * 0.5, height * 0.52))
        parts.append(limb(name + "B", fork, mid, 0.15, 0.1, bark))
        parts.append(limb(name + "B", mid, tip, 0.1, 0.05, bark))
    for c in range(8):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0, spread * 0.5)
        clumps.append((Vector((math.cos(a) * r, math.sin(a) * r, height * 0.93 + rnd.uniform(-0.2, 0.3))),
                       Vector((1.6, 1.6, 0.45)) * rnd.uniform(0.9, 1.3)))
    parts += core(name + "C", clumps, inner, 0.5, seed)
    parts.append(leaf_cloud(name + "L", clumps, n_cards, cards, size=(0.38, 0.38), flat=0.75, seed=seed))
    return L.join(parts, name)


def round_tree(name, bark, cards, inner, height=9.0, crown=4.0, seed=0, n_cards=2200):
    """Mango / fig / jacaranda style dome crown."""
    rnd = random.Random(seed)
    parts = [limb(name + "T", (0, 0, 0), (0, 0, height * 0.45), 0.3, 0.22, bark, seg=8)]
    clumps = []
    for i in range(4):
        a = rnd.uniform(0, 2 * math.pi)
        s = Vector((0, 0, height * 0.4))
        t = s + Vector((math.cos(a) * crown * 0.45, math.sin(a) * crown * 0.45, height * 0.3))
        parts.append(limb(name + "B", s, t, 0.15, 0.07, bark))
    for c in range(7):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0, crown * 0.45)
        z = height * 0.72 + rnd.uniform(-0.4, 0.9) * (1 - r / crown)
        clumps.append((Vector((math.cos(a) * r, math.sin(a) * r, z)),
                       Vector((1, 1, 0.8)) * rnd.uniform(crown * 0.45, crown * 0.6)))
    parts += core(name + "C", clumps, inner, 0.6, seed)
    parts.append(leaf_cloud(name + "L", clumps, n_cards, cards, size=(0.45, 0.45), hang=0.15, seed=seed, shell=0.7))
    return L.join(parts, name)


def shrub(name, cards, inner, size=1.0, seed=0, n_cards=260):
    rnd = random.Random(seed)
    clumps = [(Vector((rnd.uniform(-0.4, 0.4) * size, rnd.uniform(-0.4, 0.4) * size, size * 0.45)),
               Vector((1, 1, 0.75)) * size * rnd.uniform(0.5, 0.7)) for _ in range(3)]
    parts = core(name + "C", clumps, inner, 0.6, seed)
    parts.append(leaf_cloud(name + "L", clumps, n_cards, cards, size=(0.3, 0.3), seed=seed, shell=0.6))
    return L.join(parts, name)


def rock(name, mat, size=1.0, seed=0):
    return L.blob(name, size, (0, 0, size * 0.25), mat, squash=(1.2, 1.0, 0.6), rough=0.35, seed=seed, subdiv=3)
