"""Full assembly: every printed part plus every bought component (carbon,
fasteners, servos, motor, prop, battery, avionics), checked for collisions.

    .venv/bin/python cad/assembly.py

Writes assembly/pusher_1290_full.3mf (one named, coloured object per part or
component, for Bambu Studio and other 3MF viewers), assembly/pusher_1290_full.stl
(one mesh, for anything else), renders/full_assembly.png and renders/internals.png.
Exits non-zero if a component collides with a printed part.
"""
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import quoteattr

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

import fuselage  # noqa: E402
import hardware  # noqa: E402
import mass  # noqa: E402
import tail  # noqa: E402
import wing  # noqa: E402
from geom import mesh_arrays, union, write_stl  # noqa: E402
from render import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
COLLISION_MM3 = 1.0


def write_3mf(objects, path):
    """objects: list of (name, manifold, rgb). One mesh object per entry."""
    mats = "".join(f'<base name={quoteattr(n)} displaycolor="#{"".join(f"{int(c * 255):02X}" for c in rgb)}FF"/>'
                   for n, _, rgb in objects)
    res, items = [f'<basematerials id="1">{mats}</basematerials>'], []
    for i, (name, man, _) in enumerate(objects):
        v, t = mesh_arrays(man)
        verts = "".join(f'<vertex x="{a:.3f}" y="{b:.3f}" z="{c:.3f}"/>' for a, b, c in v)
        tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in t)
        oid = i + 2
        res.append(f'<object id="{oid}" type="model" name={quoteattr(name)} pid="1" pindex="{i}">'
                   f"<mesh><vertices>{verts}</vertices><triangles>{tris}</triangles></mesh></object>")
        items.append(f'<item objectid="{oid}"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Title">Pusher 1290 full assembly</metadata>'
             f'<resources>{"".join(res)}</resources><build>{"".join(items)}</build></model>')
    types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
             '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def collisions(parts, comps):
    """Volume of each component that sits inside printed material."""
    printed = union([p.assembly for p in parts])
    hits = []
    for c in comps:
        v = (c.shape ^ printed).volume()
        if v > COLLISION_MM3:
            hits.append((c.name, v))
    return hits


def main():
    parts = wing.parts() + fuselage.parts() + tail.parts()
    comps = hardware.components()

    hits = collisions(parts, comps)
    objects = ([(p.name, p.assembly, p.color) for p in parts]
               + [(c.name, c.shape, c.color) for c in comps])
    out = ROOT / "assembly"
    write_3mf(objects, out / "pusher_1290_full.3mf")
    write_stl(union([m for _, m, _ in objects]), out / "pusher_1290_full.stl")

    items = [(m, rgb) for _, m, rgb in objects]
    render(items, (-1, 1.3, -0.8), (0, 0, 1), ROOT / "renders" / "full_assembly.png")
    # Cutaway: printed parts on the near (left, -Y) side removed, so the inside shows.
    cut = [(p.assembly.trim_by_plane((0, 1, 0), 0.0) if p.name.startswith(("fuse", "motor")) else p.assembly,
            p.color) for p in parts if not p.name.startswith(("wing", "aileron"))]
    render(cut + [(c.shape, c.color) for c in comps if c.group != "Wing"], (0.15, 1, -0.3), (0, 0, 1),
           ROOT / "renders" / "internals.png", size=(1600, 800))

    width = max(len(c.name) for c in comps)
    for c in comps:
        print(f"{c.category:10s} {c.name:{width}s} {c.mass:6.1f} g  {c.spec}")
    print()
    balance_ok = True
    for filament in ("LW-PLA", "PLA"):
        rows = mass.budget(parts, comps, filament)
        auw, cg, shift = mass.balance(rows)
        move = f"move the battery {abs(shift):.0f} mm {'aft' if shift > 0 else 'forward'}" if abs(shift) > 3 else "on target"
        print(f"Printed in {filament:6s}: all-up {auw:5.0f} g, CG {cg:5.1f} mm behind the LE "
              f"(target {mass.CG_TARGET:.0f}) -> {move}")
        if filament == mass.DESIGN_FILAMENT and abs(cg - mass.CG_TARGET) > mass.CG_TOLERANCE:
            no_ballast = [r for r in rows if r[0] != "Nose weight"]
            need = mass.nose_weight_for_target(no_ballast, sum(hardware.NOSE_WEIGHT_X) / 2)
            print(f"  -> set hardware.NOSE_WEIGHT_G = {need:.0f} to balance the {filament} build")
            balance_ok = False
    print(f"\n{len(parts)} printed parts + {len(comps)} components -> assembly/pusher_1290_full.3mf")
    if not balance_ok:
        sys.exit(1)
    if hits:
        print("COLLISIONS (mm3 inside printed parts):\n  " + "\n  ".join(f"{n}: {v:.1f}" for n, v in hits))
        sys.exit(1)
    print("No component collides with a printed part.")


if __name__ == "__main__":
    main()
