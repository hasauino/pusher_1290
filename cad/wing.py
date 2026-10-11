"""Wing: centre section, three panels per side, upswept tips and ailerons.

Each panel is modelled in its print frame: airfoil in the XY plane (x = chord
from the leading edge, y = thickness), span along +Z. That is also how it
prints: standing on its root, with only span-wise walls inside, so nothing
inside the wing overhangs.
"""
import math

import manifold3d as m3d
import numpy as np

from airfoils import WING as AF
from geom import (box, check, circle, cyl_y, cyl_z, extrude, loft, poly, rect, rot_y, teardrop,
                  transform, v_region)
from params import *
from part import Part

WING_COLOR = (0.62, 0.62, 0.60)
XZ_TO_PANEL = np.array([[1.0, 0, 0], [0, 0, 1], [0, 1, 0]])   # 2D (chord, span) extruded through the thickness
SURFACE_COLOR = (0.48, 0.50, 0.53)


def upper(x):
    return AF.surface(x, CHORD, TE_THICK)[0]


def lower(x):
    return AF.surface(x, CHORD, TE_THICK)[1]


def mid(x):
    return float(AF.mid(x, CHORD, TE_THICK))


def outer_cs():
    return poly(AF.ring(CHORD, TE_THICK))


def structure_cs(aileron):
    """Skin + span-wise webs + spar sleeves; aileron panels end at the hinge."""
    o = outer_cs()
    cs = o - o.offset(-SKIN, m3d.JoinType.Miter)
    webs = [LE_WEB_X, SPAR_X, REAR_SPAR_X] + ([] if aileron else [0.75 * CHORD])
    for x in webs:
        cs = cs + (rect(x - WEB / 2, -50, x + WEB / 2, 50) ^ o)
    spars = ((SPAR_X, SPAR_D), (REAR_SPAR_X, REAR_SPAR_D))
    for x, d in spars:
        cs = cs + (circle(x, mid(x), d / 2 + TUBE_FIT + SLEEVE_WALL) ^ o)
    for x, d in spars:
        cs = cs - circle(x, mid(x), d / 2 + TUBE_FIT)
    if aileron:
        xf = HINGE_X - SURFACE_GAP / 2
        cs = (cs ^ rect(-5, -50, xf, 50)) + (o ^ rect(xf - 1.2, -50, xf, 50))
    return cs


def aileron_cs():
    a = outer_cs() ^ v_region(HINGE_X + SURFACE_GAP / 2, mid(HINGE_X), BEVEL_DEG)
    r = AILERON_JOINER_D / 2 + TUBE_FIT
    margin = AF.half_thickness(AILERON_JOINER_X, CHORD, TE_THICK) - r
    assert margin > 0.8, f"aileron joiner wall only {margin:.2f} mm"
    return a - circle(AILERON_JOINER_X, mid(AILERON_JOINER_X), r)


def add_servo_bay(body):
    """Pocket for a servo lying flat, opening through the bottom skin."""
    pc, ps, pd = SERVO_POCKET
    x0, x1 = SERVO_POCKET_X0, SERVO_POCKET_X0 + pc
    z0, z1 = SERVO_POCKET_Z0, SERVO_POCKET_Z0 + ps
    ylo = float(np.min(lower(np.linspace(x0, x1, 25))))
    yfloor = ylo + pd
    w, s2 = 1.2, math.sqrt(2)
    bz0, bz1 = z0 - w - pd, z1 + w + pd
    block = box(x0 - w, -40, bz0, x1 + w, 40, bz1)
    # 45-degree block ends so it grows out of the bottom skin without overhangs.
    block = block.trim_by_plane((0, -1 / s2, 1 / s2), (bz0 - ylo) / s2)
    block = block.trim_by_plane((0, -1 / s2, -1 / s2), (-bz1 - ylo) / s2)
    block = block ^ extrude(outer_cs(), 0, PANEL_SPAN)
    pocket = box(x0, -40, z0, x1, yfloor, z1)
    lead = cyl_z(bz0 - 2, z0 + 1, (x0 + x1) / 2, ylo + 6, 3.5)
    return body + block - pocket - lead


def center_local():
    span = 2 * CENTER_HALF
    body = extrude(structure_cs(False), 0, span)
    prism = extrude(outer_cs(), 0, span)
    for x in BOLT_X:
        yu, yl = float(upper(x)), float(lower(x))
        sleeve = transform(extrude(teardrop(x, CENTER_HALF, 4.0, (0, -1)), yl - 1, yu + 1), XZ_TO_PANEL)
        body = body + (sleeve ^ prism)
        body = body - cyl_y(yl - 2, yu + 2, x, CENTER_HALF, BOLT_D / 2)
        body = body - cyl_y(yu - 3.2, yu + 5, x, CENTER_HALF, BOLT_HEAD_D / 2)
    # Servo leads leave the wing through the bottom skin, inside the saddle window.
    yl = float(lower(80))
    for z in (CENTER_HALF - 30, CENTER_HALF + 30):
        body = body - cyl_y(yl - 5, yl + 2.5, 80, z, 5)
    return body


