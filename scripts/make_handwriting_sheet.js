// Generates the handwriting-collection sheet (print → fill by hand → scan at 600 dpi).
// Usage: node scripts/make_handwriting_sheet.js [out.docx]
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
  BorderStyle, AlignmentType, HeightRule, PageBreak, Footer, PageNumber,
  VerticalAlign, ShadingType,
} = require("docx");

const OUT = process.argv[2] || "output/handwriting-sheet.docx";
const FONT = { ascii: "Calibri", hAnsi: "Calibri", cs: "Nirmala UI", eastAsia: "Nirmala UI" };
const PAGE_W = 11906, MARGIN = 850, CONTENT_W = PAGE_W - 2 * MARGIN; // A4, 1.5 cm margins
const GRID = { style: BorderStyle.SINGLE, size: 4, color: "A6A6A6" };
const GRID_BORDERS = { top: GRID, bottom: GRID, left: GRID, right: GRID };

const run = (text, o = {}) => new TextRun({ text, font: FONT, size: o.size || 22, bold: o.bold, color: o.color, italics: o.italics });
const para = (children, o = {}) => new Paragraph({ children: [].concat(children), alignment: o.align, keepNext: o.keepNext, spacing: { before: o.before ?? 0, after: o.after ?? 80 } });
const heading = (num, text, hint) => [
  para([run(`${num}. `, { bold: true, size: 26 }), run(text, { bold: true, size: 26 })], { before: 200, after: 40, keepNext: true }),
  ...(hint ? [para(run(hint, { size: 19, italics: true, color: "555555" }), { after: 100, keepNext: true })] : []),
];

function cell(children, width, o = {}) {
  return new TableCell({
    children: [].concat(children),
    width: { size: width, type: WidthType.DXA },
    borders: GRID_BORDERS,
    verticalAlign: VerticalAlign.CENTER,
    shading: o.shade ? { type: ShadingType.CLEAR, color: "auto", fill: "F2F2F2" } : undefined,
    margins: { left: 100, right: 100 },
  });
}

// Grid: one printed prompt column + N empty boxes to write in.
function writingGrid(items, reps, { labelW = 2600, rowH = 820, header = "লিখুন / Write" } = {}) {
  const boxW = Math.floor((CONTENT_W - labelW) / reps);
  const widths = [labelW, ...Array(reps).fill(boxW)];
  const total = widths.reduce((a, b) => a + b, 0);
  const head = new TableRow({
    tableHeader: true,
    children: [
      cell(para(run("শব্দ / Prompt", { bold: true, size: 18 }), { after: 0 }), labelW, { shade: true }),
      ...Array.from({ length: reps }, (_, i) => cell(para(run(`${header} ${i + 1}`, { bold: true, size: 18 }), { align: AlignmentType.CENTER, after: 0 }), boxW, { shade: true })),
    ],
  });
  const rows = items.map((label) => new TableRow({
    height: { value: rowH, rule: HeightRule.EXACT },
    cantSplit: true,
    children: [
      cell(para(run(label, { size: 24 }), { after: 0 }), labelW, { shade: true }),
      ...Array.from({ length: reps }, () => cell(para(run(""), { after: 0 }), boxW)),
    ],
  }));
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, rows: [head, ...rows] });
}

// Large empty boxes (signature, seal, sentences).
function boxGrid(cols, rowsN, rowH, labelFn) {
  const w = Math.floor(CONTENT_W / cols);
  const rows = Array.from({ length: rowsN }, (_, r) => new TableRow({
    height: { value: rowH, rule: HeightRule.EXACT },
    cantSplit: true,
    children: Array.from({ length: cols }, (_, c) => cell(
      para(run(labelFn(r * cols + c + 1), { size: 16, color: "8C8C8C" }), { after: 0 }), w,
    )),
  }));
  return new Table({ width: { size: w * cols, type: WidthType.DXA }, columnWidths: Array(cols).fill(w), rows });
}

const ATTESTATION = "প্রত্যয়ন করা যাইতেছে যে, মেট্রোলজি উইং এর কম্পিউটার মেরামতে পাওয়ার সাপ্লাই ক্রয় ও সার্ভিস চার্জ বাবদ উক্ত অর্থ ব্যয় করা হয়েছে।";

