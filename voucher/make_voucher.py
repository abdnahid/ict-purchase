"""Render a Star-World invoice (A5) from a JSON case file to HTML + PDF.

Usage: python3 voucher/make_voucher.py voucher/demo.json [-o output/voucher-demo.pdf]

Optional images are picked up from private/ (git-ignored) when present:
  starworld_logo, starworld_sign, attestation, my_sign, my_seal (.svg or .png)
If the case has an "attestation" ({"unit": ..., "part": ...} or {"text": ...}) and the handwriting bank
exists (handwriting/slice_sheet.py), the hand-written certificate is composed from it instead.
"""
import argparse
import base64
import io
import json
import mimetypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "private"
ASSETS = {
    "logo": "starworld_logo",
    "vendor_sign": "starworld_sign",
    "attestation": "attestation",
    "my_sign": "my_sign",
    "my_seal": "my_seal",
}
ASSET_EXTS = (".svg", ".png")

ATTESTATION = "প্রত্যয়ন করা যাইতেছে যে, {unit} এর কম্পিউটার মেরামতে {part} ক্রয় ও সার্ভিস চার্জ বাবদ উক্ত অর্থ ব্যয় করা হয়েছে।"

ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
        "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _below_hundred(n):
    return ONES[n] if n < 20 else (TENS[n // 10] + (" " + ONES[n % 10] if n % 10 else ""))


def _below_thousand(n):
    head = f"{ONES[n // 100]} Hundred" if n >= 100 else ""
    tail = _below_hundred(n % 100) if n % 100 else ""
    return " ".join(p for p in (head, tail) if p)


def taka_in_words(amount):
    """English words in the South-Asian system (crore / lakh / thousand), e.g. 'Four Thousand One Hundred Twenty Five Taka Only'."""
    n = int(amount)
    if n == 0:
        return "Zero Taka Only"
    parts = []
    for size, name in ((10**7, "Crore"), (10**5, "Lakh"), (10**3, "Thousand")):
        if n >= size:
            parts.append(f"{_below_thousand(n // size) if size == 10**7 else _below_hundred(n // size)} {name}")
            n %= size
    if n:
        parts.append(_below_thousand(n))
    return " ".join(parts) + " Taka Only"


def money(n):
    """Indian/Bangladeshi digit grouping: 1,25,000."""
    s = str(int(n))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def data_uri(path):
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def composed_attestation(case):
    """Hand-written certificate + signature + date + seal from the word bank, as a data URI (None if unavailable)."""
    att = case.get("attestation")
    if not att or not (PRIVATE / "handwriting" / "bank.json").exists():
        return None
    sys.path.insert(0, str(ROOT / "handwriting"))
    from compose import compose
    img = compose(att.get("text") or ATTESTATION.format(**att), date=case["date"], seed=case["sl_no"])
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def build(case):
    items = case["items"]
    for it in items:
        if it.get("amount") is None:
            it["amount"] = (it.get("qty") or 1) * it["rate"]
    total = sum(it["amount"] for it in items)
    advance = case.get("advance", 0)
    case.update(total=total, advance=advance, balance=total - advance, total_words=taka_in_words(total))
    return case


def find_browser():
    """Chrome (or Chromium / Edge, which print the same way) on Linux, macOS or Windows; $CHROME overrides."""
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        if shutil.which(name):
            return shutil.which(name)
    roots = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
    candidates = [Path(r) / sub for r in roots if r for sub in (r"Google\Chrome\Application\chrome.exe",
                                                              r"Microsoft\Edge\Application\msedge.exe")]
    candidates.append(Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))
    for c in candidates:
        if c.is_file():
            return str(c)
    raise FileNotFoundError("No Chrome or Edge found to print the voucher PDF; set the CHROME environment variable to its path.")


def render(case, out_pdf):
    """Build totals, compose the attestation and print the A5 PDF. Returns the built case."""
    case = build(case)
    out_pdf = Path(out_pdf).resolve()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    assets = {k: data_uri(path) for k, stem in ASSETS.items()
              for path in [next((PRIVATE / (stem + e) for e in ASSET_EXTS if (PRIVATE / (stem + e)).exists()), None)] if path}
    if (att := composed_attestation(case)):
        assets["attestation"] = att
    env = Environment(loader=FileSystemLoader(Path(__file__).parent), autoescape=True)
    html = env.get_template("template.html").render(v=case, assets=assets, money=money,
                                              filler_mm=12)  # minimum; the template grows it to fill the page
    out_html = out_pdf.with_suffix(".html")
    out_html.write_text(html, encoding="utf-8")
    subprocess.run([find_browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={out_pdf}", out_html.as_uri()],
                   check=True, capture_output=True)
    out_html.unlink()
    return case


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()

    case = json.loads(Path(args.case).read_text(encoding="utf-8"))
    out_pdf = Path(args.out or ROOT / "output" / f"voucher-{case['sl_no']}.pdf")
    case = render(case, out_pdf)
    print(f"total {money(case['total'])}/= ({case['total_words']})")
    print("wrote", out_pdf)


if __name__ == "__main__":
    main()
