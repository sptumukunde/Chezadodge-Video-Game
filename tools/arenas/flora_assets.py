"""Phone-ready ground flora from Poly Haven (CC0) for the game's 3D worlds.

Inputs (Poly Haven .blend downloads, one folder each):
  grass_medium_01_1k, fern_02_2k, shrub_02_2k, shrub_sorrel_01_2k
Outputs (into the game's assets/flora):
  grass_cards.png   RGBA atlas, 4 x 2 cards rendered side-on from the real
                    grass clumps (albedo + alpha, unlit), used on crossed
                    quads so thousands of clumps stay cheap
  fern.glb          fern_02 a..d meshes (b, c thinned to ~1k triangles)
  shrub.glb         shrub_02 a..d LOD2 meshes
  sorrel.glb        shrub_sorrel_01 a..f (small clover-like ground cover)
  fern.png / shrub.png / sorrel.png   diffuse with alpha in A, 1024 px

Run:  python flora_assets.py -- <polyhaven_dir> <game_assets_flora_dir>
"""
import sys, os, math
import bpy
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SRC = args[0] if args else '/opt/assets/polyhaven'
OUT = args[1] if len(args) > 1 else '/tmp/flora'
os.makedirs(OUT, exist_ok=True)


def rgba_texture(diff, alpha, out, size=1024, gain=1.0):
    a = bpy.data.images.load(diff)
    b = bpy.data.images.load(alpha)
    for im in (a, b):
        im.colorspace_settings.name = 'Non-Color'
        if im.size[0] != size:
            im.scale(size, size)
    pa = np.array(a.pixels[:], dtype=np.float32).reshape(size, size, 4)
    pb = np.array(b.pixels[:], dtype=np.float32).reshape(size, size, 4)
    pa[..., :3] = np.clip(pa[..., :3] * gain, 0, 1)
    pa[..., 3] = pb[..., 0]
    img = bpy.data.images.new(os.path.basename(out), size, size, alpha=True)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(pa.ravel())
    img.filepath_raw = out
    img.file_format = 'PNG'
    img.save()
    print("TEX", out)


def export_meshes(blend, names, out, decimate=None):
    bpy.ops.wm.open_mainfile(filepath=blend)
    keep = []
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None:
            print("missing", n)
            continue
        keep.append(o)
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    for i, o in enumerate(keep):
        o.location = (0, 0, 0)
        o.rotation_euler = (0, 0, 0)
        o.name = "v%d" % i
        if decimate and decimate.get(i):
            md = o.modifiers.new("dec", 'DECIMATE')
            md.ratio = decimate[i]
        o.data.materials.clear()
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        print("  ", n if False else o.name, "tris", tris, "size", tuple(round(d, 2) for d in o.dimensions))
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_visible=False, export_apply=True,
                              export_materials='NONE', export_yup=True, export_cameras=False, export_lights=False)
    print("GLB", out)


