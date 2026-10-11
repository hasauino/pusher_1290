"""Aerodynamic analysis: the original design vs the current CAD, plus trade studies.

    .venv/bin/python aero/report.py     ->  AERODYNAMICS.md, aero/figures/*.png

"Before" is the first version of this design (E193 wing, stab at 0 deg, CG at
62 mm). "After" is whatever cad/params.py says now.
"""
import sys
from pathlib import Path

import aerosandbox as asb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import analysis as A  # noqa: E402
import model  # noqa: E402
from model import P  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIG = Path(__file__).parent / "figures"
SPEEDS = np.arange(10, 22.01, 0.5)
NU = 1.5e-5

# Reference palette (light): categorical slots in fixed order, ink and grid tokens.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
AFTER_C, BEFORE_C, CONTEXT_C = SERIES[0], SERIES[1], "#a9a8a2"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "legend.frameon": False})


def evaluate(name, airplane_kw, flight):
    ap = model.make_airplane(**airplane_kw)
    pts, best, minp = A.performance(ap, flight, SPEEDS)
    stab = A.stability(ap, flight)
    return dict(name=name, ap=ap, flight=flight, pts=pts, best=best, minp=minp, stab=stab,
                cm=A.cm_trim(ap, flight, best.V, best.alpha),
                hours=flight.battery_wh / minp.P_elec)


def plot_performance(before, after):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    for r, c in ((before, BEFORE_C), (after, AFTER_C)):
        V = [p.V for p in r["pts"]]
        ax1.plot(V, [p.LD for p in r["pts"]], color=c, lw=1.6, label=r["name"])
        ax2.plot(V, [p.P_elec for p in r["pts"]], color=c, lw=1.6, label=r["name"])
        b, m = r["best"], r["minp"]
        ax1.plot(b.V, b.LD, "o", color=c, ms=7, mec=SURFACE, mew=1.5)
        ax1.annotate(f"{b.LD:.1f}", (b.V, b.LD), textcoords="offset points", xytext=(6, 4), color=INK2)
        ax2.plot(m.V, m.P_elec, "o", color=c, ms=7, mec=SURFACE, mew=1.5)
        ax2.annotate(f"{m.P_elec:.0f} W", (m.V, m.P_elec), textcoords="offset points", xytext=(4, -14),
                     color=INK2)
    ax1.set(title="Glide ratio L/D (level flight, trimmed lift)", xlabel="Airspeed (m/s)", ylabel="L/D")
    ax2.set(title="Electrical power for level flight", xlabel="Airspeed (m/s)", ylabel="Power (W)")
    ax1.legend(loc="lower center")
    fig.tight_layout()
    fig.savefig(FIG / "performance.png", dpi=160)
    plt.close(fig)


DRAG_ORDER = [("induced", "Induced (lift)"), ("Wing", "Wing profile"), ("Pod", "Pod"),
              ("H-stab", "Stabiliser"), ("V-stab", "Fin"), ("Boom + tail hub", "Boom + hub")]


def drag_parts(r):
    p = r["best"]
    vals = dict(p.parts, induced=p.D_induced)
    return [vals[k] for k, _ in DRAG_ORDER]


def plot_drag(before, after):
    fig, ax = plt.subplots(figsize=(10, 2.8))
    rows = [(before, f"{before['name']}\n@ {before['best'].V:.1f} m/s"),
            (after, f"{after['name']}\n@ {after['best'].V:.1f} m/s")]
    for i, (r, label) in enumerate(rows):
        left = 0.0
        for (key, name), v, c in zip(DRAG_ORDER, drag_parts(r), SERIES):
            ax.barh(i, v, left=left, color=c, height=0.55, edgecolor=SURFACE, linewidth=2,
                    label=name if i == 0 else None)
            if v > 0.07:
                ax.text(left + v / 2, i, f"{v:.2f}", ha="center", va="center", color="white", fontsize=9)
            left += v
        ax.text(left + 0.02, i, f"{left:.2f} N", va="center", color=INK)
    ax.set_yticks([0, 1], [r[1] for r in rows])
    ax.invert_yaxis()
    ax.set(title="Drag at best L/D, by component (N)", xlabel="Drag (N)")
    ax.grid(axis="y", visible=False)
    ax.legend(ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.32), fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "drag_breakdown.png", dpi=160)
    plt.close(fig)


