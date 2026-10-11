"""Bought parts placed in the aircraft frame: carbon, fasteners, servos,
propulsion and avionics. Simplified shapes, but at true size and position,
so the full assembly can be checked for collisions with the printed parts.

Electronics boxes use typical sizes for the parts suggested in the README;
swap the dimensions here if yours differ and rebuild to re-check the fit.
"""
import math
from dataclasses import dataclass

import numpy as np

import fuselage as fz
import tail
import wing
from geom import CrossSection, Manifold, box, cyl_x, cyl_y, cyl_z, extrude, rect, rot_x, rot_y, transform, union
from params import *

CARBON, STEEL, BRASS = (0.10, 0.10, 0.11), (0.62, 0.63, 0.66), (0.80, 0.62, 0.25)
SERVO, PCB, CELLS = (0.12, 0.12, 0.14), (0.10, 0.36, 0.20), (0.18, 0.42, 0.72)
MOTOR_RED, CAMERA_BLACK = (0.70, 0.13, 0.12), (0.08, 0.08, 0.09)

M3_LENGTHS = (6, 8, 10, 12, 14, 16, 20, 25)
ES08 = dict(body=(24.0, 23.0, 11.5), ears=32.5, ear_w=2.5)   # height, length, thickness
BATTERY_PACK = (65.0, 75.0, 56.0)    # one 4S3P 18650 pack: x, y, z
BATTERY_X0 = 96.0
FC = (45.0, 35.0, 13.0)
ESC = (50.0, 26.0, 10.0)
ESC_X = 410.0                        # centre, inside the rear segment / motor cone
VTX, RECEIVER, GPS = (32.0, 22.0, 10.0), (22.0, 14.0, 6.0), (20.0, 20.0, 9.0)


@dataclass
class Component:
    name: str
    category: str      # Carbon, Fasteners, Servos, Propulsion, Avionics
    shape: Manifold
    color: tuple
    spec: str = ""
    group: str = "Fuselage"   # assembly it belongs to: Wing, Fuselage, Boom, Tail


def rounded_bar_x(x0, x1, y0, y1, z0, z1, r):
    """Box along X with rounded long edges (a battery pack of cylindrical cells)."""
    cs = rect(y0 + r, z0 + r, y1 - r, z1 - r).offset(r, circular_segments=24)
    yz = np.array([[0.0, 0, 1], [1, 0, 0], [0, 1, 0]])
    return transform(extrude(cs, x0, x1), yz)


def m3_length(available):
    """Longest standard M3 bolt that leaves 0.5 mm in the hole."""
    return max(L for L in M3_LENGTHS if L <= available - 0.5)


# --- Carbon --------------------------------------------------------------------

def carbon():
    out = []
    mid = wing.mid
    span = lambda y0, y1, x, d: wing.center_frame(cyl_z(y0 + CENTER_HALF, y1 + CENTER_HALF, x, mid(x), d / 2, 32))
    main_half = 500.0
    rear_end = TIP_Y0 + 35.0 - 5.0     # 35 mm socket in the tip, 5 mm short of its bottom
    out.append(Component("Main spar", "Carbon", span(-main_half, main_half, SPAR_X, SPAR_D), CARBON,
                         f"tube {SPAR_D:.0f} mm OD x {2 * main_half:.0f} mm"))
    for side, (a, b) in (("R", (0.0, rear_end)), ("L", (-rear_end, 0.0))):
        out.append(Component(f"Rear spar {side}", "Carbon", span(a, b, REAR_SPAR_X, REAR_SPAR_D), CARBON,
                             f"tube {REAR_SPAR_D:.0f} mm OD x {rear_end:.0f} mm"))
    joint = CENTER_HALF + 2 * PANEL_SPAN          # S2/S3 joint, middle of the aileron pair
    for side, sign in (("R", 1), ("L", -1)):
        a, b = sorted((sign * (joint - 40), sign * (joint + 40)))
        out.append(Component(f"Aileron joiner {side}", "Carbon",
                             span(a, b, AILERON_JOINER_X, AILERON_JOINER_D), CARBON,
                             f"rod {AILERON_JOINER_D:.0f} mm x 80 mm"))
    out.append(Component("Boom", "Carbon", cyl_x(BOOM_X0, BOOM_X1, 0, BOOM_Z, BOOM_D / 2, 40), CARBON,
                         f"tube {BOOM_D:.0f} mm OD x {BOOM_X1 - BOOM_X0:.0f} mm"))
    stab_half = HUB_HALF_W + STAB_SPAR_DEPTH - 0.2
    out.append(Component("Stab spar", "Carbon", cyl_y(-stab_half, stab_half, STAB_SPAR_X, STAB_Z, STAB_SPAR_D / 2, 32),
                         CARBON, f"tube {STAB_SPAR_D:.0f} mm OD x {2 * stab_half:.0f} mm"))
    pin_half = HUB_HALF_W + STAB_PIN_DEPTH - 0.2
    out.append(Component("Stab pin", "Carbon",
                         tail.stab_pitch(cyl_y(-pin_half, pin_half, STAB_PIN_X, STAB_Z, STAB_PIN_D / 2, 24)),
                         CARBON, f"rod {STAB_PIN_D:.0f} mm x {2 * pin_half:.0f} mm"))
    joiner_half = HUB_HALF_W + ELEV_JOINER_DEPTH - 0.2
    out.append(Component("Elevator joiner", "Carbon",
                         tail.stab_pitch(cyl_y(-joiner_half, joiner_half, ELEV_JOINER_X, STAB_Z, ELEV_JOINER_D / 2, 16)),
                         STEEL, f"wire {ELEV_JOINER_D:.0f} mm x {2 * joiner_half:.0f} mm"))
    return out