def grass_cards(blend, names, out, cell=512, cols=4):
    """Render each clump side-on, unlit, into one RGBA atlas."""
    bpy.ops.wm.open_mainfile(filepath=blend)
    tex = os.path.join(os.path.dirname(blend), "textures")
    m = bpy.data.materials.new("CardSrc")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out_n = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    td = nt.nodes.new("ShaderNodeTexImage")
    td.image = bpy.data.images.load(os.path.join(tex, "grass_medium_01_diff_1k.jpg"))
    ta = nt.nodes.new("ShaderNodeTexImage")
    ta.image = bpy.data.images.load(os.path.join(tex, "grass_medium_01_alpha_1k.png"))
    ta.image.colorspace_settings.name = 'Non-Color'
    nt.links.new(td.outputs["Color"], em.inputs["Color"])
    nt.links.new(ta.outputs["Color"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out_n.inputs[0])
    objs = [bpy.data.objects[n] for n in names]
    for o in list(bpy.data.objects):
        o.hide_render = True
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 24
    sc.cycles.use_denoising = False
    sc.render.film_transparent = True
    sc.render.resolution_x = cell
    sc.render.resolution_y = cell
    sc.view_settings.view_transform = 'Standard'
    sc.world = bpy.data.worlds.new("w") if sc.world is None else sc.world
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    cam_d = bpy.data.cameras.new("cardcam")
    cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new("cardcam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    rows = math.ceil(len(objs) / cols)
    atlas = np.zeros((rows * cell, cols * cell, 4), dtype=np.float32)
    path = os.path.join(OUT, "_card.png")
    for i, o in enumerate(objs):
        for p in objs:
            p.hide_render = p is not o
        o.data.materials.clear()
        o.data.materials.append(m)
        o.location = (0, 0, 0)
        bpy.context.view_layer.update()
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        size = max(hi.x - lo.x, hi.z - lo.z) * 1.02
        cam_d.ortho_scale = size
        cx = (lo.x + hi.x) / 2
        # the clump stands on the bottom edge of its cell
        cam.location = (cx, lo.y - 5.0, lo.z + size / 2)
        cam.rotation_euler = (math.radians(90), 0, 0)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(path, check_existing=False)
        px = np.array(im.pixels[:], dtype=np.float32).reshape(cell, cell, 4)[::-1]
        r, c = divmod(i, cols)
        atlas[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell] = px
        bpy.data.images.remove(im)
        print("card", i, o.name, "h/w", round((hi.z - lo.z) / max(1e-3, hi.x - lo.x), 2))
    # edge colour bleed: spread colour into transparent texels so mipmaps and
    # alpha-scissor edges don't pick up a dark fringe (PNG alpha is straight)
    rgb, a = atlas[..., :3], atlas[..., 3:4]
    col = np.where(a > 0.02, rgb, 0)
    for _ in range(6):
        filled = (a > 0.02)[..., 0]
        acc = np.zeros_like(col); cnt = np.zeros(filled.shape, dtype=np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(col * filled[..., None], dy, 0), dx, 1)
            cnt += np.roll(np.roll(filled.astype(np.float32), dy, 0), dx, 1)
        grow = (~filled) & (cnt > 0)
        col[grow] = acc[grow] / cnt[grow][:, None]
        a = np.where(grow[..., None], 0.021, a)
    atlas[..., :3] = np.clip(col, 0, 1)
    img = bpy.data.images.new("grass_cards", cols * cell, rows * cell, alpha=True)
    img.pixels.foreach_set(atlas[::-1].ravel())
    img.filepath_raw = out
    img.file_format = 'PNG'
    img.save()
    os.remove(path)
    print("ATLAS", out)


if '--ground' not in sys.argv:
  g = os.path.join(SRC, "grass_medium_01_1k", "grass_medium_01_1k.blend")
  grass_cards(g, ["grass_medium_01_tall_a_LOD2", "grass_medium_01_tall_b_LOD2", "grass_medium_01_tall_c_LOD2",
                  "grass_medium_01_mid_a_LOD2", "grass_medium_01_mid_b_LOD2", "grass_medium_01_large_a_LOD2",
                  "grass_medium_01_large_b_LOD2", "grass_medium_01_small_a_LOD2"],
              os.path.join(OUT, "grass_cards.png"))

  f = os.path.join(SRC, "fern_02_2k")
  export_meshes(os.path.join(f, "fern_02_2k.blend"), ["fern_02_a", "fern_02_b", "fern_02_c", "fern_02_d"],
                os.path.join(OUT, "fern.glb"), decimate={1: 0.45, 2: 0.45})
  rgba_texture(os.path.join(f, "textures", "fern_02_diff_2k.jpg"), os.path.join(f, "textures", "fern_02_alpha_2k.png"),
               os.path.join(OUT, "fern.png"))
  s = os.path.join(SRC, "shrub_02_2k")
  export_meshes(os.path.join(s, "shrub_02_2k.blend"), ["shrub_02_a_LOD2", "shrub_02_b_LOD2", "shrub_02_c_LOD2",
                                                        "shrub_02_d_LOD2"], os.path.join(OUT, "shrub.glb"))
  rgba_texture(os.path.join(s, "textures", "shrub_02_diff_2k.jpg"), os.path.join(s, "textures", "shrub_02_alpha_2k.png"),
               os.path.join(OUT, "shrub.png"))
  so = os.path.join(SRC, "shrub_sorrel_01_2k")
  export_meshes(os.path.join(so, "shrub_sorrel_01_2k.blend"), ["shrub_sorrel_01_%s" % c for c in "abdef"],
                os.path.join(OUT, "sorrel.glb"))
  rgba_texture(os.path.join(so, "textures", "shrub_sorrel_01_diff_2k.jpg"),
               os.path.join(so, "textures", "shrub_sorrel_01_alpha_2k.png"), os.path.join(OUT, "sorrel.png"))
  print("DONE")


def ground_textures(names, size=1024):
    """Poly Haven ground sets -> <name>_diff.jpg + <name>_nor.png (GL) for terrain detail."""
    for n, folder in names:
        tex = os.path.join(SRC, folder, "textures")
        for kind, pat, ext in (("diff", "_diff", "JPEG"), ("nor", "_nor_gl", "PNG")):
            src = [f for f in os.listdir(tex) if pat in f and f.startswith(n)]
            if not src:
                print("missing", n, kind); continue
            im = bpy.data.images.load(os.path.join(tex, src[0]))
            im.colorspace_settings.name = 'Non-Color'
            if im.size[0] != size:
                im.scale(size, size)
            px = np.array(im.pixels[:], dtype=np.float32)
            out = bpy.data.images.new(n + kind, size, size, alpha=False)
            out.colorspace_settings.name = 'Non-Color'
            out.pixels.foreach_set(np.clip(px, 0, 1))
            out.filepath_raw = os.path.join(OUT, "%s_%s.%s" % (n, kind, "jpg" if ext == "JPEG" else "png"))
            out.file_format = ext
            out.save()
            print("GROUND", out.filepath_raw)


if '--ground' in sys.argv:
    ground_textures([("leaves_forest_ground", "leaves_forest_ground_1k"), ("forest_floor", "forest_floor_1k"),
                     ("forest_ground_05", "forest_ground_05_1k"), ("forest_leaves_02", "forest_leaves_02_2k")])
