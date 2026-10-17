# Workflow: post-facto ICT repair reimbursement

## Actors

| Role | Person (as of Aug 2026) | Note |
|---|---|---|
| Operator / note writer | আব্দুল্লাহ আল নাহিদ, পরিদর্শক, শিল্প ও বৈজ্ঞানিক মেট্রোলজি, প্রধান কার্যালয় | The user. Phone ০১৭৫৭৯২১৩৫৪, fax +৮৮-০২-৫৫০৩০০৯২ |
| Programmer, ICT cell | শাহীন সুলতানা, প্রোগ্রামার, আইসিটি সেল | |
| DD Admin-1 | মো: মেহেদী হাসান বিশ্বাস, উপপরিচালক (প্রশাসন-১), প্রশাসন-১ অধিশাখা | |
| Approver | মোঃ সাইফুল ইসলাম, পরিচালক, প্রশাসন উইং | Financial power serial 44 |
| AD Accounts & Audit | মোঃ আবু ইউসুফ, সহকারী পরিচালক, হিসাব ও অভ্যন্তরীন নিরীক্ষা শাখা | Pass letter is addressed to this post |
| Audit officer | শাহ আজম, সহকারী নিরীক্ষা কর্মকর্তা, হিসাব ও অভ্যন্তরীন নিরীক্ষা শাখা | Writes paragraph X.1 |
| Vendor | Star-World, 46-48 New Elephant Road, Suvastu Arcade, ICT Bhaban, Shop 642-643 (6th floor), Dhaka-1205 | Gives blank invoice books |

## Steps

1. **Demand letter (চাহিদাপত্র).** An employee or wing reports a fault. The format varies: a handwritten note, a typed letter to পরিচালক (প্রশাসন), or a typed nothi page. It is forwarded through the wing head and Director (Admin) to the Programmer and then to the operator.
2. **Repair.** The operator calls a Star-World technician, who diagnoses the fault and replaces the part. The operator pays immediately from their own money.
3. **Voucher.** The operator fills Star-World's blank invoice:
   - Fields: SL No., date, Name `BSTI, Tejgaon`, Address `Dhaka`, mobile `01757921354`.
   - Lines: the part, e.g. "Brand PC Power Supply (H290AM-00), 290W", plus "Service Charge".
   - TOTAL / ADVANCE `—` / BALANCE, and the amount in English words ("Five Thousand Taka Only").
   - A handwritten certificate, signed and dated, with the operator's seal, e.g.:
     `প্রত্যয়ন করা যাইতেছে যে, মেট্রোলজি উইং এর কম্পিউটার মেরামতে পাওয়ার সাপ্লাই ক্রয় ও সার্ভিস চার্জ বাবদ ৫০০০/= (পাঁচ হাজার টাকা) ব্যয়সংক্রান্ত ব্যয়িত হয়েছে।`
   - The total includes VAT and tax. It is the gross amount that the audit branch will deduct from (see the open question in the session log about gross-up).
4. **D-Nothi note.** File no. `৩৬.০৫.০০০০.০০০.১০৮.০৭.০০০১.১৭`; file subject `বিএসটিআই'র আইসিটি দ্রব্যাদি/এক্সেসরিজ ক্রয় সংক্রান্ত।` Each case is a new note numbered sequentially (87, 88, 90…).
   - Note subject: `বিএসটিআই'র <unit> এর একটি অকেজো কম্পিউটার মেরামত সংক্রান্ত।`
   - **Para X.0 (operator).** Asks for the audit branch's opinion. Attachments: demand PDF and voucher PDF. Route: operator → Programmer → DD Admin-1 → AD Accounts → audit officer.
   - **Para X.1 (audit officer).** Adds the calculation table and the budget statement, e.g. `উল্লেখ্য যে, ২০২৬-২৭ অর্থ বছরে হিসাব শাখার তথ্যমতে "কম্পিউটার মেরামত" খাতে ২০,০০,০০০.০০ (বিশ লক্ষ) টাকা মাত্র বাজেট বরাদ্দ রয়েছে।` Route: audit officer → AD Accounts → DD Admin-1 → back to the operator.
   - **Para X.2 (operator).** Final proposal citing X.1. Route: operator → Programmer → DD Admin-1 → Director (Admin), who approves → DD Admin-1 → Programmer → operator.