# --- Fasteners -----------------------------------------------------------------

def fasteners():
    out = []
    for x, label in zip(BOLT_X, ("front", "rear")):
        yu, yl = float(wing.upper(x)), float(wing.lower(x))
        seat = yu - 3.2                                    # counterbore floor
        L = m3_length(seat - (yl - 0.2 - INSERT_DEPTH))    # down to the bottom of the insert hole
        bolt = (cyl_y(seat, seat + 3.0, x, CENTER_HALF, 2.75, 24)
                + cyl_y(seat - L, seat, x, CENTER_HALF, 1.5, 16))
        insert = cyl_y(yl - 0.2 - 5.7, yl - 0.2, x, CENTER_HALF, INSERT_D / 2, 24)
        out.append(Component(f"Wing bolt {label}", "Fasteners", wing.center_frame(bolt), STEEL,
                             f"M3 x {L} socket head"))
        out.append(Component(f"Heat-set insert {label}", "Fasteners", wing.center_frame(insert), BRASS,
                             "M3 x 5.7 brass insert"))
    plate_in = MOTOR_X - 8.0
    L = m3_length(10.0 + 4.5)              # mount plate + flange, ~4 mm into the motor
    for dy, dz in ((8, 0), (-8, 0), (0, 9.5), (0, -9.5)):
        screw = (cyl_x(plate_in - 3.0, plate_in, dy, MOTOR_Z + dz, 2.75, 20)
                 + cyl_x(plate_in, plate_in + L, dy, MOTOR_Z + dz, 1.5, 12))
        out.append(Component(f"Motor screw {dy:+.0f}/{dz:+.1f}", "Fasteners", screw, STEEL, f"M3 x {L} socket head"))
    return out


# --- Servos --------------------------------------------------------------------

def _servo(height_axis, length_axis, thick_axis, origin, ears_at_top=True):
    """ES08MA II lying flat, built along the given unit axes from `origin`
    (the corner at height 0, length 0, thickness 0)."""
    h, l, t = ES08["body"]
    ear, ew = ES08["ears"], ES08["ear_w"]
    m = np.column_stack([height_axis, length_axis, thick_axis])
    body = box(0, 0, 0, h, l, t)
    ears = box(h - 6 - ew, -(ear - l) / 2, 0, h - 6, l + (ear - l) / 2, t)
    shaft = cyl_z(t, t + 5.0, h - 5.5, 5.5, 2.5, 16)         # output spline, out of the pocket
    return transform(body + ears + shaft, m, origin)


def servos():
    out = []
    pc, ps, pd = SERVO_POCKET
    x0, z0 = SERVO_POCKET_X0, SERVO_POCKET_Z0
    ylo = float(np.min(wing.lower(np.linspace(x0, x0 + pc, 25))))
    floor = ylo + pd
    h, l, t = ES08["body"]
    # Panel frame: height along chord (+x), length along span (+z), thickness down from the pocket floor.
    local = _servo((1, 0, 0), (0, 0, 1), (0, -1, 0), (x0 + 0.5, floor, z0 + (ps - l) / 2))
    y_s2 = CENTER_HALF + PANEL_SPAN
    out.append(Component("Aileron servo R", "Servos", wing.to_assembly(local, y_s2), SERVO, "EMAX ES08MA II"))
    out.append(Component("Aileron servo L", "Servos", wing.to_assembly(local, y_s2).mirror((0, 1, 0)), SERVO,
                         "EMAX ES08MA II"))
    for name, (fx, fz_, side) in (("Elevator servo", tail.ELEV_SERVO_POCKET),
                                  ("Rudder servo", tail.RUDDER_SERVO_POCKET)):
        fl = tail.pocket_floor(fx, fz_, side)
        # Fin frame: height up (+z), length along x, thickness outward from the pocket floor.
        s = _servo((0, 0, 1), (1, 0, 0), (0, side, 0), (fx + (ps - l) / 2, fl, fz_ + 0.5))
        out.append(Component(name, "Servos", s, SERVO, "EMAX ES08MA II"))
    return out


