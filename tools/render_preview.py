"""Software z-buffer preview of the generated katana (no GPU needed)."""
import math
import os

import numpy as np
from PIL import Image, ImageFilter

import generate_katana as gk

SS = 2  # supersampling factor


def rot(yaw, pitch, roll=0.0):
    cy, sy, cp, sp, cr, sr = (math.cos(yaw), math.sin(yaw), math.cos(pitch),
                              math.sin(pitch), math.cos(roll), math.sin(roll))
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return rz @ rx @ ry


def render(parts, view, center, scale, size):
    """view rows are camera right / up / towards-viewer in model space."""
    w, h = size[0] * SS, size[1] * SS
    color = np.zeros((h, w, 3))
    color[:] = (0.035, 0.035, 0.06)
    glow = np.zeros((h, w, 3))
    zbuf = np.full((h, w), -1e9)
    light = np.array([0.35, 0.55, 0.75])
    light /= np.linalg.norm(light)
    half = light + np.array([0, 0, 1.0])
    half /= np.linalg.norm(half)
    for name, (verts, faces, normals, corner_normals, _) in parts.items():
        base = np.array(gk.MATERIALS[name])
        emissive = name in gk.EMISSIVE
        metal = name in ("Blade", "Hamon", "Habaki", "GuardRim", "Fuchi", "Kashira", "Tsuba")
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
            diff = np.clip(n @ light, 0, 1)
            spec = np.clip(n @ half, 0, 1) ** 60 * (0.9 if metal else 0.15)
            shade = base * (0.30 + 0.75 * diff[..., None]) + spec[..., None]
            if emissive:
                shade = np.broadcast_to(base * 0.9 + 0.25, shade.shape)
            sub[mask] = depth[mask]
            color[y0:y1 + 1, x0:x1 + 1][mask] = shade[mask]
            glow[y0:y1 + 1, x0:x1 + 1][mask] = base if emissive else 0
    img = Image.fromarray((np.clip(color, 0, 1) * 255).astype(np.uint8))
    bloom = Image.fromarray((np.clip(glow, 0, 1) * 255).astype(np.uint8))
    out = np.asarray(img, dtype=float)
    for radius, gain in ((4 * SS, 0.7), (14 * SS, 0.6)):
        out += np.asarray(bloom.filter(ImageFilter.GaussianBlur(radius)), dtype=float) * gain
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    return img.resize(size, Image.LANCZOS)


def main():
    parts = gk.build()
    out = os.path.join(gk.ROOT, "preview")
    os.makedirs(out, exist_ok=True)
    # side view: blade to the right, edge down, looking at the -X face
    side = np.array([[0, 1, 0], [0, 0, -1], [-1, 0, 0]], dtype=float)
    views = {
        "side": (rot(0, math.radians(-12)) @ side, (0, 1.1, -0.1), 290, (1800, 520)),
        "guard": (rot(math.radians(35), math.radians(-28)) @ side, (0, -0.35, 0), 560, (1400, 900)),
        "blade": (rot(0, math.radians(-8)) @ side, (0, 1.6, -0.03), 1000, (1600, 520)),
        "tip": (rot(math.radians(-25), math.radians(-15)) @ side, (0, 3.4, -0.2), 900, (1200, 600)),
    }
    for name, (view, center, scale, size) in views.items():
        render(parts, view, np.array(center, dtype=float), scale, size).save(
            os.path.join(out, f"{name}.png"))
        print("rendered", name)


if __name__ == "__main__":
    main()
