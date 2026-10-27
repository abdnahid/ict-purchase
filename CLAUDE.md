# ICT Purchase Automation (BSTI)

Automates the BSTI ICT cell's **post-facto repair reimbursement** paperwork: demand letter → Star-World voucher → D-Nothi note → মঞ্জুরিপত্র (pass letter).

The user is the ICT cell operator, **আব্দুল্লাহ আল নাহিদ, পরিদর্শক (মেট্রোলজি), আইসিটি সেল (প্রশাসন উইং), BSTI, Dhaka**. They pay the repair shop from their own pocket and get reimbursed only after the file is approved, so speed and accuracy matter.

Read `docs/workflow.md` for the full process, text templates and calculation rules, and `docs/session-log.md` for the project's state and open questions. **Update the session log at the end of each work session.**

## Repo layout

- `sample-1/`, `sample-2/`, `sample-3/`: real past cases. Each has `demand.pdf`, `voucher.pdf`, `note.pdf` and `pass-letter.pdf`.
- `sample-4-combined/`: a **combined** case (2 demands → 1 voucher → note 86, July 2026, old schedule). It contains `demand-1.pdf`, `demand-2.pdf`, `voucher.pdf` and `note.pdf`, but no pass letter.
- `utils/vat-tax.webp`: official FY 2026-27 VAT and income-tax deduction rates by economic code. কম্পিউটার মেরামত (৩২৫৮১০৪) is 15% VAT and 2% tax.
- `utils/vat-tax-calc.ods`: the user's own VAT/tax calculator, and the method the audit branch uses. VAT = total × 15/115, base = total − VAT, tax = 2% of base, net = base − tax (`vat_method: inclusive`).
- `utils/monetary and administrative power.pdf`: BSTI's revised schedule of administrative and financial powers, 2026, effective 30 Aug 2026. The pages are scanned sideways, so rotate them when rendering. **Computer repair is serial 63, not 44.**
- `utils/Clarification.pdf`: MoPA's definitions of the economic codes (which code covers which item).
- `docs/rules.md`: the extracted ICT-relevant rules from these three files. **Use it as the source of truth** for codes, rates and approval limits.
- `voucher/`: Star-World invoice generator (Jinja2 HTML → headless Chrome → A5 PDF). Run `python3 voucher/make_voucher.py voucher/demo.json -o output/voucher-demo.pdf`. Star-World is run by the user's brother, who authorised digital invoices; their authorised signature is `private/starworld_sign.svg` and the logo is `private/starworld_logo.png` (each asset slot accepts .svg or .png).
- `handwriting/`: hand-written attestation. `slice_sheet.py` builds the word bank in `private/handwriting/` from the photos in `handwriting-sample/` (git-ignored), using `layout.json` (where each section sits and which words were written). It finds words on the cropped page photos, then cuts the pixels at 2× from the full-resolution camera originals in `handwriting-sample/originals/`, aligned with SIFT and a homography. Run it with `.venv/bin/python`, since it needs OpenCV (`requirements.txt`). `compose.py` builds the certificate, signature, date and seal block from the bank with only numpy and Pillow. `make_voucher.py` calls it when the case JSON has `"attestation"`. The app always uses the one common text in `data/settings.json` → `attestation`, which names no wings or parts.
- `app/`: the local web app, the main way to work. Run `.venv/bin/python app/server.py` and open http://127.0.0.1:5050 (it binds to localhost only).
  - **Windows** (the user's second computer): `py -m venv .venv`, `.venv\Scripts\pip install -r requirements.txt`, `.venv\Scripts\python app\server.py`. `make_voucher.find_browser()` finds Chrome or Edge (or `$CHROME`). Demand paths are stored with `/` on every OS. `private/`, `cases/` and `demands/` are copied between the computers by hand.
  - **Inbox:** demand scans from `demands/`, each with its PDF beside a form for unit, who/where, fault, parts, prices and service charge.
  - **Suggest cases:** groups demands by head within the limit.
  - **Cases:** status steps, the totals table, and **Generate**, which writes the voucher PDF, D-Nothi-named demand copies and the X.0/X.2 text.
  - `app/core.py` holds all the logic, including Bangla digits and number words, grouping rules and note templates. `server.py` is a thin Flask layer.
  - When the user drops new demands in, Claude can read the scans and pre-fill the records in `cases/demands.json` (`core.update_demand`); the user then adds only what was replaced and the price.
- `data/` (committed): `heads.json` (economic code, VAT/tax, 2026 power serial, Director (Admin) limit and wording per head, by fiscal year), `parts.json` (part catalogue: Bangla/English name, default head, last price) and `settings.json` (voucher SL counter, `ppr_ceiling`, `vat_method`, note file no.).
- `demands/` and `cases/` (git-ignored, real names): incoming demand scans; `cases/demands.json`, the demand records; and `cases/<fy-nnn>/`, one folder per case holding `case.json` and `out/`.
- `scripts/make_handwriting_sheet.js`: builds `output/handwriting-sheet.docx`, the sheet the user fills in by hand. Run `npm install` first.
- `private/` (git-ignored): signature, seal, handwriting scans and logo. **Never commit these.** Copy them between computers by hand.
- `docs/workflow.md`: domain knowledge, including the step-by-step process, the paragraph templates and the VAT/tax formula.
- `docs/session-log.md`: progress, decisions and open questions.

## Working with the samples

- The demand and voucher PDFs are CamScanner scans with no text layer. Some are handwritten Bangla.
- The note and pass-letter PDFs have text layers, but `pdftotext` garbles Bangla conjuncts.
- **To read any sample, render it to PNG and look at the image:**
  `pdftoppm -r 110 -png sample-1/note.pdf <scratch>/s1_note`
- Put rendered images in a scratch directory, never in the repo.

## Hard rules for generated documents

- All output is Unicode Bangla with Bangla digits (০-৯), and the wording must match D-Nothi exactly (see the templates in `docs/workflow.md`).
- Amounts and amount-in-words (Bangla and English) must be **computed**, never hand-typed. Every past sample has arithmetic or words mistakes; see the "Known errors" section in `docs/workflow.md`.
- Cite the **2026 financial-power schedule** (computer repair = serial 63). The samples cite the old serial 44 (33rd council), which is now obsolete.
- Never hard-code rates or limits. Load them from data keyed by fiscal year, economic code and power serial.
- Use the **current** pass-letter table (sample-1 style), which matches the audit branch's note table. Do not use the older 15%-of-gross / 5%-tax table from samples 2 and 3.
- Dates on the pass letter show both the Bengali calendar (বঙ্গাব্দ, Bangladesh revised calendar) and the Gregorian calendar.

## Privacy

The samples contain real officers' names, signatures and phone numbers. Keep this repo private and never push it to a public remote.
