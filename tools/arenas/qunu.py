"""Qunu arena (Eastern Cape, South Africa): rolling veld, rondavels with pastel
walls and thatch, aloes, stone kraals, distant mountains. Open court or stands."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arena_common as C
import bpy
import arena_lib as L
import arena_flora as F
import arena_build as B

L.reset_scene()
rnd = random.Random(41)
H0 = L.fbm(0, 0, 0.0018, 4, 7.1)


def h(x, y):
    r = math.hypot(x, y)
    roll = (0.15 + 0.85 * L.smoothstep(60, 600, r)) * (55 * (L.fbm(x, y, 0.0018, 4, 7.1) - H0) + 10 * L.fbm(x, y, 0.007, 3, 2.0))
    mtn = 520 * L.smoothstep(3000, 5200, y + 600 * L.fbm(x, 0, 0.0005, 3, 9.0))
    return roll + mtn


H = C.shelf(h, 28, 70)
veld = L.noisy("Veld", (0.72, 0.64, 0.38), (0.58, 0.56, 0.30), scale=0.3, rough=0.95, bump=0.3, c3=(0.46, 0.50, 0.24), scale2=0.02)
yard = L.noisy("Yard", (0.62, 0.48, 0.32), (0.68, 0.54, 0.36), scale=0.7, rough=0.95, bump=0.3)
far_veld = L.noisy("FarVeld", (0.66, 0.60, 0.36), (0.50, 0.50, 0.28), scale=0.004, rough=0.95, bump=0.1, c3=(0.40, 0.40, 0.30), scale2=0.0015)


def assign(ob):
    me = ob.data
    for m in (veld, yard, far_veld):
        me.materials.append(m)
    for p in me.polygons:
        r = math.hypot(p.center.x, p.center.y)
        p.material_index = 1 if r < 32 + 5 * L.fbm(p.center.x, p.center.y, 0.05, 2) else (0 if r < 600 else 2)


C.rings(H, veld, assign=assign)

thatch = L.noisy("Thatch", (0.58, 0.48, 0.30), (0.46, 0.38, 0.24), scale=8, rough=0.95, bump=1.0)
walls = [L.noisy(f"Rondavel{i}", c, tuple(v * 0.9 for v in c), scale=2, rough=0.9, bump=0.2)
         for i, c in enumerate([(0.93, 0.92, 0.88), (0.62, 0.78, 0.82), (0.95, 0.86, 0.70), (0.80, 0.86, 0.72), (0.90, 0.72, 0.68)])]
door = L.flat("Door", (0.20, 0.30, 0.42))
roof_iron = L.corrugated("IronRoof", color=(0.70, 0.71, 0.72), rust=(0.45, 0.28, 0.18), rust_amount=0.4)
huts = [L.hide_template(B.round_hut(f"Rond{i}", walls[i % len(walls)], thatch if i % 4 else roof_iron, r=3.0, h=2.5, door=door)) for i in range(6)]
stone = L.noisy("Stone", (0.55, 0.52, 0.46), (0.42, 0.40, 0.36), scale=6, rough=0.9, bump=0.8)
aloe_leaf = L.noisy("AloeLeaf", (0.38, 0.48, 0.38), (0.30, 0.40, 0.32), scale=4, rough=0.6)
aloe_fl = L.flat("AloeFlower", (0.86, 0.30, 0.14), rough=0.6)
aloes = [L.hide_template(F.aloe(f"Aloe{i}", aloe_leaf, aloe_fl, size=rnd.uniform(1.2, 1.8), seed=i)) for i in range(3)]
bark = L.noisy("Bark", (0.32, 0.27, 0.22), (0.44, 0.38, 0.30), scale=5, rough=0.9, bump=0.5)
cards = L.leaf_card("ThornLeaves", (0.30, 0.40, 0.18), (0.38, 0.46, 0.22), tiles=(5, 3), width=0.45, power=0.6)
inner = L.flat("ThornInner", (0.14, 0.20, 0.08))
thorn = [L.hide_template(F.acacia(f"Acacia{i}", bark, cards, inner, height=rnd.uniform(5, 7), spread=rnd.uniform(4, 6), seed=i)) for i in range(2)]


def kraal(x, y, r=7.0):
    parts = []
    n = 26
    for k in range(n):
        a = 2 * math.pi * k / n
        if k in (0, 1):
            continue
        parts.append(L.blob("KraalStone", 0.55, (x + r * math.cos(a), y + r * math.sin(a), H(x, y) + 0.3), stone,
                            squash=(1.3, 0.8, 0.8), rough=0.3, seed=k, subdiv=1))
    L.join(parts, "Kraal")


# homesteads: rondavel clusters on the slopes facing the court
def homestead(x, y, r):
    for k in range(r.randint(2, 5)):
        hx, hy = x + r.uniform(-12, 12), y + r.uniform(-12, 12)
        L.instance(r.choice(huts), (hx, hy, H(hx, hy) - 0.1), r.uniform(0, 6.28), r.uniform(0.9, 1.15))
    if r.random() < 0.5:
        kraal(x + r.uniform(-20, 20), y + r.uniform(-20, 20))


C.scatter(C.res(25, 120, 120), (-1500, 1500, -1200, 2500), lambda x, y: math.hypot(x, y) > 70, homestead, seed=2)
for k, (x, y) in enumerate(((-24, 24), (-34, 4), (26, 26), (36, 6))):
    L.instance(huts[k], (x, y, H(x, y) - 0.1), math.atan2(-x, -y), 1.0)
C.scatter(C.res(80, 500, 500), (-300, 300, -300, 300), lambda x, y: math.hypot(x, y) > 30,
          lambda x, y, r: L.instance(r.choice(aloes), (x, y, H(x, y)), r.uniform(0, 6.28), r.uniform(0.8, 1.2)), seed=4)
C.scatter(C.res(40, 250, 250), (-1200, 1200, -1200, 1500), lambda x, y: math.hypot(x, y) > 45,
          lambda x, y, r: L.instance(r.choice(thorn), (x, y, H(x, y)), r.uniform(0, 6.28), r.uniform(0.8, 1.2)), seed=6)

C.finish("qunu", rot_deg=0, sky=dict(clouds=0.35, cloud_seed=12.0, sun_elev_deg=44, sun_rot_deg=150, aerosol=0.9,
                                    strength=0.45, haze_density=0.00005, haze_color=(0.86, 0.88, 0.92), sun_energy=4.8),
         cams={"broadcast": ((0, -27, 9.5), (0, 8, 2), 24), "veld": ((-12, -16, 3.5), (40, 400, 20), 26)})
