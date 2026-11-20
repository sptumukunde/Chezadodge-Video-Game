"""Shared building blocks for ChezaDodge open-court arenas (Blender 5.x, bpy).

Coordinates: Blender Z-up, metres. The court is centred on the origin and runs
along the Y axis. Everything is procedural: no external textures are needed, so
arenas can be rebuilt from source at any time.
"""
import os
import bpy
import bmesh
import math
import random
from mathutils import Vector, noise, Matrix

# ---------------------------------------------------------------- scene setup

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    return sc


def collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def link(obj, col_name="Arena"):
    collection(col_name).objects.link(obj)
    return obj


def _world_clouds(nt, sky_col, coverage, height, scale, seed):
    """Cumulus projected onto a plane at `height` from the view direction,
    mixed over the sky colour. Lives in the world shader, so it never gets
    aerial-perspective haze and has no edge."""
    N, lk = nt.nodes, nt.links.new
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    lk(tc.outputs["Generated"], sep.inputs[0])

    def m(op, a=None, b=None, va=None, vb=None):
        n = N.new("ShaderNodeMath")
        n.operation = op
        if a is not None:
            lk(a, n.inputs[0])
        else:
            n.inputs[0].default_value = va
        if b is not None:
            lk(b, n.inputs[1])
        elif vb is not None:
            n.inputs[1].default_value = vb
        return n
    dz = m('MAXIMUM', sep.outputs[2], vb=0.02)
    t = m('DIVIDE', va=height * scale, b=dz.outputs[0])
    px = m('MULTIPLY', sep.outputs[0], t.outputs[0])
    py = m('MULTIPLY', sep.outputs[1], t.outputs[0])
    cmb = N.new("ShaderNodeCombineXYZ")
    lk(m('ADD', px.outputs[0], vb=seed).outputs[0], cmb.inputs[0])
    lk(m('MULTIPLY', py.outputs[0], vb=1.6).outputs[0], cmb.inputs[1])
    cmb.inputs[2].default_value = seed * 0.3
    n = N.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 1.0
    n.inputs["Detail"].default_value = 10
    n.inputs["Roughness"].default_value = 0.6
    lk(cmb.outputs[0], n.inputs["Vector"])
    r = N.new("ShaderNodeMapRange")
    r.inputs["From Min"].default_value = 1.0 - coverage
    r.inputs["From Max"].default_value = 1.0 - coverage + 0.12
    lk(n.outputs["Fac"], r.inputs["Value"])
    fade = N.new("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value = 0.03
    fade.inputs["From Max"].default_value = 0.18
    lk(sep.outputs[2], fade.inputs["Value"])
    fac = m('MULTIPLY', r.outputs["Result"], fade.outputs["Result"])
    # cloud brightness follows the sky's own brightness so exposure stays sane
    bw = N.new("ShaderNodeRGBToBW")
    lk(sky_col, bw.inputs[0])
    bright = m('MULTIPLY', bw.outputs[0], vb=2.4)
    shade = N.new("ShaderNodeMapRange")
    shade.inputs["From Min"].default_value = 1.0 - coverage
    shade.inputs["From Max"].default_value = 1.0
    shade.inputs["To Min"].default_value = 1.0
    shade.inputs["To Max"].default_value = 0.72
    lk(n.outputs["Fac"], shade.inputs["Value"])
    cval = m('MULTIPLY', bright.outputs[0], shade.outputs["Result"])
    ccol = N.new("ShaderNodeCombineColor")
    for i in range(3):
        lk(cval.outputs[0], ccol.inputs[i])
    mix = N.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    lk(fac.outputs[0], mix.inputs[0])
    lk(sky_col, mix.inputs[6])
    lk(ccol.outputs[0], mix.inputs[7])
    return mix.outputs[2]


def sky_world(sun_elev_deg=38.0, sun_rot_deg=140.0, air=1.0, aerosol=1.0, strength=0.9,
              haze_density=0.0, haze_color=(0.75, 0.82, 0.9), haze_height=1600.0, sun_energy=4.0, haze_radius=12000.0,
              clouds=0.0, cloud_height=1800.0, cloud_scale=0.00045, cloud_seed=0.0):
    """Physical sky + matching sun lamp. Optional homogeneous haze volume."""
    sc = bpy.context.scene
    w = bpy.data.worlds.new("Sky")
    sc.world = w
    nt = w.node_tree if w.node_tree else None
    if nt is None:
        w.use_nodes = True
        nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.radians(sun_elev_deg)
    sky.sun_rotation = math.radians(sun_rot_deg)
    sky.air_density = air
    sky.aerosol_density = aerosol
    sky.sun_disc = False  # the sun lamp provides direct light; disc is far too hot
    bg.inputs[1].default_value = strength
    sky_col = sky.outputs[0]
    if clouds > 0:
        sky_col = _world_clouds(nt, sky_col, clouds, cloud_height, cloud_scale, cloud_seed)
    nt.links.new(sky_col, bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    if haze_density > 0:
        mist_haze(haze_density, haze_color)
    # Sun lamp pointing the same way as the sky's sun.
    ld = bpy.data.lights.new("Sun", 'SUN')
    ld.energy = sun_energy
    ld.angle = math.radians(0.6)
    ld.color = (1.0, 0.96, 0.9)
    lo = bpy.data.objects.new("Sun", ld)
    lo.rotation_euler = (math.radians(90 - sun_elev_deg), 0, math.radians(sun_rot_deg + 90))
    link(lo, "Lighting")
    return sky


def cloud_layer(z=1600.0, size=240000.0, coverage=0.45, scale=0.00045, seed=0.0, fade=60000.0):
    """Fair-weather cumulus as an alpha-masked noise sheet, faded out with
    distance so its edge never shows. `scale` is in cycles per metre."""
    m, nt, p, out = _mat("Clouds")
    N, lk = nt.nodes, nt.links.new
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (seed * 1000, seed * 700, 0)
    mp.inputs["Scale"].default_value = (scale, scale * 1.6, scale)
    lk(tc.outputs["Object"], mp.inputs["Vector"])
    n = N.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 1.0
    n.inputs["Detail"].default_value = 10
    n.inputs["Roughness"].default_value = 0.6
    lk(mp.outputs["Vector"], n.inputs["Vector"])
    r = N.new("ShaderNodeMapRange")
    r.inputs["From Min"].default_value = 1.0 - coverage
    r.inputs["From Max"].default_value = 1.0 - coverage + 0.12
    lk(n.outputs["Fac"], r.inputs["Value"])
    # radial fade
    ln = N.new("ShaderNodeVectorMath")
    ln.operation = 'LENGTH'
    lk(tc.outputs["Object"], ln.inputs[0])
    fd = N.new("ShaderNodeMapRange")
    fd.inputs["From Min"].default_value = fade
    fd.inputs["From Max"].default_value = fade * 0.4
    lk(ln.outputs["Value"], fd.inputs["Value"])
    mul = N.new("ShaderNodeMath")
    mul.operation = 'MULTIPLY'
    lk(r.outputs["Result"], mul.inputs[0])
    lk(fd.outputs["Result"], mul.inputs[1])
    lk(mul.outputs[0], p.inputs["Alpha"])
    # darker, denser cores
    shade = N.new("ShaderNodeValToRGB")
    shade.color_ramp.elements[0].color = (0.62, 0.66, 0.72, 1)
    shade.color_ramp.elements[1].color = (1, 1, 1, 1)
    lk(n.outputs["Fac"], shade.inputs["Fac"])
    lk(shade.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 1.0
    v = [(-size / 2, -size / 2, z), (size / 2, -size / 2, z), (size / 2, size / 2, z), (-size / 2, size / 2, z)]
    ob = mesh_obj("Clouds", v, [(0, 1, 2, 3)], m, "Lighting")
    ob.visible_shadow = True
    return ob


HAZE = {}


def mist_haze(density, color, depth=30000.0):
    """Aerial perspective: haze = 1 - exp(-distance * density) toward `color`,
    on geometry only (sky pixels have mist == 1). Applied after the render in
    render_to() from the mist pass (the Blender 5 compositor needs a GPU)."""
    sc = bpy.context.scene
    sc.view_layers[0].use_pass_mist = True
    ms = sc.world.mist_settings
    ms.start, ms.depth, ms.falloff = 0.0, depth, 'LINEAR'
    HAZE.update(density=density, color=color, depth=depth)


def _apply_haze(png_path, exr_path, sky_path):
    """geometry RGBA (transparent film) + mist + sky-only render -> hazed image.

    Coverage c comes from alpha; a pixel's mist is c*m0 + (1-c)*1 (sky = 1),
    so the true geometry depth m0 is recovered and edges get no false haze."""
    import numpy as np
    import OpenEXR
    from PIL import Image
    mist = None
    with OpenEXR.File(exr_path) as f:
        for part in f.parts:  # multi-part EXR: one part per pass
            for k, ch in part.channels.items():
                if ".mist" in k.lower():
                    mist = np.asarray(ch.pixels, dtype=np.float32)
    rgba = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.float32) / 255.0
    sky = np.asarray(Image.open(sky_path).convert("RGB"), dtype=np.float32) / 255.0
    geo, c = rgba[..., :3], rgba[..., 3]
    if mist is None:
        mist = np.zeros_like(c)
    if mist.ndim == 3:
        mist = mist[..., 0]
    m0 = np.clip((mist - (1.0 - c)) / np.maximum(c, 1e-3), 0.0, 1.0)
    fac = 1.0 - np.exp(-m0 * HAZE["depth"] * HAZE["density"])
    hc = np.array(HAZE["color"], dtype=np.float32)
    hazed = geo * (1 - fac[..., None]) + hc * fac[..., None]
    out = hazed * c[..., None] + sky * (1 - c[..., None])
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(png_path)

def render_settings(samples=64, res=(1600, 900), exposure=0.0):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.transparent_max_bounces = 24
    sc.cycles.volume_bounces = 0
    sc.cycles.volume_step_rate = 4.0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Punchy'
    sc.view_settings.exposure = exposure
    sc.render.image_settings.file_format = 'PNG'


def camera(name, loc, target, lens=28):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 6000
    co = bpy.data.objects.new(name, cd)
    co.location = loc
    d = Vector(target) - Vector(loc)
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    link(co, "Cameras")
    return co


def render_to(cam, path):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.filepath = path
    if HAZE:
        sc.render.film_transparent = True
        sc.render.image_settings.color_mode = 'RGBA'
    bpy.ops.render.render(write_still=True)
    if HAZE:
        exr = path[:-4] + "_passes.exr"
        settings = sc.render.image_settings
        fmt, media = settings.file_format, settings.media_type
        settings.media_type = 'MULTI_LAYER_IMAGE'
        settings.file_format = 'OPEN_EXR_MULTILAYER'
        bpy.data.images["Render Result"].save_render(exr, scene=sc)
        settings.media_type = media
        settings.file_format = fmt
        # sky-only pass: hide every collection, keep the world
        sky = path[:-4] + "_sky.png"
        hidden = []
        for col in bpy.data.collections:
            if not col.hide_render:
                col.hide_render = True
                hidden.append(col)
        sc.render.film_transparent = False
        sc.render.image_settings.color_mode = 'RGB'
        samples = sc.cycles.samples
        sc.cycles.samples = 16
        sc.view_layers[0].use_pass_mist = False
        sc.render.filepath = sky
        bpy.ops.render.render(write_still=True)
        sc.cycles.samples = samples
        sc.view_layers[0].use_pass_mist = True
        for col in hidden:
            col.hide_render = False
        _apply_haze(path, exr, sky)
        os.remove(exr)
        os.remove(sky)

# ---------------------------------------------------------------- materials

def lin(c):
    """sRGB (what a colour picker shows) -> linear (what shader sockets expect)."""
    def f(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4
    return tuple(f(u) for u in c[:3])


def _mat(name):
    m = bpy.data.materials.new(name)
    if not m.node_tree:
        m.use_nodes = True
    nt = m.node_tree
    return m, nt, nt.nodes["Principled BSDF"], nt.nodes["Material Output"]


def flat(name, color, rough=0.8, metal=0.0, emit=None):
    m, nt, p, _ = _mat(name)
    p.inputs["Base Color"].default_value = (*lin(color), 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        p.inputs["Emission Color"].default_value = (*lin(emit), 1)
        p.inputs["Emission Strength"].default_value = 2.0
    return m


def noisy(name, c1, c2, scale=2.0, rough=0.85, bump=0.3, detail=6, c3=None, scale2=0.15,
          coords='Object', bump_scale=None):
    """Two/three-colour noise material with bump. Good for soil, plaster, bark."""
    m, nt, p, out = _mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = scale
    n1.inputs["Detail"].default_value = detail
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*lin(c1), 1)
    ramp.color_ramp.elements[1].color = (*lin(c2), 1)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.65
    nt.links.new(tc.outputs[coords], n1.inputs["Vector"])
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    col_out = ramp.outputs["Color"]
    if c3 is not None:
        n2 = nt.nodes.new("ShaderNodeTexNoise")
        n2.inputs["Scale"].default_value = scale2
        n2.inputs["Detail"].default_value = 3
        r2 = nt.nodes.new("ShaderNodeMapRange")
        r2.inputs["From Min"].default_value = 0.45
        r2.inputs["From Max"].default_value = 0.6
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        nt.links.new(tc.outputs[coords], n2.inputs["Vector"])
        nt.links.new(n2.outputs["Fac"], r2.inputs["Value"])
        nt.links.new(r2.outputs["Result"], mix.inputs["Factor"])
        nt.links.new(col_out, mix.inputs[6])
        mix.inputs[7].default_value = (*lin(c3), 1)
        col_out = mix.outputs[2]
    nt.links.new(col_out, p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    if bump > 0:
        nb = nt.nodes.new("ShaderNodeTexNoise")
        nb.inputs["Scale"].default_value = bump_scale or scale * 12
        nb.inputs["Detail"].default_value = 8
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        nt.links.new(tc.outputs[coords], nb.inputs["Vector"])
        nt.links.new(nb.outputs["Fac"], b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    return m


def leaf(name, c1, c2, translucency=0.25):
    """Foliage: noisy colour, slight translucency, matte."""
    m = noisy(name, c1, c2, scale=3.0, rough=0.7, bump=0.4)
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Subsurface Weight"].default_value = translucency
    p.inputs["Subsurface Radius"].default_value = (0.2, 0.4, 0.1)
    return m


LEAF_CARDS = {}


def leaf_card(name, c1, c2, tiles=(4, 1), width=0.42, power=1.0, translucency=0.35, rough=0.6):
    """Alpha-masked leaf sprite material for card foliage.

    Each card UV is split into tiles; every tile holds one leaf whose half-width
    follows sin(pi*v)**power (lanceolate for power~1, rounder for <1)."""
    LEAF_CARDS[name] = dict(c1=c1, c2=c2, tiles=tiles, width=width, power=power)
    m, nt, p, out = _mat(name)
    N = nt.nodes
    lk = nt.links.new
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (tiles[0], tiles[1], 1)
    lk(tc.outputs["UV"], mp.inputs["Vector"])
    sep = N.new("ShaderNodeSeparateXYZ")
    lk(mp.outputs["Vector"], sep.inputs[0])

    def math_node(op, a=None, b=None, va=None, vb=None):
        n = N.new("ShaderNodeMath")
        n.operation = op
        if a is not None:
            lk(a, n.inputs[0])
        elif va is not None:
            n.inputs[0].default_value = va
        if b is not None:
            lk(b, n.inputs[1])
        elif vb is not None:
            n.inputs[1].default_value = vb
        return n
    uf = math_node('FRACT', sep.outputs[0])
    vf = math_node('FRACT', sep.outputs[1])
    vpi = math_node('MULTIPLY', vf.outputs[0], vb=math.pi)
    sn = math_node('SINE', vpi.outputs[0])
    pw = math_node('POWER', sn.outputs[0], vb=power)
    halfw = math_node('MULTIPLY', pw.outputs[0], vb=width)
    du = math_node('SUBTRACT', uf.outputs[0], vb=0.5)
    adu = math_node('ABSOLUTE', du.outputs[0])
    mask = math_node('LESS_THAN', adu.outputs[0], halfw.outputs[0])
    lk(mask.outputs[0], p.inputs["Alpha"])
    # per-leaf colour variation
    fl = N.new("ShaderNodeVectorMath")
    fl.operation = 'FLOOR'
    lk(mp.outputs["Vector"], fl.inputs[0])
    oi = N.new("ShaderNodeObjectInfo")
    add = N.new("ShaderNodeVectorMath")
    add.operation = 'ADD'
    lk(fl.outputs[0], add.inputs[0])
    lk(oi.outputs["Location"], add.inputs[1])
    wn = N.new("ShaderNodeTexWhiteNoise")
    wn.noise_dimensions = '3D'
    lk(add.outputs[0], wn.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*lin(c1), 1)
    ramp.color_ramp.elements[1].color = (*lin(c2), 1)
    lk(wn.outputs["Value"], ramp.inputs["Fac"])
    # midrib darkening
    rib = math_node('MULTIPLY', adu.outputs[0], vb=14.0)
    ribc = math_node('MINIMUM', rib.outputs[0], vb=1.0)
    ribf = math_node('SUBTRACT', va=1.0, b=ribc.outputs[0])
    mix = N.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    lk(ribf.outputs[0], mix.inputs[0])
    lk(ramp.outputs["Color"], mix.inputs[6])
    mix.inputs[7].default_value = (0.8, 0.85, 0.7, 1)
    lk(mix.outputs[2], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    p.inputs["Subsurface Weight"].default_value = translucency
    p.inputs["Subsurface Radius"].default_value = (0.2, 0.4, 0.1)
    try:
        m.surface_render_method = 'DITHERED'
    except Exception:
        pass
    return m


def soft_card(name, color=(0.97, 0.97, 0.97), opacity=0.22):
    """Soft round sprite (radial alpha falloff) for spray, dust and mist."""
    m, nt, p, out = _mat(name)
    N, lk = nt.nodes, nt.links.new
    tc = N.new("ShaderNodeTexCoord")
    sub = N.new("ShaderNodeVectorMath")
    sub.operation = 'SUBTRACT'
    sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    lk(tc.outputs["UV"], sub.inputs[0])
    ln = N.new("ShaderNodeVectorMath")
    ln.operation = 'LENGTH'
    lk(sub.outputs[0], ln.inputs[0])
    r = N.new("ShaderNodeMapRange")
    r.inputs["From Min"].default_value = 0.5
    r.inputs["From Max"].default_value = 0.05
    r.inputs["To Max"].default_value = opacity
    lk(ln.outputs["Value"], r.inputs["Value"])
    lk(r.outputs["Result"], p.inputs["Alpha"])
    p.inputs["Base Color"].default_value = (*lin(color), 1)
    p.inputs["Roughness"].default_value = 1.0
    return m


def water(name, deep=(0.02, 0.07, 0.08), rough=0.04, wave_scale=0.6, wave=0.06):
    m, nt, p, out = _mat(name)
    p.inputs["Base Color"].default_value = (*lin(deep), 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["IOR"].default_value = 1.33
    p.inputs["Specular IOR Level"].default_value = 0.6
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = wave_scale
    n.inputs["Detail"].default_value = 10
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1, 3, 1)
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = wave
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    nt.links.new(n.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    return m


def corrugated(name, color=(0.62, 0.63, 0.64), rust=(0.42, 0.22, 0.12), rust_amount=0.45,
               painted=False):
    """Iron-sheet roofing: corrugation bump, rust/paint patches."""
    m, nt, p, out = _mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs["Scale"].default_value = 40.0
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 2.5
    n.inputs["Detail"].default_value = 12
    n.inputs["Roughness"].default_value = 0.7
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*lin(color), 1)
    ramp.color_ramp.elements[1].color = (*lin(rust), 1)
    ramp.color_ramp.elements[0].position = 1.0 - rust_amount
    ramp.color_ramp.elements[1].position = min(1.0, 1.0 - rust_amount + 0.3)
    ramp.color_ramp.elements[0].position = max(0.0, 1.0 - rust_amount - 0.15)
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    nt.links.new(n.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Metallic"].default_value = 0.2 if painted else 0.55
    p.inputs["Roughness"].default_value = 0.55
    return m


def brick(name, brick_col=(0.45, 0.17, 0.08), mortar=(0.6, 0.55, 0.48), scale=6.0):
    m, nt, p, out = _mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (*lin(brick_col), 1)
    br.inputs["Color2"].default_value = (*lin((brick_col[0] * 0.8, brick_col[1] * 0.85, brick_col[2] * 0.9)), 1)
    br.inputs["Mortar"].default_value = (*lin(mortar), 1)
    br.inputs["Scale"].default_value = scale
    br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Brick Width"].default_value = 0.5
    br.inputs["Row Height"].default_value = 0.2
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], p.inputs["Base Color"])
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = 0.4
    nt.links.new(br.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    p.inputs["Roughness"].default_value = 0.9
    return m


def field_patchwork(name, palette, patch=(14.0, 9.0), band=None, rough=0.9, rot_deg=23.0,
                    bank_color=(0.30, 0.40, 0.16)):
    """Patchwork of crop fields: each cell (and terrace band) gets a palette colour.

    Used for the cultivated Kigezi hills and farmland in the distance."""
    m, nt, p, out = _mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot_deg))
    mp.inputs["Scale"].default_value = (1.0 / patch[0], 1.0 / patch[1], 1.0 / (band or 1000.0))
    # Wobble cell borders so fields are not perfect rectangles.
    wob = nt.nodes.new("ShaderNodeTexNoise")
    wob.inputs["Scale"].default_value = 0.08
    wobm = nt.nodes.new("ShaderNodeVectorMath")
    wobm.operation = 'MULTIPLY_ADD'
    wobm.inputs[1].default_value = (0.35, 0.35, 0.0)
    snap = nt.nodes.new("ShaderNodeVectorMath")
    snap.operation = 'FLOOR'
    wn = nt.nodes.new("ShaderNodeTexWhiteNoise")
    wn.noise_dimensions = '3D'
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = 'CONSTANT'
    els = ramp.color_ramp.elements
    while len(els) < len(palette):
        els.new(0.5)
    for i, c in enumerate(palette):
        els[i].position = i / len(palette)
        els[i].color = (*lin(c), 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], wob.inputs["Vector"])
    nt.links.new(wob.outputs["Color"], wobm.inputs[0])
    nt.links.new(mp.outputs["Vector"], wobm.inputs[2])
    nt.links.new(wobm.outputs[0], snap.inputs[0])
    nt.links.new(snap.outputs[0], wn.inputs["Vector"])
    nt.links.new(wn.outputs["Value"], ramp.inputs["Fac"])
    # Crop-row texture on top.
    rows = nt.nodes.new("ShaderNodeTexWave")
    rows.inputs["Scale"].default_value = 6.0
    rows.inputs["Distortion"].default_value = 2.0
    rows.inputs["Detail"].default_value = 2.0
    nt.links.new(mp.outputs["Vector"], rows.inputs["Vector"])
    dn = nt.nodes.new("ShaderNodeTexNoise")
    dn.inputs["Scale"].default_value = 0.6
    dn.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], dn.inputs["Vector"])
    shade = nt.nodes.new("ShaderNodeMix")
    shade.data_type = 'RGBA'
    shade.blend_type = 'MULTIPLY'
    shade.inputs[0].default_value = 0.15
    nt.links.new(ramp.outputs["Color"], shade.inputs[6])
    nt.links.new(rows.outputs["Color"], shade.inputs[7])
    shade2 = nt.nodes.new("ShaderNodeMix")
    shade2.data_type = 'RGBA'
    shade2.blend_type = 'OVERLAY'
    shade2.inputs[0].default_value = 0.4
    nt.links.new(shade.outputs[2], shade2.inputs[6])
    nt.links.new(dn.outputs["Color"], shade2.inputs[7])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sepn = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sepn.inputs[0])
    steep = nt.nodes.new("ShaderNodeMapRange")
    steep.inputs["From Min"].default_value = 0.97
    steep.inputs["From Max"].default_value = 0.86
    nt.links.new(sepn.outputs[2], steep.inputs["Value"])
    bank = nt.nodes.new("ShaderNodeMix")
    bank.data_type = 'RGBA'
    nt.links.new(steep.outputs["Result"], bank.inputs[0])
    nt.links.new(shade2.outputs[2], bank.inputs[6])
    bank.inputs[7].default_value = (*lin(bank_color), 1)
    nt.links.new(bank.outputs[2], p.inputs["Base Color"])
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = 0.25
    nt.links.new(dn.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    p.inputs["Roughness"].default_value = rough
    return m

# ---------------------------------------------------------------- geometry helpers

def mesh_obj(name, verts, faces, mat=None, col="Arena", smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    if mat:
        me.materials.append(mat)
    link(ob, col)
    return ob


def box(name, size, loc, mat=None, rot_z=0.0, col="Arena"):
    sx, sy, sz = (s / 2 for s in size)
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
         (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh_obj(name, v, f, mat, col)
    ob.location = loc
    ob.rotation_euler.z = rot_z
    return ob


def cylinder(name, r1, r2, h, loc, mat=None, seg=12, col="Arena", rot=(0, 0, 0), cap=True):
    v, f = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        v.append((r1 * math.cos(a), r1 * math.sin(a), 0))
        v.append((r2 * math.cos(a), r2 * math.sin(a), h))
    for i in range(seg):
        j = (i + 1) % seg
        f.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    if cap:
        f.append(tuple(2 * i for i in reversed(range(seg))))
        f.append(tuple(2 * i + 1 for i in range(seg)))
    ob = mesh_obj(name, v, f, mat, col, smooth=True)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def blob(name, radius, loc, mat, squash=(1, 1, 1), rough=0.35, seed=0, subdiv=3, col="Arena"):
    """Displaced icosphere: foliage clumps, rocks, bushes."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    off = Vector((seed * 7.31, seed * 3.17, seed * 1.93))
    for vtx in bm.verts:
        n = vtx.co.normalized()
        d = noise.fractal(n * 1.8 + off, 0.6, 2.0, 4)
        vtx.co = vtx.co * (1.0 + rough * d)
        vtx.co.x *= squash[0]; vtx.co.y *= squash[1]; vtx.co.z *= squash[2]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    me.materials.append(mat)
    ob.location = loc
    link(ob, col)
    return ob


def join(objs, name):
    """Join objects into one mesh (keeps materials)."""
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    ctx = bpy.context
    # Joining onto an object without UVs drops the others' UVs (leaf cards
    # would turn invisible), so give every mesh the same UV layer first.
    if any(o.data.uv_layers for o in objs if o.type == 'MESH'):
        for o in objs:
            if o.type == 'MESH' and "UVMap" not in o.data.uv_layers:
                o.data.uv_layers.new(name="UVMap")
    for o in ctx.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    ctx.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def instance(src, loc, rot_z=0.0, scale=1.0, col="Arena"):
    ob = src.copy()  # linked duplicate: shares mesh data
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    ob.scale = (scale, scale, scale)
    ob.hide_render = False
    ob.hide_viewport = False
    link(ob, col)
    return ob


def hide_template(ob):
    ob.hide_render = True
    ob.hide_viewport = True
    for c in ob.users_collection:
        c.objects.unlink(ob)
    collection("Templates").objects.link(ob)
    collection("Templates").hide_render = True
    return ob

# ---------------------------------------------------------------- terrain

def heightfield(name, size, res, height_fn, mat, center=(0, 0), col="Terrain"):
    sx, sy = size if isinstance(size, (tuple, list)) else (size, size)
    nx, ny = res if isinstance(res, (tuple, list)) else (res, res)
    v, f = [], []
    for j in range(ny + 1):
        y = center[1] - sy / 2 + sy * j / ny
        for i in range(nx + 1):
            x = center[0] - sx / 2 + sx * i / nx
            v.append((x, y, height_fn(x, y)))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            f.append((a, a + 1, a + nx + 2, a + nx + 1))
    ob = mesh_obj(name, v, f, mat, col, smooth=True)
    return ob


def fbm(x, y, scale, octaves=5, seed=0.0):
    return noise.fractal(Vector((x * scale + seed, y * scale - seed, seed * 0.5)), 0.55, 2.0, octaves)


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def terrace(h, step, sharp=0.75):
    """Quantise a height into level benches with short risers (Kigezi terraces)."""
    t = h / step
    base = math.floor(t)
    fr = t - base
    return (base + smoothstep(sharp, 1.0, fr)) * step

# ---------------------------------------------------------------- scatter

def grass_tuft_template(name, mat, blades=9, height=0.18, spread=0.06, seed=1):
    rnd = random.Random(seed)
    v, f = [], []
    for b in range(blades):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0, spread)
        bx, by = r * math.cos(a), r * math.sin(a)
        h = height * rnd.uniform(0.6, 1.2)
        lean = rnd.uniform(-0.5, 0.5) * h
        w = 0.008
        d = rnd.uniform(0, math.pi)
        dx, dy = math.cos(d) * w, math.sin(d) * w
        k = len(v)
        tipx = bx + math.cos(a) * lean
        tipy = by + math.sin(a) * lean
        v += [(bx - dx, by - dy, 0), (bx + dx, by + dy, 0),
              ((bx + tipx) / 2 + dx * 0.6, (by + tipy) / 2 + dy * 0.6, h * 0.55),
              ((bx + tipx) / 2 - dx * 0.6, (by + tipy) / 2 - dy * 0.6, h * 0.55),
              (tipx, tipy, h)]
        f += [(k, k + 1, k + 2, k + 3), (k + 3, k + 2, k + 4)]
    ob = mesh_obj(name, v, f, mat, "Templates")
    return hide_template(ob)


def scatter_particles(target, template, count, seed=1, size=1.0, size_rand=0.4,
                      density_group=None, name="scatter"):
    """Hair particle system rendering instances of template over target mesh."""
    mod = target.modifiers.new(name, 'PARTICLE_SYSTEM')
    ps = mod.particle_system
    st = ps.settings
    st.type = 'HAIR'
    st.use_advanced_hair = True
    st.count = count
    st.hair_length = 1.0
    st.render_type = 'OBJECT'
    st.instance_object = template
    st.particle_size = size
    st.size_random = size_rand
    st.use_rotations = True
    st.rotation_mode = 'OB_Z'  # keep up-right in world Z
    st.phase_factor_random = 2.0
    st.use_rotation_instance = False
    st.emit_from = 'FACE'
    st.use_emit_random = True
    st.distribution = 'RAND'
    ps.seed = seed
    if density_group:
        ps.vertex_group_density = density_group
    return ps


def density_group(obj, name, fn):
    """Vertex group with weight fn(world_co) in 0..1 to steer scatter density."""
    vg = obj.vertex_groups.new(name=name)
    mw = obj.matrix_world
    for v in obj.data.vertices:
        w = fn(mw @ v.co)
        if w > 0:
            vg.add([v.index], min(1.0, w), 'REPLACE')
    return name

# ---------------------------------------------------------------- court

COURT_W = 8.0      # playing width (m)
COURT_L = 18.0     # dodging area length (m)
END_L = 3.0        # hitting (shooter) zone depth at each end (m)


def court(surface="clay", col="Court"):
    """Court matching the 0.7 colours: clay dodging area, green hitting zones,
    white lines, centre circle and half-circles. Named so the game can swap it."""
    clay = noisy("CourtClay", (0.79, 0.53, 0.40), (0.83, 0.57, 0.43), scale=1.2, rough=0.92,
                 bump=0.08, c3=(0.74, 0.49, 0.36), scale2=0.3)
    green = noisy("CourtEnd", (0.16, 0.42, 0.31), (0.18, 0.45, 0.33), scale=1.5, rough=0.9, bump=0.05)
    line = flat("CourtLine", (0.92, 0.92, 0.86), rough=0.7)
    apron = noisy("CourtApron", (0.66, 0.70, 0.48), (0.70, 0.73, 0.50), scale=1.0, rough=0.9, bump=0.05)
    parts = []
    hw, hl = COURT_W / 2, COURT_L / 2
    parts.append(box("CourtApron", (COURT_W + 3.0, COURT_L + 2 * END_L + 3.0, 0.04), (0, 0, 0.0), apron, col=col))
    parts.append(box("CourtPlay", (COURT_W, COURT_L, 0.05), (0, 0, 0.005), clay, col=col))
    for s in (-1, 1):
        parts.append(box("CourtEnd", (COURT_W, END_L, 0.05), (0, s * (hl + END_L / 2), 0.005), green, col=col))
    lw = 0.08
    z = 0.032
    # outer lines and zone lines
    for s in (-1, 1):
        parts.append(box("Line", (lw, COURT_L + 2 * END_L, 0.01), (s * hw, 0, z), line, col=col))
        parts.append(box("Line", (COURT_W, lw, 0.01), (0, s * (hl + END_L), z), line, col=col))
        parts.append(box("Line", (COURT_W, lw, 0.01), (0, s * hl, z), line, col=col))
    # centre circle + spot + half circles at each end of dodging area
    def ring(cx, cy, r, a0, a1, seg=48):
        v, f = [], []
        for i in range(seg + 1):
            a = a0 + (a1 - a0) * i / seg
            v.append((cx + (r - lw / 2) * math.cos(a), cy + (r - lw / 2) * math.sin(a), z))
            v.append((cx + (r + lw / 2) * math.cos(a), cy + (r + lw / 2) * math.sin(a), z))
        for i in range(seg):
            f.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
        return mesh_obj("Ring", v, f, line, col)
    parts.append(ring(0, 0, 1.5, 0, 2 * math.pi))
    parts.append(ring(0, 0, 0.18, 0, 2 * math.pi, 16))
    parts.append(ring(0, -hl, 1.6, 0, math.pi))
    parts.append(ring(0, hl, 1.6, math.pi, 2 * math.pi))
    return join(parts, "Court")


def log_bench(name, length, loc, rot_z, wood):
    seat = cylinder(name, 0.16, 0.16, length, (0, 0, 0), wood, seg=10, rot=(0, math.radians(90), 0))
    seat.location = (-length / 2, 0, 0.42)
    legs = [box(name + "Leg", (0.14, 0.5, 0.36), (x, 0, 0.18), wood) for x in (-length * 0.4, length * 0.4)]
    ob = join([seat] + legs, name)
    # re-centre
    ob.location = loc
    ob.rotation_euler.z = rot_z
    return ob


def scoreboard(loc, rot_z, wood, dark, col="Arena"):
    parts = [cylinder("Post", 0.08, 0.08, 4.2, (x, 0, 0), wood, seg=8) for x in (-1.6, 1.6)]
    parts.append(box("Board", (3.6, 0.12, 1.4), (0, 0, 3.4), dark))
    ob = join(parts, "Scoreboard")
    ob.location = loc
    ob.rotation_euler.z = rot_z
    return ob
