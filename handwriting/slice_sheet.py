"""Cut the hand-written sample pages into a word-image bank.

Usage: .venv/bin/python handwriting/slice_sheet.py [--src handwriting-sample] [--out private/handwriting] [--debug DIR]

Reads handwriting/layout.json, which says where each section sits on each photo and which
words were written there (top-to-bottom, repeated in every column). Words are found on the
page photos; when the layout names a full-resolution camera original for a page, the original
is aligned to that photo and the pixels are cut from it at HI_RES× the scale. Writes transparent PNGs to
<out>/bank/<section>/ and an index <out>/bank.json: {label: [{file, h, w, matra}, ...]}.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
INK_T = 38          # background-minus-pixel difference that counts as ink
MIN_INK = 40        # ignore specks with fewer ink pixels than this
PAD = 4
HI_RES = 2          # cut scale when a camera original is available


def ink_map(bgr, k=1):
    """Return (diff, gray): diff = local background brightness minus pixel brightness (phone-photo shading removed)."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.int16)
    size = 31 * k | 1
    bg = cv2.GaussianBlur(cv2.dilate(gray.astype(np.uint8), np.ones((size, size), np.uint8)), (0, 0), 15 * k).astype(np.int16)
    return np.clip(bg - gray, 0, 255).astype(np.uint8), gray


def align_original(page_bgr, original_path, k):
    """Warp the full-resolution camera original onto the (cropped, flattened) page photo's frame, scaled by k.
    Segmentation runs on the page photo; the pixels are then cut from this sharper image. None if matching fails."""
    orig = cv2.imread(str(original_path))
    if orig is None:
        return None
    target = cv2.resize(page_bgr, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    sift = cv2.SIFT_create(nfeatures=8000)
    ka, da = sift.detectAndCompute(cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY), None)
    kb, db = sift.detectAndCompute(cv2.cvtColor(target, cv2.COLOR_BGR2GRAY), None)
    pairs = [m for m, n in cv2.FlannBasedMatcher({"algorithm": 1, "trees": 5}, {"checks": 64}).knnMatch(da, db, k=2)
             if m.distance < 0.75 * n.distance]
    if len(pairs) < 40:
        return None
    H, inl = cv2.findHomography(np.float32([ka[m.queryIdx].pt for m in pairs]),
                                np.float32([kb[m.trainIdx].pt for m in pairs]), cv2.RANSAC, 3.0 * k)
    if H is None or inl.sum() < 40:
        return None
    return cv2.warpPerspective(orig, H, (target.shape[1], target.shape[0]), flags=cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_REPLICATE), int(inl.sum())


def blobs(mask, grow):
    """Connected word blobs: dilate so the pieces of one word join, then label."""
    joined = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, grow))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(joined)
    out = []
    for i in range(1, n):
        x, y, w, h, _ = stats[i]
        if mask[y:y + h, x:x + w][lab[y:y + h, x:x + w] == i].sum() / 255 >= MIN_INK:
            out.append([x, y, x + w, y + h])
    return out


def split_columns(boxes, k):
    """Group boxes into k columns by x-centre: split at the k-1 widest gaps between sorted centres."""
    boxes = sorted(boxes, key=lambda b: (b[0] + b[2]) / 2)
    if k == 1:
        return [boxes]
    if len(boxes) <= k:
        return [[b] for b in boxes]
    cx = [(b[0] + b[2]) / 2 for b in boxes]
    cuts = sorted(sorted(range(1, len(cx)), key=lambda i: cx[i] - cx[i - 1])[-(k - 1):])
    return [boxes[a:b] for a, b in zip([0] + cuts, cuts + [len(boxes)])]


def merge_rows(col, want):
    """Within one column, merge vertically overlapping boxes, then keep merging the closest pair until `want` remain."""
    col = sorted(col, key=lambda b: b[1])
    def union(a, b):
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
    i = 0
    while i < len(col) - 1:
        a, b = col[i], col[i + 1]
        overlap = min(a[3], b[3]) - max(a[1], b[1])
        if overlap > 0.4 * min(a[3] - a[1], b[3] - b[1]):
            col[i:i + 2] = [union(a, b)]
        else:
            i += 1
    while len(col) > want:
        gaps = [col[i + 1][1] - col[i][3] for i in range(len(col) - 1)]
        i = int(np.argmin(gaps))
        col[i:i + 2] = [union(col[i], col[i + 1])]
    return col


def tighten(mask, box):
    """Shrink a box to the ink it contains."""
    x0, y0, x1, y1 = box
    ys, xs = np.nonzero(mask[y0:y1, x0:x1])
    return [x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1] if len(xs) else box


