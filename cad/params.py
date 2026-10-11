"""Every dimension of the airframe, in millimetres and degrees.

Assembly frame: +X points aft (nose tip at X=0), +Y along the right wing,
+Z up. The fuselage bottom sits at Z=0.
"""

# --- Printer -----------------------------------------------------------------
BED = 180.0          # Bambu Lab A1 mini: 180 x 180 x 180
BED_MARGIN = 2.0     # keep parts this far inside every bed edge

# --- Wing ----------------------------------------------------------------------
WING_AIRFOIL = "sd7037"   # cad/data/<name>.dat; see AERODYNAMICS.md for why not E193
CHORD = 200.0
WING_LE_X = 200.0
WING_LE_Z = 140.0
INCIDENCE = 1.5      # wing incidence relative to the boom / tail
SKIN = 0.8           # wing skin = 2 perimeters of a 0.4 nozzle
WEB = 0.8            # internal span-wise webs
TE_THICK = 0.6       # minimum printable trailing edge
LE_WEB_X = 16.0
SPAR_X, SPAR_D = 50.0, 10.0              # main spar, carbon tube
REAR_SPAR_X, REAR_SPAR_D = 110.0, 6.0    # rear spar, carbon tube
SLEEVE_WALL = 1.0
TUBE_FIT = 0.1       # radial clearance around carbon tubes / rods

CENTER_HALF = 80.0   # centre section spans Y = -80..80
PANEL_SPAN = 160.0   # S1, S2, S3 each 160 mm
TIP_Y0 = CENTER_HALF + 3 * PANEL_SPAN    # 560
TIP_REACH = 85.0     # horizontal reach of the tip -> 1290 mm span
TIP_PHI_MAX = 45.0   # upsweep at the very tip (45 deg keeps it printable)
TIP_END_CHORD = 70.0
TIP_LE_SWEEP = 22.0

HINGE_X = 150.0      # aileron hinge line, 75 % chord
SURFACE_GAP = 1.0    # gap between any fixed surface and its control surface
BEVEL_DEG = 30.0     # control-surface V bevel -> +/-30 deg throw
AILERON_JOINER_D = 3.0
AILERON_JOINER_X = HINGE_X + 8.0

SERVO_POCKET = (25.0, 33.0, 12.5)   # chord, span, depth: EMAX ES08MA II lying flat
SERVO_POCKET_X0 = 79.0
SERVO_POCKET_Z0 = 25.0              # from the root end of S2

BOLT_X = (30.0, 135.0)   # wing-to-fuselage M3 bolts, chord stations on Y=0
BOLT_D = 3.4
BOLT_HEAD_D = 6.0
INSERT_D = 4.1           # M3 heat-set insert
INSERT_DEPTH = 7.0

# --- Fuselage ------------------------------------------------------------------
WALL = 1.2               # fuselage shell = 3 perimeters
SUPER_N = 2.5            # superellipse exponent of the cross sections
MOTOR_Z = 120.0
MOTOR_X = 445.0          # rear face of the fuselage cone = motor mount seat
# Control stations: x, width, z_bottom, z_top. Between the wing LE and TE the
# top follows the wing camber line instead (the wing sits in a saddle).
# The nose tip sits low; the top line is a convex arc that levels off into the
# wing LE: z = 44 + 96 * (1 - (1 - x/200)^2)^0.55.
POD_X = [0, 3, 10, 25, 45, 70, 100, 150, 180, 200, 400, 420, MOTOR_X]
POD_W = [6, 34, 56, 80, 94, 104, 110, 110, 110, 108, 44, 39, 36]
POD_ZB = [34, 22, 12, 5, 2, 0.5, 0, 0, 0, 0, 82, 96, MOTOR_Z - 18]
POD_ZT = [44, 57.9, 70.7, 87.2, 101.9, 115.0, 126.0, 136.7, 139.5, None, None, 136.5, MOTOR_Z + 18]
# Width/bottom between the LE and TE (top comes from the wing).
POD_MID_X = [250, 290, 330, 365]
POD_MID_W = [100, 86, 68, 54]
POD_MID_ZB = [2, 10, 30, 58]

FUSE_CUTS = [85.0, 250.0, 415.0]   # nose | front | rear | tail cone
LIP = 10.0                         # glue sleeve length at each cut
LIP_FIT = 0.15

HATCH_X = (100.0, 198.0)
HATCH_Z = 85.0
FLOOR_Z = 14.0
FLOOR_T = 1.6
SADDLE_T = 3.0
SADDLE_WINDOW_X = (245.0, 322.0)
SADDLE_WINDOW_HALF_Y = 35.0
CAMERA = 19.0            # 19 x 19 mm FPV camera
CAMERA_LENS_D = 15.0

# --- Boom & tail ---------------------------------------------------------------
BOOM_D = 12.0
BOOM_Z = 14.0
BOOM_X0 = 300.0          # front end of the boom (inside the fuselage socket)
BOOM_X1 = 790.0          # rear end (inside the tail hub)
SOCKET_END_X = 460.0

TAIL_TE_X = 865.0        # -> 865 mm overall length
HUB_X0 = 680.0
HUB_HALF_W = 10.2
HUB_Z0 = 4.0
HUB_Z1 = 36.0

STAB_Z = 28.0
STAB_ROOT_CHORD = 140.0
STAB_TIP_CHORD = 115.0
STAB_TIP_Y = 188.0
STAB_THICK = 0.09
STAB_INCIDENCE = -1.0   # elevator sits neutral at cruise with the CG at 66 mm
STAB_SPAR_X, STAB_SPAR_D, STAB_SPAR_DEPTH = 760.0, 6.0, 55.0
STAB_PIN_X, STAB_PIN_D, STAB_PIN_DEPTH = 800.0, 3.0, 30.0
ELEV_HINGE_X = 825.0
ELEV_JOINER_X = ELEV_HINGE_X + 6.0
ELEV_JOINER_D = 2.0
ELEV_JOINER_DEPTH = 40.0

FIN_ROOT_Z = 30.0
FIN_TOP_Z = 164.0
FIN_ROOT_LE = 700.0
FIN_TIP_LE = 750.0
FIN_THICK = 0.12
RUDDER_HINGE_X = 815.0
RUDDER_Z0 = HUB_Z1
