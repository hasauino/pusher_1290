"""Bought parts placed in the aircraft frame: carbon, fasteners, servos,
propulsion and avionics. Simplified shapes, but at true size, mass and
position, so the full assembly can be checked for collisions and balance.

Every part is a common one you can order on Amazon; `spec` is the search
name. Sizes and masses come from the makers' and retailers' listings. If you
buy something different, change its entry here and rebuild to re-check fit and CG.
"""
import math
from dataclasses import dataclass

import numpy as np

import fuselage as fz
import tail
import wing
from geom import Manifold, box, cyl_x, cyl_y, cyl_z, extrude, path, rect, rot_x, rot_y, segment, transform, union
from params import *

CARBON, STEEL, BRASS = (0.10, 0.10, 0.11), (0.62, 0.63, 0.66), (0.80, 0.62, 0.25)
SERVO, PCB, CELLS = (0.12, 0.12, 0.14), (0.10, 0.36, 0.20), (0.18, 0.42, 0.72)
MOTOR_RED, CAMERA_BLACK = (0.70, 0.13, 0.12), (0.08, 0.08, 0.09)

M3_LENGTHS = (6, 8, 10, 12, 14, 16, 20, 25)
CARBON_DENSITY, STEEL_DENSITY = 1.55, 7.85     # g/cm3
# MG90S (metal-gear SG90): case height/length/thickness, ear span and position,
# gear dome and spline heights, spline centre from the case end. Mass 13.4 g.
MG90S = dict(case=(22.7, 22.8, 12.2), ears=32.5, ear_at=18.5, ear_w=2.5, dome=28.4, spline=32.1, spline_c=5.9)
BATTERY = (140.0, 48.0, 48.0)        # 4S 5200 mAh LiPo, x, y, z (Zeee / Powerhobby size)
BATTERY_X0 = 49.0                    # as far forward as the camera-cage ribs allow; slides in with the nose off
FC = (52.0, 32.0, 19.0)              # SpeedyBee F405 WING APP
ESC = (60.0, 25.0, 8.0)              # Hobbywing Skywalker V2 40A
NOSE_WEIGHT_G = 92.0                 # lead in the nose to put the PLA build on the CG target (cad/assembly.py)
LEAD_DENSITY = 11.3
VTX, RECEIVER, GPS = (36.0, 36.0, 9.0), (22.0, 14.0, 6.0), (28.0, 28.0, 10.0)
WIRING = (45.0, (300.0, 0.0, 40.0))  # g and position of leads, connectors, servo extensions
FC_X0 = 240.0                        # front edge of the flight controller, on the floor behind the battery


@dataclass
class Component:
    name: str
    category: str      # Carbon, Fasteners, Servos, Propulsion, Avionics
    shape: Manifold
    color: tuple
    spec: str = ""
    mass: float = 0.0         # g
    group: str = "Fuselage"   # assembly it belongs to: Wing, Fuselage, Boom, Tail