5. **মঞ্জুরিপত্র (pass letter).** The operator issues it from the note as an অনুচ্ছেদ পত্র. Memo no. `৩৬.০৫.০০০০.০০০.১০৮.০৭.০০০১.১৭.<serial>`, where the serial is D-Nothi's running letter number (75, 76, 79…). Accounts then reimburses the operator.

## Text templates

Placeholders are in `<>`.

**Para X.0**
> বিএসটিআই'র <unit/person/room> ব্যবহৃত একটি কম্পিউটার <fault> থাকায় দাপ্তরিক কার্যক্রম সম্পাদনে অসুবিধা হচ্ছে এই মর্মে একটি চাহিদাপত্র পাওয়া গিয়েছে (সংযুক্তি: <demand.pdf>)।
>
> পরবর্তীতে সমস্যা নির্ণয়ের পর কম্পিউটারের <part> ত্রুটিযুক্ত পাওয়ায় দাপ্তরিক কার্যক্রমের গুরুত্ব বিবেচনায় একটি নতুন <part> প্রতিস্থাপন/সংযুক্ত করে দ্রুততর সময়ে মেরামত করা হয়।
>
> এমতাবস্থায়, ইতোমধ্যে মেরামতকৃত কম্পিউটারটির যন্ত্রাংশ ক্রয় ও সার্ভিজ চার্জ বাবদ ভ্যাট ও ট্যাক্সসহ সর্বমোট <total>/- (<total in words> টাকা) মাত্র (সংযুক্তি: <voucher.pdf>) পরিচালক(প্রশাসন) মহোদয়ের আর্থিক ক্ষমতার ক্রমিক নং-৪৪ (সংশোধিত ৩৩ তম কাউন্সিল) মোতাবেক 'কম্পিউটার মেরামত' ক্রয় খাত থেকে **পোস্ট ফ্যাক্টো** মঞ্জুরির প্রস্তাব অনুমোদনের পূর্বে নিরীক্ষা শাখার মতামত নেয়া যেতে পারে।
>
> সদয় অনুমোদনের জন্য পেশ করা হলো।

**Para X.2.** The first two paragraphs are the same as X.0. The third becomes:
> এমতাবস্থায়, নোট অনুচ্ছেদ <অনুচ্ছেদ X.1> এর নিরীক্ষা শাখার মতামতের আলোকে ইতোমধ্যে মেরামতকৃত কম্পিউটারটির যন্ত্রাংশ ক্রয় ও সার্ভিজ চার্জ বাবদ ভ্যাট ও ট্যাক্সসহ সর্বমোট <total>/- (<words> টাকা) মাত্র (সংযুক্তি: <voucher.pdf>) পরিচালক(প্রশাসন) মহোদয়ের আর্থিক ক্ষমতার ক্রমিক নং-৪৪ (সংশোধিত ৩৩ তম কাউন্সিল) মোতাবেক 'কম্পিউটার মেরামত' ক্রয় খাত থেকে **পোস্ট ফ্যাক্টো** মঞ্জুরির প্রস্তাবটি সদয় অনুমোদনের জন্য পেশ করা হলো।

**মঞ্জুরিপত্র (current format, sample-1)**
- Letterhead: গণপ্রজাতন্ত্রী বাংলাদেশ সরকার / শিল্প মন্ত্রণালয় / বাংলাদেশ স্ট্যান্ডার্ডস এন্ড টেস্টিং ইনস্টিটিউশন / মান ভবন, ১১৬/ক, তেজগাঁও শিল্প এলাকা, ঢাকা-১২০৮। / www.bsti.gov.bd. Bangladesh govt logo on the left, BSTI logo on the right.
- স্মারক নম্বর (left), তারিখ with the Bengali date above and the Gregorian date below (right).
- বিষয়: **মঞ্জুরিপত্র**
- Body:
  > বিএসটিআই'র <unit> ব্যবহৃত একটি কম্পিউটার মেরামতের জন্য <part> ক্রয় ও সার্ভিজ চার্জ বাবদ ভ্যাট ও ট্যাক্সসহ সর্বমোট <total>/- (<words> টাকা) মাত্র (বিবেচ্য সংযুক্তি: <voucher.pdf>, সদয় দ্রষ্টব্য।) 'কম্পিউটার মেরামত' ক্রয় খাত থেকে **পোস্ট ফ্যাক্টো** মঞ্জুরির প্রস্তাবটি কর্তৃপক্ষ কর্তৃক মঞ্জুর করা হয়েছে।