def airfoil_polars(re):
    foils = {"E193 (before)": model.E193, f"{P.WING_AIRFOIL.upper()} (after)": model.WING_AIRFOIL,
             "MH32": asb.Airfoil("mh32"), "S7075": asb.Airfoil("s7075")}
    alpha = np.linspace(-3, 12, 151)
    out = {}
    for name, af in foils.items():
        r = af.get_aero_from_neuralfoil(alpha=alpha, Re=re, mach=0.05, model_size="large")
        top = int(np.argmax(r["CL"]))
        out[name] = (af, r["CL"][:top + 1], r["CD"][:top + 1], r["CM"][:top + 1])
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.set_xlim(60, 200)
    styles = [(BEFORE_C, "-", 0.9, (8, -4)), (AFTER_C, "-", 1.2, (-6, 8)),
              (CONTEXT_C, "-", None, None), (CONTEXT_C, "--", None, None)]
    for (name, (af, cl, cd, _)), (c, ls, at_cl, offset) in zip(out.items(), styles):
        ax.plot(cd * 1e4, cl, color=c, ls=ls, lw=1.6 if c != CONTEXT_C else 1.2, label=name)
        if offset:
            k = int(np.argmin(np.abs(cl - at_cl)))
            ax.annotate(name, (cd[k] * 1e4, cl[k]), textcoords="offset points", xytext=offset,
                        ha="left" if offset[0] > 0 else "right", color=INK, fontsize=9)
    ax.legend(loc="lower right", fontsize=9)
    ax.axhspan(0.45, 0.75, color=GRID, alpha=0.6, lw=0)
    ax.text(198, 0.6, "cruise range", ha="right", va="center", color=INK2, fontsize=9)
    ax.set(title=f"Airfoil drag polars at Re {re / 1e3:.0f}k (NeuralFoil)", xlabel="Drag coefficient × 10⁴",
           ylabel="Lift coefficient")
    fig.tight_layout()
    fig.savefig(FIG / "airfoil_polars.png", dpi=160)
    plt.close(fig)
    rows = []
    for name, (af, cl, cd, cm) in out.items():
        rows.append((name, af.max_thickness(), np.interp(0.45, cl, cd), np.interp(0.6, cl, cd),
                     np.interp(0.75, cl, cd), np.interp(0.6, cl, cm), cl.max()))
    return rows


def main():
    FIG.mkdir(exist_ok=True)
    before = evaluate("Before (E193, stab 0°)", dict(airfoil=model.E193, stab_incidence=0.0),
                      model.Flight(cg_from_le=62.0))
    after = evaluate(f"After ({P.WING_AIRFOIL.upper()}, stab {P.STAB_INCIDENCE:+.0f}°)", {}, model.Flight())
    plot_performance(before, after)
    plot_drag(before, after)
    re = after["best"].V * P.CHORD / 1000 / NU
    foils = airfoil_polars(re)

    trades = [("Current: 200 mm constant chord", {}),
              ("Constant chord 180 mm", dict(planform=model.wing_planform(chord=180))),
              ("Constant chord 220 mm", dict(planform=model.wing_planform(chord=220))),
              ("Taper S2–S3 to 150 mm", dict(planform=model.wing_planform(taper_from=240, tip_panel_chord=150))),
              ("Taper S1–S3 to 140 mm", dict(planform=model.wing_planform(taper_from=80, tip_panel_chord=140))),
              ("Wing incidence 2.5° (vs 1.5°)", dict(incidence=2.5))]
    trade_rows = []
    for name, kw in trades:
        ap = model.make_airplane(**kw)
        pts, best, minp = A.performance(ap, model.Flight(), SPEEDS)
        trade_rows.append(dict(name=name, S=ap.s_ref, AR=ap.wings[0].aspect_ratio(), LD=best.LD, V=best.V,
                               P=minp.P_elec, Vp=minp.V, alpha=best.alpha, Vmin=pts[0].V))

    write_report(before, after, foils, re, trade_rows)
    print(f"L/D {before['best'].LD:.2f} -> {after['best'].LD:.2f}, "
          f"P_min {before['minp'].P_elec:.1f} -> {after['minp'].P_elec:.1f} W, "
          f"NP {after['stab']['np_mm']:.0f} mm, SM {after['stab']['static_margin']:.0%}")


