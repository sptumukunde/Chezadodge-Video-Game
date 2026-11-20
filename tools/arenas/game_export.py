"""Export a built arena scene as a phone-friendly GLB for the ChezaDodge game.

What happens:
  * Blender-only props around the court are removed (the game draws its own
    court, benches, scoreboard and stands).
  * Terrain keeps its shape; the procedural ground materials are baked into
    one colour texture per terrain ring (Cycles DIFFUSE colour bake).
  * Leaf-card materials get a generated RGBA leaf texture (alpha clip).
  * Every other procedural material becomes a plain colour (its average).
  * Instances: full detail near the court, a cheap proxy (trunk + crown) in
    the distance, nothing beyond `far_r` (the game's fog hides it).
  * Everything is merged into a few chunk meshes to keep draw calls low.
  * The scene is rotated so the hero view (lake / street / river) is on the
    side the game's broadcast camera looks at (Blender +Y = Godot -Z).
"""
import math
import os
import random
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix
import arena_lib as L

NEAR_DROP = ("Court", "Bench", "Scoreboard", "WornEarth", "WornMurram", "Road")


def _ramp_avg(nt):
    for n in nt.nodes:
        if n.type == 'VALTORGB':
            cs = [e.color for e in n.color_ramp.elements]
            return [sum(c[i] for c in cs) / len(cs) for i in range(3)]
    for n in nt.nodes:
        if n.type == 'TEX_BRICK':
            return list(n.inputs["Color1"].default_value[:3])
    p = nt.nodes.get("Principled BSDF")
    if p:
        return list(p.inputs["Base Color"].default_value[:3])
    return [0.5, 0.5, 0.5]


def _emission(nt):
    p = nt.nodes.get("Principled BSDF")
    if p and p.inputs["Emission Strength"].default_value > 0:
        return list(p.inputs["Emission Color"].default_value[:3]), p.inputs["Emission Strength"].default_value
    return None, 0.0


def _plain(m, color, rough=0.85, alpha=None, emit=None, emit_s=0.0):
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color[:3], 1)
    p.inputs["Roughness"].default_value = rough
    if alpha is not None:
        p.inputs["Alpha"].default_value = alpha
        m.surface_render_method = 'BLENDED'
    if emit is not None and emit_s > 0:
        p.inputs["Emission Color"].default_value = (*emit[:3], 1)
        p.inputs["Emission Strength"].default_value = emit_s
    nt.links.new(p.outputs[0], out.inputs[0])


def _leaf_image(name, spec, size=256):
    """RGBA image of the leaf-card pattern (same maths as arena_lib.leaf_card)."""
    tx, ty = spec["tiles"]
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    v = 1.0 - v  # image rows go down, UV v goes up
    uf, vf = np.modf(u * tx)[0], np.modf(v * ty)[0]
    half = np.power(np.sin(vf * math.pi), spec["power"]) * spec["width"]
    mask = (np.abs(uf - 0.5) < half).astype(np.float32)
    cell = np.floor(u * tx) + 7.0 * np.floor(v * ty)
    rnd = np.modf(np.sin(cell * 12.9898 + 4.1) * 43758.5453)[0]
    rnd = np.abs(rnd)
    c1, c2 = np.array(L.lin(spec["c1"])), np.array(L.lin(spec["c2"]))
    col = c1[None, None, :] * (1 - rnd[..., None]) + c2[None, None, :] * rnd[..., None]
    rib = np.minimum(np.abs(uf - 0.5) * 14.0, 1.0)
    col = col * (0.8 + 0.2 * rib[..., None])
    img = bpy.data.images.new(name + "_tex", size, size, alpha=True)
    px = np.concatenate([col, mask[..., None]], axis=2)
    img.pixels.foreach_set(px[::-1].astype(np.float32).ravel())  # Blender stores bottom row first
    img.pack()
    return img


def _leaf_material(m, spec):
    img = _leaf_image(m.name, spec)
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    rnd = nt.nodes.new("ShaderNodeMath")
    rnd.operation = 'ROUND'  # glTF exporter: alpha MASK
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(t.outputs["Alpha"], rnd.inputs[0])
    nt.links.new(rnd.outputs[0], p.inputs["Alpha"])
    p.inputs["Roughness"].default_value = 0.8
    nt.links.new(p.outputs[0], out.inputs[0])
    m.surface_render_method = 'DITHERED'
    m.use_backface_culling = False


