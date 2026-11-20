"""High Tides arena: a court on the deck of a container ship at sea. Container
stacks, the bridge tower, lifeboats and cranes; open ocean all round with
other ships and a lighthouse island on the horizon. Open court or stands."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arena_common as C
import bpy
import arena_lib as L
import arena_build as B

L.reset_scene()
rnd = random.Random(97)
SEA = -14.0
LEN, BEAM = 300.0, 48.0          # built along X, then turned so the bridge is ahead of the broadcast camera
deck = L.noisy("Deck", (0.30, 0.40, 0.34), (0.36, 0.46, 0.40), scale=0.5, rough=0.7, bump=0.2, c3=(0.40, 0.30, 0.22), scale2=0.12)
hull = L.noisy("Hull", (0.12, 0.16, 0.22), (0.16, 0.20, 0.26), scale=0.3, rough=0.6, bump=0.1, c3=(0.42, 0.20, 0.14), scale2=0.05)
antifoul = L.flat("Antifoul", (0.55, 0.16, 0.12), rough=0.7)
white = L.noisy("Superstructure", (0.92, 0.92, 0.90), (0.84, 0.84, 0.82), scale=1, rough=0.6, bump=0.05)
rail = L.flat("Rail", (0.92, 0.80, 0.20), rough=0.5, metal=0.3)
window = L.flat("BridgeGlass", (0.10, 0.16, 0.22), rough=0.05, metal=0.6)
steel = L.flat("Steel", (0.50, 0.52, 0.55), rough=0.4, metal=0.8)
orange = L.flat("Lifeboat", (0.98, 0.45, 0.10), rough=0.5)

# hull: deck slab at court level, tapered bow at +X, freeboard down to the sea
L.box("Deck", (LEN, BEAM, 0.6), (0, 0, -0.33), deck)
L.box("Hull", (LEN, BEAM - 0.4, -SEA + 8), (0, 0, (SEA - 8) / 2 - 0.6), hull)
L.box("Waterline", (LEN + 0.2, BEAM, 1.6), (0, 0, SEA + 0.6), antifoul)
bow = L.mesh_obj("Bow", [(LEN / 2, -BEAM / 2, -0.03), (LEN / 2, BEAM / 2, -0.03), (LEN / 2 + 34, 0, 1.0),
                         (LEN / 2, -BEAM / 2, SEA - 6), (LEN / 2, BEAM / 2, SEA - 6), (LEN / 2 + 26, 0, SEA - 6)],
                 [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], hull)
# railings along both sides
for s in (-1, 1):
    L.box("Rail", (LEN, 0.08, 0.08), (0, s * (BEAM / 2 - 0.3), 1.1), rail)
    L.box("DeckStripe", (LEN, 0.3, 0.02), (0, s * (BEAM / 2 - 2.2), 0.0), L.flat("DeckStripe", (0.92, 0.80, 0.20)))
    L.box("Rail", (LEN, 0.06, 0.06), (0, s * (BEAM / 2 - 0.3), 0.6), rail)
    for k in range(int(LEN / 3)):
        L.box("Stanchion", (0.06, 0.06, 1.1), (-LEN / 2 + k * 3, s * (BEAM / 2 - 0.3), 0.55), rail)
# bridge tower aft (-X), container stacks fore and aft of the court
br = -LEN / 2 + 26  # aft end; after the turn this is far ahead (+Y)
L.box("Bridge", (22, BEAM - 6, 26), (br, 0, 13), white)
for f in range(5):
    L.box("BridgeWin", (22.2, BEAM - 8, 1.4), (br, 0, 4 + f * 4.6), window)
L.box("Wheelhouse", (10, BEAM + 6, 4), (br, 0, 28), white)
L.box("WheelhouseWin", (10.2, BEAM + 6.2, 1.6), (br, 0, 28.6), window)
L.cylinder("Funnel", 4, 3.4, 14, (br - 12, 0, 20), L.flat("Funnel", (0.12, 0.30, 0.55), rough=0.5), seg=20)
for s in (-1, 1):
    L.cylinder("Lifeboat", 1.4, 1.4, 8, (br + 4, s * (BEAM / 2 + 1.5), 9), orange, seg=12, rot=(0, math.radians(90), 0))
cols = [(0.70, 0.18, 0.14), (0.14, 0.34, 0.60), (0.20, 0.50, 0.30), (0.86, 0.62, 0.16), (0.60, 0.60, 0.62), (0.30, 0.30, 0.34), (0.82, 0.40, 0.18)]
cmats = [L.corrugated(f"Container{i}", color=c, rust=tuple(v * 0.6 for v in c), rust_amount=0.15, painted=True) for i, c in enumerate(cols)]


def bay(x0, x1):
    x = x0
    while x < x1:
        for row in range(-6, 7):
            stack = rnd.randint(2, 6)
            for tier in range(stack):
                B.container("Box", rnd.choice(cmats), (x, row * 2.6, 1.3 + tier * 2.62), 0.0)
        x += 13.0


bay(br + 16, -40)
bay(40, LEN / 2 - 12)
# deck cranes
for x in (-60, 70):
    for s in (-1, 1):
        post = L.cylinder("CranePost", 1.0, 0.8, 18, (x, s * (BEAM / 2 - 3), 0), steel, seg=10)
        jib = L.box("Jib", (24, 0.8, 0.8), (x + 10, s * (BEAM / 2 - 3), 18), steel)
        jib.rotation_euler.y = math.radians(-18)
# turn the whole ship 90 degrees: bow toward -Y (behind the camera), bridge at +Y
import mathutils
R = mathutils.Matrix.Rotation(math.radians(-90), 4, 'Z')
bpy.context.view_layer.update()  # matrix_world is stale until the scene updates
for ob in list(bpy.data.objects):
    if ob.type == 'MESH' and ob.parent is None:
        ob.matrix_world = R @ ob.matrix_world
# ocean, other ships, lighthouse island
L.box("Lake", (16000, 16000, 0.1), (0, 0, SEA), L.water("Water", deep=(0.04, 0.16, 0.24), rough=0.06, wave_scale=0.08, wave=0.3))
for k, (x, y, sc) in enumerate(((-1800, 2600, 1.0), (2400, 3800, 0.8), (600, 5200, 1.2), (-3200, -2600, 0.9))):
    L.box("FarShip", (180 * sc, 30 * sc, 18 * sc), (x, y, SEA + 9 * sc), L.flat(f"FarHull{k}", (0.20, 0.24, 0.30)), rot_z=rnd.uniform(-0.3, 0.3))
    L.box("FarBridge", (20 * sc, 26 * sc, 22 * sc), (x - 70 * sc, y, SEA + 28 * sc), white)
island = L.blob("Island", 1.0, (2800, 6200, SEA - 10), L.noisy("IslandRock", (0.36, 0.40, 0.26), (0.46, 0.42, 0.34), scale=0.02), squash=(500, 340, 160), rough=0.35, seed=4, subdiv=4)
L.cylinder("Lighthouse", 9, 6, 60, (2800, 6200, SEA + 140), L.flat("LighthouseWhite", (0.95, 0.94, 0.92)), seg=16)
L.cylinder("LighthouseBand", 7.6, 7.2, 8, (2800, 6200, SEA + 170), L.flat("LighthouseRed", (0.80, 0.14, 0.12)), seg=16)

C.finish("hightides", rot_deg=0, export_kw={"terrain_res": {}, "clear_r": 0.0},
         sky=dict(clouds=0.5, cloud_seed=40.0, sun_elev_deg=36, sun_rot_deg=230, aerosol=1.0, strength=0.45,
                  haze_density=0.00004, haze_color=(0.84, 0.88, 0.94), sun_energy=4.8),
         cams={"broadcast": ((0, -27, 9.5), (0, 8, 2), 24), "deck": ((-10, -18, 3.0), (60, 400, 10), 24)})
