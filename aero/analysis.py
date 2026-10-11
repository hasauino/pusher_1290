"""Trimmed level-flight performance, drag breakdown and stability for an airplane."""
from dataclasses import dataclass

import aerosandbox as asb
import numpy as np

G = 9.81
Z_CG = 0.06        # m, battery sits low on the floor
AVIONICS_W = 4.0   # FC, GPS, receiver, VTX, camera


@dataclass
class Point:
    V: float
    alpha: float
    CL: float
    CD: float
    LD: float
    D: float
    P_elec: float
    Cm: float
    parts: dict          # component name -> drag [N]
    D_induced: float


def _run(ap, flight, V, alpha):
    op = asb.OperatingPoint(velocity=V, alpha=alpha)
    return asb.AeroBuildup(ap, op, xyz_ref=[flight.x_cg, 0, Z_CG]).run()


def level_flight(ap, flight, V):
    """Find the angle of attack where lift equals weight at speed V."""
    alphas = np.linspace(-5, 14, 96)
    lift = np.asarray(_run(ap, flight, V, alphas)["L"]).ravel()
    W = flight.mass * G
    if not lift.min() < W < lift.max():
        return None
    a = float(np.interp(W, lift, alphas))
    r = _run(ap, flight, V, a)
    names = [w.name for w in ap.wings] + [f.name for f in ap.fuselages]
    comps = r["wing_aero_components"] + r["fuselage_aero_components"]
    parts = {n: float(np.ravel(c.D)[0]) for n, c in zip(names, comps)}
    D = float(np.ravel(r["D"])[0])
    return Point(V=V, alpha=a, CL=float(np.ravel(r["CL"])[0]), CD=float(np.ravel(r["CD"])[0]),
                 LD=W / D, D=D, P_elec=D * V / flight.prop_efficiency + AVIONICS_W,
                 Cm=float(np.ravel(r["Cm"])[0]), parts=parts,
                 D_induced=float(np.ravel(r["D_induced"])[0]))


def min_level_speed(ap, flight, lo=7.0, hi=14.0, step=0.1):
    """Slowest speed at which the model can still make lift equal to weight."""
    for V in np.arange(lo, hi, step):
        if level_flight(ap, flight, float(V)):
            return float(V)
    return float("nan")


def performance(ap, flight, speeds=np.arange(10, 25.01, 0.5)):
    pts = [p for p in (level_flight(ap, flight, float(V)) for V in speeds) if p]
    best_ld = max(pts, key=lambda p: p.LD)
    min_power = min(pts, key=lambda p: p.P_elec)
    return pts, best_ld, min_power


def _vlm(ap, flight, V, alpha):
    """Lifting surfaces only. 6 spanwise panels per section: the upswept tip makes
    AeroSandbox's VLM singular at finer resolutions (checked: 4 and 6 agree)."""
    wings = asb.Airplane(wings=ap.wings, s_ref=ap.s_ref, c_ref=ap.c_ref, b_ref=ap.b_ref)
    r = asb.VortexLatticeMethod(wings, asb.OperatingPoint(velocity=V, alpha=alpha),
                                xyz_ref=[flight.x_cg, 0, Z_CG],
                                spanwise_resolution=6, chordwise_resolution=6).run()
    return {k: float(np.ravel(r[k])[0]) for k in ("CL", "CD", "Cm")}


def _body_cm(ap, flight, V, alpha):
    op = asb.OperatingPoint(velocity=V, alpha=alpha)
    r = asb.AeroBuildup(ap, op, xyz_ref=[flight.x_cg, 0, Z_CG]).run()
    m = sum(float(np.ravel(c.M_b[1])[0]) for c in r["fuselage_aero_components"])
    return m / (op.dynamic_pressure() * ap.s_ref * ap.c_ref)


def stability(ap, flight, V=15.0):
    """Neutral point from the VLM (it models the wing's downwash on the tail,
    which AeroBuildup does not) plus the pod's destabilising moment."""
    a0, a1 = 0.0, 4.0
    w0, w1 = _vlm(ap, flight, V, a0), _vlm(ap, flight, V, a1)
    dCL = w1["CL"] - w0["CL"]
    dCm = (w1["Cm"] - w0["Cm"]) + (_body_cm(ap, flight, V, a1) - _body_cm(ap, flight, V, a0))
    CLa = dCL / np.radians(a1 - a0)
    assert 3.0 < CLa < 7.0, f"VLM lift slope {CLa:.2f}/rad is not plausible"
    x_np = flight.x_cg - dCm / dCL * ap.c_ref
    np_from_le = x_np * 1000 - 200.0
    cg_for = lambda sm: np_from_le - sm * ap.c_ref * 1000
    return {"np_mm": np_from_le, "static_margin": (x_np - flight.x_cg) / ap.c_ref, "CLa": CLa,
            "cg_range_mm": (cg_for(0.18), cg_for(0.08))}


def cm_trim(ap, flight, V, alpha):
    """Pitching moment about the CG with the elevator neutral (VLM wings + bodies)."""
    return _vlm(ap, flight, V, alpha)["Cm"] + _body_cm(ap, flight, V, alpha)


def span_efficiency(ap, V=15.0, alpha=3.0):
    """Inviscid span efficiency of the main wing alone (relative comparisons only:
    the upswept tips push the planar-wing value above 1)."""
    wing_only = asb.Airplane(wings=[ap.wings[0]], s_ref=ap.s_ref, c_ref=ap.c_ref, b_ref=ap.b_ref)
    r = asb.VortexLatticeMethod(wing_only, asb.OperatingPoint(velocity=V, alpha=alpha),
                                spanwise_resolution=6, chordwise_resolution=6).run()
    CL, CDi = float(np.ravel(r["CL"])[0]), float(np.ravel(r["CD"])[0])
    return CL**2 / (np.pi * ap.wings[0].aspect_ratio() * CDi)
