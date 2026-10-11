"""Report unsupported overhang area for every STL in stl/, as it sits on the bed.

    .venv/bin/python cad/check_print.py

Counts down-facing area steeper than 50 degrees from vertical, ignoring the
first 0.3 mm (the bed contact). Compare against the known baseline below:
short bridges (servo-pocket ceilings, the camera ring at the nose tip) are
accepted; anything new and large is a printability regression.
"""
import glob
import os
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LIMIT_DEG = 50.0
BASELINE = {   # mm2 of accepted overhang per part type, after the printability pass
    "fuse_1_nose": 3000, "fuse_2_front": 1050, "fuse_3_rear": 500, "tail_fin_hub": 900,
    "wing_s2": 320, "fuse_hatch": 200, "fuse_4_tail_motor_cone": 170, "wing_center": 100,
}


def overhang_mm2(path):
    data = Path(path).read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    rec = np.frombuffer(data[84:], dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")], count=n)
    v = rec["v"].astype(float)
    nrm = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    area = np.linalg.norm(nrm, axis=1) / 2
    nz = nrm[:, 2] / np.maximum(2 * area, 1e-12)
    bad = (nz < -np.cos(np.radians(90 - LIMIT_DEG))) & (v[:, :, 2].min(1) > 0.3)
    return float(area[bad].sum())


def main():
    regressions = []
    for f in sorted(glob.glob(str(ROOT / "stl" / "*.stl"))):
        name = os.path.basename(f)[3:-4]
        a = overhang_mm2(f)
        allowed = next((v for k, v in BASELINE.items() if name.startswith(k)), 60)
        flag = "" if a <= allowed else f"   <-- above baseline {allowed}"
        if flag:
            regressions.append(name)
        print(f"{name:32s} {a:7.0f} mm2{flag}")
    if regressions:
        print(f"\nOverhang regression in: {', '.join(regressions)}")
        sys.exit(1)
    print("\nNo overhang regressions.")


if __name__ == "__main__":
    main()
