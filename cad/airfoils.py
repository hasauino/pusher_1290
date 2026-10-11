"""Airfoil sections resampled onto a common cosine-spaced grid, so any two
sections have the same point count and can be lofted together."""
from pathlib import Path

import numpy as np

from params import WING_AIRFOIL

DATA = Path(__file__).parent / "data"


class Airfoil:
    def __init__(self, xn, zu, zl):
        self.xn, self.zu, self.zl = xn, zu, zl

    @classmethod
    def from_selig(cls, path, n=90):
        pts = []
        for line in Path(path).read_text().splitlines()[1:]:
            parts = line.split()
            if len(parts) == 2:
                pts.append((float(parts[0]), float(parts[1])))
        pts = np.array(pts)
        le = int(np.argmin(pts[:, 0]))
        upper = pts[: le + 1][::-1]   # LE -> TE
        lower = pts[le:]              # LE -> TE
        xn = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
        return cls(xn, np.interp(xn, upper[:, 0], upper[:, 1]), np.interp(xn, lower[:, 0], lower[:, 1]))

    @classmethod
    def naca00(cls, thickness, n=90):
        xn = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
        yt = 5 * thickness * (0.2969 * np.sqrt(xn) - 0.1260 * xn - 0.3516 * xn**2
                              + 0.2843 * xn**3 - 0.1036 * xn**4)
        return cls(xn, yt, -yt)

    def _surfaces(self, chord, te):
        add = te / chord / 2 * self.xn
        return self.zu + add, self.zl - add

    def ring(self, chord, te=0.6, thickness_scale=1.0):
        """Closed CCW outline in mm: upper surface TE->LE, then lower LE->TE."""
        zu, zl = self._surfaces(chord, te)
        zu, zl = zu * thickness_scale, zl * thickness_scale
        x = self.xn * chord
        up = np.stack([x[::-1], zu[::-1] * chord], 1)
        lo = np.stack([x[1:], zl[1:] * chord], 1)
        return np.concatenate([up, lo])

    def surface(self, x_mm, chord, te=0.6):
        """(z_upper, z_lower) in mm at chord station x_mm."""
        zu, zl = self._surfaces(chord, te)
        xn = np.clip(np.asarray(x_mm) / chord, 0, 1)
        return np.interp(xn, self.xn, zu) * chord, np.interp(xn, self.xn, zl) * chord

    def mid(self, x_mm, chord, te=0.6):
        zu, zl = self.surface(x_mm, chord, te)
        return (zu + zl) / 2

    def half_thickness(self, x_mm, chord, te=0.6):
        zu, zl = self.surface(x_mm, chord, te)
        return (zu - zl) / 2


WING = Airfoil.from_selig(DATA / f"{WING_AIRFOIL}.dat")
