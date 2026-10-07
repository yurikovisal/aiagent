"""Prepare still images and particle point cloud for the MEZA teaser.

Usage: python3 scripts/prep_assets.py   (run from meza-teaser/)
"""
import json
import numpy as np
from PIL import Image

SRC = "assets-src"
OUT = "public"

# 1) MEZA silhouette -> PNG + particle cloud sampled from bright pixels
sil = Image.open(f"{SRC}/meza-silhouette.webp").convert("RGB")
sil.save(f"{OUT}/meza-silhouette.jpg", quality=95)
lum = np.asarray(sil.convert("L")).astype(np.float32) / 255.0
h, w = lum.shape
rng = np.random.default_rng(7)
ys, xs = np.nonzero(lum > 0.18)
weights = lum[ys, xs] ** 1.6
weights /= weights.sum()
N = 5200
idx = rng.choice(len(xs), size=N, replace=False, p=weights)
pts = []
for i in idx:
    x = (xs[i] + rng.uniform(-0.5, 0.5)) / w - 0.5
    y = (ys[i] + rng.uniform(-0.5, 0.5)) / h - 0.5
    pts.append([round(float(x), 4), round(float(y), 4), round(float(lum[ys[i], xs[i]]), 3)])
with open(f"{OUT}/meza-points.json", "w") as f:
    json.dump(pts, f, separators=(",", ":"))

# 2) Chef portrait: remove the baked-in HUD frame lines so we can crop/zoom freely
img = np.asarray(Image.open(f"{SRC}/chef-poster.webp").convert("RGB")).astype(np.float32)
out = img.copy()
def fix_rows(y0, y1, x0, x1):
    above = img[y0 - 3, x0:x1]
    below = img[y1 + 3, x0:x1]
    for y in range(y0, y1 + 1):
        t = (y - y0 + 1) / (y1 - y0 + 2)
        out[y, x0:x1] = above * (1 - t) + below * t
def fix_cols(x0, x1, y0, y1):
    left = img[y0:y1, x0 - 3]
    right = img[y0:y1, x1 + 3]
    for x in range(x0, x1 + 1):
        t = (x - x0 + 1) / (x1 - x0 + 2)
        out[y0:y1, x] = left * (1 - t) + right * t
fix_rows(275, 279, 110, 830)
fix_rows(1322, 1326, 110, 830)
fix_cols(140, 145, 250, 1340)
fix_cols(797, 802, 250, 1340)
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(f"{OUT}/chef.jpg", quality=95)
print("points:", len(pts))