def tube_mass(od, length, wall=1.0, density=CARBON_DENSITY):
    """Grams of a carbon tube (wall > od/2 means a solid rod)."""
    idia = max(od - 2 * wall, 0.0)
    return math.pi / 4 * (od**2 - idia**2) * length * density / 1000


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
                         f"carbon tube {SPAR_D:.0f} x 8 mm, {2 * main_half:.0f} mm", tube_mass(SPAR_D, 2 * main_half)))
    for side, (a, b) in (("R", (0.0, rear_end)), ("L", (-rear_end, 0.0))):
        out.append(Component(f"Rear spar {side}", "Carbon", span(a, b, REAR_SPAR_X, REAR_SPAR_D), CARBON,
                             f"carbon tube {REAR_SPAR_D:.0f} x 4 mm, cut to {rear_end:.0f} mm",
                             tube_mass(REAR_SPAR_D, rear_end)))
    joint = CENTER_HALF + 2 * PANEL_SPAN          # S2/S3 joint, middle of the aileron pair
    for side, sign in (("R", 1), ("L", -1)):
        a, b = sorted((sign * (joint - 40), sign * (joint + 40)))
        out.append(Component(f"Aileron joiner {side}", "Carbon",
                             span(a, b, AILERON_JOINER_X, AILERON_JOINER_D), CARBON,
                             f"carbon rod {AILERON_JOINER_D:.0f} mm, cut to 80 mm",
                             tube_mass(AILERON_JOINER_D, 80, wall=9)))
    out.append(Component("Boom", "Carbon", cyl_x(BOOM_X0, BOOM_X1, 0, BOOM_Z, BOOM_D / 2, 40), CARBON,
                         f"carbon tube {BOOM_D:.0f} x 10 mm, cut to {BOOM_X1 - BOOM_X0:.0f} mm",
                         tube_mass(BOOM_D, BOOM_X1 - BOOM_X0)))
    stab_half = HUB_HALF_W + STAB_SPAR_DEPTH - 0.2
    out.append(Component("Stab spar", "Carbon", cyl_y(-stab_half, stab_half, STAB_SPAR_X, STAB_Z, STAB_SPAR_D / 2, 32),
                         CARBON, f"carbon tube {STAB_SPAR_D:.0f} x 4 mm, cut to {2 * stab_half:.0f} mm",
                         tube_mass(STAB_SPAR_D, 2 * stab_half)))
    pin_half = HUB_HALF_W + STAB_PIN_DEPTH - 0.2
    out.append(Component("Stab pin", "Carbon",
                         tail.stab_pitch(cyl_y(-pin_half, pin_half, STAB_PIN_X, STAB_Z, STAB_PIN_D / 2, 24)),
                         CARBON, f"carbon rod {STAB_PIN_D:.0f} mm, cut to {2 * pin_half:.0f} mm",
                         tube_mass(STAB_PIN_D, 2 * pin_half, wall=9)))
    joiner_half = HUB_HALF_W + ELEV_JOINER_DEPTH - 0.2
    out.append(Component("Elevator joiner", "Carbon",
                         tail.stab_pitch(cyl_y(-joiner_half, joiner_half, ELEV_JOINER_X, STAB_Z, ELEV_JOINER_D / 2, 16)),
                         STEEL, f"piano wire {ELEV_JOINER_D:.0f} mm, cut to {2 * joiner_half:.0f} mm",
                         tube_mass(ELEV_JOINER_D, 2 * joiner_half, wall=9, density=STEEL_DENSITY)))
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
                             f"M3 x {L} socket head screw", 1.5))
        out.append(Component(f"Heat-set insert {label}", "Fasteners", wing.center_frame(insert), BRASS,
                             "M3 x 5.7 brass heat-set insert", 0.5))
    plate_in = MOTOR_X - 8.0
    L = m3_length(10.0 + 4.5)              # mount plate + flange, ~4 mm into the motor
    for dy, dz in MOTOR_HOLES:
        screw = (cyl_x(plate_in - 3.0, plate_in, dy, MOTOR_Z + dz, 2.75, 20)
                 + cyl_x(plate_in, plate_in + L, dy, MOTOR_Z + dz, 1.5, 12))
        out.append(Component(f"Motor screw {dy:+.1f}/{dz:+.1f}", "Fasteners", screw, STEEL,
                             f"M3 x {L} socket head screw", 1.0))
    return out


# --- Servos --------------------------------------------------------------------

