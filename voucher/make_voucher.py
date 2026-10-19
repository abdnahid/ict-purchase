"""Render a Star-World invoice (A5) from a JSON case file to HTML + PDF.

Usage: python3 voucher/make_voucher.py voucher/demo.json [-o output/voucher-demo.pdf]

Optional images are picked up from private/ (git-ignored) when present:
  starworld_logo.png, starworld_sign.png, attestation.png, my_sign.png, my_seal.png
"""
import argparse
import base64
import json
import mimetypes
import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "private"
ASSETS = {
    "logo": "starworld_logo.png",
    "vendor_sign": "starworld_sign.png",
    "attestation": "attestation.png",
    "my_sign": "my_sign.png",
    "my_seal": "my_seal.png",
}

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


def build(case):
    items = case["items"]
    for it in items:
        if it.get("amount") is None:
            it["amount"] = (it.get("qty") or 1) * it["rate"]
    total = sum(it["amount"] for it in items)
    advance = case.get("advance", 0)
    case.update(total=total, advance=advance, balance=total - advance, total_words=taka_in_words(total))
    return case


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()

    case = build(json.loads(Path(args.case).read_text(encoding="utf-8")))
    out_pdf = Path(args.out or ROOT / "output" / f"voucher-{case['sl_no']}.pdf").resolve()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    assets = {k: data_uri(PRIVATE / f) for k, f in ASSETS.items() if (PRIVATE / f).exists()}
    env = Environment(loader=FileSystemLoader(Path(__file__).parent), autoescape=True)
    html = env.get_template("template.html").render(v=case, assets=assets, money=money,
                                              filler_mm=max(30, 64 - 11 * len(case["items"])))
    out_html = out_pdf.with_suffix(".html")
    out_html.write_text(html, encoding="utf-8")

    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={out_pdf}", out_html.as_uri()],
                   check=True, capture_output=True)
    print(f"total {money(case['total'])}/= ({case['total_words']})")
    print("wrote", out_pdf)


if __name__ == "__main__":
    main()
