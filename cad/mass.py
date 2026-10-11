"""Weight and balance: mass of every printed part and component, all-up
weight, and where the centre of gravity lands relative to the target."""
import numpy as np

import hardware
from geom import mesh_arrays
from params import WING_LE_X

SOLID_PARTS = ("wing_tip", "aileron", "tail_")   # printed with infill, not modelled as shells
SOLID_WALL, SOLID_INFILL = 0.45, 0.05            # 1 wall loop + 5 % gyroid (the PLA print settings)
DENSITY = {"LW-PLA": 0.55, "PLA": 1.24, "PETG": 1.27}   # g/cm3 as printed (LW-PLA foamed)
CG_TARGET = 66.0                                 # mm behind the wing LE, from aero/report.py


def printed_cm3(p):
    """Estimated printed volume: shells are modelled at true wall thickness;
    solid parts print as one wall plus sparse infill."""
    v = p.printed.volume() / 1000
    if not p.name.startswith(SOLID_PARTS):
        return v
    shell = p.printed.surface_area() * SOLID_WALL / 1000
    return min(v, shell + SOLID_INFILL * max(v - shell, 0))


def centroid(man):
    """Volume centroid of a closed mesh (signed tetrahedra from the origin)."""
    v, t = mesh_arrays(man)
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    vol = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6
    return (vol[:, None] * (a + b + c) / 4).sum(0) / vol.sum()


DESIGN_FILAMENT = "PLA"          # the nose weight is sized for this
CG_TOLERANCE = 3.0               # mm


def budget(parts, comps, filament):
    """[(name, grams, xyz)] for every part (printed in `filament`) and component.
    Ballast only applies to the design filament."""
    rows = []
    for p in parts:
        rho = DENSITY["PETG"] if p.material == "PETG" else DENSITY[filament]
        rows.append((p.name, printed_cm3(p) * rho, centroid(p.assembly)))
    for c in comps:
        if c.category == "Ballast" and filament != DESIGN_FILAMENT:
            continue
        rows.append((c.name, c.mass, centroid(c.shape)))
    grams, where = hardware.WIRING
    rows.append(("Wiring and connectors", grams, np.array(where)))
    return rows


def balance(rows, battery="Battery"):
    """All-up mass, CG (mm behind the wing LE), and how far the battery must
    move (mm, + = aft) to put the CG on target."""
    m = np.array([r[1] for r in rows])
    x = np.array([r[2][0] for r in rows])
    auw = m.sum()
    cg = (m * x).sum() / auw - WING_LE_X
    batt = next(r[1] for r in rows if r[0] == battery)
    return auw, cg, (CG_TARGET - cg) * auw / batt


def nose_weight_for_target(rows, x_weight):
    """Grams of nose weight at x_weight that bring the CG onto the target."""
    m = np.array([r[1] for r in rows])
    x = np.array([r[2][0] for r in rows])
    xt = WING_LE_X + CG_TARGET
    return max(0.0, ((m * x).sum() - xt * m.sum()) / (xt - x_weight))
