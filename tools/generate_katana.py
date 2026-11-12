"""Procedural generator for the "King of the Nine Moons" katana (Roblox-ready OBJ).

Axes: blade along +Y, cutting edge towards +Z, thickness along X. 1 unit = 1 stud.
Every named object becomes its own MeshPart in the Roblox 3D importer.
"""
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "models")
NAME = "KingOfTheNineMoons"

GOLD = (0.95, 0.74, 0.26)
MOON = (0.70, 0.92, 1.00)

# name -> diffuse colour (also mirrored in roblox/SetupKatana.lua)
MATERIALS = {
    "Blade": (0.10, 0.11, 0.19),
    "Hamon": (0.74, 0.84, 1.00),
    "EdgeGlow": (0.80, 0.95, 1.00),
    "Vein": (0.62, 0.36, 1.00),
    "Moons": MOON,
    "Habaki": GOLD,
    "MoonGuard": GOLD,
    "Tsuba": (0.13, 0.11, 0.22),
    "GuardRim": GOLD,
    "MoonOrbs": MOON,
    "Fuchi": GOLD,
    "Tsuka": (0.86, 0.86, 0.92),
    "Ito": (0.22, 0.10, 0.40),
    "Kashira": GOLD,
    "CrownGem": (0.72, 0.36, 1.00),
    "MoonAura": (0.55, 0.50, 1.00),
    "MoonHalo": MOON,
}
EMISSIVE = {"EdgeGlow", "Vein", "Moons", "MoonOrbs", "CrownGem", "MoonAura", "MoonHalo"}

# Blade dimensions
L = 4.6          # blade length
TIP = 0.55       # kissaki length
SORI = 0.42      # curvature depth
W0, W1 = 0.36, 0.27
T0, T1 = 0.085, 0.060
SHINOGI = -0.10  # ridge position as a fraction of width (0 = centre)
RIDGE = 0.012    # mune roof height

# Handle dimensions
HA, HB = 0.078, 0.125   # ellipse semi-axes (x, z)
H_TOP, H_BOT = -0.03, -1.50

# Orbiting halo; the same axis is used by roblox/SetupKatana.lua to spin it
HALO_TILT = math.radians(35)
HALO_Y = 1.15

X = np.array([1.0, 0.0, 0.0])
Y = np.array([0.0, 1.0, 0.0])
Z = np.array([0.0, 0.0, 1.0])

objects = {name: [] for name in MATERIALS}


def unit(v):
    return v / np.linalg.norm(v)


def sweep(rings, name, tags=None, cap_start=True, cap_end=True, closed=False):
    """Skin a sequence of point rings into a closed, outward-facing piece.

    tags is either a per-column list or a callable (row, column) -> object name.
    """
    rings = np.asarray(rings, dtype=float)
    s, n, _ = rings.shape
    verts = [p for p in rings.reshape(-1, 3)]
    faces, ftags = [], []
    for i in range(s if closed else s - 1):
        i2 = (i + 1) % s
        for j in range(n):
            j2 = (j + 1) % n
            a, b, c, d = i * n + j, i * n + j2, i2 * n + j2, i2 * n + j
            faces += [(a, b, c), (a, c, d)]
            tag = tags(i, j) if callable(tags) else tags[j] if tags else name
            ftags += [tag] * 2
    if not closed:
        for ring_i, start in ((0, True), (s - 1, False)):
            if not (cap_start if start else cap_end):
                continue
            cen = len(verts)
            verts.append(rings[ring_i].mean(axis=0))
            for j in range(n):
                a, b = ring_i * n + j, ring_i * n + (j + 1) % n
                faces.append((cen, b, a) if start else (cen, a, b))
                ftags.append(name)
    verts = np.array(verts)
    faces = np.array(faces)
    tri = verts[faces]
    volume = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum()
    if volume < 0:
        faces = faces[:, ::-1]
    for tag in set(ftags):
        mask = np.array([t == tag for t in ftags])
        objects[tag].append((verts, faces[mask]))


def lathe(profile, name, center=(0.0, 0.0, 0.0), seg=24):
    """Revolve (radius, height) pairs around the Y axis."""
    rings = []
    for r, h in profile:
        rings.append([
            np.array((r * math.cos(a), h, r * math.sin(a))) + np.array(center)
            for a in (2 * math.pi * k / seg for k in range(seg))
        ])
    sweep(rings, name)


def sphere(center, radius, name, seg=14, stacks=9):
    profile = []
    for i in range(stacks + 1):
        t = -math.pi / 2 + math.pi * i / stacks
        profile.append((max(radius * math.cos(t), 1e-5), radius * math.sin(t)))
    lathe(profile, name, center=center, seg=seg)


