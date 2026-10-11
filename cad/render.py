"""Tiny flat-shaded z-buffer renderer for preview images."""
import math

import numpy as np
from PIL import Image

from geom import mesh_arrays


def render(items, view, up, path=None, size=(1600, 1000), bg=(246, 246, 244), ss=2):
    """items: list of (manifold, rgb 0..1). view: direction the camera looks.
    Saves to `path`, or returns the PIL image when no path is given."""
    fwd = np.asarray(view, float)
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, up)
    right /= np.linalg.norm(right)
    up2 = np.cross(right, fwd)
    light = -fwd + 0.6 * up2 + 0.3 * right
    light /= np.linalg.norm(light)

    pts, depth, cols = [], [], []
    for man, rgb in items:
        v, t = mesh_arrays(man)
        tri = v[t]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        keep = n @ fwd < 0
        tri, n = tri[keep], n[keep]
        shade = 0.38 + 0.62 * np.clip(n @ light, 0, 1)
        pts.append(np.stack([tri @ right, -(tri @ up2)], axis=2))
        depth.append(tri @ fwd)
        cols.append(np.clip(np.outer(shade, rgb) * 255, 0, 255).astype(np.uint8))
    pts, depth, cols = np.concatenate(pts), np.concatenate(depth), np.concatenate(cols)

    w, h = size[0] * ss, size[1] * ss
    lo, hi = pts.reshape(-1, 2).min(0), pts.reshape(-1, 2).max(0)
    scale = 0.92 * min(w / (hi[0] - lo[0]), h / (hi[1] - lo[1]))
    pts = pts * scale + (np.array([w, h]) / 2 - (lo + hi) / 2 * scale)

    zbuf = np.full((h, w), np.inf)
    img = np.empty((h, w, 3), np.uint8)
    img[:] = bg
    x0 = np.clip(np.floor(pts[:, :, 0].min(1)).astype(int), 0, w - 1)
    x1 = np.clip(np.ceil(pts[:, :, 0].max(1)).astype(int), 0, w - 1)
    y0 = np.clip(np.floor(pts[:, :, 1].min(1)).astype(int), 0, h - 1)
    y1 = np.clip(np.ceil(pts[:, :, 1].max(1)).astype(int), 0, h - 1)
    for i in range(len(pts)):
        xs = np.arange(x0[i], x1[i] + 1) + 0.5
        ys = np.arange(y0[i], y1[i] + 1) + 0.5
        gx, gy = np.meshgrid(xs, ys)
        (ax, ay), (bx, by), (cx, cy) = pts[i]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        l3 = 1 - l1 - l2
        inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not inside.any():
            continue
        d = l1 * depth[i, 0] + l2 * depth[i, 1] + l3 * depth[i, 2]
        sub = zbuf[y0[i]:y1[i] + 1, x0[i]:x1[i] + 1]
        win = inside & (d < sub)
        sub[win] = d[win]
        img[y0[i]:y1[i] + 1, x0[i]:x1[i] + 1][win] = cols[i]
    out = Image.fromarray(img).resize(size, Image.LANCZOS)
    if path is None:
        return out
    out.save(path)
