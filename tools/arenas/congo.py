"""DRC forest arena: a court in a rainforest clearing. Tall emergent trees on
buttressed trunks, layered canopy, oil palms, ferns, a brown river and mist
hanging in the trees. Open court or stands."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arena_common as C
import bpy
from mathutils import Vector
import arena_lib as L
import arena_flora as F
import arena_build as B

L.reset_scene()
rnd = random.Random(61)
RIVER = -5.0


def river_y(x):
    return 120 + 40 * math.sin(x * 0.006)


def h(x, y):
    r = math.hypot(x, y)
    g = (0.2 + 0.8 * L.smoothstep(60, 500, r)) * 30 * L.fbm(x, y, 0.003, 4, 6.0)
    d = abs(y - river_y(x))
    g -= 12 * (1 - L.smoothstep(25, 70, d))
    return g


H = C.shelf(h, 26, 52)
floor = L.noisy("ForestFloor", (0.30, 0.24, 0.16), (0.24, 0.30, 0.14), scale=0.6, rough=0.95, bump=0.5, c3=(0.18, 0.26, 0.10), scale2=0.05)
clearing = L.noisy("Clearing", (0.44, 0.34, 0.22), (0.36, 0.40, 0.20), scale=0.6, rough=0.95, bump=0.3)
canopy = L.noisy("CanopyFar", (0.10, 0.22, 0.07), (0.16, 0.30, 0.09), scale=0.01, rough=0.95, bump=0.4)


def assign(ob):
    me = ob.data
    for m in (floor, clearing, canopy):
        me.materials.append(m)
    for p in me.polygons:
        r = math.hypot(p.center.x, p.center.y)
        p.material_index = 1 if r < 30 else (0 if r < 150 else 2)


C.rings(H, floor, assign=assign, sizes=(360, 2400, 12000))
L.box("Lake", (12000, 12000, 0.1), (0, 0, RIVER), L.water("Water", deep=(0.34, 0.26, 0.16), rough=0.1))

bark = L.noisy("Bark", (0.46, 0.42, 0.36), (0.34, 0.30, 0.26), scale=4, rough=0.9, bump=0.6, c3=(0.30, 0.36, 0.22), scale2=0.6)
cards = L.leaf_card("RainLeaves", (0.10, 0.26, 0.06), (0.18, 0.36, 0.10), tiles=(3, 2), width=0.46, power=0.7)
cards2 = L.leaf_card("UnderLeaves", (0.14, 0.32, 0.08), (0.24, 0.42, 0.12), tiles=(2, 2), width=0.48, power=0.6)
inner = L.flat("RainInner", (0.04, 0.10, 0.03))


def giant(name, seed):
    r2 = random.Random(seed)
    t = F.round_tree(name, bark, cards, inner, height=r2.uniform(30, 40), crown=r2.uniform(10, 14), seed=seed)
    # buttress roots: thin fins radiating from the trunk base
    fins = []
    for k in range(5):
        a = 2 * math.pi * k / 5 + r2.uniform(-0.3, 0.3)
        v = [(0, 0, 0), (math.cos(a) * 3.2, math.sin(a) * 3.2, 0), (math.cos(a) * 0.3, math.sin(a) * 0.3, 4.5)]
        fins.append(L.mesh_obj(name + "Fin", v, [(0, 1, 2)], bark))
    return L.join([t] + fins, name)


giants = [L.hide_template(giant(f"Giant{i}", i)) for i in range(3)]
mids = [L.hide_template(F.round_tree(f"Mid{i}", bark, cards2, inner, height=14, crown=6, seed=i + 7)) for i in range(3)]
palm_bark = L.noisy("PalmBark", (0.42, 0.36, 0.28), (0.32, 0.28, 0.22), scale=3, rough=0.9, bump=0.8)
frond = L.noisy("Frond", (0.20, 0.38, 0.10), (0.28, 0.46, 0.14), scale=2, rough=0.7)
palms = [L.hide_template(F.borassus(f"Palm{i}", palm_bark, frond, height=rnd.uniform(9, 14), seed=i + 3)) for i in range(2)]
ferns = [L.hide_template(F.shrub(f"Fern{i}", cards2, inner, size=1.6, seed=i)) for i in range(3)]
far_leaf = L.leaf("FarCanopy", (0.08, 0.20, 0.05), (0.14, 0.28, 0.08), translucency=0.1)
far = [L.hide_template(F.round_tree(f"FarTree{i}", bark, far_leaf, far_leaf, height=32, crown=12, seed=i + 20, n_cards=1)) for i in range(2)]

ok = lambda x, y: math.hypot(x, y) > 34 and abs(y - river_y(x)) > 30
C.scatter(C.res(260, 700, 700), (-200, 200, -200, 200), ok,
          lambda x, y, r: L.instance(r.choice(giants), (x, y, H(x, y) - 0.2), r.uniform(0, 6.28), r.uniform(0.85, 1.15)), seed=2)
C.scatter(C.res(260, 700, 700), (-120, 120, -120, 120), lambda x, y: ok(x, y) and math.hypot(x, y) < 110,
          lambda x, y, r: L.instance(r.choice(mids + palms), (x, y, H(x, y) - 0.1), r.uniform(0, 6.28), r.uniform(0.8, 1.2)), seed=3)
C.scatter(C.res(120, 600, 600), (-80, 80, -80, 80), lambda x, y: math.hypot(x, y) > 31,
          lambda x, y, r: L.instance(r.choice(ferns), (x, y, H(x, y)), r.uniform(0, 6.28), r.uniform(0.7, 1.4)), seed=4)
C.scatter(C.res(1500, 4000, 4000), (-2200, 2200, -2200, 2200), lambda x, y: math.hypot(x, y) > 180 and abs(y - river_y(x)) > 40,
          lambda x, y, r: L.instance(r.choice(far + giants), (x, y, H(x, y)), r.uniform(0, 6.28), r.uniform(0.9, 1.4)), seed=5)
mist_mat = L.soft_card("Spray", (0.90, 0.94, 0.92), opacity=0.06)
F.leaf_cloud("Mist", [(Vector((0, 90, 12)), Vector((120, 50, 10))), (Vector((-70, -60, 10)), Vector((60, 40, 8)))], 220, mist_mat, size=(22, 22), seed=9, shell=0.0)

C.finish("congo", rot_deg=0, sky=dict(clouds=0.55, cloud_seed=30.0, sun_elev_deg=62, sun_rot_deg=170, aerosol=1.6,
                                     strength=0.4, haze_density=0.0002, haze_color=(0.78, 0.84, 0.80), sun_energy=4.2),
         cams={"broadcast": ((0, -27, 9.5), (0, 8, 2), 24), "clearing": ((-8, -14, 2.5), (10, 60, 12), 22)})
