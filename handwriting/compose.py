"""Compose the voucher attestation from the word-image bank built by slice_sheet.py.

Usage: python3 handwriting/compose.py "প্রত্যয়ন করা যাইতেছে যে, ... হয়েছে।" --date 17/10/2026 [-o private/attestation.png] [--seed 7]

The block mirrors a hand-filled voucher: the certificate text wrapped to a few lines, the short
signature below it with the date written across the signature line, and the name seal underneath.
When the user has written the whole sentence out (slice_paragraphs.py), that paragraph is used as
it is; otherwise every word is a real handwriting sample, picked at random from its variants, set
upright at one size on a straight line, with only the spacing varying. Needs only numpy and Pillow.
"""
import argparse
import json
import random
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "private" / "handwriting"
INK = (28, 30, 44)          # one ballpoint colour for every word, whatever the photo lighting was
PUNCT = (",", "।")


class Bank:
    def __init__(self, folder=BANK):
        self.folder = Path(folder)
        index = json.loads((self.folder / "bank.json").read_text(encoding="utf-8"))
        self.items = {k: [v for v in vs if not v.get("outlier")] for k, vs in index.items()}
        self.height = {k: float(np.median([v["h"] for v in vs])) for k, vs in self.items.items() if vs}
        self.matra = {k: float(np.median([v["matra"] for v in vs])) for k, vs in self.items.items() if vs}
        self.ref_h = float(np.median([self.height[k] for k in self.items if k not in ("sign", "seal") and not k.isdigit()]))
        self.derived = {}
        if "," not in self.items:
            self.derive_comma()
        pfile = self.folder / "paragraphs" / "paragraphs.json"
        self.paragraphs = json.loads(pfile.read_text(encoding="utf-8")) if pfile.exists() else []

    def paragraph(self, text, rng):
        """One of the user's whole hand-written copies of exactly this text, scaled to the bank's word size (None if
        they haven't written it out): straight lines, even size and their own spacing, unlike assembled words."""
        text = unicodedata.normalize("NFC", text)
        found = [p for p in self.paragraphs if p["text"] == text]
        if not found:
            return None
        p = rng.choice(found)
        img = Image.open(self.folder / "paragraphs" / p["file"]).convert("RGBA")
        k = self.ref_h / p["word_h"]
        return ink(img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS))

    def derive_comma(self):
        """No comma was written on its own, so cut the real one off the end of each "যে," sample."""
        for v in self.items.get("যে,", []):
            img = Image.open(self.folder / v["file"]).convert("RGBA")
            alpha = np.asarray(img)[:, :, 3]
            blobs = [b for b in ink_blobs(alpha > 60) if b[2] - b[0] < img.width * 0.4]
            # the comma: the right-most separate stroke that sits in the lower part of the word
            blobs = [b for b in blobs if b[0] > img.width * 0.55 and b[1] > img.height * 0.35]
            if not blobs:
                continue
            x0, y0, x1, y1, mask = max(blobs, key=lambda b: b[2])
            px = np.asarray(img).copy()
            near = mask.copy()  # grow by a pixel so the soft pen edge comes along
            near[1:] |= mask[:-1]; near[:-1] |= mask[1:]; near[:, 1:] |= mask[:, :-1]; near[:, :-1] |= mask[:, 1:]
            px[:, :, 3] = np.where(near, alpha, 0)  # drop overhanging strokes of the letter
            crop = Image.fromarray(px).crop((x0, y0, x1 + 1, y1 + 1))
            key = f"{v['file']}#comma"
            self.derived[key] = crop
            self.items.setdefault(",", []).append({"file": key, "h": crop.height, "w": crop.width, "matra": 0.0})
        if self.items.get(","):
            self.height[","] = float(np.median([v["h"] for v in self.items[","]]))
            self.matra[","] = 0.0

    def tokens(self, text):
        """Split text into bank labels, peeling trailing punctuation off words that were only written bare."""
        out, missing = [], []
        for word in unicodedata.normalize("NFC", text).split():
            tail = []
            while word not in self.items and word and word[-1] in PUNCT:
                tail.insert(0, word[-1])
                word = word[:-1]
            if word not in self.items:
                missing.append(word)
            out += [word] + tail
        if missing:
            raise KeyError("no handwriting sample for: " + " ".join(dict.fromkeys(missing)))
        return out

    def pick(self, label, rng, used):
        """A random variant, avoiding ones already used in this block when possible."""
        vs = self.items[label]
        fresh = [v for v in vs if v["file"] not in used] or vs
        v = rng.choice(fresh)
        used.add(v["file"])
        if v["file"] in self.derived:
            return v, self.derived[v["file"]].copy()
        return v, Image.open(self.folder / v["file"]).convert("RGBA")


