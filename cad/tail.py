"""Tail: a flat-sided hub on the end of the boom carries the fin on top and
the stabiliser halves on its sides. Elevators are joined by a rod that runs
through a slot in the hub, below the rudder."""
import math

import numpy as np

from airfoils import Airfoil
from geom import (box, check, cyl_y, cyl_z, extrude, loft, poly, rot_x, rot_y, teardrop, transform,
                  v_region)
from params import *
from part import Part

COLOR = (0.66, 0.66, 0.64)
SURFACE_COLOR = (0.48, 0.50, 0.53)
STAB = Airfoil.naca00(STAB_THICK)
FIN = Airfoil.naca00(FIN_THICK)
XZ_TO_ASSEMBLY = np.array([[1.0, 0, 0], [0, 0, 1], [0, 1, 0]])   # 2D (x, z) extruded along y
YZ_TO_ASSEMBLY = np.array([[0.0, 0, 1], [1, 0, 0], [0, 1, 0]])   # 2D (y, z) extruded along x


def fin_le(z):
    return FIN_ROOT_LE + (FIN_TIP_LE - FIN_ROOT_LE) * (z - FIN_ROOT_Z) / (FIN_TOP_Z - FIN_ROOT_Z)


def stab_le(y):
    f = (abs(y) - HUB_HALF_W) / (STAB_TIP_Y - HUB_HALF_W)
    return TAIL_TE_X - (STAB_ROOT_CHORD + (STAB_TIP_CHORD - STAB_ROOT_CHORD) * f)


def hub():
    # Side profile: round top-front, and 45-degree chamfers under the front and
    # the back so the hub prints flat on the bed without supports.
    r, zc, xf = (HUB_Z1 - HUB_Z0) / 2, (HUB_Z0 + HUB_Z1) / 2, HUB_X0 + (HUB_Z1 - HUB_Z0) / 2
    rise = 23.0
    a = np.radians(np.linspace(90, 180, 13))
    profile = [(xf, HUB_Z0), (TAIL_TE_X - rise, HUB_Z0), (TAIL_TE_X, HUB_Z0 + rise), (TAIL_TE_X, HUB_Z1)]
    profile += list(zip(xf + r * np.cos(a), zc + r * np.sin(a)))
    side = transform(extrude(poly(profile), -HUB_HALF_W, HUB_HALF_W), XZ_TO_ASSEMBLY)
    ch, w = 3.0, HUB_HALF_W
    octagon = poly([(-w + ch, HUB_Z0), (w - ch, HUB_Z0), (w, HUB_Z0 + ch), (w, HUB_Z1 - ch),
                    (w - ch, HUB_Z1), (-w + ch, HUB_Z1), (-w, HUB_Z1 - ch), (-w, HUB_Z0 + ch)])
    chamfer = transform(extrude(octagon, HUB_X0 - 5, TAIL_TE_X + 5), YZ_TO_ASSEMBLY)
    return side ^ chamfer


def fin():
    rings = []
    for z in (FIN_ROOT_Z, FIN_TOP_Z):
        le = fin_le(z)
        r2 = FIN.ring(TAIL_TE_X - le, TE_THICK)
        rings.append(np.stack([le + r2[:, 0], r2[:, 1], np.full(len(r2), z)], 1))
    return loft(rings)


def stab_right():
    rings = []
    for y in (HUB_HALF_W, STAB_TIP_Y):
        le = stab_le(y)
        r2 = STAB.ring(TAIL_TE_X - le, TE_THICK)
        rings.append(np.stack([le + r2[:, 0], np.full(len(r2), y), STAB_Z + r2[:, 1]], 1))
    return loft(rings)


def stab_pitch(man):
    """Set the stabiliser incidence: rotate about the stab spar axis."""
    m = man.translate((-STAB_SPAR_X, 0, -STAB_Z))
    return transform(m, rot_y(STAB_INCIDENCE)).translate((STAB_SPAR_X, 0, STAB_Z))


def fin_half_thickness(x, z):
    le = fin_le(z)
    return float(FIN.half_thickness(x - le, TAIL_TE_X - le, TE_THICK))


def servo_pocket(x0, z0, side):
    """Pocket for a servo lying against the fin side (side -1 = left)."""
    pc, ps, pd = SERVO_POCKET
    x1, z1 = x0 + ps, z0 + pc
    ht_min = min(fin_half_thickness(x, z) for x in (x0, x1) for z in (z0, z1))
    floor = side * (fin_half_thickness((x0 + x1) / 2, (z0 + z1) / 2) - pd)
    wall = ht_min + side * floor      # material left on the far side of the fin
    assert wall > 2.5, f"servo pocket leaves only {wall:.1f} mm of fin"
    y0, y1 = (floor, 40) if side > 0 else (-40, floor)
    return box(x0, y0, z0, x1, y1, z1)


