"""Cape Town arena: Table Mountain's flat top and cliffs behind the court,
Lion's Head beside it, the Atlantic to one side, city blocks along the base,
palms and a modern seaside setting. Open court or stands."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arena_common as C
import bpy
import arena_lib as L
import arena_flora as F
import arena_build as B

L.reset_scene()
rnd = random.Random(53)
SEA = -6.0


def table_mountain(x, y):
    # long flat-topped massif ~1 km high, steep upper cliffs, scree apron
    cx, cy = 0.0, 3600.0
    u = (x - cx) / 3200.0
    v = (y - cy) / 900.0
    d = math.sqrt(u * u + v * v)
    top = 1080 * (1 - L.smoothstep(0.92, 1.05, d))
    apron = 420 * (1 - L.smoothstep(0.9, 2.2, d))
    edge = L.fbm(x, y, 0.004, 3, 3.3) * 30
    return max(top, apron + edge * (1 - L.smoothstep(0.9, 1.05, d)))


def lions_head(x, y):
    d = math.hypot(x + 3400, y - 2200) / 700.0
    return 670 * max(0.0, 1 - d) ** 1.4 + 120 * max(0.0, 1 - d * 0.5)


def h(x, y):
    r = math.hypot(x, y)
    base = 8 * L.fbm(x, y, 0.004, 3, 1.0) * L.smoothstep(40, 300, r)
    land = base + 0.04 * max(0.0, y - 200)
    coast = -40 * L.smoothstep(600, 1200, -x + 200 * L.fbm(0, y, 0.002, 2, 4.0))
    return max(land + coast, -60) + table_mountain(x, y) + lions_head(x, y)


H = C.shelf(h, 28, 70)
lawn = L.noisy("Lawn", (0.34, 0.50, 0.20), (0.42, 0.56, 0.24), scale=0.4, rough=0.9, bump=0.3)
paving = L.noisy("Paving", (0.50, 0.48, 0.45), (0.56, 0.54, 0.50), scale=1.2, rough=0.85, bump=0.15)
fynbos = L.noisy("Fynbos", (0.40, 0.44, 0.30), (0.52, 0.50, 0.36), scale=0.02, rough=0.95, bump=0.2, c3=(0.60, 0.58, 0.50), scale2=0.006)
cliff = L.noisy("Sandstone", (0.62, 0.58, 0.52), (0.48, 0.44, 0.40), scale=0.01, rough=0.9, bump=0.6, c3=(0.36, 0.40, 0.30), scale2=0.003)


def assign(ob):
    me = ob.data
    for m in (lawn, paving, fynbos, cliff):
        me.materials.append(m)
    for p in me.polygons:
        r = math.hypot(p.center.x, p.center.y)
        if r < 34:
            p.material_index = 1
        elif p.normal.z < 0.75 or p.center.z > 700:
            p.material_index = 3
        elif r < 260:
            p.material_index = 0
        else:
            p.material_index = 2


C.rings(H, lawn, assign=assign, sizes=(360, 2600, 16000))
L.box("Lake", (16000, 16000, 0.1), (0, 0, SEA), L.water("Water", deep=(0.06, 0.24, 0.34)))

wall_cols = [(0.94, 0.93, 0.90), (0.86, 0.84, 0.78), (0.78, 0.82, 0.84), (0.96, 0.90, 0.80), (0.66, 0.70, 0.74)]
walls = [L.noisy(f"Facade{i}", c, tuple(v * 0.92 for v in c), scale=0.5, rough=0.6, bump=0.05) for i, c in enumerate(wall_cols)]
glass = L.flat("Glass", (0.22, 0.32, 0.40), rough=0.08, metal=0.6)
# the city bowl climbing toward the mountain
C.scatter(C.res(120, 900, 900), (-2400, 2400, 300, 2600),
          lambda x, y: H(x, y) > SEA + 3 and table_mountain(x, y) < 260 and lions_head(x, y) < 60,
          lambda x, y, r: B.tower_block("Block", r.uniform(14, 30), r.uniform(12, 24), r.choice((9, 12, 15, 21, 30, 45, 70)) * (1.6 if math.hypot(x, y - 900) < 600 else 1.0),
                                        r.choice(walls), glass, (x, y, H(x, y) - 1), r.uniform(0, 3.14)), seed=3)
# seaside promenade blocks to the west
for k in range(12):
    x = -60 - k * 18
    B.tower_block("Promenade", 14, 16, rnd.choice((12, 18, 24)), rnd.choice(walls), glass, (x, 60 + rnd.uniform(-6, 6), H(x, 60) - 0.5), 0.0)

palm_bark = L.noisy("PalmBark", (0.50, 0.46, 0.40), (0.38, 0.34, 0.30), scale=3, rough=0.9, bump=0.6)
frond = L.noisy("Frond", (0.30, 0.44, 0.18), (0.40, 0.50, 0.22), scale=2, rough=0.7, bump=0.3)
palms = [L.hide_template(F.borassus(f"Palm{i}", palm_bark, frond, height=rnd.uniform(9, 13), seed=i)) for i in range(3)]
bark = L.noisy("Bark", (0.32, 0.27, 0.22), (0.44, 0.38, 0.30), scale=5, rough=0.9, bump=0.5)
pine_cards = L.leaf_card("StonePine", (0.16, 0.26, 0.12), (0.22, 0.32, 0.14), tiles=(4, 2), width=0.4, power=0.8)
pine_in = L.flat("PineInner", (0.07, 0.12, 0.05))
pines = [L.hide_template(F.acacia(f"Pine{i}", bark, pine_cards, pine_in, height=rnd.uniform(11, 15), spread=rnd.uniform(7, 10), seed=i + 4)) for i in range(2)]
for x, y in ((-26, 28), (-14, 34), (14, 34), (26, 28), (-36, -8), (36, -8)):
    L.instance(rnd.choice(palms), (x, y, H(x, y)), rnd.uniform(0, 6.28), 1.0)
C.scatter(C.res(40, 260, 260), (-800, 800, 80, 1400), lambda x, y: math.hypot(x, y) > 50 and table_mountain(x, y) < 300,
          lambda x, y, r: L.instance(r.choice(pines + palms), (x, y, H(x, y)), r.uniform(0, 6.28), r.uniform(0.8, 1.2)), seed=7)
# floodlight masts (modern court)
metal = L.flat("Metal", (0.62, 0.64, 0.66), rough=0.4, metal=0.8)
lamp = L.flat("Lamp", (1.0, 0.96, 0.85), emit=(1.0, 0.95, 0.8))
for x in (-16, 16):
    for y in (-14, 14):
        m = B.mast("Floodlight", 16, metal, lamp)
        m.location = (x, y, H(x, y))

C.finish("capetown", rot_deg=0, sky=dict(clouds=0.3, cloud_seed=21.0, sun_elev_deg=50, sun_rot_deg=320, aerosol=0.8,
                                        strength=0.45, haze_density=0.00004, haze_color=(0.86, 0.90, 0.95), sun_energy=5.0),
         cams={"broadcast": ((0, -27, 9.5), (0, 8, 2), 24), "mountain": ((-10, -18, 4.0), (0, 3600, 700), 28)})