def pct(a, b):
    return f"{(b - a) / a * 100:+.1f}%"


def write_report(before, after, foils, re, trades):
    b, a = before, after
    bb, ab = b["best"], a["best"]
    bm, am = b["minp"], a["minp"]
    st = a["stab"]
    f = a["flight"]
    dparts = list(zip([n for _, n in DRAG_ORDER], drag_parts(b), drag_parts(a)))
    D_total_a = sum(drag_parts(a))
    induced_share = drag_parts(a)[0] / D_total_a
    cur, c180, c220, tap, inc = trades[0], trades[1], trades[2], trades[4], trades[5]
    lines = [
        "# Aerodynamics",
        "",
        "This document analyses the airframe in this repo and records the changes made to make it more efficient. "
        f"It is regenerated by `aero/report.py` from the same parameters as the CAD (`cad/params.py`).",
        "",
        f"Design point: **{f.mass:.1f} kg all-up** (about 750 g of printed parts, carbon, electronics and a "
        f"4S6P Li-ion pack), sea level. The CG is {f.cg_from_le:.0f} mm behind the wing LE.",
        "",
        "## Result",
        "",
        "| | Before | After | Change |",
        "|---|---|---|---|",
        f"| Best glide ratio (L/D) | {bb.LD:.2f} at {bb.V:.1f} m/s | {ab.LD:.2f} at {ab.V:.1f} m/s | {pct(bb.LD, ab.LD)} |",
        f"| Drag at best L/D | {bb.D:.3f} N | {ab.D:.3f} N | {pct(bb.D, ab.D)} |",
        f"| Minimum power (level flight) | {bm.P_elec:.1f} W at {bm.V:.1f} m/s | {am.P_elec:.1f} W at {am.V:.1f} m/s | {pct(bm.P_elec, am.P_elec)} |",
        f"| Endurance, 4S6P (model)* | {b['hours']:.1f} h | {a['hours']:.1f} h | {pct(b['hours'], a['hours'])} |",
        f"| Pitching moment at cruise, elevator neutral | {b['cm']:+.3f} | {a['cm']:+.3f} | elevator now ~neutral |",
        f"| Neutral point / static margin | {b['stab']['np_mm']:.0f} mm / {b['stab']['static_margin']:.0%} | {st['np_mm']:.0f} mm / {st['static_margin']:.0%} | |",
        "",
        f"\\*At the minimum-power speed with {f.prop_efficiency:.0%} propulsion efficiency, "
        f"{A.AVIONICS_W:.0f} W of avionics and {f.battery_wh:.0f} Wh usable. That's still air with no climbs or turns. "
        "Expect real flights to get roughly 60–70% of this.",
        "",
        "![performance](aero/figures/performance.png)",
        "",
        "## Where the drag comes from",
        "",
        "![drag](aero/figures/drag_breakdown.png)",
        "",
        "| Component | Before (N) | After (N) |",
        "|---|---|---|",
        *[f"| {n} | {x:.3f} | {y:.3f} |" for n, x, y in dparts],
        f"| **Total** | **{sum(drag_parts(b)):.3f}** | **{D_total_a:.3f}** |",
        "",
        f"- **Induced drag is {induced_share:.0%} of the total.** Induced drag is the cost of making lift. At a fixed weight "
        "it depends only on wingspan and span efficiency, not on wing area or airfoil. With the span fixed at the "
        "Lark's 1290 mm, the remaining levers are weight (induced drag goes with weight²: 10% lighter means about "
        "19% less induced drag) and span.",
        "- **Wing profile drag comes next.** The airfoil change cut it. See below.",
        "- **The pod** is about an eighth of the drag. It is sized by the battery bay (two 4S3P packs, each about "
        "75 × 56 × 65 mm), and its length-to-width ratio of about 3.7 is close to the lowest-drag value for the "
        "volume it holds.",
        "- **The tail** (stabiliser, fin, boom and hub) is about 12%. The tail volume (0.50 horizontal, "
        "0.030 vertical) is normal, so shrinking it would save little and cost stability.",
        "",
        "## Changes made",
        "",
        f"### 1. Wing airfoil: E193 → {P.WING_AIRFOIL.upper()}",
        "",
        f"At the cruise Reynolds number (Re ≈ {re / 1e3:.0f}k, from 200 mm chord at {ab.V:.0f} m/s), "
        f"{P.WING_AIRFOIL.upper()} has noticeably less profile drag than E193 across the whole cruise lift "
        "range. It has a similar pitching moment, more maximum lift, and enough thickness for the 10 mm spar "
        "and the flat-lying servo. It is also among the most wind-tunnel-tested airfoils at this size "
        "(UIUC low-speed tests), so the prediction can be trusted.",
        "",
        "![polars](aero/figures/airfoil_polars.png)",
        "",
        "| Airfoil | t/c | cd @ cl 0.45 | cd @ cl 0.60 | cd @ cl 0.75 | cm @ cl 0.6 | cl max |",
        "|---|---|---|---|---|---|---|",
        *[f"| {n} | {t:.1%} | {c1 * 1e4:.0f} | {c2 * 1e4:.0f} | {c3 * 1e4:.0f} | {cm:+.3f} | {mx:.2f} |"
          for n, t, c1, c2, c3, cm, mx in foils],
        "",
        "(cd in drag counts, × 10⁻⁴.) MH32 and S7075 are shown for context. MH32 is about as good but thinner "
        "(8.7%), which leaves too little room around the spar sleeve. S7075 only pulls ahead above "
        "cl ≈ 0.7, which is slow, heavy flight.",
        "",
        f"### 2. Stabiliser incidence: 0° → {P.STAB_INCIDENCE:+.0f}°",
        "",
        f"With the elevator neutral, the original tail left a nose-down moment of Cm = {b['cm']:+.3f} at cruise. "
        "That has to be held with up-elevator, which kinks the tail and adds drag. Setting the stabiliser to "
        f"{P.STAB_INCIDENCE:+.0f}° (rotated about its spar; the hub's pin hole and joiner slot move with it) brings "
        f"this to {a['cm']:+.3f}, so the elevator sits close to neutral at cruise.",
        "",
        f"### 3. Centre of gravity: 62 → {f.cg_from_le:.0f} mm",
        "",
        f"The neutral point comes out at **{st['np_mm']:.0f} mm** behind the wing LE: a vortex-lattice model "
        "including the wing's downwash on the tail, plus the pod's destabilising moment. A CG at "
        f"{f.cg_from_le:.0f} mm gives a **{st['static_margin']:.0%} static margin**: stable and forgiving, "
        "with less tail download than the original 62 mm. **Fly within "
        f"{st['cg_range_mm'][0]:.0f}–{st['cg_range_mm'][1]:.0f} mm** (static margin 18% to 8%). Start at "
        f"{f.cg_from_le:.0f}.",
        "",
        "## Trade studies (changes considered and not made)",
        "",
        "All at the design point with the new airfoil:",
        "",
        "| Variant | Wing area (m²) | Aspect ratio | Best L/D | at (m/s) | Min power (W) | at (m/s) | Slowest level flight (m/s) | Pod attitude at best L/D |",
        "|---|---|---|---|---|---|---|---|---|",
        *[f"| {t['name']} | {t['S']:.3f} | {t['AR']:.2f} | {t['LD']:.2f} | {t['V']:.1f} | {t['P']:.1f} | "
          f"{t['Vp']:.1f} | {t['Vmin']:.1f} | {t['alpha']:+.1f}° |" for t in trades],
        "",
        f"- **Tapering the wing** raises best L/D by {pct(cur['LD'], tap['LD'])} but *raises* minimum power by "
        f"{pct(cur['P'], tap['P'])}, because the smaller wing has to fly at a higher lift coefficient. Endurance "
        "is the point of this airframe, so the rectangular wing stays. It also keeps the carbon spars straight "
        "and every panel identical.",
        f"- **A 180 mm chord** gives {pct(cur['LD'], c180['LD'])} best L/D for the same minimum power, but the "
        f"slowest level-flight speed rises from {cur['Vmin']:.1f} to {c180['Vmin']:.1f} m/s. That makes hand "
        "launches and landings of a 2.3 kg plane harder, which isn't worth 1–2% of cruise efficiency. "
        f"**A 220 mm chord** loses {pct(cur['LD'], c220['LD'])[1:]} of best L/D and adds weight. 200 mm stays.",
        f"- **Wing incidence** barely matters: 2.5° instead of 1.5° changes best L/D by {pct(cur['LD'], inc['LD'])}. "
        f"At 1.5° the pod flies within {abs(cur['alpha']):.1f}° of level at best L/D, so it stays.",
        "- **Span** is the one big lever left: induced drag goes with 1/span². It is fixed here at the Lark's "
        "1290 mm. Adding one more 160 mm panel per side (1610 mm span) would cut induced drag by about a third.",
        "",
        "## Build and flying tips that matter aerodynamically",
        "",
        "- **Seal the hinge gaps** on the ailerons and elevators with clear tape along the hinge line. "
        "An open 1 mm gap leaks air from the bottom to the top surface right where the airfoil is most sensitive.",
        "- **Keep it light.** Every 100 g costs about 9% more induced drag at this weight. Print the solid parts "
        "(tips, tail, ailerons) at 8% infill or less.",
        f"- **Cruise at {ab.V:.0f}–{ab.V + 2:.0f} m/s** ({ab.V * 3.6:.0f}–{(ab.V + 2) * 3.6:.0f} km/h) for range, "
        f"and around {am.V:.0f} m/s for maximum endurance.",
        "- **Keep the leading edge clean.** Sand off layer seams and blobs on the front 30% of the wing. That is "
        "where the boundary layer is laminar and most sensitive.",
        "",
        "## Method and limits",
        "",
        "- **Drag and performance:** AeroSandbox `AeroBuildup`. It combines NeuralFoil airfoil polars for wing "
        "profile drag, Oswald-efficiency induced drag, and empirical body drag. Level flight is found by solving "
        "for the angle of attack where lift equals weight at each speed.",
        "- **Stability and trim:** AeroSandbox vortex-lattice method on all lifting surfaces, plus AeroBuildup "
        "body moments. AeroBuildup alone ignores downwash on the tail and put the neutral point about 30 mm too "
        "far aft. The VLM result was checked for mesh convergence.",
        "- **Not modelled:** propeller slipstream (the pusher prop helps the pod's rear flow stay attached under "
        "power), separation at the steep underside of the pod's rear, surface roughness, and hinge-gap leakage. "
        "The absolute numbers are estimates; the before/after differences are more reliable than the absolutes.",
        "",
    ]
    (ROOT / "AERODYNAMICS.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
