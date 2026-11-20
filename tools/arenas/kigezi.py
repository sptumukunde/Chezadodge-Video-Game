"""Kigezi open-court arena: a grass shelf above Lake Bunyonyi.

Terraced, intensely cultivated hills; eucalyptus woodlots on ridges and islands;
farmhouses with iron-sheet roofs and banana groves; Virunga volcano outlines in
the haze. Open court, no stands. Colours are sRGB (converted in arena_lib).

Run:  python kigezi.py -- <out_dir> [--quick] [--cam=broadcast]
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import arena_lib as L
import arena_flora as F
import arena_build as B
if '--game' in sys.argv:
    F.CARD_SCALE = 0.3
    F.CARD_SIZE = 1.6
    F.CORE_SUBDIV = 1

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = args[0] if args else '/tmp/arenas'
QUICK = '--quick' in args
GAME = '--game' in args  # phone-friendly GLB for the game instead of renders
os.makedirs(OUT, exist_ok=True)

L.reset_scene()
rnd = random.Random(7)
WATER = -42.0
STEP = 2.4  # terrace height

# ------------------------------------------------------------------ terrain
H0A = L.fbm(0, 0, 0.0016, 5, 3.1)
H0B = L.fbm(0, 0, 0.006, 4, 8.7)


def kigezi_height(x, y):
    r = math.hypot(x, y)
    relief = 0.12 + 0.88 * L.smoothstep(50, 450, r)
    hills = relief * (110 * (L.fbm(x, y, 0.0016, 5, 3.1) - H0A) + 30 * (L.fbm(x, y, 0.006, 4, 8.7) - H0B))
    basin = -120 * L.smoothstep(40, 230, x + 40 * L.fbm(x, y, 0.004, 3, 1.3)) * \
        (1 - L.smoothstep(650, 1000, x + 60 * L.fbm(x, y, 0.003, 3, 5.5)))
    behind = 0.22 * max(0.0, -x - 30) + 0.1 * max(0.0, abs(y) - 120)
    h = hills + basin + behind
    for cx, cy, peak, rad in ((1500, 5200, 950, 2300), (-900, 6200, 800, 2100), (3400, 6000, 700, 2000)):
        d = math.hypot(x - cx, y - cy)
        h += peak * max(0.0, 1 - d / rad) ** 1.6
    if h > WATER + 3 and r > 45 and r < 2500:
        h = h * 0.25 + 0.75 * L.terrace(h, STEP, 0.7)
    s = 1 - L.smoothstep(26, 60, r)
    return h * (1 - s)


m_grass = L.noisy("Grass", (0.34, 0.46, 0.17), (0.43, 0.53, 0.21), scale=0.4, rough=0.9, bump=0.3,
                  c3=(0.52, 0.42, 0.30), scale2=0.06)  # c3: trampled bare-earth patches
m_fields = L.field_patchwork("Fields", [
    (0.33, 0.47, 0.16), (0.40, 0.53, 0.19), (0.27, 0.40, 0.12), (0.46, 0.56, 0.22),
    (0.50, 0.36, 0.24), (0.42, 0.29, 0.19), (0.62, 0.57, 0.32), (0.22, 0.34, 0.12),
    (0.36, 0.50, 0.20), (0.56, 0.44, 0.28),
], patch=(34.0, 34.0), band=STEP, bank_color=(0.30, 0.40, 0.16))
m_shore = L.noisy("Shore", (0.28, 0.38, 0.14), (0.38, 0.34, 0.22), scale=0.2, rough=0.9, bump=0.2)
m_dirt = L.noisy("Dirt", (0.48, 0.36, 0.25), (0.56, 0.43, 0.30), scale=0.8, rough=0.95, bump=0.3)


def assign_by_zone(ob):
    me = ob.data
    for m in (m_grass, m_fields, m_shore):
        if m.name not in [x.name for x in me.materials]:
            me.materials.append(m)
    names = [x.name for x in me.materials]
    gi, fi, si = names.index("Grass"), names.index("Fields"), names.index("Shore")
    for p in me.polygons:
        c = p.center
        r = math.hypot(c.x, c.y)
        if c.z < WATER + 2.5:
            p.material_index = si
        elif r < 58 + 10 * L.fbm(c.x, c.y, 0.05, 2):
            p.material_index = gi
        else:
            p.material_index = fi


def ring_height(inner, drop):
    def fn(x, y):
        h = kigezi_height(x, y)
        return h - drop if (abs(x) < inner and abs(y) < inner) else h
    return fn


near = L.heightfield("TerrainNear", 360, 120 if QUICK else (100 if GAME else 300), kigezi_height, m_grass)
assign_by_zone(near)
mid = L.heightfield("TerrainMid", 2400, 150 if QUICK else (160 if GAME else 600), ring_height(170, 2.0), m_fields)
assign_by_zone(mid)
far = L.heightfield("TerrainFar", 16000, 120 if QUICK else (64 if GAME else 320), ring_height(1150, 6.0), m_fields)
assign_by_zone(far)

L.box("Lake", (16000, 16000, 0.1), (0, 0, WATER), L.water("Water", deep=(0.10, 0.20, 0.22)))

# ------------------------------------------------------------------ court & surrounds
L.court()
wood = L.noisy("Wood", (0.42, 0.30, 0.20), (0.55, 0.42, 0.28), scale=6, rough=0.85, bump=0.4)
rope = L.flat("Rope", (0.70, 0.62, 0.46))
for s in (-1, 1):
    L.log_bench("Bench", 4.5, (s * 7.0, -4.0, 0), math.radians(90), wood)
    L.log_bench("Bench", 4.5, (s * 7.0, 4.0, 0), math.radians(90), wood)
dark = L.flat("BoardDark", (0.10, 0.11, 0.10), rough=0.6)
L.scoreboard((-12.5, 6.0, 0), math.radians(90), wood, dark)
L.box("WornEarth", (15.0, 31.0, 0.02), (0, 0, -0.005), m_dirt)
B.fence("Fence", [(16, -30, 0), (19, -10, 0), (19, 10, 0), (16, 30, 0)], wood, rope)

# ------------------------------------------------------------------ vegetation templates
bark_euc = L.noisy("BarkEuc", (0.80, 0.76, 0.70), (0.62, 0.56, 0.48), scale=4, rough=0.8, bump=0.3,
                   c3=(0.66, 0.52, 0.38), scale2=1.0)
cards_euc = L.leaf_card("EucLeaves", (0.30, 0.40, 0.24), (0.42, 0.50, 0.32), tiles=(3, 1), width=0.36, power=1.1)
inner_euc = L.flat("EucInner", (0.24, 0.31, 0.19), rough=0.9)
leaf_ban = L.leaf("LeafBanana", (0.40, 0.58, 0.18), (0.52, 0.66, 0.24), translucency=0.35)
stem_ban = L.noisy("BananaStem", (0.44, 0.50, 0.26), (0.54, 0.48, 0.32), scale=3)
cards_dark = L.leaf_card("DarkLeaves", (0.20, 0.33, 0.12), (0.30, 0.42, 0.16), tiles=(3, 2), width=0.45, power=0.7)
inner_dark = L.flat("DarkInner", (0.08, 0.14, 0.05), rough=0.9)
bark = L.noisy("Bark", (0.33, 0.26, 0.20), (0.44, 0.36, 0.28), scale=5, rough=0.9, bump=0.5)

euc_t = [L.hide_template(F.eucalyptus(f"Euc{i}", bark_euc, cards_euc, inner_euc,
                                      height=rnd.uniform(18, 26), seed=i, n_cards=900 if QUICK else 1600))
         for i in range(4)]
ban_t = [L.hide_template(F.banana(f"Ban{i}", stem_ban, leaf_ban, seed=i)) for i in range(3)]
shrub_t = [L.hide_template(F.shrub(f"Shrub{i}", cards_dark, inner_dark, size=1.2, seed=i)) for i in range(3)]
tree_t = [L.hide_template(F.round_tree(f"Rnd{i}", bark, cards_dark, inner_dark, height=8, crown=3.5, seed=i))
          for i in range(2)]

# ------------------------------------------------------------------ houses
mats = {
    "wall": L.noisy("MudWall", (0.72, 0.52, 0.38), (0.78, 0.58, 0.43), scale=2, rough=0.95, bump=0.3),
    "plinth": L.noisy("Plinth", (0.52, 0.50, 0.47), (0.60, 0.58, 0.54), scale=3),
    "roof": L.corrugated("IronRoof", color=(0.74, 0.75, 0.76), rust=(0.55, 0.32, 0.18), rust_amount=0.35),
    "door": L.noisy("DoorBlue", (0.20, 0.36, 0.58), (0.24, 0.42, 0.62), scale=3, rough=0.6),
    "window": L.flat("Window", (0.12, 0.12, 0.13), rough=0.3),
}
mats_rust = dict(mats, roof=L.corrugated("IronRoofRust", color=(0.70, 0.70, 0.70), rust=(0.52, 0.28, 0.15),
                                         rust_amount=0.75))
mats_white = dict(mats, wall=L.noisy("LimeWall", (0.90, 0.87, 0.80), (0.82, 0.77, 0.69), scale=2, rough=0.9, bump=0.2))
house_t = [L.hide_template(B.house(f"House{i}", m, w=rnd.uniform(6, 9), d=rnd.uniform(4.5, 6), seed=i))
           for i, m in enumerate([mats, mats_rust, mats_white, mats_rust])]

# ------------------------------------------------------------------ placement
placed = []


def ok_spot(x, y, min_r=40, spacing=0.0):
    if math.hypot(x, y) < min_r:
        return False
    if kigezi_height(x, y) < WATER + 2:
        return False
    for px, py, pr in placed:
        if math.hypot(x - px, y - py) < spacing + pr:
            return False
    return True


def ground(x, y):
    return kigezi_height(x, y) - 0.3


n_houses = 25 if QUICK else 90
tries = 0
while n_houses > 0 and tries < 8000:
    tries += 1
    x, y = rnd.uniform(-500, 900), rnd.uniform(-400, 900)
    if not ok_spot(x, y, 70, 16):
        continue
    L.instance(rnd.choice(house_t), (x, y, ground(x, y) + 0.2), rnd.uniform(0, 6.28))
    placed.append((x, y, 6))
    for k in range(rnd.randint(5, 12)):
        bx, by = x + rnd.uniform(-16, 16), y + rnd.uniform(-16, 16)
        if math.hypot(bx - x, by - y) > 5:
            L.instance(rnd.choice(ban_t), (bx, by, ground(bx, by)), rnd.uniform(0, 6.28), rnd.uniform(0.8, 1.25))
    n_houses -= 1

# Eucalyptus woodlots, dense in patches (ridges, islands, field boundaries)
n_euc = 500 if QUICK else 2200
tries = 0
while n_euc > 0 and tries < 80000:
    tries += 1
    x, y = rnd.uniform(-900, 1500), rnd.uniform(-800, 1800)
    lot = L.fbm(x, y, 0.005, 3, 42.0)
    if lot < 0.05 or not ok_spot(x, y, 48, 0):
        continue
    L.instance(rnd.choice(euc_t), (x, y, ground(x, y)), rnd.uniform(0, 6.28), rnd.uniform(0.7, 1.15))
    n_euc -= 1

# Eucalyptus lines along field boundaries / paths (very typical of Kigezi)
for line in range(14 if QUICK else 40):
    x0, y0 = rnd.uniform(-500, 1100), rnd.uniform(-400, 1300)
    ang = rnd.uniform(0, math.pi)
    for k in range(rnd.randint(6, 18)):
        x, y = x0 + math.cos(ang) * k * 7, y0 + math.sin(ang) * k * 7
        if ok_spot(x, y, 50, 0):
            L.instance(rnd.choice(euc_t), (x, y, ground(x, y)), rnd.uniform(0, 6.28), rnd.uniform(0.7, 1.05))

for x, y in ((-24, -26), (-30, 6), (-26, 30), (24, 34), (-38, -8), (30, -36), (-44, 22), (-20, 44)):
    L.instance(rnd.choice(euc_t + tree_t), (x, y, ground(x, y)), rnd.uniform(0, 6.28), rnd.uniform(0.8, 1.0))
for k in range(40):
    a = rnd.uniform(0, 6.28); r = rnd.uniform(26, 58)
    x, y = r * math.cos(a), r * math.sin(a)
    if x > 14 and abs(y) < 32:
        continue
    L.instance(rnd.choice(shrub_t + ban_t), (x, y, ground(x, y) + 0.2), rnd.uniform(0, 6.28), rnd.uniform(0.7, 1.3))

grass_tuft_mat = L.leaf("GrassBlade", (0.36, 0.50, 0.17), (0.48, 0.58, 0.22), translucency=0.3)
tuft = L.grass_tuft_template("Tuft", grass_tuft_mat, blades=11, height=0.14)
tuft2 = L.grass_tuft_template("Tuft2", grass_tuft_mat, blades=7, height=0.26, seed=3)


def shelf_density(co):
    if abs(co.x) < 6.2 and abs(co.y) < 15.2:
        return 0.0
    if abs(co.x) < 7.6 and abs(co.y) < 15.6:
        return 0.25  # trampled edge
    r = math.hypot(co.x, co.y)
    return 1.0 - L.smoothstep(45, 80, r)


dg = L.density_group(near, "shelf", shelf_density)
if not GAME: L.scatter_particles(near, tuft, 30000 if QUICK else 380000, seed=1, density_group=dg, name="g1")
if not GAME: L.scatter_particles(near, tuft2, 6000 if QUICK else 70000, seed=2, density_group=dg, name="g2")

# ------------------------------------------------------------------ sky, light, cameras
L.sky_world(clouds=0.5, cloud_seed=3.0, sun_elev_deg=34, sun_rot_deg=205, air=1.0, aerosol=1.0, strength=0.45,
            haze_density=0.00005, haze_color=(0.85, 0.90, 0.96), sun_energy=4.5)
L.render_settings(samples=48 if QUICK else 128, res=(960, 540) if QUICK else (1600, 900), exposure=0.0)

cams = {
    "broadcast": L.camera("CamBroadcast", (0, -27, 9.5), (0, 2, 0), lens=24),
    "lakeside": L.camera("CamLake", (-16, -22, 5.0), (120, 60, -30), lens=22),
    "aerial": L.camera("CamAerial", (-120, -160, 90), (60, 40, -20), lens=26),
}
if GAME:
    import game_export
    game_export.export(os.path.join(OUT, 'kigezi.glb'), rot_deg=90)
    sys.exit(0)
only = [a for a in args if a.startswith('--cam=')]
for key, cam in cams.items():
    if only and only[0][6:] != key:
        continue
    L.render_to(cam, os.path.join(OUT, f"kigezi_{key}.png"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "kigezi.blend"))
print("DONE")
