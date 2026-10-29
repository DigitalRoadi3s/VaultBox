#!/usr/bin/env python
"""Render 360x360 RGBA isometric thumbnails for every STL under parts/ (numpy splat z-buffer)."""
import os, sys, time, math, re, traceback
import numpy as np
from PIL import Image
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "parts")
DST = os.path.join(ROOT, "assets", "thumbs")
ERRLOG = os.path.join(ROOT, "tools", "thumbs_errors.log")
S = 360
MARGIN = 0.08
MAXTRI = 1_500_000
BASE = np.array([190, 205, 225], np.float32)
AZ, EL = math.radians(35), math.radians(30)
LIGHT = np.array([-0.5, 0.6, 0.65], np.float32); LIGHT /= np.linalg.norm(LIGHT)
DT = np.dtype([("n", "<f4", 3), ("v", "<f4", 9), ("a", "<u2")])


def load(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        head = f.read(84)
    cnt = int.from_bytes(head[80:84], "little") if len(head) >= 84 else 0
    if len(head) >= 84 and 84 + 50 * cnt == size and cnt > 0:
        mm = np.memmap(path, dtype=DT, mode="r", offset=84, shape=(cnt,))
        if cnt > MAXTRI:
            idx = np.sort(np.random.default_rng(0).choice(cnt, MAXTRI, replace=False))
            v = np.asarray(mm["v"][idx])
        else:
            v = np.array(mm["v"])
        return v.reshape(-1, 3, 3).astype(np.float32)
    if head[:5].lower() == b"solid":
        txt = open(path, "r", errors="ignore").read()
        nums = re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", txt)
        a = np.array(nums, dtype=np.float32).reshape(-1, 3, 3)
        if len(a) > MAXTRI:
            a = a[np.random.default_rng(0).choice(len(a), MAXTRI, replace=False)]
        return a
    raise ValueError("unrecognised STL (size %d, count %d)" % (size, cnt))


def render(tris):
    ca, sa, ce, se = math.cos(AZ), math.sin(AZ), math.cos(EL), math.sin(EL)
    x, y, z = tris[..., 0], tris[..., 1], tris[..., 2]
    x1 = x * ca - y * sa
    y1 = x * sa + y * ca
    xs = x1
    ys = z * ce + y1 * se          # screen up
    zd = z * se - y1 * ce          # toward viewer (larger = nearer)
    P = np.stack([xs, ys, zd], -1)  # (N,3,3) view frame, right/up/toward
    ok = np.isfinite(P).all(axis=(1, 2))
    P = P[ok]
    if len(P) == 0:
        raise ValueError("no finite triangles")
    mn = P[..., :2].reshape(-1, 2).min(0); mx = P[..., :2].reshape(-1, 2).max(0)
    ext = float(max(mx - mn)) or 1.0
    sc = S * (1 - 2 * MARGIN) / ext
    c = (mn + mx) / 2
    px = (P[..., 0] - c[0]) * sc + S / 2
    py = S / 2 - (P[..., 1] - c[1]) * sc
    pz = P[..., 2]
    # normals in view frame
    e1 = P[:, 1] - P[:, 0]; e2 = P[:, 2] - P[:, 0]
    nrm = np.cross(e1, e2)
    ln = np.linalg.norm(nrm, axis=1)
    good = ln > 0
    nrm[good] /= ln[good, None]
    nrm[nrm[:, 2] < 0] *= -1       # two-sided
    lam = np.clip(nrm @ LIGHT, 0, 1)
    shade = (0.22 + 0.78 * lam).astype(np.float32)
    area = 0.5 * np.abs((px[:, 1] - px[:, 0]) * (py[:, 2] - py[:, 0]) - (px[:, 2] - px[:, 0]) * (py[:, 1] - py[:, 0]))
    nsub = np.where(area > 1.5, np.ceil(np.sqrt(area / 1.0)).astype(np.int32), 1)
    nsub = np.minimum(nsub, 250)

    zbuf = np.full(S * S, -np.inf, np.float32)
    sbuf = np.zeros(S * S, np.float32)

    def splat(X, Y, Z, Sh):
        for dx in (0, 1):
            for dy in (0, 1):
                ix = np.floor(X).astype(np.int32) + dx - 0
                iy = np.floor(Y).astype(np.int32) + dy - 0
                m = (ix >= 0) & (ix < S) & (iy >= 0) & (iy < S)
                if not m.any():
                    continue
                pi = iy[m] * S + ix[m]; zz = Z[m]; ss = Sh[m]
                o = np.argsort(zz, kind="stable")  # ascending; last write = nearest
                pi, zz, ss = pi[o], zz[o], ss[o]
                # last occurrence per pixel
                last = np.ones(len(pi), bool)
                srt = np.argsort(pi, kind="stable")
                p2 = pi[srt]
                lm = np.r_[p2[1:] != p2[:-1], True]
                sel = srt[lm]
                pp, z2, s2 = pi[sel], zz[sel], ss[sel]
                upd = z2 > zbuf[pp]
                zbuf[pp[upd]] = z2[upd]; sbuf[pp[upd]] = s2[upd]

    # centroids
    splat(px.mean(1), py.mean(1), pz.mean(1), shade)
    # extra barycentric samples, grouped by subdivision level
    big = np.nonzero(nsub > 1)[0]
    if len(big):
        for n in np.unique(nsub[big]):
            ids = big[nsub[big] == n]
            ii, jj = np.meshgrid(np.arange(n + 1), np.arange(n + 1), indexing="ij")
            m = ii + jj <= n
            u = (ii[m] / n).astype(np.float32); w = (jj[m] / n).astype(np.float32)
            v0 = 1 - u - w
            per = len(u)
            step = max(1, 1_500_000 // per)
            for s in range(0, len(ids), step):
                t = ids[s:s + step]
                X = px[t, 0, None] * v0 + px[t, 1, None] * u + px[t, 2, None] * w
                Y = py[t, 0, None] * v0 + py[t, 1, None] * u + py[t, 2, None] * w
                Z = pz[t, 0, None] * v0 + pz[t, 1, None] * u + pz[t, 2, None] * w
                Sh = np.broadcast_to(shade[t, None], X.shape)
                splat(X.ravel(), Y.ravel(), Z.ravel(), Sh.ravel())
    # also splat original vertices-free chunks for the small triangles done above
    hit = np.isfinite(zbuf)
    img = np.zeros((S * S, 4), np.uint8)
    rgb = np.clip(BASE[None, :] * sbuf[:, None], 0, 255)
    img[hit, :3] = rgb[hit].astype(np.uint8)
    img[hit, 3] = 255
    return img.reshape(S, S, 4)


def work(rel):
    out = os.path.join(DST, os.path.splitext(rel)[0] + ".png")
    try:
        if os.path.exists(out) and os.path.getsize(out) > 0:
            return rel, "skip", 0
        t0 = time.time()
        img = render(load(os.path.join(SRC, rel)))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        tmp = out + ".tmp.png"
        Image.fromarray(img, "RGBA").save(tmp)
        os.replace(tmp, out)
        return rel, "ok", time.time() - t0
    except Exception as e:
        return rel, "ERR " + repr(e) + " " + traceback.format_exc().splitlines()[-3].strip(), 0


def main():
    rels = []
    for d, _, fs in os.walk(SRC):
        for f in fs:
            if f.lower().endswith(".stl"):
                rels.append(os.path.relpath(os.path.join(d, f), SRC))
    rels.sort(key=lambda r: os.path.getsize(os.path.join(SRC, r)))
    print("STLs:", len(rels), flush=True)
    t0 = time.time(); n = 0; fails = 0
    with Pool(8) as p:
        for rel, st, dt in p.imap_unordered(work, rels, chunksize=1):
            n += 1
            if st.startswith("ERR"):
                fails += 1
                with open(ERRLOG, "a") as f:
                    f.write(f"{rel}\t{st}\n")
            if n % 25 == 0 or st.startswith("ERR"):
                print(f"{n}/{len(rels)} fails={fails} {time.time()-t0:.0f}s last={rel} {st}", flush=True)
    print(f"done {n} files, {fails} failures, {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