def split_tall(mask, col, want):
    """Rows that touch get merged into one blob: split the tallest box at its thinnest ink row until `want` remain."""
    col = sorted(col, key=lambda b: b[1])
    while len(col) < want:
        i = max(range(len(col)), key=lambda j: col[j][3] - col[j][1])
        x0, y0, x1, y1 = col[i]
        others = [b[3] - b[1] for j, b in enumerate(col) if j != i]
        step = (y1 - y0) / max(2, round((y1 - y0) / np.median(others))) if others else (y1 - y0) / 2
        lo, hi = int(y0 + step * 0.65), int(y0 + step * 1.35)  # look for the gap near the first expected boundary
        prof = mask[lo:hi, x0:x1].sum(1, dtype=np.float32)
        cut_y = lo + int(np.argmin(np.convolve(prof, np.ones(5) / 5, mode="same")))
        col[i:i + 1] = [tighten(mask, [x0, y0, x1, cut_y]), tighten(mask, [x0, cut_y, x1, y1])]
    return col


def line_bands(mask, want, min_gap=4):
    """Horizontal text lines in a block: runs of rows that contain ink, split further if lines touch."""
    rows = (mask.sum(1) / 255) > 3
    bands, start = [], None
    for y, on in enumerate(list(rows) + [False] * min_gap):
        if on and start is None:
            start, last = y, y
        elif on:
            last = y
        elif start is not None and y - last >= min_gap:
            bands.append([0, start, mask.shape[1], last + 1])
            start = None
    return split_tall(mask, [b for b in bands if b[3] - b[1] > 15], want)


def words_in_line(mask, line, want):
    """Split one written line at blank column runs; widen the required gap until exactly `want` words remain."""
    x0, y0, x1, y1 = line
    cols = mask[y0:y1, x0:x1].sum(0) > 0
    for gap in range(3, 60):
        runs, start, last = [], None, None
        for x, on in enumerate(list(cols) + [False] * gap):
            if on:
                start, last = (x if start is None else start), x
            elif start is not None and x - last >= gap:
                runs.append((start, last + 1))
                start = None
        runs = [r for r in runs if mask[y0:y1, x0 + r[0]:x0 + r[1]].sum() / 255 >= MIN_INK]
        if len(runs) <= want:
            return [tighten(mask, [x0 + a, y0, x0 + b, y1]) for a, b in runs]
    return []


def strokes_in(strokes, box, k=1):
    """Whole ink strokes whose centre lies in the box, so a cut never slices a letter and never drags in a
    neighbour's descender. Returns (keep mask, box grown to cover those strokes)."""
    lab, stats, cents = strokes
    x0, y0, x1, y1 = box
    pad = PAD * k
    sel = [i for i in range(1, len(stats))
           if x0 - pad <= cents[i][0] <= x1 + pad and y0 - pad <= cents[i][1] <= y1 + pad and stats[i][4] >= 6 * k * k]
    if not sel:
        return np.zeros(lab.shape, np.float32), box
    keep = cv2.dilate(np.isin(lab, sel).astype(np.uint8), np.ones((4 * k + 1, 4 * k + 1), np.uint8)).astype(np.float32)
    s = stats[sel]
    return keep, [s[:, 0].min(), s[:, 1].min(), (s[:, 0] + s[:, 2]).max(), (s[:, 1] + s[:, 3]).max()]


def cut(bgr, diff, box, kind, keep, k=1):
    """Crop a box to a transparent RGBA image, keeping only the ink in `keep`."""
    x0, y0, x1, y1 = box
    pad = PAD * k
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(bgr.shape[1], x1 + pad), min(bgr.shape[0], y1 + pad)
    d = diff[y0:y1, x0:x1].astype(np.float32)
    alpha = np.clip((d - INK_T * 0.5) / (INK_T * 1.6), 0, 1) * keep[y0:y1, x0:x1]
    rgb = bgr[y0:y1, x0:x1][:, :, ::-1].astype(np.float32)
    # one flat ink colour: the median of the strongest strokes. Pen ink is kept dark; stamp ink keeps its
    # hue but is lifted to stamp-pad brightness (a dim photo makes it look almost black).
    strong = alpha > 0.9
    colour = np.median(rgb[strong], axis=0) if strong.any() else np.array([30, 30, 40])
    if kind == "seal":
        colour = colour * (0.55 * 255 / max(colour.max(), 1))
    else:
        colour = np.minimum(colour, 90)
    rgb = np.broadcast_to(colour, rgb.shape)
    rgba = np.dstack([rgb, alpha * 255]).astype(np.uint8)
    ys, xs = np.nonzero(alpha > 0.15)  # tighten to the visible ink
    if len(xs):
        rgba = rgba[max(0, ys.min() - 2):ys.max() + 3, max(0, xs.min() - 2):xs.max() + 3]
    return rgba


