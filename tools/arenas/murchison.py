"""Murchison Falls open-court arena: north-bank savanna above the Victoria Nile.

Cropped grass court surround in golden savanna dotted with borassus palms and
umbrella acacias, termite mounds, thatched ranger bandas; the Nile in the
middle distance with riverine woodland on the south bank; upstream, the falls
cut through the escarpment with a spray cloud. Uganda kob graze nearby and a
few Rothschild giraffes browse in the distance. Open court, no stands.

Run:  python murchison.py -- <out_dir> [--quick] [--cam=broadcast]
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
rnd = random.Random(23)
RIVER_Y = 300.0
WATER = -24.0
FALLS = Vector((2150.0, RIVER_Y, 0.0))


def river_center(x):
    return RIVER_Y + 60 * math.sin(x * 0.0021) + 25 * math.sin(x * 0.0057 + 1.0)


def murchison_height(x, y):
    r = math.hypot(x, y)
    d = abs(y - river_center(x))
    calm = L.smoothstep(60, 260, d)  # flatter towards the river so the view opens
    h = calm * (7 * L.fbm(x, y, 0.003, 4, 4.4) + 3 * L.fbm(x, y, 0.02, 2, 1.1))
    # river valley: convex bluff on the north bank
    width = 80 + 20 * L.fbm(x, 0, 0.004, 2, 7.0)
    t = 1 - L.smoothstep(width, width + 170, d)
    h -= 40 * t ** 0.7
    # south bank rises gently to wooded hills
    if y > river_center(x):
        h += 0.035 * max(0.0, y - river_center(x) - 200) + 25 * L.fbm(x, y, 0.0015, 3, 3.3)
    # rift escarpment upstream (east), river cuts through at the falls
    esc = 230 * L.smoothstep(1700, 2500, x + 80 * L.fbm(x, y, 0.002, 3, 6.0))
    gorge = 1 - 0.92 * math.exp(-((y - river_center(x)) / 40.0) ** 2) * L.smoothstep(2000, 2450, x)
    h += esc * gorge
    s = 1 - L.smoothstep(28, 70, r)
    return h * (1 - s)


def ring_height(inner, drop):
    def fn(x, y):
        h = murchison_height(x, y)
        return h - drop if (abs(x) < inner and abs(y) < inner) else h
    return fn


m_short = L.noisy("ShortGrass", (0.47, 0.52, 0.24), (0.56, 0.58, 0.30), scale=0.4, rough=0.9, bump=0.3,
                  c3=(0.60, 0.48, 0.32), scale2=0.05)
m_savanna = L.noisy("Savanna", (0.66, 0.60, 0.34), (0.50, 0.54, 0.24), scale=0.02, rough=0.95, bump=0.25,
                    c3=(0.38, 0.44, 0.20), scale2=0.004)
m_bank = L.noisy("Bank", (0.45, 0.36, 0.26), (0.35, 0.40, 0.20), scale=0.2, rough=0.9, bump=0.3)
m_rock = L.noisy("Rock", (0.42, 0.38, 0.34), (0.55, 0.50, 0.45), scale=0.08, rough=0.85, bump=0.6,
                 c3=(0.30, 0.38, 0.18), scale2=0.01)


def assign(ob):
    me = ob.data
    for m in (m_short, m_savanna, m_bank, m_rock):
        me.materials.append(m)
    for p in me.polygons:
        c = p.center
        if c.z < WATER + 4:
            p.material_index = 2
        elif p.normal.z < 0.8:
            p.material_index = 3
        elif math.hypot(c.x, c.y) < 55 + 8 * L.fbm(c.x, c.y, 0.06, 2):
            p.material_index = 0
        else:
            p.material_index = 1


near = L.heightfield("TerrainNear", 360, 110 if QUICK else 300, murchison_height, m_short)
assign(near)
mid = L.heightfield("TerrainMid", 2800, 140 if QUICK else 560, ring_height(170, 1.0), m_savanna)
assign(mid)
far = L.heightfield("TerrainFar", 16000, 110 if QUICK else 320, ring_height(1390, 4.0), m_savanna)
assign(far)
L.box("Nile", (16000, 16000, 0.1), (0, 0, WATER),
      L.water("NileWater", deep=(0.26, 0.30, 0.22), rough=0.08, wave_scale=0.25, wave=0.12))

# ------------------------------------------------------------------ the falls
white = L.noisy("Whitewater", (0.95, 0.96, 0.95), (0.80, 0.84, 0.82), scale=0.6, rough=0.4, bump=0.6)
fx = FALLS.x - 120
fy = river_center(fx)
top = murchison_height(fx - 40, fy) + 2
for i in range(3):
    L.box("Falls", (14, 9 - i * 2, top - WATER), (fx + i * 2, fy + (i - 1) * 6, (top + WATER) / 2), white)
spray_mat = L.soft_card("Spray", (0.97, 0.98, 0.98), opacity=0.16)
spray = F.leaf_cloud("Spray", [(Vector((fx - 20, fy, WATER + 45)), Vector((90, 60, 55)))], 1600, spray_mat,
                     size=(18, 18), seed=5, shell=0.0)

# ------------------------------------------------------------------ court & surrounds
L.court()
wood = L.noisy("Wood", (0.45, 0.33, 0.22), (0.56, 0.42, 0.29), scale=6, rough=0.85, bump=0.4)
for s in (-1, 1):
    L.log_bench("Bench", 4.5, (s * 7.0, -4.0, 0), math.radians(90), wood)
    L.log_bench("Bench", 4.5, (s * 7.0, 4.0, 0), math.radians(90), wood)
dark = L.flat("BoardDark", (0.10, 0.11, 0.10), rough=0.6)
L.scoreboard((-12.5, 6.0, 0), math.radians(90), wood, dark)
L.box("WornEarth", (15.0, 31.0, 0.02), (0, 0, -0.005),
      L.noisy("Dust", (0.62, 0.50, 0.36), (0.68, 0.56, 0.40), scale=0.8, rough=0.95, bump=0.3))

# ranger bandas + post
thatch = L.noisy("Thatch", (0.62, 0.52, 0.34), (0.48, 0.40, 0.26), scale=4, rough=0.95, bump=0.8)
banda_wall = L.noisy("BandaWall", (0.86, 0.82, 0.72), (0.80, 0.75, 0.64), scale=2, rough=0.9, bump=0.2)
door = L.flat("BandaDoor", (0.30, 0.22, 0.15), rough=0.7)
for i, (x, y) in enumerate(((-34, 18), (-40, 30), (-30, 40), (34, 36))):
    b = B.round_hut(f"Banda{i}", banda_wall, thatch, r=3.0, h=2.4, door=door)
    b.location = (x, y, murchison_height(x, y))
    b.rotation_euler.z = math.atan2(-y, -x) + math.pi / 2
post_mats = {"wall": banda_wall, "plinth": L.flat("Stone", (0.50, 0.48, 0.44)), "door": door,
             "roof": L.corrugated("GreenRoof", color=(0.22, 0.38, 0.24), rust=(0.4, 0.3, 0.2), rust_amount=0.2,
                                  painted=True),
             "window": L.flat("Window", (0.12, 0.12, 0.13), rough=0.3)}
post = B.house("RangerPost", post_mats, w=9, d=6, seed=3)
post.location = (30, -30, murchison_height(30, -30))
post.rotation_euler.z = math.radians(-90)
B.water_tank("Tank", L.flat("TankGreen", (0.18, 0.30, 0.20), rough=0.6),
             L.flat("Metal", (0.3, 0.3, 0.3), metal=0.8), h_stand=3.0).location = (36, -24, 0)

# ------------------------------------------------------------------ vegetation & animals
palm_bark = L.noisy("PalmBark", (0.48, 0.45, 0.40), (0.36, 0.33, 0.29), scale=3, rough=0.9, bump=0.6)
frond = L.noisy("Frond", (0.40, 0.48, 0.20), (0.55, 0.52, 0.28), scale=2, rough=0.7, bump=0.3,
                c3=(0.58, 0.48, 0.30), scale2=0.8)
palm_t = [L.hide_template(F.borassus(f"Palm{i}", palm_bark, frond, height=rnd.uniform(13, 19), seed=i))
          for i in range(4)]
bark = L.noisy("Bark", (0.30, 0.25, 0.20), (0.42, 0.36, 0.28), scale=5, rough=0.9, bump=0.5)
acacia_cards = L.leaf_card("AcaciaLeaves", (0.30, 0.40, 0.14), (0.40, 0.48, 0.18), tiles=(5, 3), width=0.45, power=0.6)
acacia_inner = L.flat("AcaciaInner", (0.14, 0.20, 0.07), rough=0.9)
acacia_t = [L.hide_template(F.acacia(f"Acacia{i}", bark, acacia_cards, acacia_inner, height=rnd.uniform(6, 9),
                                     spread=rnd.uniform(5, 8), seed=i)) for i in range(3)]
wood_cards = L.leaf_card("WoodLeaves", (0.16, 0.30, 0.10), (0.24, 0.38, 0.12), tiles=(3, 2), width=0.45, power=0.7)
wood_inner = L.flat("WoodInner", (0.07, 0.13, 0.04), rough=0.9)
far_leaf = L.leaf("FarCanopy", (0.18, 0.30, 0.10), (0.26, 0.38, 0.14), translucency=0.1)
far_t = [L.hide_template(F.round_tree(f"FarTree{i}", bark, far_leaf, far_leaf, height=12, crown=6, seed=i + 40,
                                      n_cards=1)) for i in range(3)]
bush_t = [L.hide_template(F.shrub(f"Bush{i}", wood_cards, wood_inner, size=1.6, seed=i)) for i in range(3)]
mound_mat = L.noisy("TermiteMound", (0.66, 0.40, 0.26), (0.58, 0.34, 0.22), scale=3, rough=0.95, bump=0.8)
mound_t = []
for i in range(3):
    m = L.cylinder(f"Mound{i}", 1.4, 0.25, rnd.uniform(1.8, 3.2), (0, 0, 0), mound_mat, seg=12)
    t2 = L.blob(f"MoundB{i}", 1.0, (0.4, 0.2, 0.6), mound_mat, squash=(0.9, 0.8, 1.2), rough=0.4, seed=i)
    mound_t.append(L.hide_template(L.join([m, t2], f"Mound{i}")))


def ok(x, y, min_r=36):
    if math.hypot(x, y) < min_r:
        return False
    return murchison_height(x, y) > WATER + 3


def ground(x, y):
    return murchison_height(x, y) - 0.2


n_palms = 250 if QUICK else 1400
tries = 0
while n_palms > 0 and tries < 30000:
    tries += 1
    x, y = rnd.uniform(-1500, 2000), rnd.uniform(-1200, RIVER_Y - 60)
    if not ok(x, y, 45) or L.fbm(x, y, 0.004, 2, 13.0) < -0.1:
        continue
    L.instance(rnd.choice(palm_t), (x, y, ground(x, y)), rnd.uniform(0, 6.28), rnd.uniform(0.85, 1.15))
    n_palms -= 1
for k in range(60 if QUICK else 300):
    x, y = rnd.uniform(-1200, 1800), rnd.uniform(-1000, RIVER_Y - 80)
    if ok(x, y, 50):
        L.instance(rnd.choice(acacia_t), (x, y, ground(x, y)), rnd.uniform(0, 6.28), rnd.uniform(0.8, 1.2))
for k in range(40 if QUICK else 200):
    x, y = rnd.uniform(-600, 900), rnd.uniform(-500, RIVER_Y - 80)
    if ok(x, y, 40):
        L.instance(rnd.choice(mound_t + bush_t), (x, y, ground(x, y)), rnd.uniform(0, 6.28), rnd.uniform(0.7, 1.3))
# woodland clothing the escarpment around the falls
for k in range(800 if QUICK else 5000):
    x, y = rnd.uniform(1500, 3200), rnd.uniform(-700, 1400)
    if murchison_height(x, y) > WATER + 6 and abs(y - river_center(x)) > 30 and rnd.random() < 0.8:
        L.instance(rnd.choice(far_t), (x, y, ground(x, y)), rnd.uniform(0, 6.28), rnd.uniform(1.2, 2.2))
# riverine woodland on both banks + the wooded south side
for k in range(1500 if QUICK else 9000):
    x = rnd.uniform(-2500, 3000)
    side = rnd.random()
    if side < 0.25:
        y = river_center(x) - rnd.uniform(70, 160)
    else:
        y = river_center(x) + rnd.uniform(80, 2200)
    if murchison_height(x, y) > WATER + 2:
        L.instance(rnd.choice(far_t), (x, y, ground(x, y)), rnd.uniform(0, 6.28), rnd.uniform(0.7, 1.3))
# palms framing the court
for x, y in ((-26, -30), (24, -36), (-38, 4), (40, 10), (-22, 34), (18, 42)):
    L.instance(rnd.choice(palm_t), (x, y, ground(x, y)), rnd.uniform(0, 6.28), rnd.uniform(0.9, 1.1))
L.instance(acacia_t[0], (-48, -14, ground(-48, -14)), 0.4, 1.1)
L.instance(acacia_t[1], (46, -8, ground(46, -8)), 2.1, 1.0)

# animals (simple, they are seen from a distance)
kob_mat = L.noisy("Kob", (0.72, 0.50, 0.28), (0.66, 0.44, 0.24), scale=6, rough=0.8)
belly = L.flat("KobBelly", (0.90, 0.86, 0.78))
gir_mat = L.noisy("Giraffe", (0.80, 0.62, 0.36), (0.48, 0.28, 0.14), scale=9, rough=0.8)


def quadruped(name, body_mat, under, size, neck_len, neck_angle, leg_len):
    parts = [L.blob(name + "Body", 1.0, (0, 0, leg_len + size * 0.35), body_mat,
                    squash=(size * 0.35, size * 0.9, size * 0.42), rough=0.05, subdiv=2)]
    parts.append(L.blob(name + "Belly", 1.0, (0, 0, leg_len + size * 0.22), under,
                        squash=(size * 0.3, size * 0.7, size * 0.2), rough=0.05, subdiv=2))
    base = Vector((0, size * 0.75, leg_len + size * 0.5))
    tip = base + Vector((0, math.cos(neck_angle), math.sin(neck_angle))) * neck_len
    parts.append(F.limb(name + "Neck", base, tip, size * 0.13, size * 0.09, body_mat))
    parts.append(L.blob(name + "Head", 1.0, tuple(tip + Vector((0, size * 0.15, 0))), body_mat,
                        squash=(size * 0.1, size * 0.25, size * 0.12), rough=0.05, subdiv=2))
    for lx in (-1, 1):
        for ly in (-1, 1):
            parts.append(F.limb(name + "Leg", (lx * size * 0.2, ly * size * 0.6, leg_len + size * 0.2),
                                (lx * size * 0.2, ly * size * 0.62, 0), size * 0.05, size * 0.03, body_mat))
    return L.join(parts, name)


kob_t = [L.hide_template(quadruped("Kob", kob_mat, belly, 1.0, 0.45, math.radians(a), 0.55)) for a in (40, -35)]
gir_t = L.hide_template(quadruped("Giraffe", gir_mat, gir_mat, 2.0, 2.6, math.radians(62), 1.9))
for k in range(18):
    x, y = rnd.uniform(-160, 140) + 30, rnd.uniform(60, 200)
    if ok(x, y, 60):
        L.instance(rnd.choice(kob_t), (x, y, ground(x, y) + 0.2), rnd.uniform(0, 6.28), rnd.uniform(0.9, 1.1))
for x, y in ((420, 260), (450, 300), (-380, 330)):
    L.instance(gir_t, (x, y, ground(x, y) + 0.2), rnd.uniform(0, 6.28), 1.0)

# grass: cropped near the court, tall golden savanna grass beyond
blade = L.leaf("GrassBlade", (0.50, 0.56, 0.24), (0.60, 0.60, 0.30), translucency=0.3)
tall_blade = L.leaf("TallGrass", (0.74, 0.66, 0.40), (0.60, 0.60, 0.30), translucency=0.35)
tuft = L.grass_tuft_template("Tuft", blade, blades=11, height=0.14)
tall = L.grass_tuft_template("Tall", tall_blade, blades=14, height=1.0, spread=0.18, seed=5)


def short_density(co):
    if abs(co.x) < 6.2 and abs(co.y) < 15.2:
        return 0.0
    if abs(co.x) < 7.6 and abs(co.y) < 15.6:
        return 0.25
    return 1.0 - L.smoothstep(45, 62, math.hypot(co.x, co.y))


def tall_density(co):
    r = math.hypot(co.x, co.y)
    return L.smoothstep(55, 75, r) * (1 - L.smoothstep(150, 180, r)) * (0.6 + 0.4 * L.fbm(co.x, co.y, 0.04, 2))


dg = L.density_group(near, "short", short_density)
L.scatter_particles(near, tuft, 30000 if QUICK else 380000, seed=1, density_group=dg, name="short")
dt = L.density_group(near, "tall", tall_density)
L.scatter_particles(near, tall, 60000 if QUICK else 700000, seed=2, density_group=dt, name="tall")

# ------------------------------------------------------------------ sky, light, cameras
L.sky_world(clouds=0.48, cloud_seed=17.0, sun_elev_deg=46, sun_rot_deg=235, air=1.0, aerosol=1.6,
            strength=0.45, haze_density=0.00006, haze_color=(0.86, 0.86, 0.84), sun_energy=5.0)
L.render_settings(samples=48 if QUICK else 128, res=(960, 540) if QUICK else (1600, 900), exposure=0.0)

cams = {
    "broadcast": L.camera("CamBroadcast", (0, -27, 9.5), (0, 2, 0), lens=24),
    "river": L.camera("CamRiver", (-10, -18, 7.0), (40, 300, -20), lens=24),
    "falls": L.camera("CamFalls", (40, 120, 6.0), (2100, 330, 20), lens=45),
}
only = [a for a in args if a.startswith('--cam=')]
for key, cam in cams.items():
    if only and only[0][6:] != key:
        continue
    L.render_to(cam, os.path.join(OUT, f"murchison_{key}.png"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "murchison.blend"))
print("DONE")
