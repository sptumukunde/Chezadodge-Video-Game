"""Scaffolding shared by the arena scripts: args, terrain rings, placement,
render-or-export. Each arena script supplies its own height function,
materials and dressing."""
import sys
import os
import math
import random
import bpy
from mathutils import Vector
import arena_lib as L
import arena_flora as F

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = args[0] if args else '/tmp/arenas'
QUICK = '--quick' in args
GAME = '--game' in args
os.makedirs(OUT, exist_ok=True)
if GAME:
    F.CARD_SCALE = 0.3
    F.CARD_SIZE = 1.6
    F.CORE_SUBDIV = 1


def res(quick, full, game):
    return quick if QUICK else (game if GAME else full)


def shelf(h_fn, r0=26.0, r1=60.0, level=0.0):
    """Flatten the ground around the court."""
    def fn(x, y):
        r = math.hypot(x, y)
        s = 1 - L.smoothstep(r0, r1, r)
        return h_fn(x, y) * (1 - s) + level * s
    return fn


def rings(h_fn, near_mat, mid_mat=None, far_mat=None, sizes=(360, 2400, 14000), assign=None):
    mid_mat = mid_mat or near_mat
    far_mat = far_mat or mid_mat

    def ring(inner, drop):
        def fn(x, y):
            h = h_fn(x, y)
            return h - drop if (abs(x) < inner and abs(y) < inner) else h
        return fn
    near = L.heightfield("TerrainNear", sizes[0], res(110, 300, 100), h_fn, near_mat)
    mid = L.heightfield("TerrainMid", sizes[1], res(140, 560, 160), ring(sizes[0] / 2 - 10, 1.5), mid_mat)
    far = L.heightfield("TerrainFar", sizes[2], res(100, 300, 64), ring(sizes[1] / 2 - 50, 5.0), far_mat)
    if assign:
        for t in (near, mid, far):
            t.data.materials.clear()
            assign(t)
    return near, mid, far


def scatter(n, area, ok, place, seed=1, tries=40):
    """Rejection-sample n placements in area=(x0,x1,y0,y1); ok(x,y)->bool."""
    rnd = random.Random(seed)
    done = 0
    for _ in range(n * tries):
        if done >= n:
            break
        x, y = rnd.uniform(area[0], area[1]), rnd.uniform(area[2], area[3])
        if not ok(x, y):
            continue
        place(x, y, rnd)
        done += 1
    return done


def finish(name, rot_deg=0.0, cams=None, export_kw=None, sky=None, render=None):
    if GAME:
        import game_export
        game_export.export(os.path.join(OUT, name + '.glb'), rot_deg=rot_deg, **(export_kw or {}))
        sys.exit(0)
    sky = sky or {}
    L.sky_world(**sky)
    L.render_settings(samples=48 if QUICK else 128, res=(960, 540) if QUICK else (1600, 900), **(render or {}))
    cams = cams or {"broadcast": ((0, -27, 9.5), (0, 2, 0), 24)}
    only = [a for a in args if a.startswith('--cam=')]
    for key, (loc, tgt, lens) in cams.items():
        if only and only[0][6:] != key:
            continue
        L.render_to(L.camera("Cam" + key, loc, tgt, lens=lens), os.path.join(OUT, f"{name}_{key}.png"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, name + ".blend"))
    print("DONE")