def matra_row(rgba):
    """Fraction of height where the Bangla headline (মাত্রা) sits: the densest ink row in the top 65%."""
    a = rgba[:, :, 3].astype(np.float32).sum(1)
    top = max(1, int(len(a) * 0.65))
    return round(float(np.argmax(a[:top]) / max(1, len(a) - 1)), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=ROOT / "handwriting-sample", type=Path)
    ap.add_argument("--out", default=ROOT / "private" / "handwriting", type=Path)
    ap.add_argument("--debug", type=Path, help="write page overlays showing every cut")
    args = ap.parse_args()

    layout = json.loads((Path(__file__).parent / "layout.json").read_text(encoding="utf-8"))["pages"]
    bank, problems = {}, []
    (args.out / "bank").mkdir(parents=True, exist_ok=True)
    if args.debug:
        args.debug.mkdir(parents=True, exist_ok=True)

    originals = json.loads((Path(__file__).parent / "layout.json").read_text(encoding="utf-8")).get("originals", {})
    for page, blocks in layout.items():
        bgr = cv2.imread(str(args.src / page))
        diff, _ = ink_map(bgr)
        mask = np.where(diff > INK_T, 255, 0).astype(np.uint8)
        strokes = cv2.connectedComponentsWithStats(mask, connectivity=8)[1:]
        overlay = bgr.copy()
        # where the pixels come from: the aligned camera original if there is one, else the page photo
        k, src_bgr, src_diff, src_strokes = 1, bgr, diff, strokes
        if page in originals:
            aligned = align_original(bgr, args.src / originals[page], HI_RES)
            if aligned is None:
                problems.append(f"{page}: could not align {originals[page]}, cutting from the page photo")
            else:
                k, src_bgr = HI_RES, aligned[0]
                src_diff, _ = ink_map(src_bgr, k)
                src_strokes = cv2.connectedComponentsWithStats(np.where(src_diff > INK_T, 255, 0).astype(np.uint8), connectivity=8)[1:]
        for bi, blk in enumerate(blocks):
            X0, Y0, X1, Y1 = blk["box"]
            region = np.zeros_like(mask)
            region[Y0:Y1, X0:X1] = mask[Y0:Y1, X0:X1]
            cv2.rectangle(overlay, (X0, Y0), (X1, Y1), (200, 200, 0), 1)
            if blk["kind"] == "sentence":
                lines = [[X0 + x0, Y0 + y0, X0 + x1, Y0 + y1] for x0, y0, x1, y1 in line_bands(region[Y0:Y1, X0:X1], len(blk["lines"]))]
                items = []
                for li, (words, line) in enumerate(zip(blk["lines"], lines)):
                    if not words:  # line skipped in the layout (e.g. has a crossed-out word)
                        continue
                    found = words_in_line(region, line, len(words))
                    if len(found) != len(words):
                        problems.append(f"{page} sentence line {li + 1}: {len(found)} words, expected {len(words)} — skipped")
                        continue
                    items += list(zip(words, found))
            else:
                grow = (15, 15) if blk["kind"] == "seal" else (19, 9)
                cols = split_columns(blobs(region, grow), blk["cols"])
                items = []
                for ci, col in enumerate(cols):
                    col = split_tall(region, merge_rows(col, len(blk["labels"])), len(blk["labels"]))
                    if len(col) != len(blk["labels"]):
                        problems.append(f"{page} {blk['name']} column {ci + 1}: {len(col)} items, expected {len(blk['labels'])}")
                    items += [(lbl, b) for lbl, b in zip(blk["labels"], col)]
            for n, (label, box) in enumerate(items):
                _, box = strokes_in(strokes, box)
                x0, y0, x1, y1 = box
                keep, hi_box = strokes_in(src_strokes, [c * k for c in box], k)
                rgba = cut(src_bgr, src_diff, hi_box, blk["kind"], keep, k)
                rel = f"bank/{blk['name']}/{Path(page).stem}-{bi}-{n:02d}.png"
                (args.out / rel).parent.mkdir(exist_ok=True)
                cv2.imwrite(str(args.out / rel), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
                bank.setdefault(label, []).append({"file": rel, "h": rgba.shape[0], "w": rgba.shape[1], "matra": matra_row(rgba), "scale": k})
                cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 0, 255), 2)
                cv2.putText(overlay, str(n), (x0, y0 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 140, 0), 1)
        if args.debug:
            cv2.imwrite(str(args.debug / f"overlay-{Path(page).stem}.jpg"), overlay)

    for label, vs in bank.items():  # a variant much taller than its siblings picked up a stray mark
        med = np.median([v["h"] for v in vs])
        for v in vs:
            if len(vs) >= 3 and v["h"] > 1.45 * med:
                v["outlier"] = True
    (args.out / "bank.json").write_text(json.dumps(bank, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{sum(len(v) for v in bank.values())} images, {len(bank)} labels → {args.out / 'bank.json'}")
    for p in problems:
        print("CHECK:", p)


if __name__ == "__main__":
    main()
