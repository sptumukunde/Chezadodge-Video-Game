"""Afro-Futuristic arena (night): a dark plaza with glowing lines, towers
banded with neon in kente-style colour blocks, ring arches and floating
platforms over a city that runs to the horizon. Open court or stands."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arena_common as C
import bpy
import arena_lib as L
import arena_build as B

L.reset_scene()
rnd = random.Random(71)


def h(x, y):
    return 0.0


plaza = L.noisy("Plaza", (0.08, 0.10, 0.16), (0.12, 0.14, 0.22), scale=0.4, rough=0.5, bump=0.1)
C.rings(h, plaza, sizes=(360, 2400, 9000))
glow = [L.flat(f"Neon{i}", c, rough=0.3, emit=c) for i, c in enumerate(
    [(0.46, 0.94, 0.84), (0.66, 0.54, 1.0), (1.0, 0.78, 0.30), (1.0, 0.36, 0.42), (0.36, 0.70, 1.0)])]
for g in glow:
    g.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 3.0
shell = [L.noisy(f"Shell{i}", c, tuple(v * 0.8 for v in c), scale=0.2, rough=0.35, bump=0.05)
         for i, c in enumerate([(0.10, 0.12, 0.20), (0.16, 0.14, 0.24), (0.20, 0.22, 0.28)])]
glass = L.flat("Glass", (0.10, 0.16, 0.26), rough=0.05, metal=0.7)

# glowing lines in the plaza (radial and rings), clear of the court
for k in range(12):
    a = 2 * math.pi * k / 12
    L.box("Line", (60, 0.25, 0.02), (math.cos(a) * 52, math.sin(a) * 52, 0.01), glow[k % 2], rot_z=a)
for r in (36, 70):
    seg = 64
    for k in range(seg):
        a = 2 * math.pi * (k + 0.5) / seg
        L.box("Ring", (2 * math.pi * r / seg * 0.8, 0.3, 0.02), (math.cos(a) * r, math.sin(a) * r, 0.01), glow[0], rot_z=a + math.pi / 2)


def tower(x, y, r):
    w, d = r.uniform(18, 40), r.uniform(18, 40)
    ht = r.choice((40, 60, 90, 130, 180, 240)) * (1.4 if math.hypot(x, y) > 400 else 1.0)
    parts = [L.box("Tower", (w, d, ht), (0, 0, ht / 2), r.choice(shell))]
    # kente-style banding: stacked colour blocks of light around the tower
    z = 6.0
    while z < ht - 4:
        bh = r.choice((0.6, 0.6, 1.2, 2.4))
        parts.append(L.box("Band", (w + 0.2, d + 0.2, bh), (0, 0, z), r.choice(glow)))
        z += bh + r.uniform(4, 12)
    parts.append(L.box("Crown", (w * 0.6, d * 0.6, 3), (0, 0, ht + 1.5), r.choice(glow)))
    ob = L.join(parts, "Tower")
    ob.location = (x, y, 0)
    ob.rotation_euler.z = r.uniform(0, 1.5)


C.scatter(C.res(60, 420, 420), (-3000, 3000, 120, 3500), lambda x, y: True, tower, seed=3)
C.scatter(C.res(20, 120, 120), (-3000, 3000, -3000, -200), lambda x, y: True, tower, seed=4)
C.scatter(C.res(20, 140, 140), (-3500, -150, -1500, 1500), lambda x, y: True, tower, seed=5)
C.scatter(C.res(20, 140, 140), (150, 3500, -1500, 1500), lambda x, y: True, tower, seed=6)
# ring arches over the plaza approaches and floating platforms
for k, a in enumerate((60, 120, 240, 300)):
    ar = math.radians(a)
    ring = L.cylinder("Arch", 14, 14, 1.2, (0, 0, 0), glow[k % len(glow)], seg=40, rot=(math.radians(90), 0, 0), cap=False)
    ring.location = (math.cos(ar) * 62, math.sin(ar) * 62, 12)
    ring.rotation_euler.z = ar + math.pi / 2
for k in range(6):
    x, y = rnd.uniform(-120, 120), rnd.uniform(60, 200)
    p = L.cylinder("Platform", 9, 7, 1.2, (x, y, rnd.uniform(25, 60)), rnd.choice(shell), seg=24)
    L.cylinder("PlatformGlow", 9.1, 9.1, 0.25, (x, y, p.location.z), rnd.choice(glow), seg=24, cap=False)

C.finish("future", rot_deg=0, sky=dict(clouds=0.2, cloud_seed=2.0, sun_elev_deg=-8, sun_rot_deg=200, aerosol=1.0,
                                      strength=0.15, haze_density=0.0, sun_energy=0.0),
         cams={"broadcast": ((0, -27, 9.5), (0, 8, 2), 24), "city": ((-10, -18, 3.0), (0, 600, 120), 26)},
         render={"exposure": 0.5})
