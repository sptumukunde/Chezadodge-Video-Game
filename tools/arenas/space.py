"""Outer Space arena: a court on a lunar base. Grey cratered regolith, glass
habitat domes, antenna masts with beacons, solar arrays, and Earth hanging in
the black sky. Open court or stands (the game lights it as a night arena)."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arena_common as C
import bpy
import arena_lib as L
import arena_build as B

L.reset_scene()
rnd = random.Random(83)
CRATERS = [c for c in ((rnd.uniform(-3000, 3000), rnd.uniform(-3000, 3000), rnd.uniform(20, 380)) for _ in range(200)) if math.hypot(c[0], c[1]) > c[2] * 1.7 + 160]
CRATERS += [c for c in ((rnd.uniform(-400, 400), rnd.uniform(-400, 400), rnd.uniform(6, 30)) for _ in range(80)) if math.hypot(c[0], c[1]) > c[2] * 1.7 + 80]


def h(x, y):
    g = 25 * L.fbm(x, y, 0.0012, 4, 1.7) + 3 * L.fbm(x, y, 0.02, 2, 3.0)
    for cx, cy, cr in CRATERS:
        d = math.hypot(x - cx, y - cy) / cr
        if d < 1.6:
            bowl = -0.28 * cr * max(0.0, 1 - d * d)
            rim = 0.09 * cr * math.exp(-((d - 1.0) / 0.18) ** 2)
            g += bowl + rim
    return g


H = C.shelf(h, 30, 70)
regolith = L.noisy("Regolith", (0.46, 0.45, 0.43), (0.36, 0.35, 0.34), scale=0.5, rough=0.98, bump=0.6, c3=(0.56, 0.55, 0.52), scale2=0.03)
pad = L.noisy("LandingPad", (0.30, 0.31, 0.33), (0.36, 0.37, 0.39), scale=1.5, rough=0.7, bump=0.1)


def assign(ob):
    me = ob.data
    for m in (regolith, pad):
        me.materials.append(m)
    for p in me.polygons:
        p.material_index = 1 if math.hypot(p.center.x, p.center.y) < 32 else 0


C.rings(H, regolith, assign=assign, sizes=(360, 2400, 12000))
glass = L.flat("DomeGlass", (0.55, 0.70, 0.80), rough=0.05, metal=0.3)
frame = L.flat("Frame", (0.80, 0.82, 0.85), rough=0.35, metal=0.8)
beacon = L.flat("Beacon", (1.0, 0.25, 0.2), emit=(1.0, 0.25, 0.2))
beacon.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 6.0
window = L.flat("HabitatLight", (1.0, 0.86, 0.6), emit=(1.0, 0.86, 0.6))
window.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 3.0
panel = L.flat("SolarCell", (0.08, 0.12, 0.30), rough=0.15, metal=0.6)

for k, (x, y, r) in enumerate(((-70, 100, 14), (0, 130, 20), (70, 105, 12), (-120, 30, 9), (120, 40, 10))):
    d = B.dome(f"Dome{k}", r, glass, (x, y, H(x, y)), frame)
    L.cylinder(f"DomeGlow{k}", r * 0.6, r * 0.6, 0.4, (x, y, H(x, y) + 0.3), window, seg=24)
for k, (x, y) in enumerate(((-34, 60), (34, 60), (-52, -30), (52, -30))):
    m = B.mast("Mast", 18 + 6 * (k % 2), frame, beacon)
    m.location = (x, y, H(x, y))
for k in range(18):
    x, y = -120 + (k % 6) * 14, 90 + (k // 6) * 12
    p = L.box("SolarPanel", (10, 5, 0.2), (x, y, H(x, y) + 2.6), panel)
    p.rotation_euler.x = math.radians(35)
    L.cylinder("PanelPost", 0.15, 0.15, 2.4, (x, y, H(x, y)), frame, seg=6)
# Earth: big lit sphere low in the sky behind the base
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=520, location=(-600, 5200, 640))
earth = bpy.context.object
earth.name = "Earth"
em = bpy.data.materials.new("Earth")
em.use_nodes = True
nt = em.node_tree
p = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord")
n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 0.004; n.inputs["Detail"].default_value = 10
c = nt.nodes.new("ShaderNodeTexNoise"); c.inputs["Scale"].default_value = 0.009; c.inputs["Detail"].default_value = 8
land = nt.nodes.new("ShaderNodeValToRGB")
land.color_ramp.elements[0].position = 0.50; land.color_ramp.elements[0].color = (*L.lin((0.04, 0.18, 0.50)), 1)
land.color_ramp.elements[1].position = 0.53; land.color_ramp.elements[1].color = (*L.lin((0.36, 0.44, 0.18)), 1)
land.color_ramp.elements.new(0.62).color = (*L.lin((0.62, 0.50, 0.30)), 1)
cl = nt.nodes.new("ShaderNodeMapRange"); cl.inputs["From Min"].default_value = 0.55; cl.inputs["From Max"].default_value = 0.7
mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.inputs[7].default_value = (1, 1, 1, 1)
nt.links.new(tc.outputs["Object"], n.inputs["Vector"]); nt.links.new(tc.outputs["Object"], c.inputs["Vector"])
nt.links.new(n.outputs["Fac"], land.inputs["Fac"]); nt.links.new(c.outputs["Fac"], cl.inputs["Value"])
nt.links.new(cl.outputs["Result"], mix.inputs[0]); nt.links.new(land.outputs["Color"], mix.inputs[6])
nt.links.new(mix.outputs[2], p.inputs["Base Color"]); nt.links.new(mix.outputs[2], p.inputs["Emission Color"])
p.inputs["Emission Strength"].default_value = 0.6
earth.data.materials.append(em)
L.collection("Arena").objects.link(earth); bpy.context.scene.collection.objects.unlink(earth)
earth["bake"] = 1024
earth["bake_emit"] = 1.6

C.finish("space", rot_deg=0, sky=dict(clouds=0.0, sun_elev_deg=24, sun_rot_deg=120, air=0.0, aerosol=0.0,
                                     strength=0.0, haze_density=0.0, sun_energy=5.0),
         cams={"broadcast": ((0, -27, 9.5), (0, 8, 2), 24), "base": ((-10, -22, 4.0), (-600, 4500, 500), 30)})