const FIXED_WORDS = ["প্রত্যয়ন", "করা", "যাইতেছে", "যে,", "এর", "কম্পিউটার", "মেরামতে", "ক্রয়", "ও", "সার্ভিস", "চার্জ", "বাবদ", "উক্ত", "অর্থ", "ব্যয়", "হয়েছে।", "ব্যবহৃত", "একটি", "নতুন", "কক্ষ", "নং", "এবং"];
const UNIT_WORDS = ["মেট্রোলজি", "পদার্থ", "পরীক্ষণ", "রসায়ন", "সিএম", "মান", "প্রশাসন", "জারী", "হিসাব", "নিরীক্ষা", "টাইলস", "টেস্টিং", "ল্যাব", "আইসিটি", "সেল", "উইং", "শাখা", "শাখার", "মহাপরিচালকের", "দপ্তর", "লাইব্রেরি", "স্টোর"];
const PART_WORDS = ["র‍্যাম", "মাদারবোর্ড", "পাওয়ার", "সাপ্লাই", "হার্ডডিস্ক", "এসএসডি", "প্রসেসর", "কিবোর্ড", "মাউস", "মনিটর", "ইউপিএস", "ব্যাটারি", "প্রিন্টার", "টোনার", "কার্টিজ", "ক্যাবল", "ল্যাপটপ", "ডিসপ্লে", "রাউটার", "সফটওয়্যার"];
const BLANK_ROWS = (n) => Array(n).fill("");

const children = [
  para(run("Handwriting Sample Sheet", { bold: true, size: 36 }), { align: AlignmentType.CENTER, after: 40 }),
  para(run("হাতের লেখার নমুনা সংগ্রহ — ভাউচার প্রত্যয়ন অটোমেশন", { size: 24 }), { align: AlignmentType.CENTER, after: 200 }),
  para(run("How to fill", { bold: true, size: 24 }), { after: 60 }),
  ...[
    "Use the same pen you normally sign vouchers with (black ballpoint). Write at your normal size and speed — do not write more neatly than usual.",
    "Write each word once per box, centred, without touching the box borders. Keep a clear gap between words in the sentence boxes.",
    "Grey boxes are printed prompts. White boxes are for your handwriting.",
    "Empty prompt rows: write a word you often need (a unit or part not listed) in the grey box too, then repeat it in the white boxes.",
    "When done, scan every page flat at 600 dpi (PNG/TIFF). If using a phone, use CamScanner \"Original\" mode — not \"Magic Color\".",
  ].map((t, i) => para([run(`${i + 1}.  `, { bold: true, size: 20 }), run(t, { size: 20 })], { after: 50 })),

  ...heading("1", "পূর্ণ প্রত্যয়ন বাক্য — ৩ বার লিখুন", "Copy the sentence below exactly as you would write it on a voucher (2–3 lines per box). If you prefer different wording, write YOUR wording instead and mark it with ✓."),
  para(run(ATTESTATION, { size: 24 }), { after: 120 }),
  boxGrid(1, 3, 2500, (i) => `বাক্য ${i}`),

  new Paragraph({ children: [new PageBreak()] }),
  ...heading("2", "স্থায়ী শব্দ — প্রতিটি ৩ বার", "Common words in the attestation. Include the punctuation shown (, ।)."),
  writingGrid([...FIXED_WORDS, ...BLANK_ROWS(2)], 3),

  ...heading("3", "শাখা / উইং এর নাম — প্রতিটি ৩ বার", "Units are collected word-by-word so they can be combined (e.g. পদার্থ + পরীক্ষণ + উইং)."),
  writingGrid([...UNIT_WORDS, ...BLANK_ROWS(4)], 3),

  ...heading("4", "যন্ত্রাংশের নাম — প্রতিটি ৩ বার", "Parts and equipment you commonly replace or repair."),
  writingGrid([...PART_WORDS, ...BLANK_ROWS(4)], 3),

  ...heading("5", "সংখ্যা ও তারিখ — প্রতিটি ৫ বার", "Digits as you write them in dates. Then write three full dates in your usual style (e.g. 26/07/26)."),
  writingGrid(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "/", "০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯", "/= (টাকা চিহ্ন)", "( )"], 5, { labelW: 1700, rowH: 700 }),
  para(run(""), { after: 120 }),
  boxGrid(3, 1, 900, (i) => `তারিখ ${i}`),

  new Paragraph({ children: [new PageBreak()] }),
  ...heading("6", "স্বাক্ষর — ৬ বার", "Sign as you sign the voucher attestation (the short signature)."),
  boxGrid(2, 3, 1700, (i) => `স্বাক্ষর ${i}`),
  ...heading("7", "সিল — ৩ বার", "Stamp your name seal (আব্দুল্লাহ আল নাহিদ / পরিদর্শক ...) with fresh ink, fully inside the box. Avoid double-stamping."),
  boxGrid(3, 1, 2300, (i) => `সিল ${i}`),
];

const doc = new Document({
  creator: "ICT Purchase Automation",
  title: "Handwriting Sample Sheet",
  styles: { default: { document: { run: { font: FONT, size: 22 } } } },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [run("Handwriting sheet — page ", { size: 16, color: "8C8C8C" }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "8C8C8C" })],
        })],
      }),
    },
    children,
  }],
});

fs.mkdirSync(require("path").dirname(OUT), { recursive: true });
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT); });
