# Designed for regular PLA, balanced with nose weight

Wall thicknesses, print settings and the weight budget assume regular PLA: a 0.45 mm single-line wing skin, a 0.8 mm fuselage shell, and one wall with 5 % infill on solid parts. The builder prints in PLA, and foamed LW-PLA is harder to source and to tune. PLA makes the printed parts about twice as heavy (about 880 g against 400 g), so the thinner walls are what keep the all-up weight near 1.84 kg.

Even with the tail servos in the pod and the battery as far forward as the nose allows, the PLA build needs about 92 g of lead in the nose to reach the 66 mm CG target. The alternatives were moving the wing aft, which would rework the pod's top line, the saddle, the bolt bosses and the hatch, or accepting a static margin of about 6 %. The lead is cheap and adjustable, and `cad/assembly.py` fails if the PLA CG drifts more than 3 mm from target, printing the nose weight that would fix it (`hardware.NOSE_WEIGHT_G`).

An LW-PLA build still works: it comes out nose-heavy, so it flies without the lead and with the battery about 30 mm further back.
