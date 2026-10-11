"""Build every part, orient it on a 180 mm bed, check the fit, export STLs,
an assembly model, a parts table and preview renders.

    .venv/bin/python cad/build.py
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

import fuselage  # noqa: E402
import hardware  # noqa: E402
import tail  # noqa: E402
import wing  # noqa: E402
from geom import mesh_arrays, rot_z, transform, union, write_stl  # noqa: E402
from params import BED, BED_MARGIN  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from render import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LW_PLA_DENSITY = 0.55   # g/cm3, foamed
PETG_DENSITY = 1.27


def place_on_bed(man):
    """Spin about Z for the smallest footprint, then centre on the bed."""
    v, _ = mesh_arrays(man)
    best = None
    for deg in range(0, 180):
        a = math.radians(deg)
        x = v[:, 0] * math.cos(a) - v[:, 1] * math.sin(a)
        y = v[:, 0] * math.sin(a) + v[:, 1] * math.cos(a)
        size = max(np.ptp(x), np.ptp(y))
        if best is None or size < best[0] - 1e-6:
            best = (size, deg)
    man = transform(man, rot_z(best[1]))
    b = man.bounding_box()
    man = man.translate((BED / 2 - (b[0] + b[3]) / 2, BED / 2 - (b[1] + b[4]) / 2, -b[2]))
    b = man.bounding_box()
    return man, (b[3] - b[0], b[4] - b[1], b[5] - b[2])


def parts_sheet(printed, path, cols=6, tile=300):
    """Every part as it sits on the bed, labelled with its STL file name."""
    rows = (len(printed) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile, rows * (tile + 24)), (246, 246, 244))
    draw = ImageDraw.Draw(sheet)
    for k, (fname, man, color) in enumerate(printed):
        img = render([(man, color)], (0.55, 0.8, -0.45), (0, 0, 1), size=(tile, tile))
        x, y = (k % cols) * tile, (k // cols) * (tile + 24)
        sheet.paste(img, (x, y))
        draw.text((x + 8, y + tile + 4), fname[:-4], fill=(40, 40, 40))
    sheet.save(path)


def fits(dims):
    return dims[0] <= BED - 2 * BED_MARGIN and dims[1] <= BED - 2 * BED_MARGIN and dims[2] <= BED


def main():
    parts = wing.parts() + fuselage.parts() + tail.parts()
    stl_dir, asm_dir, img_dir = ROOT / "stl", ROOT / "assembly", ROOT / "renders"
    for d in (stl_dir, asm_dir, img_dir):
        d.mkdir(exist_ok=True)
        for old in d.glob("*.stl"):
            old.unlink()

    rows, failures, printed = [], [], []
    for i, p in enumerate(parts, 1):
        on_bed, dims = place_on_bed(p.printed)
        fname = f"{i:02d}_{p.name}.stl"
        write_stl(on_bed, stl_dir / fname)
        printed.append((fname, on_bed, p.color))
        density = PETG_DENSITY if p.material == "PETG" else LW_PLA_DENSITY
        rows.append((fname, p.material, dims, p.printed.volume() / 1000 * density, p.note))
        if not fits(dims):
            failures.append(f"{p.name}: {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f}")

    write_stl(union([p.assembly for p in parts]), asm_dir / "pusher_1290.stl")

    with open(stl_dir / "PARTS.md", "w") as f:
        f.write("| File | Material | X x Y x Z on bed (mm) | Solid-model mass* (g) | Notes |\n")
        f.write("|---|---|---|---|---|\n")
        for fname, mat, d, mass, note in rows:
            f.write(f"| {fname} | {mat} | {d[0]:.0f} x {d[1]:.0f} x {d[2]:.0f} | {mass:.0f} | {note} |\n")
        f.write("\n*Upper bound: assumes the model is printed fully solid. Wing panels and "
                "fuselage shells are modelled at their true wall thickness, so they come out close "
                "to this figure; solid parts (tips, tail, ailerons) print far lighter at 8-10 % infill.\n")

    items = [(p.assembly, p.color) for p in parts] + [(c.shape, c.color) for c in hardware.components()]
    render(items, (-1, 1.3, -0.8), (0, 0, 1), img_dir / "iso_front.png")
    render(items, (1, -1.2, -0.7), (0, 0, 1), img_dir / "iso_rear.png")
    render(items, (0, 0, -1), (-1, 0, 0), img_dir / "top.png")
    render(items, (0, 1, 0), (0, 0, 1), img_dir / "side.png", size=(1600, 700))
    render(items, (1, 0, 0), (0, 0, 1), img_dir / "front.png", size=(1600, 600))
    parts_sheet(printed, img_dir / "parts_sheet.png")

    for fname, mat, d, mass, _ in rows:
        print(f"{fname:38s} {mat:6s} {d[0]:6.1f} x {d[1]:6.1f} x {d[2]:6.1f}  {mass:5.0f} g")
    print(f"\n{len(rows)} parts.")
    if failures:
        print("DOES NOT FIT:\n  " + "\n  ".join(failures))
        sys.exit(1)
    print(f"All parts fit {BED - 2 * BED_MARGIN:.0f} x {BED - 2 * BED_MARGIN:.0f} x {BED:.0f} mm.")


if __name__ == "__main__":
    main()