def ink_blobs(on):
    """Connected ink strokes of a boolean mask (8-neighbour): [(x0, y0, x1, y1, mask), ...]."""
    seen = np.zeros_like(on)
    h, w = on.shape
    out = []
    for y, x in zip(*np.nonzero(on)):
        if seen[y, x]:
            continue
        stack, mask = [(y, x)], np.zeros_like(on)
        seen[y, x] = mask[y, x] = True
        while stack:
            cy, cx = stack.pop()
            for ny in range(max(cy - 1, 0), min(cy + 2, h)):
                for nx in range(max(cx - 1, 0), min(cx + 2, w)):
                    if on[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = mask[ny, nx] = True
                        stack.append((ny, nx))
        ys, xs = np.nonzero(mask)
        if len(ys) > 8:  # ignore specks
            out.append((xs.min(), ys.min(), xs.max(), ys.max(), mask))
    return out


def ink(img, colour=INK):
    """Recolour a word to the common pen colour, keeping its alpha (stroke texture)."""
    a = img.getchannel("A")
    out = Image.new("RGBA", img.size, colour + (0,))
    out.putalpha(a)
    return out


def jitter(img, rng, scale, tilt=1.2):
    w, h = img.size
    img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    return img.rotate(rng.uniform(-tilt, tilt), resample=Image.BICUBIC, expand=True)


def write_lines(bank, text, max_w, rng, used):
    """Lay the words out on lines. Bangla words hang from their headline (মাত্রা); returns (placements, width, height)."""
    ref = bank.ref_h
    pitch = ref * 1.45
    placed, x, line = [], 0.0, 0
    for tok in bank.tokens(text):
        v, img = bank.pick(tok, rng, used)
        scale = bank.height[tok] / v["h"]  # every variant at its word's typical size: no random size, no tilt
        if tok == "।":
            scale *= 0.8
        img = jitter(ink(img), rng, scale, tilt=0)
        w, h = img.size
        if tok in PUNCT:
            gap = rng.uniform(0.04, 0.12) * ref
        else:
            gap = rng.uniform(0.24, 0.4) * ref if x else 0
            if x and x + gap + w > max_w:  # wrap
                line, x, gap = line + 1, 0.0, 0
        x += gap
        top_line = line * pitch + rng.uniform(-0.01, 0.01) * ref  # where the headline runs: straight
        if tok == "।":
            y = top_line - 0.05 * ref
        elif tok == ",":
            y = top_line + 0.55 * ref
        else:
            m = v["matra"] if abs(v["matra"] - bank.matra[tok]) < 0.12 else bank.matra[tok]
            y = top_line - m * h
        placed.append((img, x, y))
        x += w
    return placed


def write_digits(bank, text, rng, used, height, rise=0.0):
    """A date or number in the hand-written digits, bottoms on one line (climbing `rise` per unit of x)."""
    placed, x = [], 0.0
    for ch in text:
        if ch == " ":
            x += 0.4 * height
            continue
        v, img = bank.pick(ch, rng, used)
        img = jitter(ink(img), rng, height / bank.height["1"] * rng.uniform(0.97, 1.03), tilt=0.8)
        placed.append((img, x, -img.size[1] - rise * x + rng.uniform(-0.04, 0.04) * height))
        x += img.size[0] + rng.uniform(0.02, 0.12) * height
    return placed


def paste_all(canvas, placed, dx, dy):
    for img, x, y in placed:
        canvas.alpha_composite(img, (round(x + dx), round(y + dy)))


def bounds(placed):
    xs = [x for _, x, _ in placed] + [x + im.size[0] for im, x, _ in placed]
    ys = [y for _, _, y in placed] + [y + im.size[1] for im, _, y in placed]
    return min(xs), min(ys), max(xs), max(ys)


def compose(text, date=None, sign=True, seal=True, width_words=7, seed=None, bank=None, word_px=74):
    """Return the attestation block as a transparent PIL image, scaled so a typical word is `word_px` tall
    (74 px ≈ 500 dpi once the block is fitted into the voucher's attestation box).
    Under the text, on the left: the signature with the date climbing across its underline, and the name seal
    under that, tilted a little (as on the user's hand-written voucher, 2026-10-27). Nothing goes right of the
    text, so the block stays clear of the vendor's signature on the voucher."""
    rng = random.Random(seed)
    bank = bank or Bank()
    used = set()
    para = bank.paragraph(text, rng)
    lines = [(para, 0, 0)] if para else write_lines(bank, text, bank.ref_h * width_words * 2.3, rng, used)
    x0, y0, x1, y1 = bounds(lines)
    parts = [(lines, -x0, -y0)]
    top = y1 - y0 + bank.ref_h * 0.5  # where the signature row starts
    text_w = x1 - x0
    sx, bottom = text_w * rng.uniform(0.06, 0.12), top

    if sign and bank.items.get("sign"):
        v, img = bank.pick("sign", rng, used)
        img = jitter(ink(img), rng, bank.ref_h * 1.7 / v["h"] * rng.uniform(0.97, 1.03), tilt=1.5)
        parts.append(([(img, 0, 0)], sx, top))
        bottom = top + img.size[1]
        if date:  # written across the signature's underline, like on the real vouchers
            digits = write_digits(bank, date, rng, used, bank.ref_h * 0.62, rise=0.07)
            dx0, dy0, dx1, dy1 = bounds(digits)
            line_y = top + img.size[1] * 0.88  # the signature's underline
            dx = sx + img.size[0] * rng.uniform(0.18, 0.3) - dx0
            parts.append((digits, dx, line_y + (dy1 - dy0) * rng.uniform(0.8, 0.95)))
            bottom = line_y + (dy1 - dy0)
    if seal and bank.items.get("seal"):
        v, img = bank.pick("seal", rng, used)
        h = bank.ref_h * 3.2
        img = img.resize((round(img.size[0] * h / v["h"]), round(h)), Image.LANCZOS)
        img = img.rotate(rng.uniform(2, 6), resample=Image.BICUBIC, expand=True)
        parts.append(([(img, 0, 0)], sx + bank.ref_h * rng.uniform(-0.3, 0.5), bottom + bank.ref_h * 0.2))  # under the signature

    pad = round(bank.ref_h * 0.15)
    boxes = [bounds([(im, x + dx, y + dy) for im, x, y in pl]) for pl, dx, dy in parts]
    W = int(max(b[2] for b in boxes) - min(0, min(b[0] for b in boxes))) + 2 * pad
    H = int(max(b[3] for b in boxes)) + 2 * pad
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for pl, dx, dy in parts:
        paste_all(canvas, pl, dx + pad, dy + pad)
    k = word_px / bank.ref_h
    if abs(k - 1) > 0.05:
        canvas = canvas.resize((round(W * k), round(H * k)), Image.LANCZOS)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--date", help="written under the signature, e.g. 17/10/2026")
    ap.add_argument("-o", "--out", default=ROOT / "private" / "attestation.png", type=Path)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--no-sign", action="store_true")
    ap.add_argument("--no-seal", action="store_true")
    args = ap.parse_args()
    img = compose(args.text, args.date, sign=not args.no_sign, seal=not args.no_seal, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print("wrote", args.out, img.size)


if __name__ == "__main__":
    main()