def tube(points, radius, name, seg=8):
    """Round tube along a polyline using a parallel-transported frame."""
    pts = np.asarray(points, dtype=float)
    t0 = unit(pts[1] - pts[0])
    nrm = unit(np.cross(t0, X if abs(t0[0]) < 0.9 else Y))
    rings = []
    for i, p in enumerate(pts):
        t = unit(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
        nrm = unit(nrm - t * (nrm @ t))
        b = np.cross(t, nrm)
        rings.append([p + radius * (math.cos(a) * nrm + math.sin(a) * b)
                      for a in (2 * math.pi * k / seg for k in range(seg))])
    sweep(rings, name)


def lune_rows(R, r, d, steps):
    """Crescent between two circles. Yields (inner, outer, relative width) in (u, v);
    the outer circle is centred on the origin and the horns point towards +u."""
    a = (d * d + R * R - r * r) / (2 * d)
    h = math.sqrt(R * R - a * a)
    t_max, s_max = math.atan2(h, -a), math.atan2(h, -(a - d))
    for t in np.linspace(-t_max * 0.985, t_max * 0.985, steps):
        s = t * s_max / t_max
        outer = np.array([-R * math.cos(t), R * math.sin(t)])
        inner = np.array([d - r * math.cos(s), r * math.sin(s)])
        yield inner, outer, np.linalg.norm(outer - inner) / (R - r + d)


def lune(origin, eu, ev, en, R, r, d, thick, name, steps=40, inlay=None):
    """Solid crescent with a bevelled lens section; optional raised glowing inlay."""
    origin = np.asarray(origin, dtype=float)
    rings, glow = [], {1.0: [], -1.0: []}
    for inner, outer, rel in lune_rows(R, r, d, steps):
        th = thick * (0.2 + 0.8 * rel)

        def at(f, x):
            q = inner + (outer - inner) * f
            return origin + eu * q[0] + ev * q[1] + en * x

        rings.append([at(0, 0), at(0.3, th), at(0.7, th), at(1, 0), at(0.7, -th), at(0.3, -th)])
        for side in glow:
            glow[side].append([at(0.44, side * (th + 0.007)), at(0.56, side * (th + 0.007)),
                               at(0.56, side * (th - 0.004)), at(0.44, side * (th - 0.004))])
    sweep(rings, name)
    if inlay:
        for side_rings in glow.values():
            sweep(side_rings, inlay)


# ---------------------------------------------------------------- blade

def frame(y):
    """Centre of the blade spine curve and the local 'towards edge' direction."""
    zc = -SORI * (y / L) ** 2
    dz = -2 * SORI * y / L ** 2
    norm = math.hypot(1.0, dz)
    zdir = np.array([0.0, -dz / norm, 1.0 / norm])
    return np.array([0.0, y, zc]), zdir


def blade_dims(y):
    t = min(max(y / (L - TIP), 0.0), 1.0)
    return W0 + (W1 - W0) * t, T0 + (T1 - T0) * t


def half_thickness(y, zl):
    """Half thickness of the blade bevel at local z (between ridge and edge)."""
    w, t = blade_dims(y)
    zs, ze = SHINOGI * w, 0.5 * w
    return 0.5 * t * (ze - zl) / (ze - zs)


def hamon_z(y, w):
    return 0.5 * w - w * (0.16 + 0.030 * math.sin(y * 19.0) + 0.015 * math.sin(y * 43.0 + 1.0))


def groove_factor(y):
    """0..1 depth of the glowing fuller, fading in after the collar and out before the tip."""
    a0, a1 = 0.46, L - TIP - 0.35
    if y <= a0 or y >= a1:
        return 0.0
    return min(1.0, (y - a0) / 0.15, (a1 - y) / 0.15)


def blade_ring(y):
    w, t = blade_dims(y)
    zm, zs, ze = -0.5 * w, SHINOGI * w, 0.5 * w

    def flat(z):  # the flat above the ridge narrows slightly towards the spine
        return 0.5 * t * (1.0 - 0.2 * (zs - z) / (zs - zm))

    zg, zh = ze - 0.035 * w, hamon_z(y, w)
    za, zmid, zb = -0.25 * w, -0.31 * w, -0.37 * w
    depth = 0.45 * 0.5 * t * groove_factor(y)
    half = [
        (0.0, ze), (half_thickness(y, zg), zg), (half_thickness(y, zh), zh), (0.5 * t, zs),
        (flat(za), za), (flat(zmid) - depth, zmid), (flat(zb), zb), (flat(zm), zm),
        (0.0, zm - RIDGE),
    ]
    pts = half + [(-x, z) for x, z in reversed(half[1:-1])]
    if y > L - TIP:
        u = (y - (L - TIP)) / TIP
        f, g = 1.0 - u ** 2, 1.0 - 0.9 * u
        pts = [(x * g, zm + (z - zm) * f) for x, z in pts]
    c, zdir = frame(y)
    return [c + np.array([x, 0.0, 0.0]) + zdir * z for x, z in pts]


def build_blade():
    ys = list(np.linspace(0.0, L - TIP, 170)) + list(np.linspace(L - TIP, L - 0.002, 30))[1:]

    def tag(i, j):
        if j in (0, 15):
            return "EdgeGlow"
        if j in (1, 14):
            return "Hamon"
        if j in (4, 5, 10, 11) and groove_factor(ys[i]) > 0 and groove_factor(ys[i + 1]) > 0:
            return "Vein"
        return "Blade"

    sweep([blade_ring(y) for y in ys], "Blade", tags=tag)


def build_moons():
    """Nine moon phases inlaid on both faces of the blade, waxing to full to waning."""
    for i in range(9):
        y0 = 0.66 + i * 0.40
        w, _ = blade_dims(y0)
        r = 0.17 * w
        zc = 0.09 * w
        theta = math.pi * (i + 1) / 5 if i <= 4 else math.pi * (9 - i) / 5
        k = math.cos(theta)
        flip = 1.0 if i <= 4 else -1.0
        for side in (1.0, -1.0):
            rings = []
            for a in np.linspace(-math.pi / 2 + 0.03, math.pi / 2 - 0.03, 18):
                ring = []
                for depth, order in ((0.008, range(4)), (-0.010, range(3, -1, -1))):
                    for m in order:
                        s = m / 3
                        px = flip * r * math.cos(a) * (k + (1 - k) * s)
                        zl = zc + r * math.sin(a)
                        c, zdir = frame(y0 + px)
                        x = side * (half_thickness(y0 + px, zl) + depth)
                        ring.append(c + np.array([x, 0.0, 0.0]) + zdir * zl)
                rings.append(ring)
            sweep(rings, "Moons")


def build_habaki():
    rings = []
    for y, s in ((0.02, 1.22), (0.04, 1.30), (0.40, 1.30), (0.44, 1.10)):
        c, _ = frame(y)
        rings.append([c + (p - c) * np.array([s * 1.25, 1.0, s]) for p in blade_ring(y)])
    sweep(rings, "Habaki")


# ---------------------------------------------------------------- guard

def guard_radius(a):
    return 0.40 * (1.0 + 0.07 * math.cos(9 * a))


def build_guard():
    seg = 108
    rings = []
    for h, s in ((-0.035, 0.95), (-0.018, 1.0), (0.018, 1.0), (0.035, 0.95)):
        rings.append([
            (s * guard_radius(a) * math.cos(a), h, s * guard_radius(a) * math.sin(a))
            for a in (2 * math.pi * k / seg for k in range(seg))
        ])
    sweep(rings, "Tsuba")

    # gold rim following the nine-lobed outline
    rings = []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        r0 = guard_radius(a)
        ring = []
        for q in range(8):
            b = 2 * math.pi * q / 8
            rr = r0 + 0.030 * math.cos(b)
            ring.append((rr * math.cos(a), 0.042 * math.sin(b), rr * math.sin(a)))
        rings.append(ring)
    sweep(rings, "GuardRim", closed=True)

    lathe([(0.15, 0.030), (0.19, 0.030), (0.19, 0.052), (0.15, 0.052)], "GuardRim", seg=36)
    lathe([(0.15, -0.030), (0.15, -0.052), (0.19, -0.052), (0.19, -0.030)], "GuardRim", seg=36)

    # nine moons orbiting on the lobes
    for k in range(9):
        a = 2 * math.pi * k / 9
        r = guard_radius(a)
        sphere((r * math.cos(a), 0.0, r * math.sin(a)), 0.058, "MoonOrbs")

    # great crescent cradling the base of the blade, horns pointing at the tip
    lune((0.0, 0.58, 0.0), Y, Z, X, R=0.56, r=0.52, d=0.24, thick=0.078,
         name="MoonGuard", steps=56, inlay="CrownGem")


# ---------------------------------------------------------------- handle

def ellipse_ring(y, sx, sz, seg=32):
    return [(HA * sx * math.cos(2 * math.pi * k / seg), y, HB * sz * math.sin(2 * math.pi * k / seg))
            for k in range(seg)]


def handle_scale(y):
    u = (y - H_TOP) / (H_BOT - H_TOP)
    return 1.0 - 0.07 * math.sin(math.pi * u)


def build_handle():
    ys = np.linspace(H_TOP, H_BOT, 24)
    sweep([ellipse_ring(y, handle_scale(y), handle_scale(y)) for y in ys], "Tsuka")

    sweep([ellipse_ring(y, s, s) for y, s in
           ((-0.030, 1.10), (-0.045, 1.18), (-0.20, 1.18), (-0.225, 1.08))], "Fuchi")

    sweep([ellipse_ring(y, s, s) for y, s in
           ((-1.455, 1.08), (-1.475, 1.18), (-1.58, 1.18), (-1.615, 1.05),
            (-1.640, 0.75), (-1.652, 0.35))], "Kashira")

    # ito: two opposite helical bands crossing on the wide faces -> diamond pattern
    y_a, y_b, turns, half_w = -0.24, -1.44, 6.0, 0.036
    steps = int(turns * 44)
    for direction in (1.0, -1.0):
        rings = []
        for i in range(steps + 1):
            u = i / steps
            y = y_a + (y_b - y_a) * u
            phi = direction * 2 * math.pi * turns * u
            s = handle_scale(y)
            p = np.array([HA * s * math.cos(phi), y, HB * s * math.sin(phi)])
            n = unit(np.array([math.cos(phi) / HA, 0.0, math.sin(phi) / HB]))
            up = np.array([0.0, half_w, 0.0])
            lift = 0.016 if direction > 0 else 0.013
            rings.append([p + up + n * lift, p - up + n * lift, p - up - n * 0.01, p + up - n * 0.01])
        sweep(rings, "Ito")

    # crescent pommel cradling the crown gem
    lune((0.0, -1.81, 0.0), -Y, Z, X, R=0.17, r=0.15, d=0.08, thick=0.036, name="Kashira", steps=36)
    sphere((0.0, -1.875, 0.0), 0.058, "CrownGem")

    # tassel: cord, gold bead and tuft
    cord = [(0.05 * math.sin(5 * u), -1.60 - 0.55 * u, -0.13 - 0.20 * math.sin(2.4 * u) - 0.04 * u)
            for u in np.linspace(0.0, 1.0, 36)]
    tube(cord, 0.014, "Ito")
    end = np.array(cord[-1])
    sphere(end, 0.042, "Kashira", seg=12, stacks=7)
    lathe([(0.014, 0.0), (0.052, -0.07), (0.046, -0.26), (0.002, -0.31)], "Ito",
          center=end + np.array([0.0, -0.03, 0.0]), seg=14)


# ---------------------------------------------------------------- effects

def build_aura():
    """Two tapered energy ribbons spiralling up the blade and past the tip."""
    for phase in (0.0, math.pi):
        def pos(u):
            y = 0.55 + (L + 0.20 - 0.55) * u
            c, zdir = frame(y)
            phi = phase + 2 * math.pi * 1.7 * u ** 1.25
            rho = 0.42 - 0.20 * u + 0.035 * math.sin(7.0 * u + phase)
            er = math.cos(phi) * X + math.sin(phi) * zdir
            return c + rho * er, er

        rings, n = [], 170
        for i in range(n + 1):
            u = i / n
            p, er = pos(u)
            t = unit(pos(u + 1e-3)[0] - p)
            b = unit(np.cross(t, er))
            taper = math.sin(math.pi * u) ** 0.7
            wd, th = 0.034 * taper + 0.002, 0.009 * taper + 0.001
            rings.append([p + b * wd, p + er * th, p - b * wd, p - er * th])
        sweep(rings, "MoonAura")


def build_halo():
    """Tilted ring of nine crescent moons orbiting the blade above the guard.

    The ring is the outermost geometry so the part's bounding-box centre is the spin centre.
    """
    c, _ = frame(HALO_Y)
    n = math.sin(HALO_TILT) * X + math.cos(HALO_TILT) * Y
    e1, e2 = Z, np.cross(n, Z)
    R = 0.84
    rings = []
    for k in range(96):
        a = 2 * math.pi * k / 96
        er = math.cos(a) * e1 + math.sin(a) * e2
        rings.append([c + er * (R + 0.013 * math.cos(b)) + n * 0.013 * math.sin(b)
                      for b in (2 * math.pi * q / 6 for q in range(6))])
    sweep(rings, "MoonHalo", closed=True)
    for k in range(9):
        a = 2 * math.pi * k / 9
        er = math.cos(a) * e1 + math.sin(a) * e2
        et = -math.sin(a) * e1 + math.cos(a) * e2
        lune(c + er * 0.71, et, er, n, R=0.105, r=0.090, d=0.048, thick=0.020,
             name="MoonHalo", steps=22)


# ---------------------------------------------------------------- export

def finalize(name, crease_deg=42.0):
    """Merge pieces, weld vertices and compute crease-aware corner normals."""
    verts, faces, offset = [], [], 0
    for v, f in objects[name]:
        verts.append(v)
        faces.append(f + offset)
        offset += len(v)
    verts, faces = np.vstack(verts), np.vstack(faces)
    uniq, inverse = np.unique(np.round(verts, 5), axis=0, return_inverse=True)
    faces = inverse.reshape(-1)[faces]
    tri = uniq[faces]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(cross, axis=1)
    keep = area > 1e-9
    faces, cross, area = faces[keep], cross[keep], area[keep]
    fnorm = cross / area[:, None]

    used, remap = np.unique(faces, return_inverse=True)
    verts, faces = uniq[used], remap.reshape(faces.shape)

    adjacency = [[] for _ in range(len(verts))]
    for fi, face in enumerate(faces):
        for vi in face:
            adjacency[vi].append(fi)
    cos_crease = math.cos(math.radians(crease_deg))
    normals, normal_index, corner_normals = [], {}, np.zeros_like(faces)
    for fi, face in enumerate(faces):
        for ci, vi in enumerate(face):
            adj = np.array(adjacency[vi])
            sel = adj[fnorm[adj] @ fnorm[fi] > cos_crease]
            n = (cross[sel]).sum(axis=0)
            n /= np.linalg.norm(n)
            key = tuple(np.round(n, 4))
            if key not in normal_index:
                normal_index[key] = len(normals)
                normals.append(key)
            corner_normals[fi, ci] = normal_index[key]
    return verts, faces, np.array(normals), corner_normals, fnorm


def write_obj(path, parts, mtl_name):
    v_off = n_off = 1
    with open(path, "w") as fh:
        fh.write("# King of the Nine Moons katana - generated by tools/generate_katana.py\n")
        fh.write(f"# units: studs, +Y blade direction, +Z cutting edge\nmtllib {mtl_name}\n")
        for name, (verts, faces, normals, corner_normals, _) in parts.items():
            fh.write(f"o {name}\ng {name}\nusemtl {name}\n")
            for v in verts:
                fh.write(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}\n")
            for n in normals:
                fh.write(f"vn {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}\n")
            for f, cn in zip(faces, corner_normals):
                fh.write("f " + " ".join(f"{a + v_off}//{b + n_off}" for a, b in zip(f, cn)) + "\n")
            v_off += len(verts)
            n_off += len(normals)


def write_mtl(path):
    with open(path, "w") as fh:
        for name, (r, g, b) in MATERIALS.items():
            fh.write(f"newmtl {name}\nKd {r:.3f} {g:.3f} {b:.3f}\nKa 0 0 0\n")
            if name in EMISSIVE:
                fh.write(f"Ke {r:.3f} {g:.3f} {b:.3f}\n")
            fh.write("Ks 0.5 0.5 0.5\nNs 80\nillum 2\n\n")


def build():
    build_blade()
    build_moons()
    build_habaki()
    build_guard()
    build_handle()
    build_aura()
    build_halo()
    return {name: finalize(name) for name in MATERIALS}


def main():
    parts = build()
    os.makedirs(os.path.join(OUT_DIR, "parts"), exist_ok=True)
    write_mtl(os.path.join(OUT_DIR, f"{NAME}.mtl"))
    write_obj(os.path.join(OUT_DIR, f"{NAME}.obj"), parts, f"{NAME}.mtl")
    for name, data in parts.items():
        write_obj(os.path.join(OUT_DIR, "parts", f"{name}.obj"), {name: data}, f"../{NAME}.mtl")
    total = 0
    for name, (verts, faces, *_rest) in parts.items():
        lo, hi = verts.min(axis=0), verts.max(axis=0)
        total += len(faces)
        print(f"{name:9s} tris={len(faces):5d} verts={len(verts):5d} "
              f"bbox=({lo[0]:.2f},{lo[1]:.2f},{lo[2]:.2f})..({hi[0]:.2f},{hi[1]:.2f},{hi[2]:.2f})")
    print(f"total triangles: {total}")


if __name__ == "__main__":
    main()
