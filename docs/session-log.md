# Session log

## 2026-10-17: Session 1 (discovery)

**Done**
- Reviewed all three sample cases (demand, voucher, note, pass letter) by rendering them to images.
- Documented the full workflow, actors, text templates, the VAT/tax formula and the errors in the samples in `docs/workflow.md`.
- Created `CLAUDE.md` and initialized git.

**Proposed automation (not yet built)**
- Input: the demand scan, the voucher scan and a few fields (unit, room, fault, part, amount, note no., memo serial).
- Output:
  - Voucher fill-in text: line items, total in English words, Bangla certificate.
  - Para X.0 and Para X.2 text, ready to paste into D-Nothi.
  - The calculation table, to check against the audit branch's figures.
  - The মঞ্জুরিপত্র, with the Bengali date and the amount in words.
  - A case log with status tracking.
- Optional: AI extraction (Claude vision) from the scans to pre-fill the form, which the user then confirms.

**Open questions (waiting for the user)**
1. **Voucher gross-up.** Does the user start from the actual amount paid and inflate the voucher total so the reimbursement after deductions covers it (total ≈ paid × 1.15 / 0.98)? How is the total split between the part and the service charge?
2. **Output format.** Text to paste into D-Nothi, or also DOCX/PDF? Does D-Nothi generate the pass-letter PDF itself (the sample PDFs come from wkhtmltopdf, which suggests it does)?
3. **Input method.** AI reading the scans, a manual form, or both (recommended)?
4. **Platform.** Local web app, desktop script or other? Should the tool track note numbers and memo serials, or should the user enter them?

**Next step:** get answers to the questions above, then pick a stack and build the generator.