def _servo(height_axis, length_axis, thick_axis, origin):
    """MG90S lying flat, built along the given unit axes from `origin` (case
    corner at height 0, length 0, thickness 0). The spline points along the
    height axis; the horn arm points along the thickness axis, out of the pocket."""
    h, l, t = MG90S["case"]
    ear, ew, ea = MG90S["ears"], MG90S["ear_w"], MG90S["ear_at"]
    c = MG90S["spline_c"]
    m = np.column_stack([height_axis, length_axis, thick_axis])
    case = box(0, 0, 0, h, l, t)
    ears = box(ea, -(ear - l) / 2, 0, ea + ew, l + (ear - l) / 2, t)
    dome = transform(Manifold.cylinder(MG90S["dome"] - h, t / 2, circular_segments=24), rot_y(90), (h, c, t / 2))
    spline = transform(Manifold.cylinder(MG90S["spline"] - MG90S["dome"], 2.4, circular_segments=16), rot_y(90),
                       (MG90S["dome"], c, t / 2))
    horn = box(MG90S["spline"], c - 2.5, t / 2 - 3, MG90S["spline"] + 1.6, c + 2.5, t + 10)
    return transform(case + ears + dome + spline + horn, m, origin)


def servos():
    out = []
    pc, ps, pd = SERVO_POCKET
    x0, z0 = SERVO_POCKET_X0, SERVO_POCKET_Z0
    ylo = float(np.min(wing.lower(np.linspace(x0, x0 + pc, 25))))
    floor = ylo + pd
    h, l, t = MG90S["case"]
    spec = "MG90S metal-gear 9 g micro servo"
    # Panel frame: height along chord (+x, spline aft), length along span (+z), thickness down to the opening.
    local = _servo((1, 0, 0), (0, 0, 1), (0, -1, 0), (x0 + 0.5, floor, z0 + (ps - l) / 2))
    y_s2 = CENTER_HALF + PANEL_SPAN
    out.append(Component("Aileron servo R", "Servos", wing.to_assembly(local, y_s2), SERVO, spec, 13.4))
    out.append(Component("Aileron servo L", "Servos", wing.to_assembly(local, y_s2).mirror((0, 1, 0)), SERVO,
                         spec, 13.4))
    for name, side in (("Elevator servo", -1), ("Rudder servo", 1)):
        # In the pod: upright between the floor rails, spline at the back, horn pointing outward.
        s_ = _servo((0, 0, 1), (-1, 0, 0), (0, side, 0), (TAIL_SERVO_X0 + l, side * 4.0, FLOOR_Z + FLOOR_T))
        out.append(Component(name, "Servos", s_, SERVO, spec, 13.4))
    return out


def tail_horn_tip(side):
    """Where a pod servo's horn arm ends (the pushrod's front end)."""
    h, l, t = MG90S["case"]
    return np.array([TAIL_SERVO_X0 + l - MG90S["spline_c"], side * (4.0 + t + 10.0),
                     FLOOR_Z + FLOOR_T + MG90S["spline"] + 0.8])


# --- Linkages --------------------------------------------------------------------

NYLON = (0.92, 0.92, 0.88)
PUSHROD_G_PER_MM, BOWDEN_G_PER_MM = 0.0062, 0.0026     # 1 mm steel, 2 mm PTFE tube


def linkages():
    """Bowden cables from the pod servos through the boom, pushrods and horns."""
    out = []
    for name, side, (start, exit_), horn, horn_hole in (
            ("Elevator", -1, tail.ELEV_BOWDEN, _elevator_horn(), np.array([838.0, -24.0, 16.0])),
            ("Rudder", 1, tail.RUDDER_BOWDEN, _rudder_horn(), np.array([838.0, 13.0, 45.0]))):
        tip = tail_horn_tip(side)
        route = [tip + np.array([12.0, -side * 4, -2]), np.array([285.0, side * 6, 44.0]),
                 np.array([303.5, side * 1.5, 36.0]), np.array([305.0, side * 1.5, 20.0]),
                 np.array([312.0, side * 2.5, BOOM_Z]), np.array(start), np.array(exit_)]
        length = sum(np.linalg.norm(b - a) for a, b in zip(route, route[1:]))
        out.append(Component(f"{name} Bowden cable", "Linkages", path(route, BOWDEN_D / 2, 12), NYLON,
                             f"2 mm Bowden tube with 1 mm steel pushrod, {length + 60:.0f} mm",
                             length * (BOWDEN_G_PER_MM + PUSHROD_G_PER_MM)))
        rods = segment(tip, route[0], 0.5, 8) + segment(np.array(exit_), horn_hole, 0.5, 8)
        out.append(Component(f"{name} pushrod ends", "Linkages", rods, STEEL, "1 mm steel, Z-bend at the horn", 0.5))
        out.append(Component(f"{name} horn", "Linkages", horn, NYLON, "nylon control horn", 1.0))
    for side, sign in (("R", 1), ("L", -1)):
        horn, rod = _aileron_linkage()
        place = (lambda m: wing.to_assembly(m, CENTER_HALF + PANEL_SPAN)) if sign > 0 else \
                (lambda m: wing.to_assembly(m, CENTER_HALF + PANEL_SPAN).mirror((0, 1, 0)))
        out.append(Component(f"Aileron horn {side}", "Linkages", place(horn), NYLON, "nylon control horn", 1.0))
        out.append(Component(f"Aileron pushrod {side}", "Linkages", place(rod), STEEL,
                             "1.2 mm steel pushrod, Z-bend + clevis", 1.0))
    return out