def _bake_ao(ob, res, distance, samples=12):
    """Ambient occlusion of the terrain under trees, houses and terrace banks."""
    img = bpy.data.images.new(ob.name + "_ao", res, res, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    for m in ob.data.materials:
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = img
        m.node_tree.nodes.active = t
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.world.light_settings.distance = distance
    sc.render.bake.margin = 4
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='AO')
    return np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)[:, 0]


def _bake_terrain(ob, res, darken=1.0, keep_uv=False, ao_dist=0.0):
    """Bake the object's (procedural, multi-material) colour into one texture."""
    me = ob.data
    if keep_uv and me.uv_layers:
        return _bake_with_uv(ob, res)
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    uvl = me.uv_layers.new(name="BakeUV")
    me.uv_layers.active = uvl
    for li, loop in enumerate(me.loops):
        co = me.vertices[loop.vertex_index].co
        uvl.data[li].uv = ((co.x - x0) / (x1 - x0), (co.y - y0) / (y1 - y0))
    img = bpy.data.images.new(ob.name + "_bake", res, res, alpha=False)
    for m in me.materials:
        nt = m.node_tree
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        nt.nodes.active = t
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 4
    sc.cycles.bake_type = 'DIFFUSE'
    sc.render.bake.use_pass_direct = False
    sc.render.bake.use_pass_indirect = False
    sc.render.bake.use_pass_color = True
    sc.render.bake.margin = 4
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='DIFFUSE')
    if ao_dist > 0:
        ao = _bake_ao(ob, res, ao_dist)
        px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)
        px[:, :3] *= (0.38 + 0.62 * np.clip(ao, 0, 1) ** 1.2)[:, None]
        img.pixels.foreach_set(px.ravel())
    if darken != 1.0:
        px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)
        px[:, :3] *= darken
        img.pixels.foreach_set(px.ravel())
    img.pack()
    bm = bpy.data.materials.new(ob.name + "_ground")
    if not bm.node_tree:
        bm.use_nodes = True
    nt = bm.node_tree
    p = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.95
    me.materials.clear()
    me.materials.append(bm)
    for poly in me.polygons:
        poly.material_index = 0
    # keep only the bake UVs
    for u in list(me.uv_layers):
        if u.name != "BakeUV":
            me.uv_layers.remove(u)


def _bake_with_uv(ob, res):
    me = ob.data
    img = bpy.data.images.new(ob.name + "_bake", res, res, alpha=False)
    for m in me.materials:
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = img
        m.node_tree.nodes.active = t
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 4
    sc.render.bake.use_pass_direct = False
    sc.render.bake.use_pass_indirect = False
    sc.render.bake.use_pass_color = True
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='DIFFUSE')
    img.pack()
    bm = bpy.data.materials.new(ob.name + "_ground")
    bm.use_nodes = True
    p = bm.node_tree.nodes["Principled BSDF"]
    t = bm.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = img
    bm.node_tree.links.new(t.outputs["Color"], p.inputs["Base Color"])
    me.materials.clear()
    me.materials.append(bm)


def _kind(template_name):
    for k in ("Euc", "Rnd", "Mango", "Jac", "Acacia", "Palm", "FarTree", "Fig", "Giant", "Mid", "Pine", "Maple", "Willow"):
        if template_name.startswith(k):
            return "tree"
    if template_name.startswith(("Ban", "Shrub", "Bush", "Tuft", "Aloe", "Fern")):
        return "small"
    return "prop"


