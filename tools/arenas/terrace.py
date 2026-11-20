"""Waterside Terrace arena (night, open court): a mown lawn running down to the
water, a long stone-pillared pavilion with a deep timber pergola along one
side, a tiled terrace, a gravel promenade with lamp posts, an autumn maple with
silver bark, weeping willows by the shore, a patio umbrella and a barbecue.
Built from the user's reference picture. Material names Paving*, Stone*,
Timber*, Gravel*, Lamp* are given real surfaces / lights in the game.

Run:  python terrace.py -- <out_dir> [--quick] [--game]
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arena_common as C
import bpy
from mathutils import Vector
import arena_lib as L
import arena_flora as F

L.reset_scene()
rnd = random.Random(808)
WATER = -1.6
SHORE = 58.0  # lawn meets the water around here (+Y is the hero side)


def h(x, y):
    # flat lawn, a gentle fall to a rocky shore, low hills across the water
    shore = SHORE + 10 * math.sin(x * 0.02) + 6 * L.fbm(x, y, 0.01, 3, 2.0)
    g = 0.15 * L.fbm(x, y, 0.03, 3, 5.0)
    g -= 3.2 * L.smoothstep(shore - 14, shore + 6, y)
    g -= 6.0 * L.smoothstep(shore + 6, shore + 60, y)
    g += 0.04 * max(0.0, -x - 40)  # garden rises behind the pavilion
    far = L.smoothstep(1800, 2600, y) * 140 * (0.4 + L.fbm(x, y, 0.0012, 4, 9.0))
    return g + far


H = C.shelf(h, 30, 55)
lawn = L.noisy("Lawn", (0.17, 0.31, 0.08), (0.24, 0.38, 0.11), scale=0.5, rough=0.92, bump=0.2,
               c3=(0.30, 0.34, 0.14), scale2=0.08)
shore = L.noisy("ShoreRock", (0.30, 0.28, 0.24), (0.20, 0.19, 0.17), scale=0.3, rough=0.9, bump=0.5)
hills = L.noisy("FarHills", (0.07, 0.10, 0.06), (0.10, 0.13, 0.08), scale=0.004, rough=0.95)


def assign(ob):
    me = ob.data
    for m in (lawn, shore, hills):
        me.materials.append(m)
    for p in me.polygons:
        c = p.center
        p.material_index = 1 if (c.z < WATER + 1.4 and c.y < 800) else (2 if c.y > 800 else 0)


C.rings(H, lawn, assign=assign, sizes=(360, 2400, 12000))
L.box("Lake", (12000, 12000, 0.1), (0, 2000, WATER), L.water("Water", deep=(0.02, 0.05, 0.08), rough=0.05))

# ------------------------------------------------------------------ pavilion + pergola (left side, -X)
stone = L.noisy("StonePillar", (0.46, 0.42, 0.36), (0.30, 0.27, 0.23), scale=3.0, rough=0.9, bump=0.8,
                c3=(0.55, 0.52, 0.46), scale2=0.6)
plaster = L.noisy("PlasterWall", (0.82, 0.80, 0.75), (0.74, 0.72, 0.68), scale=1.0, rough=0.85, bump=0.1)
timber = L.noisy("TimberBeam", (0.40, 0.22, 0.10), (0.27, 0.14, 0.06), scale=8.0, rough=0.6, bump=0.2)
glass = L.flat("Glass", (0.05, 0.07, 0.09), rough=0.08, metal=0.4)
paving = L.noisy("PavingTerrace", (0.52, 0.45, 0.38), (0.44, 0.38, 0.32), scale=1.0, rough=0.7, bump=0.1)
carpet = L.flat("TerraceEdge", (0.36, 0.30, 0.36), rough=0.95)
floor_red = L.flat("PavilionFloor", (0.30, 0.10, 0.12), rough=0.6)
gravel = L.noisy("GravelPath", (0.70, 0.63, 0.52), (0.60, 0.54, 0.44), scale=6.0, rough=0.95, bump=0.4)
lamp_post = L.flat("LampPost", (0.86, 0.86, 0.84), rough=0.4, metal=0.3)
lamp_glow = L.flat("LampGlobe", (1.0, 0.94, 0.80), rough=0.3, emit=(1.0, 0.92, 0.75))
lamp_glow.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 6.0

PX = -19.0       # pillar line (front of the pavilion)
Y0, Y1 = -34.0, 44.0
# building: back wall, floor, roof slab
L.box("PavilionBack", (6.0, Y1 - Y0, 3.4), (PX - 6.5, (Y0 + Y1) / 2, 1.7), plaster)
L.box("PavilionFloor", (6.0, Y1 - Y0, 0.25), (PX - 3.2, (Y0 + Y1) / 2, 0.12), floor_red)
for k in range(int((Y1 - Y0) / 7)):
    y = Y0 + 3.5 + k * 7
    L.box("PavilionGlass", (0.12, 5.6, 2.4), (PX - 3.6, y, 1.45), glass)
L.box("PavilionRoof", (8.5, Y1 - Y0 + 1.0, 0.45), (PX - 4.0, (Y0 + Y1) / 2, 3.55), plaster)
# stone pillars with a low stone rail between them
y = Y0
while y <= Y1 + 0.01:
    L.box("StonePillar", (0.75, 0.75, 3.4), (PX, y, 1.7), stone)
    y += 4.0
for z in (0.55, 1.05):
    L.box("StoneRail", (0.22, Y1 - Y0, 0.16), (PX + 0.1, (Y0 + Y1) / 2, z), stone)
# deep pergola: two edge beams and dense cross slats reaching over the terrace
for x in (PX - 1.0, PX + 7.5):
    L.box("TimberBeam", (0.35, Y1 - Y0 + 2, 0.55), (x, (Y0 + Y1) / 2, 3.9), timber)
for k in range(int((Y1 - Y0 + 2) / 0.62)):
    yy = Y0 - 1 + k * 0.62
    L.box("TimberSlat", (10.5, 0.14, 0.32), (PX + 3.0, yy, 4.25), timber)
for yy in (Y0, (Y0 + Y1) / 2, Y1):
    L.box("StonePillar", (0.6, 0.6, 4.3), (PX + 7.5, yy, 2.15), stone)
# terrace paving, edge strip and gravel promenade
L.box("PavingTerrace", (9.0, Y1 - Y0 + 8, 0.06), (PX + 4.5, (Y0 + Y1) / 2, 0.03), paving)
L.box("TerraceEdge", (0.7, Y1 - Y0 + 8, 0.07), (PX + 9.3, (Y0 + Y1) / 2, 0.035), carpet)
for k in range(28):
    t = k / 27
    yy = -40 + t * 100
    xx = PX + 11.2 + 4.0 * L.smoothstep(30, 60, yy) + 1.5 * math.sin(yy * 0.05)
    L.box("GravelPath", (3.2, 3.9, 0.05), (xx, yy, 0.025 + max(0.0, H(xx, yy))), gravel, rot_z=0.04 * math.sin(k))

# ------------------------------------------------------------------ lamps, patio, barbecue, benches
LAMPS = []


def lamp(x, y):
    z = H(x, y)
    L.cylinder("LampPost", 0.07, 0.05, 3.6, (x, y, z), lamp_post, seg=8)
    L.blob("LampGlobe", 0.22, (x, y, z + 3.75), lamp_glow, rough=0.0, subdiv=2)
    LAMPS.append((x, y, z + 3.75))


for yy in (-28, -12, 4, 20, 36, 52):
    lamp(PX + 13.6 + 3.0 * L.smoothstep(30, 60, yy), yy)
lamp(14, 46); lamp(-2, 54); lamp(26, 30)

canvas = L.flat("UmbrellaCanvas", (0.86, 0.78, 0.62), rough=0.9)
chair = L.flat("ChairRed", (0.55, 0.10, 0.16), rough=0.6)
metal = L.flat("GrillMetal", (0.12, 0.12, 0.13), rough=0.4, metal=0.8)
wood_cart = L.flat("CartWood", (0.50, 0.28, 0.12), rough=0.7)


def patio(x, y):
    z = H(x, y)
    L.cylinder("UmbrellaPole", 0.04, 0.04, 2.5, (x, y, z), lamp_post, seg=6)
    L.cylinder("UmbrellaCanvas", 1.7, 0.05, 0.55, (x, y, z + 2.2), canvas, seg=16)
    L.cylinder("PatioTable", 0.6, 0.6, 0.05, (x, y, z + 0.72), wood_cart, seg=16)
    L.cylinder("PatioLeg", 0.05, 0.05, 0.72, (x, y, z), metal, seg=6)
    for k in range(4):
        a = k * math.pi / 2 + 0.3
        cx, cy = x + math.cos(a) * 1.0, y + math.sin(a) * 1.0
        L.box("ChairRed", (0.45, 0.45, 0.05), (cx, cy, z + 0.45), chair, rot_z=a)
        L.box("ChairRed", (0.45, 0.05, 0.45), (cx + math.cos(a) * 0.22, cy + math.sin(a) * 0.22, z + 0.68), chair, rot_z=a + math.pi / 2)


patio(PX + 17.5, 34); patio(PX + 15.0, -20)
gx, gy = PX + 13.0, 22.0
L.box("CartWood", (1.1, 0.6, 0.06), (gx, gy, 0.8), wood_cart)
L.box("GrillMetal", (0.9, 0.55, 0.35), (gx, gy, 1.0), metal)
for dx in (-0.45, 0.45):
    L.cylinder("CartWheel", 0.12, 0.12, 0.05, (gx + dx, gy - 0.3, 0.12), metal, seg=10, rot=(math.radians(90), 0, 0))
for (bx, by, a) in ((10, 50, 0.4), (-4, 47, -0.3), (22, 38, 1.2)):
    L.box("StoneBench", (1.8, 0.45, 0.08), (bx, by, H(bx, by) + 0.45), stone, rot_z=a)
    L.box("StoneBench", (0.3, 0.4, 0.45), (bx, by, H(bx, by) + 0.22), stone, rot_z=a)
planter = L.noisy("StonePlanter", (0.50, 0.47, 0.42), (0.40, 0.37, 0.33), scale=2.0, rough=0.9, bump=0.4)
flowers = L.leaf_card("FlowerBed", (0.85, 0.20, 0.25), (0.95, 0.75, 0.20), tiles=(4, 2), width=0.5, power=0.6)
greens = L.leaf_card("HedgeLeaves", (0.10, 0.24, 0.07), (0.17, 0.32, 0.09), tiles=(3, 2), width=0.46, power=0.7)
inner = L.flat("HedgeInner", (0.04, 0.10, 0.03))
for yy in (Y0 - 2, Y1 + 2):
    L.box("StonePlanter", (3.0, 1.4, 0.6), (PX + 6, yy, 0.3), planter)
    F.leaf_cloud("FlowerBedL", [(Vector((PX + 6, yy, 0.75)), Vector((1.3, 0.55, 0.25)))], 160, flowers, size=(0.25, 0.25), seed=int(yy))

# ------------------------------------------------------------------ trees
silver = L.noisy("SilverBark", (0.80, 0.79, 0.76), (0.62, 0.61, 0.58), scale=5, rough=0.8, bump=0.5)
bark = L.noisy("WillowBark", (0.30, 0.25, 0.20), (0.22, 0.18, 0.15), scale=5, rough=0.9, bump=0.6)
# leaf-card colours are stored un-gamma'd in the game texture, so these are
# lifted to land on the picture's orange and gold
maple_cards = L.leaf_card("MapleLeaves", (1.0, 0.84, 0.36), (0.99, 0.64, 0.24), tiles=(3, 3), width=0.48, power=0.6)
maple_inner = L.flat("MapleInner", (0.35, 0.10, 0.03))
willow_cards = L.leaf_card("WillowLeaves", (0.46, 0.62, 0.18), (0.62, 0.74, 0.28), tiles=(5, 1), width=0.42, power=1.2)
willow_inner = L.flat("WillowInner", (0.18, 0.28, 0.07))


def maple(name, seed):
    """Spreading autumn maple: silver trunk splitting into many limbs."""
    r2 = random.Random(seed)
    parts = [F.limb(name + "T", (0, 0, 0), (0, 0, 2.2), 0.34, 0.28, silver, seg=10)]
    clumps = []
    for k in range(7):
        a = 2 * math.pi * k / 7 + r2.uniform(-0.3, 0.3)
        s = Vector((0, 0, 2.0 + r2.uniform(0, 0.6)))
        ln = r2.uniform(3.5, 5.5)
        t = s + Vector((math.cos(a) * ln, math.sin(a) * ln, r2.uniform(2.5, 4.5)))
        parts.append(F.limb(name + "B", s, t, 0.16, 0.06, silver, seg=7))
        for j in range(2):
            u = t + Vector((r2.uniform(-1.5, 1.5), r2.uniform(-1.5, 1.5), r2.uniform(0.5, 1.6)))
            parts.append(F.limb(name + "b", t, u, 0.06, 0.02, silver, seg=5))
        clumps.append((t + Vector((0, 0, 0.6)), Vector((2.2, 2.2, 1.5)) * r2.uniform(0.9, 1.2)))
    parts += F.core(name + "C", clumps, maple_inner, 0.35, seed)
    parts.append(F.leaf_cloud(name + "L", clumps, 2600, maple_cards, size=(0.4, 0.4), hang=0.1, seed=seed, shell=0.65))
    return L.join(parts, name)


def willow(name, seed):
    """Weeping willow: short trunk, arching crown, long hanging leaf curtains."""
    r2 = random.Random(seed)
    ht = r2.uniform(8, 10)
    parts = [F.limb(name + "T", (0, 0, 0), (0, 0, ht * 0.5), 0.35, 0.25, bark, seg=8)]
    clumps = []
    for k in range(9):
        a = 2 * math.pi * k / 9 + r2.uniform(-0.2, 0.2)
        s = Vector((0, 0, ht * 0.45))
        t = s + Vector((math.cos(a) * 2.8, math.sin(a) * 2.8, ht * 0.4))
        parts.append(F.limb(name + "B", s, t, 0.14, 0.05, bark, seg=6))
        # the curtain hangs from the arching branch tips almost to the lawn
        clumps.append((t + Vector((math.cos(a) * 0.8, math.sin(a) * 0.8, -ht * 0.3)), Vector((1.6, 1.6, ht * 0.38))))
    clumps.append((Vector((0, 0, ht * 0.85)), Vector((2.6, 2.6, 1.4))))
    parts += F.core(name + "C", clumps[-1:], willow_inner, 0.5, seed)
    parts.append(F.leaf_cloud(name + "L", clumps, 3200, willow_cards, size=(1.1, 0.22), hang=0.95, seed=seed, shell=0.75))
    return L.join(parts, name)


maples = [L.hide_template(maple(f"Maple{i}", i + 1)) for i in range(2)]
willows = [L.hide_template(willow(f"Willow{i}", i + 5)) for i in range(2)]
hedges = [L.hide_template(F.shrub(f"Shrub{i}", greens, inner, size=1.3, seed=i)) for i in range(3)]
for (x, y, s) in ((PX + 13.5, 12, 1.0), (PX + 15.5, -32, 0.9), (24, -30, 0.85)):
    L.instance(rnd.choice(maples), (x, y, H(x, y)), rnd.uniform(0, 6.28), s)
for (x, y) in ((6, 52), (18, 48), (-8, 56), (30, 40), (34, 22)):
    L.instance(rnd.choice(willows), (x, y, H(x, y) - 0.1), rnd.uniform(0, 6.28), rnd.uniform(0.9, 1.15))
for k in range(26):
    yy = Y0 + k * (Y1 - Y0) / 25
    L.instance(rnd.choice(hedges), (PX - 10.5, yy, H(PX - 10.5, yy)), rnd.uniform(0, 6.28), rnd.uniform(0.8, 1.2))
rock_m = L.noisy("ShoreBoulder", (0.36, 0.34, 0.30), (0.24, 0.22, 0.20), scale=2, rough=0.9, bump=0.8)
rocks = [L.hide_template(L.blob(f"Rock{i}", 1.0, (0, 0, 0.25), rock_m, squash=(1.2, 1.0, 0.6), rough=0.35, seed=i,
                                 subdiv=2 if C.GAME else 3)) for i in range(3)]
for k in range(60):
    x = rnd.uniform(-60, 90)
    y = SHORE + 10 * math.sin(x * 0.02) + rnd.uniform(-2, 10)
    L.instance(rnd.choice(rocks), (x, y, H(x, y) - 0.2), rnd.uniform(0, 6.28), rnd.uniform(0.6, 2.2))
# a rocky headland on the right and dark wooded hills across the water
for k in range(14):
    x, y = 70 + rnd.uniform(-8, 30), 70 + rnd.uniform(-10, 40)
    L.instance(rnd.choice(rocks), (x, y, WATER - 0.5), rnd.uniform(0, 6.28), rnd.uniform(3, 7))
far_leaf = L.leaf("FarCanopy", (0.04, 0.08, 0.04), (0.06, 0.10, 0.05), translucency=0.1)
far = [L.hide_template(F.round_tree(f"FarTree{i}", bark, far_leaf, far_leaf, height=14, crown=6, seed=i + 20, n_cards=1)) for i in range(2)]
C.scatter(C.res(200, 900, 900), (-3000, 3000, 1900, 3200), lambda x, y: H(x, y) > WATER + 4,
          lambda x, y, r: L.instance(r.choice(far), (x, y, H(x, y)), r.uniform(0, 6.28), r.uniform(1.0, 1.6)), seed=5)
C.scatter(C.res(60, 240, 240), (-200, -60, -200, 120), lambda x, y: True,
          lambda x, y, r: L.instance(r.choice(maples + hedges), (x, y, H(x, y)), r.uniform(0, 6.28), r.uniform(0.8, 1.3)), seed=6)

# merge the static props (pavilion, pergola slats, paving, lamps...) so the
# phone draws them in a handful of calls instead of hundreds
arena_col = bpy.data.collections.get("Arena")
static = [o for o in (arena_col.objects if arena_col else []) if o.type == 'MESH' and o.data.users == 1
          and not o.name.startswith(("Terrain", "Lake"))]
if static:
    L.join(static, "Props_terrace")
print("LAMPS_GODOT", [[round(x, 2), round(z, 2), round(-y, 2)] for x, y, z in LAMPS])
C.finish("terrace", rot_deg=0, export_kw={"near_trees": 60, "far_trees": 700, "clear_r": 11.0},
         sky=dict(clouds=0.15, cloud_seed=5.0, sun_elev_deg=-10, sun_rot_deg=200, aerosol=1.0,
                  strength=0.12, haze_density=0.0, sun_energy=0.0),
         cams={"broadcast": ((0, -27, 9.5), (0, 8, 2), 24), "terrace": ((-9, -30, 1.7), (-8, 30, 2.5), 20)},
         render={"exposure": 1.2})
