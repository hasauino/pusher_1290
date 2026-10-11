"""AeroSandbox model of the airframe, built from the same parameters as the CAD.

Every geometric number comes from cad/params.py (and the fuselage section
function in cad/fuselage.py), so the analysis always matches the printed parts.
Units here are SI (metres), the CAD is in millimetres.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

import aerosandbox as asb
import aerosandbox.numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cad"))

import fuselage as fz  # noqa: E402
import params as P  # noqa: E402
import tail  # noqa: E402
import wing as wg  # noqa: E402

MM = 1e-3
DATA = Path(P.__file__).parent / "data"
E193 = asb.Airfoil("e193", coordinates=str(DATA / "e193.dat"))           # original choice
WING_AIRFOIL = asb.Airfoil(P.WING_AIRFOIL, coordinates=str(DATA / f"{P.WING_AIRFOIL}.dat"))


@dataclass
class Flight:
    mass: float = 2.3                  # kg, all-up with a 4S6P Li-ion pack
    cg_from_le: float = 66.0           # mm behind the wing LE (root)
    prop_efficiency: float = 0.55      # motor x ESC x prop, cruise
    battery_wh: float = 4 * 3.6 * 21.0 * 0.85   # 4S6P Li-ion, 85 % usable

    @property
    def x_cg(self):
        return (P.WING_LE_X + self.cg_from_le) * MM


def wing_planform(chord=None, taper_from=None, tip_panel_chord=None):
    """(y, x_le, z_le, chord) stations of the right wing in mm, root to tip.

    Defaults reproduce the CAD. For trade studies: a different constant chord, or
    a linear taper from span station `taper_from` down to `tip_panel_chord` at the
    tip joint. The quarter-chord line (main spar) stays straight.
    """
    c0 = chord or P.CHORD
    c1 = tip_panel_chord or c0
    st = [(0.0, 0.25 * (P.CHORD - c0), 0.0, c0)]
    if taper_from:
        st.append((taper_from, 0.25 * (P.CHORD - c0), 0.0, c0))
    st.append((P.TIP_Y0, 0.25 * (P.CHORD - c1), 0.0, c1))
    k = c1 / P.CHORD
    return st + [(y, 0.25 * (P.CHORD - c1) + x * k, z, c * k) for y, z, x, c in wg.tip_stations()]


def make_airplane(airfoil=WING_AIRFOIL, incidence=None, stab_incidence=None, planform=None):
    incidence = P.INCIDENCE if incidence is None else incidence
    stab_incidence = getattr(P, "STAB_INCIDENCE", 0.0) if stab_incidence is None else stab_incidence
    planform = planform or wing_planform()

    xsecs = []
    for y, x, z, c in planform:
        xsecs.append(asb.WingXSec(
            xyz_le=[(P.WING_LE_X + x) * MM, y * MM, (P.WING_LE_Z + z) * MM],
            chord=c * MM, twist=incidence,
            airfoil=airfoil))
    main_wing = asb.Wing(name="Wing", symmetric=True, xsecs=xsecs)

    naca9, naca12 = asb.Airfoil("naca0009"), asb.Airfoil("naca0012")
    stab = asb.Wing(name="H-stab", symmetric=True, xsecs=[
        asb.WingXSec(xyz_le=[tail.stab_le(y) * MM, y * MM, P.STAB_Z * MM],
                     chord=(P.TAIL_TE_X - tail.stab_le(y)) * MM, twist=stab_incidence, airfoil=naca9)
        for y in (0.0, P.HUB_HALF_W, P.STAB_TIP_Y)])
    fin = asb.Wing(name="V-stab", xsecs=[
        asb.WingXSec(xyz_le=[tail.fin_le(z) * MM, 0, z * MM],
                     chord=(P.TAIL_TE_X - tail.fin_le(z)) * MM, airfoil=naca12)
        for z in (P.HUB_Z1, P.FIN_TOP_Z)])

    pod = asb.Fuselage(name="Pod", xsecs=[
        asb.FuselageXSec(xyz_c=[x * MM, 0, (zb + zt) / 2 * MM], width=w * MM, height=(zt - zb) * MM,
                         shape=P.SUPER_N)
        for x in np.linspace(0, P.MOTOR_X, 60) for w, zb, zt in [fz.section(float(x))]]
        + [asb.FuselageXSec(xyz_c=[(P.MOTOR_X + 30) * MM, 0, P.MOTOR_Z * MM], radius=17 * MM),
           asb.FuselageXSec(xyz_c=[(P.MOTOR_X + 34) * MM, 0, P.MOTOR_Z * MM], radius=8 * MM)])

    socket = [(x, w, zb, zt) for x, w, zb, zt in fz.SOCKET if x >= 300]
    boom_xs = [asb.FuselageXSec(xyz_c=[x * MM, 0, (zb + zt) / 2 * MM], width=w * MM,
                                height=(zt - zb) * MM, shape=2.2) for x, w, zb, zt in socket]
    boom_xs += [asb.FuselageXSec(xyz_c=[x * MM, 0, P.BOOM_Z * MM], radius=P.BOOM_D / 2 * MM)
                for x in (P.SOCKET_END_X + 5, P.HUB_X0 - 5)]
    boom_xs += [asb.FuselageXSec(xyz_c=[x * MM, 0, (P.HUB_Z0 + P.HUB_Z1) / 2 * MM],
                                 width=2 * P.HUB_HALF_W * MM, height=h * MM, shape=4)
                for x, h in ((P.HUB_X0 + 16, 32), (P.TAIL_TE_X - 23, 32), (P.TAIL_TE_X, 9))]
    boom = asb.Fuselage(name="Boom + tail hub", xsecs=boom_xs)

    return asb.Airplane(name="Lark-style", wings=[main_wing, stab, fin], fuselages=[pod, boom],
                        s_ref=main_wing.area(), c_ref=main_wing.mean_aerodynamic_chord(),
                        b_ref=main_wing.span())