# --- Propulsion ----------------------------------------------------------------

def propulsion():
    face = MOTOR_X + 2.0                                      # outer face of the motor mount flange
    motor = (cyl_x(face, face + 6, 0, MOTOR_Z, 16, 48)       # stator base
             + cyl_x(face + 6, face + 28, 0, MOTOR_Z, 17, 48)  # bell
             + cyl_x(face + 28, face + 40, 0, MOTOR_Z, 2.5, 16))
    hub = cyl_x(face + 30, face + 38, 0, MOTOR_Z, 7, 24) + cyl_x(face + 38, face + 44, 0, MOTOR_Z, 4, 16)
    blade = transform(box(-1.5, 6, -7, 1.5, 89, 7), rot_y(-12))   # pitched about its own axis
    blade = blade.translate((face + 32.5, 0, 0))
    blades = blade + blade.rotate((180, 0, 0))
    prop = transform(blades, rot_x(60)).translate((0, 0, MOTOR_Z)) + hub
    return [Component("Motor", "Propulsion", motor, MOTOR_RED, "28xx outrunner, ~1300 KV"),
            Component("Propeller", "Propulsion", prop, CARBON, "7 x 5 pusher")]


# --- Avionics ------------------------------------------------------------------

def avionics():
    out = []
    z_floor = FLOOR_Z + FLOOR_T
    lx, wy, hz = BATTERY_PACK
    for i in range(2):
        x0 = BATTERY_X0 + i * (lx + 2)
        out.append(Component(f"Battery pack {i + 1}", "Avionics",
                             rounded_bar_x(x0, x0 + lx, -wy / 2, wy / 2, z_floor, z_floor + hz, 9.0), CELLS,
                             "4S3P 18650 Li-ion; two in parallel = 4S6P"))
    top = z_floor + hz
    out.append(Component("VTX", "Avionics", box(106, 4, top, 106 + VTX[0], 4 + VTX[1], top + VTX[2]), PCB,
                         "digital VTX, ~32 x 22 mm"))
    out.append(Component("Receiver", "Avionics",
                         box(146, -20, top, 146 + RECEIVER[0], -20 + RECEIVER[1], top + RECEIVER[2]), PCB,
                         "ELRS receiver"))
    out.append(Component("GPS", "Avionics", box(172, -GPS[1] / 2, top, 172 + GPS[0], GPS[1] / 2, top + GPS[2]),
                         (0.85, 0.85, 0.82), "M10 GPS with compass"))
    out.append(Component("Flight controller", "Avionics",
                         box(242, -FC[1] / 2, z_floor, 242 + FC[0], FC[1] / 2, z_floor + FC[2]), PCB,
                         "F405 wing FC"))
    # ESC on the centreline of the rising motor cone, tilted to follow it, close to the motor.
    zc = lambda x: (lambda w_zb_zt: (w_zb_zt[1] + w_zb_zt[2]) / 2)(fz.section(x))
    pitch = -math.degrees(math.atan((zc(ESC_X + 10) - zc(ESC_X - 10)) / 20))
    esc = transform(box(-ESC[0] / 2, -ESC[1] / 2, -ESC[2] / 2, ESC[0] / 2, ESC[1] / 2, ESC[2] / 2), rot_y(pitch))
    out.append(Component("ESC", "Avionics", esc.translate((ESC_X, 0, zc(ESC_X))), PCB,
                         "30-40 A ESC, in the motor cone"))
    _, zb, zt = fz.section(3.0)
    cz, c = (zb + zt) / 2, CAMERA / 2 - 0.2
    cam = box(6.2, -c, cz - c, 26, c, cz + c) + cyl_x(1.0, 6.2, 0, cz, 7.0, 32)
    out.append(Component("FPV camera", "Avionics", cam, CAMERA_BLACK, f"{CAMERA:.0f} x {CAMERA:.0f} mm"))
    return out


GROUPS = {"Main spar": "Wing", "Rear spar": "Wing", "Aileron": "Wing", "Wing bolt": "Wing",
          "Boom": "Boom", "Stab": "Tail", "Elevator": "Tail", "Rudder": "Tail"}


def components():
    out = carbon() + fasteners() + servos() + propulsion() + avionics()
    for c in out:
        c.group = next((g for k, g in GROUPS.items() if c.name.startswith(k)), "Fuselage")
    return out
