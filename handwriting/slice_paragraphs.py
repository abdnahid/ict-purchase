"""Cut the user's whole hand-written attestations out of their photos into transparent ink images.

Usage: python3 handwriting/slice_paragraphs.py [--debug out_dir]

Reads handwriting/paragraphs.json (photo, rotation, one box per paragraph) and the photos in handwriting-sample/,
writes private/handwriting/paragraphs/pNN.png and paragraphs.json (text, file, typical word height). The paper is
flattened by dividing out a heavily blurred copy of the photo, so uneven light doesn't leave grey patches.
Needs only numpy and Pillow.
"""
import argparse
import json
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "handwriting-sample"
OUT = ROOT / "private" / "handwriting" / "paragraphs"


def ink_alpha(gray):
    """Pen strokes as alpha 0..255: darkness relative to the local paper colour."""
    paper = np.asarray(Image.fromarray(gray).filter(ImageFilter.GaussianBlur(25)), dtype=float) + 1
    ratio = gray.astype(float) / paper
    return (np.clip((0.88 - ratio) / 0.2, 0, 1) * 255).astype(np.uint8)  # steep: a solid ballpoint core


def despeckle(alpha, min_px=40):
    """Drop dust: ink blobs smaller than min_px pixels (a full stop or the dot of ড় is far bigger)."""
    on = alpha > 60
    seen = np.zeros_like(on)
    h, w = on.shape
    for y, x in zip(*np.nonzero(on)):
        if seen[y, x]:
            continue
        stack, blob = [(y, x)], [(y, x)]
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            for ny in range(max(cy - 1, 0), min(cy + 2, h)):
                for nx in range(max(cx - 1, 0), min(cx + 2, w)):
                    if on[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
                        blob.append((ny, nx))
        if len(blob) < min_px:
            ys, xs = zip(*blob)
            alpha[list(ys), list(xs)] = 0
    return alpha


def line_bands(alpha, n):
    """Split the paragraph into its n lines at the emptiest row between them (lines may touch: a tall letter
    of one line can reach into the line above, so a clean gap isn't guaranteed)."""
    profile = np.convolve((alpha > 90).sum(1), np.ones(5) / 5, mode="same")
    H, cuts = len(profile), [0]
    for i in range(1, n):
        lo, hi = int(H * (i - 0.35) / n), int(H * (i + 0.35) / n)
        cuts.append(lo + int(np.argmin(profile[lo:hi])))
    return list(zip(cuts, cuts[1:] + [H]))


def word_height(alpha, n_lines):
    """Median height of the words: each line band, then words from column gaps within it."""
    on = alpha > 90
    heights = []
    for y, y1 in line_bands(alpha, n_lines):
        band = on[y:y1]
        cols = band.sum(0) > 0
        x = 0
        while x < len(cols):
            if not cols[x]:
                x += 1
                continue
            x1 = x
            while x1 < len(cols) and cols[x1:x1 + 12].any():  # gaps inside a word are narrower than between words
                x1 += 1
            ys = np.nonzero(band[:, x:x1].any(1))[0]
            if x1 - x > 25 and len(ys):
                heights.append(ys[-1] - ys[0] + 1)
            x = x1
    return float(np.median(heights)) if heights else float(alpha.shape[0] / n_lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", type=Path, help="also save each cut on white for checking")
    args = ap.parse_args()
    cfg = json.loads((Path(__file__).parent / "paragraphs.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for src in cfg["sources"]:
        photo = Image.open(SAMPLES / src["photo"]).rotate(src.get("rotate", 0), expand=True).convert("L")
        for p in src["paragraphs"]:
            gray = np.asarray(photo.crop(tuple(p["box"])))
            alpha = despeckle(ink_alpha(gray))
            ys, xs = np.nonzero(alpha > 60)
            pad = 6
            alpha = alpha[max(ys.min() - pad, 0):ys.max() + pad, max(xs.min() - pad, 0):xs.max() + pad]
            img = Image.new("RGBA", (alpha.shape[1], alpha.shape[0]), (28, 30, 44, 0))
            img.putalpha(Image.fromarray(alpha))
            name = f"p{len(index) + 1:02d}.png"
            img.save(OUT / name)
            index.append({"text": unicodedata.normalize("NFC", p["text"]), "file": name,
                          "word_h": word_height(alpha, p["lines"]), "w": img.width, "h": img.height})
            if args.debug:
                args.debug.mkdir(parents=True, exist_ok=True)
                Image.alpha_composite(Image.new("RGBA", img.size, "white"), img).convert("RGB").save(args.debug / name)
            print(name, img.size, "word_h", round(index[-1]["word_h"], 1), p["text"][:40])
    (OUT / "paragraphs.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
