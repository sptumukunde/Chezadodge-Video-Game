# ChezaDodge arenas (Blender, procedural)

Open-court arenas (no stands) built entirely from Python in Blender 5.x (`bpy`).
No external textures are needed; every material, plant and building is generated.

| Script | Location |
|---|---|
| `kigezi.py` | Court on a grass shelf above Lake Bunyonyi: terraced farmland, eucalyptus woodlots, farmhouses with banana groves, Virunga cones in the haze |
| `kampala.py` | Neighbourhood court on red murram: painted shop row with verandahs, boda bodas, kiosk, power lines, mango and jacaranda, hills packed with iron roofs, city blocks on the far hills |
| `murchison.py` | North-bank savanna above the Victoria Nile: borassus palms, acacias, termite mounds, ranger bandas, kob and giraffes, the falls in the escarpment upstream |

Shared modules: `arena_lib.py` (scene, sky + clouds, haze, materials, terrain, court),
`arena_flora.py` (eucalyptus, banana, borassus, acacia, round-crowned trees, shrubs),
`arena_build.py` (houses, shop rows, huts, tanks, poles, wires, boda bodas, fences).

## Run

```
pip install bpy==5.3.0 OpenEXR pillow   # Python 3.13
python kigezi.py -- out/ --quick          # fast low-res preview
python kigezi.py -- out/                  # full preview renders + kigezi.blend
python kigezi.py -- out/ --cam=broadcast  # one camera only
```

The court is centred on the origin along Y, using the 0.7 court colours, and is
named `Court` so the game can keep its own court mesh. Colours in the scripts are
sRGB; `arena_lib.lin()` converts them.

Haze is aerial perspective applied after rendering from the mist pass and alpha
coverage (the Blender 5 compositor needs a GPU, so it is done with numpy).