def _proxy_for(t):
    """Cheap stand-in for a tree template: trunk + crown blob, leaf-coloured."""
    bb = [t.matrix_world @ Vector(c) for c in t.bound_box]
    lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
    hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    h = hi.z - lo.z
    rx, ry = (hi.x - lo.x) / 2, (hi.y - lo.y) / 2
    leaf_col = [0.12, 0.2, 0.07]
    for m in t.data.materials:
        if m and m.name in L.LEAF_CARDS:
            leaf_col = list(L.lin(L.LEAF_CARDS[m.name]["c1"]))
    lm = bpy.data.materials.new(t.name + "_proxyLeaf")
    lm.use_nodes = True
    _plain(lm, leaf_col, 0.9)
    bark = bpy.data.materials.new(t.name + "_proxyBark")
    bark.use_nodes = True
    _plain(bark, [0.25, 0.2, 0.16], 0.9)
    crown_h = h * (0.45 if not t.name.startswith("Acacia") else 0.25)
    crown = L.blob(t.name + "_pc", 1.0, (0, 0, h - crown_h * 0.55), lm,
                   squash=(max(rx, 0.8) * 0.85, max(ry, 0.8) * 0.85, crown_h * 0.6), rough=0.25, subdiv=0)
    for poly in crown.data.polygons:
        poly.use_smooth = True  # soft, rounded distant crowns instead of facets
    trunk = L.cylinder(t.name + "_pt", 0.25, 0.15, h - crown_h * 0.6, (0, 0, 0), bark, seg=4, cap=False)
    p = L.join([crown, trunk], t.name + "_proxy")
    p.hide_render = True
    return p


def _house_proxy(t):
    """Distant house: wall box + roof slab in the template's own colours."""
    bb = [Vector(c) for c in t.bound_box]
    lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
    hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    mats = [m for m in t.data.materials if m]
    wall = mats[0] if mats else None
    roof = next((m for m in mats if "Roof" in m.name), wall)
    h = hi.z - lo.z
    c = (lo + hi) / 2
    w = L.box(t.name + "_hw", (hi.x - lo.x, hi.y - lo.y, h * 0.72), (c.x, c.y, lo.z + h * 0.36), wall)
    r = L.box(t.name + "_hr", ((hi.x - lo.x) * 1.04, (hi.y - lo.y) * 1.04, h * 0.28), (c.x, c.y, lo.z + h * 0.86), roof)
    p = L.join([w, r], t.name + "_hproxy")
    p.hide_render = True
    return p


def _realize(ob, mesh):
    """Make a standalone copy of `mesh` at ob's transform (for joining)."""
    me = mesh.copy()
    me.transform(ob.matrix_world)
    o = bpy.data.objects.new(ob.name + "_r", me)
    L.collection("Export").objects.link(o)
    return o


