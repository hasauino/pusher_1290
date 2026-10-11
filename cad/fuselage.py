"""Fuselage pod: a superellipse loft that rises into a motor cone at the back,
with a boom socket below it (the Lark-style notch the prop spins in).

The pod is a 1.2 mm shell. It is cut into segments that print standing on
their rear face; each segment carries a glue sleeve ("lip") that slides into
the one in front of it.
"""
import math

import numpy as np

import wing
from airfoils import WING as AF
from geom import (Manifold, box, check, cyl_x, cyl_z, extrude, loft, pchip, poly, rot_y,
                  superellipse, teardrop, transform, union)
from params import *
from part import Part

COLOR = (0.70, 0.70, 0.68)
HARD_COLOR = (0.25, 0.25, 0.27)
RING_N = 96
TE_X = WING_LE_X + CHORD * math.cos(math.radians(INCIDENCE))

_WX = sorted(POD_X + POD_MID_X)
_W = [dict(zip(POD_X + POD_MID_X, POD_W + POD_MID_W))[x] for x in _WX]
_ZB = [dict(zip(POD_X + POD_MID_X, POD_ZB + POD_MID_ZB))[x] for x in _WX]

SOCKET = [  # x, width, z_bottom, z_top
    (240, 60, 1.0, 40), (270, 40, 2.5, 32), (300, 28, 3.5, 26),
    (340, 22, BOOM_Z - 10, BOOM_Z + 10), (SOCKET_END_X, 20, BOOM_Z - 10, BOOM_Z + 10)]


def wing_mid_z(x):
    """Height of the wing camber line above aircraft station x."""
    a = math.radians(INCIDENCE)
    xl = (np.asarray(x, float) - WING_LE_X) / math.cos(a)
    return WING_LE_Z - xl * math.sin(a) + AF.mid(xl, CHORD, TE_THICK) * math.cos(a)


_ZT_FRONT = ([x for x, z in zip(POD_X, POD_ZT) if z is not None and x < WING_LE_X] + [WING_LE_X],
             [z for x, z in zip(POD_X, POD_ZT) if z is not None and x < WING_LE_X] + [WING_LE_Z])
_ZT_BACK = ([TE_X] + [x for x, z in zip(POD_X, POD_ZT) if z is not None and x > TE_X],
            [float(wing_mid_z(TE_X))] + [z for x, z in zip(POD_X, POD_ZT) if z is not None and x > TE_X])


def section(x):
    """(width, z_bottom, z_top) of the outer skin at station x."""
    x = min(max(x, 0.0), MOTOR_X)
    w, zb = float(pchip(_WX, _W, x)), float(pchip(_WX, _ZB, x))
    if x < WING_LE_X:
        zt = float(pchip(*_ZT_FRONT, x))
    elif x > TE_X:
        zt = float(pchip(*_ZT_BACK, x))
    else:
        zt = float(wing_mid_z(x))
    return w, zb, zt


def ring(x, w, zb, zt, n=RING_N):
    p = superellipse(w, zt - zb, SUPER_N, n, zc=(zb + zt) / 2)
    return np.column_stack([np.full(n, x), p[:, 0], p[:, 1]])


def pod(xs, inset=0.0):
    rings = []
    for x in xs:
        w, zb, zt = section(x)
        rings.append(ring(x, w - 2 * inset, zb + inset, zt - inset))
    return loft(rings)


def grid(x0, x1, step=4.0):
    return np.linspace(x0, x1, max(2, int(math.ceil((x1 - x0) / step)) + 1))


def socket_outer():
    xs = grid(SOCKET[0][0], SOCKET_END_X, 4)
    cols = list(zip(*SOCKET))
    rings = []
    for x in xs:
        w, zb, zt = (float(pchip(cols[0], cols[i], x)) for i in (1, 2, 3))
        rings.append(ring(x, w, zb, zt, 64))
    return loft(rings)


def lip(x_cut):
    """Glue sleeve owned by the segment behind x_cut, reaching LIP mm forward."""
    xs_fwd, xs_own = grid(x_cut - LIP, x_cut, 2), grid(x_cut, x_cut + 5, 2)
    inner_face = WALL + LIP_FIT
    fwd = pod(xs_fwd, inner_face) - pod(xs_fwd, inner_face + 1.2)
    own = pod(xs_own, WALL - 0.3) - pod(xs_own, inner_face + 1.2)
    return fwd + own