- Table (same as the audit note).
- `উক্ত ব্যয় 'কম্পিউটার মেরামত' খাত হতে সমন্বয় করা হবে।`
- সংযুক্তিঃ (১) <voucher>
- Signature block: date, name, পরিদর্শক, phone, fax.
- Recipient: সহকারী পরিচালক / হিসাব ও অভ্যন্তরীন নিরীক্ষা শাখা, বাংলাদেশ স্ট্যান্ডার্ডস এন্ড টেস্টিং ইনস্টিটিউশন।

## Calculation (audit branch, VAT-inclusive)

| (১) ভ্যাট ও ট্যাক্সসহ দাবীকৃত বিল | (২) ভ্যাট পূর্ব টাকার পরিমাণ | (৩)=(২×১৫%) কর্তনকৃত ভ্যাট | (৪)=(২×২%) কর্তনকৃত ট্যাক্স | (৫)=(১-৩-৪) পরিশোধযোগ্য বিল |
|---|---|---|---|---|

```
base    = round(total / 1.15)
vat     = total - base
tax     = round(base * 0.02)
payable = total - vat - tax
```

| Total | Base | VAT | Tax | Payable |
|---|---|---|---|---|
| 3,000 | 2,609 | 391 | 52 | 2,557 |
| 4,125 | 3,587 | 538 | 72 | 3,515 |
| 5,000 | 4,348 | 652 | 87 (sample wrote 86) | 4,261 (with 87) |

Payable ≈ total × 0.98 / 1.15 ≈ total × 0.8522.

### Official rates: `utils/vat-tax.webp`

Source: রাজস্ব অডিট অধিদপ্তর, "২০২৬-২০২৭ অর্থবছরে বিলে আয়কর-ভ্যাট কর্তনের হার" (based on অর্থ আইন ২০২৬ and NBR SROs). These are the rows relevant to ICT:

| Economic code | Head | VAT | Income tax |
|---|---|---|---|
| ৩২৫৮১০৪ | কম্পিউটার মেরামত | 15% | 2% (**the head used for repairs**) |
| ৩২৫৫১০১ | কম্পিউটার সামগ্রী | 10% | 5% |
| ৩২১১১১৭ | ইন্টারনেট | 5% | 5% |
| ৩২৫৮১০৫ | অন্যান্য যন্ত্রপাতি ও সরঞ্জামাদি মেরামত | 15% | 2% |
| ৪১১২২০১ | তথ্য ও যোগাযোগ প্রযুক্তি সরঞ্জামাদি ক্রয় | 5% | 5% |
| ৪১১২২০২ | কম্পিউটার ও আনুষঙ্গিক ক্রয় | 10% | 5% |
| ৪১১২২০৪ | টেলিযোগাযোগ সামগ্রী ক্রয় | 10% | 5% |
| ৪১১৩৩০১ | কম্পিউটার সফটওয়্যার ক্রয় | 10% | 5% |

Implementation note: keep the rates in a config table keyed by economic code, not hard-coded, so the same tool can handle purchases under other heads and new fiscal years. The rates change every fiscal year.

## Known errors in the samples (do not copy)

- **sample-1:** the payable words "তিন হাজার আটশত পঁয়ত্রিশ" are wrong for ২,৫৫৭. The note's attachment list also has leftover জারীশাখা files from sample-2.
- **sample-3:** tax was written as ৮৬ (2% of ৪,৩৪৮ = ৮৬.৯৬), and the payable ৪,২৬১ is inconsistent with ৮৬.
- **sample-2 and sample-3 pass letters:** they use an obsolete table (15% VAT and 5% tax on the gross; e.g. ৭৫০ / ২৫০ / ৪,০০০) that contradicts the approved note.

## Bengali calendar check

The samples use the Bangladesh revised calendar: 10 Aug 2026 = ২৬ শ্রাবণ ১৪৩৩, 12 Aug = ২৮ শ্রাবণ, 23 Aug = ৮ ভাদ্র ১৪৩৩.