def export(out_path, rot_deg=0.0, near_r=260.0, far_r=1800.0, near_trees=90, far_trees=900,
           small_r=140.0, prop_r=1600.0, max_props=2200, terrain_res=None, clear_r=11.0,
           house_r=300.0, darken=0.82, ao=None):
    terrain_res = terrain_res or {"TerrainNear": 2048, "TerrainMid": 2048, "TerrainFar": 1024}
    sc = bpy.context.scene
    # 1. drop what the game draws itself, lights, cameras, particles
    for ob in list(bpy.data.objects):
        if ob.type in ('CAMERA', 'LIGHT') or ob.name.startswith(NEAR_DROP) or ob.name in ("Clouds",):
            bpy.data.objects.remove(ob, do_unlink=True)
    col = bpy.data.collections.get("Court")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    for ob in bpy.data.objects:
        for md in list(ob.modifiers):
            if md.type == 'PARTICLE_SYSTEM':
                ob.modifiers.remove(md)
    # 2. bake terrain colour, sink the shelf under the game's apron
    for tn, res in terrain_res.items():
        t = bpy.data.objects.get(tn)
        if t is None:
            continue
        _bake_terrain(t, res, darken=darken, ao_dist=(ao or {}).get(tn, 0.0))
        for v in t.data.vertices:
            if math.hypot(v.co.x, v.co.y) < 40:
                v.co.z -= 0.03
    for ob in list(bpy.data.objects):
        if ob.type == 'MESH' and ob.get("bake"):
            _bake_terrain(ob, int(ob["bake"]), darken=1.0, keep_uv=True)
            if ob.get("bake_emit"):
                m = ob.data.materials[0]
                p = m.node_tree.nodes["Principled BSDF"]
                t = [n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE'][0]
                m.node_tree.links.new(t.outputs["Color"], p.inputs["Emission Color"])
                p.inputs["Emission Strength"].default_value = float(ob["bake_emit"])
            terrain_res[ob.name] = 0
    # 3. materials: leaf cards -> textures, others -> plain colours
    terrain_mats = {m.name for tn in terrain_res for o in [bpy.data.objects.get(tn)] if o for m in o.data.materials}
    terrain_res = {k: v for k, v in terrain_res.items() if v}
    for m in bpy.data.materials:
        if m.name in terrain_mats or not m.node_tree:
            continue
        if m.name in L.LEAF_CARDS:
            _leaf_material(m, L.LEAF_CARDS[m.name])
        elif m.name.startswith("Spray"):
            _plain(m, [0.95, 0.96, 0.96], 1.0, alpha=0.18)
        elif m.name in ("Water", "NileWater"):
            _plain(m, _ramp_avg(m.node_tree), 0.06)
        elif not m.name.endswith(("_ground", "_proxyLeaf", "_proxyBark")):
            e, es = _emission(m.node_tree)
            _plain(m, _ramp_avg(m.node_tree), emit=e, emit_s=es)
    # 4. instances -> LOD -> realized meshes
    tmpl = bpy.data.collections.get("Templates")
    templates = {o.data.name: o for o in (tmpl.objects if tmpl else [])}
    proxies = {}
    insts = [o for o in bpy.data.objects if o.type == 'MESH' and o.data.name in templates
             and o.name not in (tmpl.objects if tmpl else [])]
    insts.sort(key=lambda o: o.location.length)
    keep = {"tree": [], "proxy": [], "small": [], "prop": []}
    nt = ft = np_ = 0
    for o in insts:
        r = Vector((o.location.x, o.location.y)).length
        if r < clear_r:
            continue
        t = templates[o.data.name]
        k = _kind(t.name)
        if k == "tree":
            if r < near_r and nt < near_trees:
                keep["tree"].append(_realize(o, o.data)); nt += 1
            elif r < far_r and ft < far_trees:
                if t.name not in proxies:
                    proxies[t.name] = _proxy_for(t)
                keep["proxy"].append(_realize(o, proxies[t.name].data)); ft += 1
        elif k == "small":
            if r < small_r:
                keep["small"].append(_realize(o, o.data))
        else:
            if r < prop_r and np_ < max_props:
                if r > house_r and t.name.startswith(("Home", "House", "Rond")):
                    if t.name not in proxies:
                        proxies[t.name] = _house_proxy(t)
                    keep["prop"].append(_realize(o, proxies[t.name].data))
                else:
                    keep["prop"].append(_realize(o, o.data))
                np_ += 1
        bpy.data.objects.remove(o, do_unlink=True)
    for o in list(tmpl.objects if tmpl else []):
        bpy.data.objects.remove(o, do_unlink=True)
    for p in proxies.values():
        bpy.data.objects.remove(p, do_unlink=True)
    # 5. merge into spatial chunks (fewer draw calls)
    def chunked(objs, cell, label):
        cells = {}
        for o in objs:
            c = o.matrix_world @ Vector(o.data.vertices[0].co) if False else Vector(o.data.vertices[0].co)
            key = (int(math.floor(c.x / cell)), int(math.floor(c.y / cell)))
            cells.setdefault(key, []).append(o)
        for key, group in cells.items():
            L.join(group, "%s_%d_%d" % (label, key[0], key[1]))
    chunked(keep["tree"], 120.0, "Trees")
    chunked(keep["small"], 80.0, "Plants")
    chunked(keep["proxy"], 600.0, "FarTrees")
    chunked(keep["prop"], 300.0, "Props")
    # 6. rotate world so the hero view faces the broadcast camera
    if rot_deg:
        R = Matrix.Rotation(math.radians(rot_deg), 4, 'Z')
        bpy.context.view_layer.update()
        for ob in bpy.data.objects:
            if ob.parent is None:
                ob.matrix_world = R @ ob.matrix_world
    # 7. stats + export
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
    print("EXPORT objects=%d tris=%d" % (len([o for o in bpy.data.objects if o.type == 'MESH']), tris))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB', use_visible=False,
                              export_apply=True, export_image_format='WEBP', export_yup=True,
                              export_cameras=False, export_lights=False)
    print("EXPORTED", out_path, os.path.getsize(out_path))