def parts():
    gap = SURFACE_GAP
    f = fin()
    rudder = (f ^ transform(extrude(v_region(RUDDER_HINGE_X + gap / 2, 0, BEVEL_DEG), -50, 300),
                            np.eye(3))) ^ box(0, -50, RUDDER_Z0 + gap, 2000, 50, 300)
    fin_fixed = f - box(RUDDER_HINGE_X - gap / 2, -50, RUDDER_Z0, 2000, 50, 300)

    body = hub() + fin_fixed
    r_boom = BOOM_D / 2 + TUBE_FIT
    # Horizontal holes are teardrops (point up) so their ceilings print cleanly.
    body = body - transform(extrude(teardrop(0, BOOM_Z, r_boom), HUB_X0 - 1, BOOM_X1), YZ_TO_ASSEMBLY)
    # The stab spar is the incidence pivot; the pin hole and the elevator-joiner
    # slot move with the stab.
    body = body - transform(extrude(teardrop(STAB_SPAR_X, STAB_Z, STAB_SPAR_D / 2 + TUBE_FIT), -20, 20),
                            XZ_TO_ASSEMBLY)
    body = body - stab_pitch(transform(extrude(teardrop(STAB_PIN_X, STAB_Z, STAB_PIN_D / 2 + TUBE_FIT), -20, 20),
                                       XZ_TO_ASSEMBLY))
    slot_h = 3.5     # elevator joiner swings +/-30 deg on a 6 mm arm
    body = body - stab_pitch(box(ELEV_JOINER_X - 1.5, -20, STAB_Z - slot_h, ELEV_JOINER_X + 1.5, 20, STAB_Z + slot_h)
                             + cyl_y(-20, 20, ELEV_JOINER_X, STAB_Z - slot_h, 1.5)
                             + cyl_y(-20, 20, ELEV_JOINER_X, STAB_Z + slot_h, 1.5))
    body = body - servo_pocket(728, 44, -1) - servo_pocket(750, 74, 1)
    body = body - cyl_z(BOOM_Z, 46, 744, -3, 3.5) - cyl_z(BOOM_Z, 82, 767, 3, 3.5)

    s = stab_right()
    v = transform(extrude(v_region(ELEV_HINGE_X + gap / 2, STAB_Z, BEVEL_DEG), -1, 400), XZ_TO_ASSEMBLY)
    elev = (s ^ v) ^ box(0, HUB_HALF_W + 0.8, -50, 2000, 400, 300)
    elev = elev - cyl_y(0, HUB_HALF_W + ELEV_JOINER_DEPTH, ELEV_JOINER_X, STAB_Z, ELEV_JOINER_D / 2 + TUBE_FIT)
    stab = s - box(ELEV_HINGE_X - gap / 2, 0, -50, 2000, 400, 300)
    stab = stab - cyl_y(0, HUB_HALF_W + STAB_SPAR_DEPTH, STAB_SPAR_X, STAB_Z, STAB_SPAR_D / 2 + TUBE_FIT)
    stab = stab - cyl_y(0, HUB_HALF_W + STAB_PIN_DEPTH, STAB_PIN_X, STAB_Z, STAB_PIN_D / 2 + TUBE_FIT)
    stab, elev = stab_pitch(stab), stab_pitch(elev)

    root_down_r, root_down_l = rot_x(90), rot_x(-90)
    out = [Part("tail_fin_hub", body, body, "LW-PLA", COLOR,
                "Boom socket, fin, stab mounts, elevator + rudder servo pockets."),
           Part("tail_rudder", rudder, rudder, "LW-PLA", SURFACE_COLOR, "")]
    for name, m, color, note in (("tail_stab", stab, COLOR, "Root face down."),
                                 ("tail_elevator", elev, SURFACE_COLOR, "Halves joined by a 2 mm rod.")):
        left = m.mirror((0, 1, 0))
        out.append(Part(f"{name}_R", transform(m, root_down_r), m, "LW-PLA", color, note))
        out.append(Part(f"{name}_L", transform(left, root_down_l), left, "LW-PLA", color, note))
    for p in out:
        check(p.printed, p.name)
    return out
