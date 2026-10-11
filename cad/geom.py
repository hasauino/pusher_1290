"""Small geometry toolkit on top of manifold3d: lofts, primitives, STL export."""
import math

import manifold3d as m3d
import numpy as np

Manifold = m3d.Manifold
CrossSection = m3d.CrossSection
m3d.set_circular_segments(64)


def check(man, what="manifold"):
    if man.status() != m3d.Error.NoError:
        raise RuntimeError(f"{what}: {man.status()}")
    return man


# --- 2D ------------------------------------------------------------------------

def poly(points):
    return CrossSection([np.asarray(points, dtype=np.float64)])


def rect(x0, y0, x1, y1):
    return CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))


def circle(cx, cy, r, segments=48):
    return CrossSection.circle(r, segments).translate((cx, cy))


def teardrop(cx, cy, r, toward=(0, 1)):
    """Circle with a 45-degree point added in direction `toward`.

    Point a hole's tip up (+print Z) so its ceiling prints without support;
    point a solid boss's tip down so its underside does.
    """
    d = np.asarray(toward, float)
    d /= np.linalg.norm(d)
    tip = np.array([cx, cy]) + d * (r * math.sqrt(2) - 0.2)
    return CrossSection.batch_hull([circle(cx, cy, r), circle(tip[0], tip[1], 0.2, 12)])


def v_region(apex_x, apex_y, bevel_deg, reach=400.0):
    """Everything aft of a V whose apex is at (apex_x, apex_y).

    Used to cut the leading edge of a control surface: each face of the V is
    `bevel_deg` off vertical, so the surface can swing that far either way.
    """
    h = 80.0
    dx = h * math.tan(math.radians(bevel_deg))
    return poly([(apex_x, apex_y), (apex_x + dx, apex_y - h), (apex_x + reach, apex_y - h),
                 (apex_x + reach, apex_y + h), (apex_x + dx, apex_y + h)])


# --- 3D primitives ---------------------------------------------------------------

def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl_x(x0, x1, y, z, r, segments=48):
    return Manifold.cylinder(x1 - x0, r, circular_segments=segments).rotate((0, 90, 0)).translate((x0, y, z))


def cyl_y(y0, y1, x, z, r, segments=48):
    return Manifold.cylinder(y1 - y0, r, circular_segments=segments).rotate((-90, 0, 0)).translate((x, y0, z))


def cyl_z(z0, z1, x, y, r, segments=48):
    return Manifold.cylinder(z1 - z0, r, circular_segments=segments).translate((x, y, z0))


def segment(p0, p1, r, segments=16):
    """Round rod from p0 to p1 (flat ends)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    length = float(np.linalg.norm(d))
    z = d / length
    helper = np.array([1.0, 0, 0]) if abs(z[0]) < 0.9 else np.array([0, 1.0, 0])
    x = np.cross(helper, z)
    x /= np.linalg.norm(x)
    rot = np.column_stack([x, np.cross(z, x), z])
    return transform(Manifold.cylinder(length, r, circular_segments=segments), rot, p0)


def path(points, r, segments=16):
    """Rod through a list of points, with ball joints so the bends stay closed."""
    pts = [np.asarray(p, float) for p in points]
    rods = [segment(a, b, r, segments) for a, b in zip(pts, pts[1:])]
    balls = [Manifold.sphere(r, segments).translate(tuple(p)) for p in pts[1:-1]]
    return union(rods + balls)


def extrude(cs, z0, z1):
    return Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))


def union(parts):
    parts = [p for p in parts if p is not None]
    return Manifold.batch_boolean(parts, m3d.OpType.Add) if len(parts) > 1 else parts[0]


def affine(rot, trans=(0, 0, 0)):
    m = np.zeros((3, 4))
    m[:, :3] = rot
    m[:, 3] = trans
    return m


def transform(man, rot, trans=(0, 0, 0)):
    return check(man.transform(affine(rot, trans)), "transform")


def rot_x(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


# --- Loft ------------------------------------------------------------------------

def _newell(ring):
    nxt = np.roll(ring, -1, axis=0)
    return np.cross(ring, nxt).sum(axis=0)


def _cap(ring, normal, base):
    """Triangulate a planar ring so the triangles face `normal`."""
    n = normal / np.linalg.norm(normal)
    helper = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(n, helper)
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    c = ring.mean(axis=0)
    p2 = np.stack([(ring - c) @ u, (ring - c) @ v], axis=1)
    area = 0.5 * np.sum(p2[:, 0] * np.roll(p2[:, 1], -1) - np.roll(p2[:, 0], -1) * p2[:, 1])
    order = np.arange(len(ring))
    if area < 0:
        order = order[::-1]
    tris = np.asarray(m3d.triangulate([p2[order]]))
    return order[tris] + base


def loft(rings):
    """Closed solid through a list of planar rings (same point count, same winding)."""
    rings = [np.asarray(r, dtype=np.float64) for r in rings]
    n = len(rings[0])
    d = rings[-1].mean(axis=0) - rings[0].mean(axis=0)
    if np.dot(_newell(rings[0]), d) < 0:
        rings = [r[::-1].copy() for r in rings]
    verts = np.concatenate(rings)
    tris = []
    j = np.arange(n)
    jn = (j + 1) % n
    for i in range(len(rings) - 1):
        a, b, c, dd = i * n + j, i * n + jn, (i + 1) * n + j, (i + 1) * n + jn
        tris.append(np.stack([a, b, dd], 1))
        tris.append(np.stack([a, dd, c], 1))
    tris.append(_cap(rings[0], -d, 0))
    tris.append(_cap(rings[-1], d, (len(rings) - 1) * n))
    mesh = m3d.Mesh(vert_properties=verts.astype(np.float32),
                    tri_verts=np.concatenate(tris).astype(np.uint32))
    return check(Manifold(mesh), "loft")


def superellipse(width, height, n_exp, count, zc=0.0, yc=0.0):
    th = np.linspace(0, 2 * math.pi, count, endpoint=False)
    c, s = np.cos(th), np.sin(th)
    y = yc + width / 2 * np.sign(c) * np.abs(c) ** (2 / n_exp)
    z = zc + height / 2 * np.sign(s) * np.abs(s) ** (2 / n_exp)
    return np.stack([y, z], axis=1)


def pchip(xk, yk, x):
    """Shape-preserving cubic interpolation (Fritsch-Carlson)."""
    xk, yk, x = np.asarray(xk, float), np.asarray(yk, float), np.asarray(x, float)
    h = np.diff(xk)
    delta = np.diff(yk) / h
    m = np.zeros_like(yk)
    m[0], m[-1] = delta[0], delta[-1]
    for k in range(1, len(xk) - 1):
        if delta[k - 1] * delta[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k])
    i = np.clip(np.searchsorted(xk, x) - 1, 0, len(xk) - 2)
    t = (x - xk[i]) / h[i]
    h00, h10 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t
    h01, h11 = -2 * t**3 + 3 * t**2, t**3 - t**2
    return h00 * yk[i] + h10 * h[i] * m[i] + h01 * yk[i + 1] + h11 * h[i] * m[i + 1]


# --- Export ----------------------------------------------------------------------

def mesh_arrays(man):
    mesh = man.to_mesh()
    return np.asarray(mesh.vert_properties)[:, :3].astype(np.float64), np.asarray(mesh.tri_verts)


def write_stl(man, path):
    v, t = mesh_arrays(man)
    tri = v[t]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = nrm, tri
    with open(path, "wb") as f:
        f.write(b"Lark-style RC plane".ljust(80, b" "))
        f.write(np.uint32(len(t)).tobytes())
        f.write(rec.tobytes())
