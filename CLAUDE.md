# ICT Purchase Automation (BSTI)

Automates the BSTI ICT cell's **post-facto repair reimbursement** paperwork: demand letter → Star-World voucher → D-Nothi note → মঞ্জুরিপত্র (pass letter).

The user is the ICT cell operator, **আব্দুল্লাহ আল নাহিদ, পরিদর্শক (মেট্রোলজি), আইসিটি সেল (প্রশাসন উইং), BSTI, Dhaka**. They pay the repair shop from their own pocket and get reimbursed only after the file is approved, so speed and accuracy matter.

Read `docs/workflow.md` for the full process, text templates and calculation rules, and `docs/session-log.md` for the project's state and open questions. **Update the session log at the end of each work session.**

## Repo layout

- `sample-1/`, `sample-2/`, `sample-3/`: real past cases. Each has `demand.pdf`, `voucher.pdf`, `note.pdf` and `pass-letter.pdf`.
- `utils/vat-tax.webp`: official FY 2026-27 VAT and income-tax deduction rates by economic code. কম্পিউটার মেরামত (৩২৫৮১০৪) is 15% VAT and 2% tax.
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
- Use the **current** pass-letter table (sample-1 style), which matches the audit branch's note table. Do not use the older 15%-of-gross / 5%-tax table from samples 2 and 3.
- Dates on the pass letter show both the Bengali calendar (বঙ্গাব্দ, Bangladesh revised calendar) and the Gregorian calendar.

## Privacy

The samples contain real officers' names, signatures and phone numbers. Keep this repo private and never push it to a public remote.