def build():
    xs_outer = np.concatenate([np.linspace(0, 24, 13), grid(28, MOTOR_X, 4)])
    outer = pod(xs_outer)
    xs_inner = np.concatenate([np.linspace(1.5, 24, 10), grid(28, MOTOR_X + 3, 4)])
    inner = pod(xs_inner, WALL)
    # Internal features are clipped to this slightly larger cavity so they fuse with the wall.
    inner_fused = pod(xs_inner, WALL - 0.3)
    sock = socket_outer()
    core = sock ^ box(296, -50, -10, 600, 50, 300)
    body = (outer + sock) - (inner - core)

    # Wing saddle: everything inside the wing goes; a 3 mm plate under the wing
    # stays, with a window for wiring and battery access.
    env = wing.envelope(0.2)
    # The window's front end is a 45-degree point: printed nose-up, a square
    # end would be a 70 mm bridge.
    wx0, wx1, wy = SADDLE_WINDOW_X[0], SADDLE_WINDOW_X[1], SADDLE_WINDOW_HALF_Y
    window = extrude(poly([(wx0, 0), (wx0 + wy, -wy), (wx1, -wy), (wx1, wy), (wx0 + wy, wy)]), 0, 300)
    plate = (outer ^ wing.envelope(0.2 + SADDLE_T)) - env - window

    # Bosses for M3 heat-set inserts under the two wing bolts.
    # Teardrop-shaped toward the tail, so they print without support nose-up.
    bosses, inserts = [], []
    for x in BOLT_X:
        yl = float(wing.lower(x))
        bosses.append(transform(extrude(teardrop(x, CENTER_HALF, 4.5, (1, 0)), yl - 12, yl + 1),
                                wing.XZ_TO_PANEL))
        inserts.append(transform(extrude(teardrop(x, CENTER_HALF, INSERT_D / 2, (-1, 0)),
                                         yl - INSERT_DEPTH, yl + 1), wing.XZ_TO_PANEL))
    bosses = wing.center_frame(union(bosses)) ^ outer
    inserts = wing.center_frame(union(inserts))

    floor = inner_fused ^ box(92, -80, FLOOR_Z, 300, 80, FLOOR_Z + FLOOR_T)

    # Camera cage: a square tube behind the lens hole, braced to the shell by
    # two cross ribs. All walls run along X, so they print vertically, and the
    # ribs' rear edges slope at 45 degrees so they never start in mid-air.
    _, zb3, zt3 = section(3.0)
    cam_z, c, s2 = (zb3 + zt3) / 2, CAMERA / 2, math.sqrt(2)
    cage = box(6, -c - 1.2, cam_z - c - 1.2, 22, c + 1.2, cam_z + c + 1.2)
    rib_v, rib_h = box(6, -0.6, -50, 72, 0.6, 300), box(6, -100, cam_z - 0.6, 72, 100, cam_z + 0.6)
    ribs = (rib_v.trim_by_plane((-1 / s2, 0, 1 / s2), (cam_z - 22) / s2)
            + rib_v.trim_by_plane((-1 / s2, 0, -1 / s2), (-cam_z - 22) / s2)
            + rib_h.trim_by_plane((-1 / s2, 1 / s2, 0), -22 / s2)
            + rib_h.trim_by_plane((-1 / s2, -1 / s2, 0), -22 / s2))
    cam_frame = ((cage + ribs) ^ inner_fused) - box(5, -c - 0.2, cam_z - c - 0.2, 40, c + 0.2, cam_z + c + 0.2)

    body = union([body, plate, bosses, floor, cam_frame])
    body = body - env - inserts
    r_boom = BOOM_D / 2 + TUBE_FIT
    body = body - cyl_x(BOOM_X0, SOCKET_END_X + 1, 0, BOOM_Z, r_boom)
    body = body - transform(Manifold.cylinder(r_boom, 0.01, r_boom), rot_y(90), (BOOM_X0 - r_boom, 0, BOOM_Z))
    body = body - cyl_z(BOOM_Z, 40, BOOM_X0 + 5, 0, 4)            # servo leads from the boom
    body = body - cyl_x(-1, 12, 0, cam_z, CAMERA_LENS_D / 2)

    # Battery hatch on top: a tab at its front hooks under the fuselage skin,
    # its back edge rests on a ledge. Lift the back, slide it out backwards.
    hx0, hx1 = HATCH_X
    hatch = body ^ box(hx0, -80, HATCH_Z, hx1, 80, 300)
    body = body - box(hx0 - 0.3, -80, HATCH_Z - 0.3, hx1 + 0.3, 80, 300)
    xs = grid(hx0 - 8, hx0 + 7, 2)
    hatch = hatch + ((pod(xs, WALL - 0.3) - pod(xs, WALL + 1.3)) ^ box(hx0, -80, HATCH_Z + 3, hx0 + 5, 80, 300))
    hatch = hatch + ((pod(xs, WALL + 0.15) - pod(xs, WALL + 1.3)) ^ box(hx0 - 6, -80, HATCH_Z + 3, hx0, 80, 300))
    xs = grid(hx1 - 6, hx1 + 6, 2)
    ledge = ((pod(xs, WALL + 0.1) - pod(xs, WALL + 2.0)) ^ box(hx1 - 5, -80, HATCH_Z - 4, hx1 + 5, 80, 300)
             + (pod(xs, WALL - 0.3) - pod(xs, WALL + 2.0)) ^ box(hx1 + 0.3, -80, HATCH_Z - 4, hx1 + 5, 80, 300))
    body = body + ledge

    keepout = union([wing.envelope(0.5 + SADDLE_T), bosses,
                     box(80, -80, FLOOR_Z - 0.3, 310, 80, FLOOR_Z + FLOOR_T + 0.3)])
    return body, hatch, keepout