def _stab_lower(x, y):
    """Z of the (left) stab/elevator lower surface, stab incidence included."""
    le = tail.stab_le(y)
    ht = float(tail.STAB.half_thickness(x - le, TAIL_TE_X - le, TE_THICK))
    return STAB_Z + (x - STAB_SPAR_X) * math.sin(math.radians(-STAB_INCIDENCE)) - ht


def _elevator_horn():
    top = min(_stab_lower(x, -24.0) for x in np.linspace(833, 843, 11)) - 0.05
    return box(833, -25, 12.5, 843, -23, top)


def _rudder_horn():
    y0 = max(tail.fin_half_thickness(x, z) for x in np.linspace(830, 840, 11) for z in (44, 46)) + 0.05
    return box(830, y0, 44, 840, 16, 46)


def _aileron_linkage():
    """Horn under the aileron and pushrod to the servo horn, in the S2 panel frame."""
    h, l, t = MG90S["case"]
    pc, ps, pd = SERVO_POCKET
    ylo = float(np.min(wing.lower(np.linspace(SERVO_POCKET_X0, SERVO_POCKET_X0 + pc, 25))))
    zs = SERVO_POCKET_Z0 + (ps - l) / 2 + MG90S["spline_c"]
    tip = np.array([SERVO_POCKET_X0 + 0.5 + MG90S["spline"] + 0.8, ylo + pd - t - 10.0, zs])
    top = float(np.min(wing.lower(np.linspace(165, 175, 11)))) - 0.05
    horn = box(165, top - 13, zs - 1, 175, top, zs + 1)
    rod = segment(tip, np.array([170.0, top - 10, zs]), 0.6, 8)
    return horn, rod


# --- Propulsion ----------------------------------------------------------------

def propulsion():
    face = MOTOR_X + 2.0                                      # outer face of the motor mount flange
    motor = (cyl_x(face, face + 5, 0, MOTOR_Z, 15, 48)        # base
             + cyl_x(face + 5, face + 30, 0, MOTOR_Z, 17.4, 48)  # bell, 34.8 mm
             + cyl_x(face + 30, face + 44, 0, MOTOR_Z, 2.5, 16))  # M5 prop shaft
    hub = cyl_x(face + 31, face + 38, 0, MOTOR_Z, 7, 24) + cyl_x(face + 38, face + 44, 0, MOTOR_Z, 4, 16)
    blade = transform(box(-1.5, 6, -7, 1.5, 89, 7), rot_y(-12))   # pitched about its own axis
    blade = blade.translate((face + 34.5, 0, 0))
    blades = blade + blade.rotate((180, 0, 0))
    prop = transform(blades, rot_x(60)).translate((0, 0, MOTOR_Z)) + hub
    return [Component("Motor", "Propulsion", motor, MOTOR_RED, "EMAX ECO II 2807 1300KV (19 x 19 mm M3)", 47.0),
            Component("Propeller", "Propulsion", prop, CARBON, "7 inch FPV prop, reverse (CCW) rotation", 9.0)]


