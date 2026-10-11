"""Export every part for the web manual: assembly pose + on-bed print pose, as
compact quantised meshes in manual/models.json, and fill in manual/index.html.

    .venv/bin/python cad/export_web.py                # manual/ (page body for Claude artifacts)
    .venv/bin/python cad/export_web.py --site _site   # also a standalone site (GitHub Pages)
"""
import argparse
import base64
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

import build  # noqa: E402
import fuselage  # noqa: E402
import tail  # noqa: E402
import wing  # noqa: E402
from geom import mesh_arrays  # noqa: E402

MANUAL = Path(__file__).resolve().parent.parent / "manual"
OUT = MANUAL / "models.json"
SOLID_PARTS = ("wing_tip", "aileron", "tail_")   # printed with infill, not modelled as shells
LW_PLA, PLA, PETG = 0.55, 1.24, 1.27


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def pack(man):
    v, t = mesh_arrays(man)
    lo, hi = v.min(0), v.max(0)
    span = np.maximum(hi - lo, 1e-6)
    q = np.round((v - lo) / span * 65535).astype("<u2")
    wide = len(v) > 65535
    return {"min": lo.round(3).tolist(), "span": span.round(3).tolist(), "pos": b64(q),
            "idx": b64(t.astype("<u4" if wide else "<u2")), "wide": wide}


def printed_cm3(p):
    """Estimated printed volume: shells are modelled at true wall thickness;
    solid parts print as 2 walls (~0.84 mm) plus 8 % infill."""
    v = p.printed.volume() / 1000
    if not p.name.startswith(SOLID_PARTS):
        return v
    shell = p.printed.surface_area() * 0.84 / 1000
    return min(v, shell + 0.08 * max(v - shell, 0))


def group(name):
    if name.startswith(("wing", "aileron")):
        return "Wing"
    if name.startswith("tail"):
        return "Tail"
    return "Fuselage"


def hex_color(rgb):
    return "#" + "".join(f"{int(round(c * 255)):02x}" for c in rgb)


STANDALONE_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
"""


def write_site(site):
    """manual/index.html is a page body (the artifact host adds the document
    skeleton); a static host needs the full document."""
    site = Path(site)
    site.mkdir(parents=True, exist_ok=True)
    body = (MANUAL / "index.html").read_text()
    head_end = body.index("<nav ")
    page = STANDALONE_HEAD + body[:head_end] + "</head>\n<body>\n" + body[head_end:] + "\n</body>\n</html>\n"
    (site / "index.html").write_text(page)
    shutil.copy(OUT, site / "models.json")
    (site / ".nojekyll").write_text("")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", help="also write a standalone static site to this folder")
    args = ap.parse_args()
    parts = wing.parts() + fuselage.parts() + tail.parts()
    out = {"bed": build.BED, "parts": [], "hardware": []}
    for i, p in enumerate(parts, 1):
        on_bed, dims = build.place_on_bed(p.printed)
        cm3 = printed_cm3(p)
        rho = PETG if p.material == "PETG" else LW_PLA
        out["parts"].append({
            "name": p.name, "file": f"{i:02d}_{p.name}.stl", "group": group(p.name),
            "material": p.material, "note": p.note, "color": hex_color(p.color),
            "dims": [round(d, 1) for d in dims],
            "grams": round(cm3 * rho), "grams_pla": round(cm3 * (PETG if p.material == "PETG" else PLA)),
            "asm": pack(p.assembly), "bed": pack(on_bed)})
    names = ["Carbon boom 12 mm", "Motor", "Propeller 7 in"]
    for (man, rgb), n in zip(build.hardware_preview(), names):
        out["hardware"].append({"name": n, "color": hex_color(rgb), "asm": pack(man)})
    MANUAL.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    render_page(out["parts"])
    if args.site:
        write_site(args.site)
    total = sum(p["grams"] for p in out["parts"])
    print(f"{len(parts)} parts, {OUT.stat().st_size / 1e6:.1f} MB, printed mass ~{total} g LW-PLA")


def render_page(parts):
    """Fill manual/template.html with the part list and BOM, so the page reads
    complete before the 3D data loads."""
    from html import escape
    buttons = []
    for g in ("Wing", "Fuselage", "Tail"):
        rows = [f'          <button type="button" class="part-btn" data-part="{p["name"]}" aria-pressed="false">'
                f'<span>{escape(p["name"])}</span><span>{p["dims"][2]:.0f} mm</span></button>'
                for p in parts if p["group"] == g]
        buttons.append(f'        <div class="part-group"><h3>{g}</h3>\n' + "\n".join(rows) + "\n        </div>")
    rows = []
    for p in parts:
        tag = '<span class="tag petg">PETG</span>' if p["material"] == "PETG" else '<span class="tag">LW-PLA / PLA</span>'
        dims = " × ".join(f"{d:.0f}" for d in p["dims"])
        rows.append(f'          <tr><td><code>{p["file"]}</code></td><td>{tag}</td><td class="num">{dims}</td>'
                    f'<td class="num">{p["grams"]}</td><td class="num">{p["grams_pla"]}</td></tr>')
    page = (MANUAL / "template.html").read_text()
    for key, val in {"{{PART_BUTTONS}}": "\n".join(buttons), "{{PART_ROWS}}": "\n".join(rows),
                     "{{PART_COUNT}}": str(len(parts)),
                     "{{MASS_LW}}": str(sum(p["grams"] for p in parts)),
                     "{{MASS_PLA}}": str(sum(p["grams_pla"] for p in parts))}.items():
        page = page.replace(key, val)
    assert "{{" not in page, "unfilled placeholder in manual template"
    (MANUAL / "index.html").write_text(page)


if __name__ == "__main__":
    main()