def motor_mount():
    xs = grid(MOTOR_X - 8, MOTOR_X, 2)
    plug = pod(xs, WALL + LIP_FIT)
    w, zb, zt = section(MOTOR_X)
    flange = loft([ring(MOTOR_X, w, zb, zt), ring(MOTOR_X + 2, w, zb, zt)])
    mount = plug + flange
    mount = mount - cyl_x(MOTOR_X - 10, MOTOR_X + 5, 0, MOTOR_Z, 5)
    for dy, dz in ((8, 0), (-8, 0), (0, 9.5), (0, -9.5)):         # 16 x 19 mm cross pattern
        mount = mount - cyl_x(MOTOR_X - 10, MOTOR_X + 5, dy, MOTOR_Z + dz, 1.6)
    mount = mount - cyl_x(MOTOR_X - 10, MOTOR_X + 5, 6.5, MOTOR_Z - 6.5, 3)  # motor wires
    return mount


def parts():
    body, hatch, keepout = build()
    up_is_forward = rot_y(90)   # print standing on the rear face, lip pointing up
    bounds = [0.0] + FUSE_CUTS + [SOCKET_END_X + 5]
    names = ["fuse_1_nose", "fuse_2_front", "fuse_3_rear", "fuse_4_tail"]
    notes = ["Camera nose; slides over the front segment's sleeve (screw or tape it).",
             "Battery bay; hatch on top.",
             "Wing saddle rear, boom socket start, motor cone start.",
             ""]
    out = []
    for i, name in enumerate(names):
        xa, xb = bounds[i], bounds[i + 1]
        seg = body ^ box(xa, -100, -50, xb, 100, 300)
        if i > 0:
            seg = seg + (lip(xa) - keepout)
        if name == "fuse_4_tail":
            pieces = sorted(seg.decompose(), key=lambda p: -p.bounding_box()[5])
            assert len(pieces) == 2, f"tail segment has {len(pieces)} pieces"
            for suffix, p, note in (("motor_cone", pieces[0], "Print in PETG/PLA: carries the motor."),
                                    ("boom_socket", pieces[1], "Boom tail of the socket; the boom aligns it.")):
                out.append(Part(f"{name}_{suffix}", transform(p, up_is_forward), p,
                                "PETG" if suffix == "motor_cone" else "LW-PLA",
                                COLOR, note))
            continue
        out.append(Part(name, transform(seg, up_is_forward), seg, "LW-PLA", COLOR, notes[i]))
    out.append(Part("fuse_hatch", transform(hatch, up_is_forward), hatch, "LW-PLA", COLOR,
                    "Battery hatch: front tab hooks under the skin; tape or a magnet at the back."))
    mm = motor_mount()
    out.append(Part("motor_mount", transform(mm, up_is_forward), mm, "PETG", HARD_COLOR,
                    "Check the hole pattern against your motor before printing."))
    for p in out:
        check(p.printed, p.name)
    return out