# --- Avionics ------------------------------------------------------------------

def avionics():
    out = []
    z_floor = FLOOR_Z + FLOOR_T
    lx, wy, hz = BATTERY
    out.append(Component("Battery", "Avionics",
                         rounded_bar_x(BATTERY_X0, BATTERY_X0 + lx, -wy / 2, wy / 2, z_floor, z_floor + hz, 4.0),
                         CELLS, "4S 5200 mAh LiPo, XT60 (up to 140 x 48 x 48 mm)", 480.0))
    top = z_floor + hz
    out.append(Component("VTX", "Avionics", box(60, -VTX[1] / 2, top, 60 + VTX[0], VTX[1] / 2, top + VTX[2]),
                         PCB, "5.8 GHz VTX, 30.5 mm mounting", 10.0))
    out.append(Component("Receiver", "Avionics",
                         box(100, -RECEIVER[1] / 2, top, 100 + RECEIVER[0], RECEIVER[1] / 2, top + RECEIVER[2]),
                         PCB, "RadioMaster RP1 ELRS 2.4 GHz receiver", 2.0))
    out.append(Component("GPS", "Avionics", box(150, -GPS[1] / 2, top, 150 + GPS[0], GPS[1] / 2, top + GPS[2]),
                         (0.85, 0.85, 0.82), "Beitian BN-880 GPS with compass", 10.0))
    out.append(Component("Flight controller", "Avionics",
                         box(FC_X0, -FC[1] / 2, z_floor, FC_X0 + FC[0], FC[1] / 2, z_floor + FC[2]), PCB,
                         "SpeedyBee F405 WING APP", 35.0))
    # ESC on top of the flight controller, as far forward as it goes: it helps the balance.
    fc_top = z_floor + FC[2] + 0.5
    out.append(Component("ESC", "Avionics", box(FC_X0, -ESC[1] / 2, fc_top, FC_X0 + ESC[0], ESC[1] / 2, fc_top + ESC[2]),
                         PCB, "Hobbywing Skywalker V2 40A ESC (5 A BEC)", 36.0))
    if NOSE_WEIGHT_G > 0:
        out.append(Component("Nose weight", "Ballast", nose_weight(NOSE_WEIGHT_G), (0.45, 0.47, 0.5),
                             f"{NOSE_WEIGHT_G:.0f} g adhesive lead wheel weights", NOSE_WEIGHT_G))
    _, zb, zt = fz.section(3.0)
    cz, c = (zb + zt) / 2, CAMERA / 2 - 0.2
    cam = box(6.2, -c, cz - c, 26, c, cz + c) + cyl_x(1.0, 6.2, 0, cz, 7.0, 32)
    out.append(Component("FPV camera", "Avionics", cam, CAMERA_BLACK, "Caddx Ratel 2 (19 mm)", 6.0))
    return out


NOSE_WEIGHT_X = (24.0, 44.0)         # between the camera cage and the battery


def nose_weight(grams):
    """Two lead blocks low in the nose, either side of the cage's vertical rib;
    their height grows with the mass."""
    x0, x1 = NOSE_WEIGHT_X
    height = grams / LEAD_DENSITY * 1000 / 2 / ((x1 - x0) * 14.0)
    return union([box(x0, y0, 11.0, x1, y0 + 14.0, 11.0 + height) for y0 in (1.0, -15.0)])


GROUPS = {"Main spar": "Wing", "Rear spar": "Wing", "Aileron": "Wing", "Wing bolt": "Wing",
          "Boom": "Boom", "Elevator Bowden": "Boom", "Rudder Bowden": "Boom",
          "Elevator servo": "Fuselage", "Rudder servo": "Fuselage",
          "Stab": "Tail", "Elevator": "Tail", "Rudder": "Tail"}


def components():
    out = carbon() + fasteners() + servos() + linkages() + propulsion() + avionics()
    for c in out:
        c.group = next((g for k, g in GROUPS.items() if c.name.startswith(k)), "Fuselage")
    return out
