"""Kampala open-court arena: a neighbourhood court on red murram.

A row of painted shops with verandahs and parked boda bodas, a kiosk, power
lines, water tanks on stands, mango and jacaranda trees; the city's hills behind
are packed with iron-sheet roofs, with taller buildings on the far hills in the
dusty haze. Open court, no stands. Colours are sRGB.

Run:  python kampala.py -- <out_dir> [--quick] [--cam=broadcast]
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import arena_lib as L
import arena_flora as F
import arena_build as B

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = args[0] if args else '/tmp/arenas'
QUICK = '--quick' in args
os.makedirs(OUT, exist_ok=True)

L.reset_scene()
rnd = random.Random(11)

# ------------------------------------------------------------------ terrain
HILLS = [  # (x, y, height, radius) - Kampala's many hills
    (-260, 420, 70, 260), (180, 520, 85, 300), (560, 260, 60, 240), (-620, 120, 55, 260),
    (900, 900, 110, 420), (-900, 900, 95, 380), (60, 1300, 120, 450), (1500, 300, 80, 400),
    (-1500, 500, 90, 450), (400, -700, 50, 300), (-500, -800, 60, 320),
]


def kampala_height(x, y):
    r = math.hypot(x, y)
    h = 6 * L.fbm(x, y, 0.004, 3, 2.0)
    for hx, hy, hh, hr in HILLS:
        d = math.hypot(x - hx, y - hy) / hr
        h += hh * math.exp(-d * d * 2.2)
    h += 14 * L.fbm(x, y, 0.0025, 4, 9.0) * L.smoothstep(80, 400, r)
    s = 1 - L.smoothstep(30, 70, r)
    return h * (1 - s) + 0.0 * s - 0.0


def ring_height(inner, drop):
    def fn(x, y):
        h = kampala_height(x, y)
        return h - drop if (abs(x) < inner and abs(y) < inner) else h
    return fn


murram = L.noisy("Murram", (0.60, 0.31, 0.19), (0.68, 0.38, 0.23), scale=0.5, rough=0.95, bump=0.35,
                 c3=(0.36, 0.42, 0.17), scale2=0.07)  # c3: weedy grass patches
suburb = L.noisy("Suburb", (0.26, 0.36, 0.14), (0.36, 0.42, 0.18), scale=0.03, rough=0.9, bump=0.2,
                 c3=(0.58, 0.36, 0.24), scale2=0.012)
near = L.heightfield("TerrainNear", 300, 100 if QUICK else 260, kampala_height, murram)
mid = L.heightfield("TerrainMid", 2600, 130 if QUICK else 420, ring_height(145, 1.0), suburb)
far = L.heightfield("TerrainFar", 14000, 100 if QUICK else 260, ring_height(1250, 4.0), suburb)

# ------------------------------------------------------------------ court & surrounds
L.court()
wood = L.noisy("Wood", (0.45, 0.33, 0.22), (0.56, 0.42, 0.29), scale=6, rough=0.85, bump=0.4)
for s in (-1, 1):
    L.log_bench("Bench", 4.5, (s * 7.0, -4.0, 0), math.radians(90), wood)
    L.log_bench("Bench", 4.5, (s * 7.0, 4.0, 0), math.radians(90), wood)
dark = L.flat("BoardDark", (0.10, 0.11, 0.10), rough=0.6)
L.scoreboard((12.5, -6.0, 0), math.radians(-90), wood, dark)
L.box("WornMurram", (15.0, 31.0, 0.02), (0, 0, -0.005),
      L.noisy("Worn", (0.62, 0.34, 0.20), (0.68, 0.40, 0.25), scale=1.0, rough=0.95, bump=0.3))

# ------------------------------------------------------------------ materials
paint_cols = [(0.93, 0.80, 0.25), (0.82, 0.20, 0.15), (0.20, 0.47, 0.75), (0.93, 0.92, 0.86),
              (0.35, 0.65, 0.35), (0.95, 0.55, 0.20), (0.55, 0.30, 0.60)]
shop_mats = {
    "wall": L.noisy("Plaster", (0.86, 0.82, 0.74), (0.74, 0.68, 0.60), scale=2, rough=0.9, bump=0.2,
                    c3=(0.70, 0.45, 0.30), scale2=0.6),  # murram splash at the base
    "roof": L.corrugated("IronRoof", color=(0.70, 0.71, 0.72), rust=(0.46, 0.27, 0.17), rust_amount=0.8),
    "slab": L.noisy("Concrete", (0.62, 0.60, 0.56), (0.70, 0.68, 0.64), scale=2, rough=0.9, bump=0.2),
    "metal": L.flat("Metal", (0.30, 0.31, 0.32), rough=0.5, metal=0.8),
    "shop_dark": L.flat("ShopInterior", (0.06, 0.05, 0.05), rough=0.8),
    "shutter": L.corrugated("Shutter", color=(0.55, 0.58, 0.60), rust=(0.45, 0.30, 0.20), rust_amount=0.3),
    "crate": L.noisy("Crate", (0.75, 0.25, 0.15), (0.20, 0.40, 0.70), scale=2.0, rough=0.6),
}
roof_new = L.corrugated("RoofNew", color=(0.78, 0.80, 0.82), rust=(0.55, 0.40, 0.30), rust_amount=0.1)
house_mats = {
    "wall": L.noisy("HouseWall", (0.88, 0.84, 0.76), (0.80, 0.74, 0.64), scale=2, rough=0.9, bump=0.2),
    "plinth": L.noisy("Plinth", (0.62, 0.38, 0.26), (0.55, 0.33, 0.22), scale=3),
    "roof": shop_mats["roof"],
    "door": L.flat("DoorMetal", (0.25, 0.35, 0.45), rough=0.5, metal=0.4),
    "window": L.flat("Window", (0.12, 0.12, 0.13), rough=0.3),
}
brick_mats = dict(house_mats, wall=L.brick("Brick", (0.62, 0.30, 0.18), (0.70, 0.62, 0.52)))
roof_red = L.corrugated("RoofRed", color=(0.62, 0.18, 0.14), rust=(0.45, 0.22, 0.14), rust_amount=0.25, painted=True)
roof_blue = L.corrugated("RoofBlue", color=(0.25, 0.38, 0.55), rust=(0.45, 0.30, 0.20), rust_amount=0.2, painted=True)
red_mats = dict(house_mats, roof=roof_red)
blue_mats = dict(brick_mats, roof=roof_blue)

# ------------------------------------------------------------------ the street: shops, kiosk, bodas, poles
# Shops along -X side facing the court across a murram road.
B.shop_row("ShopsA", shop_mats, units=5, unit_w=4.2, seed=1, paints=paint_cols).location = (-24, -8, 0)
bpy.data.objects["ShopsA"].rotation_euler.z = math.radians(90)  # front faces +X (court)
B.shop_row("ShopsB", shop_mats, units=4, unit_w=4.2, seed=2, paints=paint_cols).location = (-24, 18, 0)
bpy.data.objects["ShopsB"].rotation_euler.z = math.radians(90)
# two-storey building at the corner
two = B.shop_row("TwoStorey", shop_mats, units=3, unit_w=4.5, h=6.8, seed=3, paints=paint_cols)
two.location = (-25, -32, 0)
two.rotation_euler.z = math.radians(90)
# houses on the other sides
for i, (x, y, rz, m) in enumerate(((26, -24, -90, red_mats), (27, 2, -90, house_mats), (26, 26, -90, blue_mats),
                                    (-6, 36, 0, brick_mats), (10, 37, 0, house_mats))):
    h = B.house(f"House{i}", m, w=rnd.uniform(8, 11), d=rnd.uniform(6, 7), seed=i + 10)
    h.location = (x, y, 0)
    h.rotation_euler.z = math.radians(rz)

boda_mats = {"body": [L.flat(f"Boda{i}", c, rough=0.35, metal=0.3) for i, c in
                      enumerate([(0.75, 0.10, 0.10), (0.10, 0.12, 0.14), (0.15, 0.30, 0.65)])],
             "tyre": L.flat("Tyre", (0.05, 0.05, 0.05), rough=0.8), "metal": shop_mats["metal"],
             "seat": L.flat("Seat", (0.08, 0.06, 0.05), rough=0.6)}
boda_t = [L.hide_template(B.boda(f"BodaT{i}", boda_mats, seed=i)) for i in range(3)]
for k in range(9):
    y = -22 + k * 3.1 + rnd.uniform(-0.4, 0.4)
    L.instance(rnd.choice(boda_t), (-17.6 + rnd.uniform(-0.3, 0.3), y, 0), math.radians(rnd.choice((80, 100, 260))))

kiosk = B.round_hut("Kiosk", L.flat("KioskBlue", (0.15, 0.40, 0.70), rough=0.6),
                    shop_mats["roof"], r=1.3, h=2.2)
kiosk.location = (-15, 30, 0)
tank_mat = L.flat("Tank", (0.15, 0.17, 0.18), rough=0.6)
B.water_tank("Tank1", tank_mat, shop_mats["metal"], h_stand=3.2).location = (-30, 5, 0)
B.water_tank("Tank2", tank_mat, shop_mats["metal"], h_stand=0.0).location = (30, -12, 0)

pole_wood = L.noisy("PoleWood", (0.35, 0.27, 0.20), (0.42, 0.33, 0.24), scale=5)
wire_mat = L.flat("Wire", (0.05, 0.05, 0.05))
poles = [(-18.5, y, 0) for y in (-45, -22, 1, 24, 47)]
for i, p in enumerate(poles):
    B.power_pole(f"Pole{i}", pole_wood).location = p
for a, b in zip(poles, poles[1:]):
    for dx in (-0.7, 0.0, 0.7):
        B.wire("Wire", (a[0] + dx, a[1], 8.5), (b[0] + dx, b[1], 8.5), 0.5, wire_mat)
# service drops to the shops
for y in (-14, 8, 20):
    B.wire("Drop", (-18.5, y, 8.5), (-24.5, y + 2, 4.2), 0.4, wire_mat)

# road ruts / tyre tracks: darker compacted murram strip
L.box("Road", (7.0, 140, 0.02), (-15.5, 0, 0.0),
      L.noisy("RoadMurram", (0.60, 0.32, 0.19), (0.66, 0.37, 0.22), scale=0.8, rough=0.95, bump=0.5,
              c3=(0.52, 0.28, 0.17), scale2=0.4))

# ------------------------------------------------------------------ trees
bark = L.noisy("Bark", (0.33, 0.26, 0.20), (0.44, 0.36, 0.28), scale=5, rough=0.9, bump=0.5)
mango_cards = L.leaf_card("MangoLeaves", (0.12, 0.26, 0.08), (0.20, 0.36, 0.12), tiles=(3, 2), width=0.4, power=1.0)
mango_inner = L.flat("MangoInner", (0.06, 0.12, 0.04), rough=0.9)
jac_cards = L.leaf_card("JacarandaFlowers", (0.52, 0.42, 0.78), (0.62, 0.52, 0.84), tiles=(3, 3), width=0.48, power=0.6)
jac_inner = L.flat("JacInner", (0.30, 0.26, 0.45), rough=0.9)
leaf_ban = L.leaf("LeafBanana", (0.40, 0.58, 0.18), (0.52, 0.66, 0.24), translucency=0.35)
stem_ban = L.noisy("BananaStem", (0.44, 0.50, 0.26), (0.54, 0.48, 0.32), scale=3)
mango_t = [L.hide_template(F.round_tree(f"Mango{i}", bark, mango_cards, mango_inner, height=11, crown=5.5, seed=i))
           for i in range(3)]
jac_t = [L.hide_template(F.round_tree(f"Jac{i}", bark, jac_cards, jac_inner, height=10, crown=5, seed=i + 5))
         for i in range(2)]
ban_t = [L.hide_template(F.banana(f"Ban{i}", stem_ban, leaf_ban, seed=i)) for i in range(2)]
for x, y, t in ((22, -40, mango_t), (-34, -18, jac_t), (32, 15, mango_t), (-6, 50, jac_t), (20, 48, mango_t),
                (-36, 32, mango_t), (36, -2, jac_t)):
    L.instance(rnd.choice(t), (x, y, kampala_height(x, y)), rnd.uniform(0, 6.28), rnd.uniform(0.8, 1.1))
for k in range(16):
    x, y = rnd.choice((rnd.uniform(28, 45), rnd.uniform(-45, -32))), rnd.uniform(-40, 45)
    L.instance(rnd.choice(ban_t), (x, y, kampala_height(x, y)), rnd.uniform(0, 6.28), rnd.uniform(0.8, 1.2))

# ------------------------------------------------------------------ the city on the hills
small = []
new_mats = dict(house_mats, roof=roof_new)
green_mats = dict(brick_mats, roof=L.corrugated("RoofGreen", color=(0.25, 0.45, 0.30), rust=(0.4, 0.3, 0.2),
                                                rust_amount=0.15, painted=True))
for i, m in enumerate([house_mats, red_mats, blue_mats, brick_mats, house_mats, new_mats, brick_mats, green_mats]):
    small.append(L.hide_template(B.house(f"Home{i}", m, w=rnd.uniform(6, 10), d=rnd.uniform(5, 8),
                                         roof=rnd.choice(("gable", "mono")), seed=i + 30)))
tower_mats = [L.noisy(f"Tower{i}", c, tuple(v * 0.9 for v in c), scale=0.3, rough=0.4, bump=0.05)
              for i, c in enumerate([(0.85, 0.85, 0.82), (0.55, 0.65, 0.72), (0.78, 0.72, 0.62)])]
glass = L.flat("Glass", (0.20, 0.30, 0.38), rough=0.08, metal=0.6)
far_leaf = L.leaf("FarCanopy", (0.18, 0.32, 0.10), (0.26, 0.40, 0.14), translucency=0.1)
far_trees = [L.hide_template(F.round_tree(f"FarTree{i}", bark, far_leaf, far_leaf, height=10, crown=5, seed=i + 40,
                                          n_cards=1)) for i in range(3)]
n_homes = 2500 if QUICK else 16000
tries = 0
while n_homes > 0 and tries < 60000:
    tries += 1
    hx, hy, hh, hr = rnd.choice(HILLS)
    x, y = hx + rnd.gauss(0, hr * 0.6), hy + rnd.gauss(0, hr * 0.6)
    if math.hypot(x, y) < 70 or (abs(x) < 50 and abs(y) < 60):
        continue
    L.instance(rnd.choice(small), (x, y, kampala_height(x, y) - 0.2), rnd.uniform(0, 6.28), rnd.uniform(0.9, 1.3))
    n_homes -= 1
    if rnd.random() < 0.6:
        tx, ty = x + rnd.uniform(-12, 12), y + rnd.uniform(-12, 12)
        near_cam = math.hypot(tx, ty) < 260
        pool = (mango_t + jac_t) if near_cam else far_trees
        L.instance(rnd.choice(pool), (tx, ty, kampala_height(tx, ty)), rnd.uniform(0, 6.28), rnd.uniform(0.7, 1.2))
# office / hotel blocks on the far hills (city centre)
for k in range(60):
    hx, hy, hh, hr = rnd.choice(HILLS[4:8])
    x, y = hx + rnd.gauss(0, hr * 0.25), hy + rnd.gauss(0, hr * 0.25)
    w, d, ht = rnd.uniform(14, 30), rnd.uniform(14, 26), rnd.uniform(18, 70)
    blk = L.box("Tower", (w, d, ht), (x, y, kampala_height(x, y) + ht / 2), rnd.choice(tower_mats),
                rot_z=rnd.uniform(0, 3.14))
    L.box("TowerGlass", (w + 0.2, d * 0.6, ht * 0.9), (x, y, kampala_height(x, y) + ht / 2 + 1), glass,
          rot_z=blk.rotation_euler.z)

# weeds along the edges of the open ground
tuft_mat = L.leaf("Weed", (0.40, 0.52, 0.18), (0.55, 0.58, 0.26), translucency=0.3)
tuft = L.grass_tuft_template("Tuft", tuft_mat, blades=9, height=0.22)


def weed_density(co):
    if abs(co.x) < 8 and abs(co.y) < 16:
        return 0.0
    if -19.5 < co.x < -11.5:
        return 0.0  # road
    r = math.hypot(co.x, co.y)
    return 0.15 + 0.85 * L.smoothstep(14, 40, r) * (0.5 + 0.5 * L.fbm(co.x, co.y, 0.08, 2))


dg = L.density_group(near, "weeds", weed_density)
L.scatter_particles(near, tuft, 15000 if QUICK else 160000, seed=4, density_group=dg, name="weeds")

# ------------------------------------------------------------------ sky, light, cameras
L.sky_world(clouds=0.46, cloud_seed=9.0, sun_elev_deg=52, sun_rot_deg=120, air=1.0, aerosol=1.4, strength=0.45,
            haze_density=0.00007, haze_color=(0.90, 0.84, 0.76), sun_energy=4.8)
L.render_settings(samples=48 if QUICK else 128, res=(960, 540) if QUICK else (1600, 900), exposure=0.0)

cams = {
    "broadcast": L.camera("CamBroadcast", (0, -27, 9.5), (0, 2, 0), lens=24),
    "street": L.camera("CamStreet", (8, -24, 3.2), (-28, 30, 3), lens=22),
    "city": L.camera("CamCity", (14, -30, 7.0), (60, 700, 60), lens=30),
}
only = [a for a in args if a.startswith('--cam=')]
for key, cam in cams.items():
    if only and only[0][6:] != key:
        continue
    L.render_to(cam, os.path.join(OUT, f"kampala_{key}.png"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "kampala.blend"))
print("DONE")
