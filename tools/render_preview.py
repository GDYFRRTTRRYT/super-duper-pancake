"""Software z-buffer preview of the generated katana (no GPU needed)."""
import math
import os

import numpy as np
from PIL import Image, ImageFilter

import generate_katana as gk

SS = 2  # supersampling factor
METAL = {"Blade", "Hamon", "Habaki", "MoonGuard", "GuardRim", "Fuchi", "Kashira", "Tsuba"}


def rot(yaw, pitch, roll=0.0):
    cy, sy, cp, sp, cr, sr = (math.cos(yaw), math.sin(yaw), math.cos(pitch),
                              math.sin(pitch), math.cos(roll), math.sin(roll))
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return rz @ rx @ ry


def background(w, h):
    gy, gx = np.mgrid[0:h, 0:w]
    d = np.hypot((gx - w / 2) / w, (gy - h / 2) / h)
    f = np.clip(1.0 - d * 1.7, 0, 1)[..., None] ** 1.5
    return np.array([0.012, 0.012, 0.028]) + f * np.array([0.06, 0.055, 0.13])


def render(parts, view, center, scale, size):
    """view rows are camera right / up / towards-viewer in model space."""
    w, h = size[0] * SS, size[1] * SS
    color = background(w, h)
    glow = np.zeros((h, w, 3))
    zbuf = np.full((h, w), -1e9)
    key = np.array([0.35, 0.55, 0.75])
    key /= np.linalg.norm(key)
    fill = np.array([-0.6, -0.25, 0.5])
    fill /= np.linalg.norm(fill)
    half = key + np.array([0, 0, 1.0])
    half /= np.linalg.norm(half)
    for name, (verts, faces, normals, corner_normals, _) in parts.items():
        base = np.array(gk.MATERIALS[name])
        emissive = name in gk.EMISSIVE
        metal = name in METAL
        cam = (verts - center) @ view.T
        px = cam[:, 0] * scale * SS + w / 2
        py = h / 2 - cam[:, 1] * scale * SS
        cn = normals @ view.T
        for face, ncorner in zip(faces, corner_normals):
            x, y, z = px[face], py[face], cam[face, 2]
            det = (x[1] - x[0]) * (y[2] - y[0]) - (x[2] - x[0]) * (y[1] - y[0])
            if det >= 0:  # back face (screen y is flipped)
                continue
            x0, x1 = max(int(x.min()), 0), min(int(x.max()) + 1, w - 1)
            y0, y1 = max(int(y.min()), 0), min(int(y.max()) + 1, h - 1)
            if x0 > x1 or y0 > y1:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            b0 = ((x[1] - gx) * (y[2] - gy) - (x[2] - gx) * (y[1] - gy)) / det
            b1 = ((x[2] - gx) * (y[0] - gy) - (x[0] - gx) * (y[2] - gy)) / det
            b2 = 1 - b0 - b1
            depth = b0 * z[0] + b1 * z[1] + b2 * z[2]
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            mask = (b0 >= 0) & (b1 >= 0) & (b2 >= 0) & (depth > sub)
            if not mask.any():
                continue
            n = (b0[..., None] * cn[ncorner[0]] + b1[..., None] * cn[ncorner[1]]
                 + b2[..., None] * cn[ncorner[2]])
            n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
            d1 = np.clip(n @ key, 0, 1)[..., None]
            d2 = np.clip(n @ fill, 0, 1)[..., None]
            rim = ((1 - np.clip(n[..., 2], 0, 1)) ** 3)[..., None] * np.array([0.10, 0.13, 0.26])
            if emissive:
                shade = np.broadcast_to(base * 0.9 + 0.25, n.shape)
            elif metal:
                # cheap studio environment: sky gradient plus one bright horizontal strip
                ry = 2 * n[..., 2] * n[..., 1]
                env = (0.10 + 0.45 * np.clip(ry * 0.5 + 0.5, 0, 1) ** 2
                       + 0.55 * np.exp(-((ry - 0.4) / 0.14) ** 2))[..., None]
                spec = (np.clip(n @ half, 0, 1) ** 70)[..., None]
                shade = (base * (0.16 + 0.45 * d1) + (0.55 * base + 0.18) * env
                         + spec * 0.9 + d2 * np.array([0.03, 0.04, 0.09]) + rim)
            else:
                spec = (np.clip(n @ half, 0, 1) ** 30)[..., None]
                shade = (base * (0.26 + 0.72 * d1) + spec * 0.12
                         + d2 * np.array([0.04, 0.05, 0.10]) + rim)
            if name == "MoonAura":  # translucent energy: blend without writing depth
                region = color[y0:y1 + 1, x0:x1 + 1]
                region[mask] = region[mask] * 0.55 + shade[mask] * 0.45
                glow[y0:y1 + 1, x0:x1 + 1][mask] += base * 0.3
                continue
            sub[mask] = depth[mask]
            color[y0:y1 + 1, x0:x1 + 1][mask] = shade[mask]
            glow[y0:y1 + 1, x0:x1 + 1][mask] = base if emissive else 0
    img = Image.fromarray((np.clip(color, 0, 1) * 255).astype(np.uint8))
    bloom = Image.fromarray((np.clip(glow, 0, 1) * 255).astype(np.uint8))
    out = np.asarray(img, dtype=float)
    for radius, gain in ((3 * SS, 0.6), (10 * SS, 0.55), (30 * SS, 0.45)):
        out += np.asarray(bloom.filter(ImageFilter.GaussianBlur(radius)), dtype=float) * gain
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    return img.resize(size, Image.LANCZOS)


def main():
    parts = gk.build()
    out = os.path.join(gk.ROOT, "preview")
    os.makedirs(out, exist_ok=True)
    # side view: blade to the right, edge down, looking at the -X face
    side = np.array([[0, 1, 0], [0, 0, -1], [-1, 0, 0]], dtype=float)
    rad = math.radians
    views = {
        "hero": (rot(rad(28), rad(-14), rad(27)) @ side, (0, 1.2, -0.15), 215, (1600, 1000)),
        "side": (rot(0, rad(-10)) @ side, (0, 1.15, -0.15), 228, (1800, 560)),
        "guard": (rot(rad(35), rad(-24)) @ side, (0, 0.25, 0), 430, (1400, 900)),
        "blade": (rot(0, rad(-8)) @ side, (0, 2.5, -0.12), 600, (1600, 520)),
    }
    for name, (view, center, scale, size) in views.items():
        render(parts, view, np.array(center, dtype=float), scale, size).save(
            os.path.join(out, f"{name}.png"))
        print("rendered", name)


if __name__ == "__main__":
    main()