def panel_local(aileron, servo=False):
    body = extrude(structure_cs(aileron), 0, PANEL_SPAN)
    return add_servo_bay(body) if servo else body


def aileron_local():
    return extrude(aileron_cs(), SURFACE_GAP / 2, PANEL_SPAN - SURFACE_GAP / 2)


def tip_path(n=40):
    """Stations along the upswept tip: (span from tip root, rise, LE offset, chord, upsweep rad)."""
    t = np.linspace(0, 1, n)
    phi = np.radians(TIP_PHI_MAX) * t**1.6
    dt = np.diff(t)
    reach = np.sum((np.cos(phi[1:]) + np.cos(phi[:-1])) / 2 * dt)
    ds = dt * TIP_REACH / reach
    pz = np.concatenate([[0], np.cumsum((np.cos(phi[1:]) + np.cos(phi[:-1])) / 2 * ds)])
    py = np.concatenate([[0], np.cumsum((np.sin(phi[1:]) + np.sin(phi[:-1])) / 2 * ds)])
    chord = CHORD - (CHORD - TIP_END_CHORD) * t**2.2
    xle = TIP_LE_SWEEP * t**2.5
    return pz, py, xle, chord, phi


def tip_stations(n=12):
    """(y, z, x_le, chord) of the tip in the aircraft frame (mm, before incidence)."""
    pz, py, xle, chord, _ = tip_path(n)
    return [(TIP_Y0 + a, b, c, d) for a, b, c, d in zip(pz, py, xle, chord)][1:]


def tip_local():
    """Upswept tip lofted along a curved path; the root matches the panels."""
    pz, py, xle, chord, phi = tip_path()
    n = len(pz)
    thick = np.ones(n)
    thick[-1], thick[-2] = 0.45, 0.8      # round the very end off a little
    rings = []
    for i in range(n):
        r2 = AF.ring(chord[i], TE_THICK, thick[i])
        c, s = math.cos(phi[i]), math.sin(phi[i])
        rings.append(np.stack([xle[i] + r2[:, 0], py[i] + r2[:, 1] * c, pz[i] - r2[:, 1] * s], 1))
    tip = loft(rings)
    socket = cyl_z(-1, 35, REAR_SPAR_X, mid(REAR_SPAR_X), REAR_SPAR_D / 2 + TUBE_FIT)
    return tip - socket


# --- Placement -------------------------------------------------------------------

def to_assembly(local, y0, side=1):
    """Panel frame -> aircraft frame: chord to +X, span to +Y, thickness to +Z,
    root at span station y0, then pitched up by INCIDENCE about the LE."""
    place = np.array([[1.0, 0, 0], [0, 0, 1], [0, 1, 0]])
    rot = rot_y(INCIDENCE) @ place
    out = transform(local, rot, (WING_LE_X, y0, WING_LE_Z))
    return out.mirror((0, 1, 0)) if side < 0 else out


def envelope(offset):
    """Centre-section outline grown by `offset`, for cutting the wing saddle."""
    cs = outer_cs().offset(offset, m3d.JoinType.Round) if offset else outer_cs()
    return to_assembly(extrude(cs, -10, 2 * CENTER_HALF + 10), -CENTER_HALF)


def center_frame(local):
    """Place something modelled in the centre section's frame (z = span from -80)."""
    return to_assembly(local, -CENTER_HALF)


# --- Parts -----------------------------------------------------------------------

def _pair(name, local, y0, material, color, note):
    right = Part(f"{name}_R", local, to_assembly(local, y0), material, color, note)
    left = Part(f"{name}_L", local.mirror((0, 1, 0)), right.assembly.mirror((0, 1, 0)),
                material, color, note)
    return [right, left]


def parts():
    out = [Part("wing_center", center_local(), center_frame(center_local()), "PLA",
                WING_COLOR, "Bolts to the fuselage with 2x M3; carries both spars.")]
    s1, s2, s3 = (panel_local(False), panel_local(True, servo=True), panel_local(True))
    ail, tip = aileron_local(), tip_local()
    y1, y2, y3 = CENTER_HALF, CENTER_HALF + PANEL_SPAN, CENTER_HALF + 2 * PANEL_SPAN
    out += _pair("wing_s1", s1, y1, "PLA", WING_COLOR, "Plain panel.")
    out += _pair("wing_s2", s2, y2, "PLA", WING_COLOR, "Aileron servo pocket (bottom).")
    out += _pair("wing_s3", s3, y3, "PLA", WING_COLOR, "Outer aileron panel.")
    out += _pair("wing_tip", tip, TIP_Y0, "PLA", WING_COLOR, "Upswept tip; print root down.")
    out += _pair("aileron_inner", ail, y2, "PLA", SURFACE_COLOR,
                 "Joined to the outer aileron by a 3 mm carbon rod.")
    out += _pair("aileron_outer", ail, y3, "PLA", SURFACE_COLOR, "")
    for p in out:
        check(p.printed, p.name)
    return out
