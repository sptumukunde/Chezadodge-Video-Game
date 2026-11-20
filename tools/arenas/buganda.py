"""Ancient Buganda arena: a royal compound. A great thatched dome (in the style
of the Kasubi tombs) behind the court, a woven reed fence, barkcloth fig
trees, matooke groves and rolling green hills. Open court or stands."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arena_common as C
import bpy
from mathutils import Vector
import arena_lib as L
import arena_flora as F
import arena_build as B

L.reset_scene()
rnd = random.Random(31)
H0 = L.fbm(0, 0, 0.002, 4, 2.2)


def h(x, y):
    r = math.hypot(x, y)
    hills = (0.15 + 0.85 * L.smoothstep(60, 500, r)) * (70 * (L.fbm(x, y, 0.0022, 4, 2.2) - H0) + 18 * L.fbm(x, y, 0.008, 3, 5.0))
    return hills + 0.05 * max(0.0, r - 200)


H = C.shelf(h, 30, 70)
grass = L.noisy("Grass", (0.30, 0.44, 0.15), (0.40, 0.52, 0.19), scale=0.4, rough=0.9, bump=0.3, c3=(0.50, 0.36, 0.22), scale2=0.05)
earth = L.noisy("Earth", (0.56, 0.36, 0.22), (0.64, 0.42, 0.26), scale=0.6, rough=0.95, bump=0.3)
fields = L.field_patchwork("Fields", [(0.24, 0.40, 0.12), (0.30, 0.46, 0.14), (0.20, 0.34, 0.10), (0.36, 0.50, 0.18), (0.46, 0.36, 0.22)], patch=(40, 30))


def assign(ob):
    me = ob.data
    for m in (grass, earth, fields):
        me.materials.append(m)
    for p in me.polygons:
        r = math.hypot(p.center.x, p.center.y)
        p.material_index = 1 if r < 34 + 6 * L.fbm(p.center.x, p.center.y, 0.05, 2) else (0 if r < 220 else 2)


C.rings(H, grass, assign=assign)

thatch = L.noisy("Thatch", (0.50, 0.40, 0.25), (0.42, 0.33, 0.20), scale=9, rough=0.95, bump=1.2)
reed = L.noisy("Reed", (0.62, 0.52, 0.34), (0.50, 0.42, 0.26), scale=14, rough=0.9, bump=0.6)
door = L.flat("DoorDark", (0.10, 0.08, 0.06))
dome = B.thatch_dome("RoyalHouse", thatch, r=11.0, h=10.5, door=door)
dome.location = (0, 52, H(0, 52))
for i, (x, y) in enumerate(((-30, 40), (30, 42), (-44, 14), (44, 18))):
    sm = B.thatch_dome(f"House{i}", thatch, r=4.2, h=4.6, door=door)
    sm.location = (x, y, H(x, y))
    sm.rotation_euler.z = math.atan2(-x, y) + math.pi
fence = B.reed_fence("ReedFence", 27.0, 2.2, reed, gap_deg=30)
fence.rotation_euler.z = math.radians(180)  # entrance faces the royal house

bark = L.noisy("Bark", (0.36, 0.30, 0.24), (0.48, 0.40, 0.32), scale=5, rough=0.9, bump=0.5)
fig_cards = L.leaf_card("FigLeaves", (0.16, 0.30, 0.10), (0.24, 0.38, 0.12), tiles=(3, 2), width=0.45, power=0.7)
inner = L.flat("FigInner", (0.07, 0.13, 0.04))
leaf_ban = L.leaf("LeafBanana", (0.36, 0.56, 0.16), (0.48, 0.64, 0.22), translucency=0.35)
stem_ban = L.noisy("BananaStem", (0.40, 0.48, 0.24), (0.50, 0.46, 0.30), scale=3)
figs = [L.hide_template(F.round_tree(f"Fig{i}", bark, fig_cards, inner, height=14, crown=8, seed=i)) for i in range(3)]
bans = [L.hide_template(F.banana(f"Ban{i}", stem_ban, leaf_ban, height=3.0, seed=i)) for i in range(3)]
far_leaf = L.leaf("FarCanopy", (0.16, 0.30, 0.09), (0.24, 0.38, 0.12), translucency=0.1)
far = [L.hide_template(F.round_tree(f"FarTree{i}", bark, far_leaf, far_leaf, height=12, crown=6, seed=i + 9, n_cards=1)) for i in range(2)]

for x, y in ((-20, 30), (22, 32), (-38, -10), (40, -6), (-16, -40), (18, -42)):
    L.instance(rnd.choice(figs), (x, y, H(x, y)), rnd.uniform(0, 6.28), rnd.uniform(0.85, 1.1))
C.scatter(C.res(300, 1600, 1600), (-500, 500, -500, 500), lambda x, y: math.hypot(x, y) > 64,
          lambda x, y, r: L.instance(r.choice(bans), (x, y, H(x, y)), r.uniform(0, 6.28), r.uniform(0.8, 1.25)), seed=3)
C.scatter(C.res(300, 2000, 2000), (-2500, 2500, -2500, 2500), lambda x, y: math.hypot(x, y) > 120,
          lambda x, y, r: L.instance(r.choice(far + figs), (x, y, H(x, y)), r.uniform(0, 6.28), r.uniform(0.8, 1.3)), seed=5)

C.finish("buganda", rot_deg=0, sky=dict(clouds=0.45, cloud_seed=4.0, sun_elev_deg=40, sun_rot_deg=200, aerosol=1.2,
                                       strength=0.45, haze_density=0.00006, haze_color=(0.84, 0.88, 0.92), sun_energy=4.6),
         cams={"broadcast": ((0, -27, 9.5), (0, 8, 2), 24), "compound": ((-14, -18, 3.5), (0, 52, 6), 26)})
