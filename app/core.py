"""Case logic for the repair-reimbursement workflow: demand records, grouping into cases, voucher lines,
D-Nothi note text and output generation. The web UI (app/server.py) is a thin layer over this module.

Storage (all git-ignored, real names inside):
  cases/demands.json          every demand scan found under demands/, with the fields read from it,
                              the repair done (items, service charge) and the case it belongs to
  cases/<id>/case.json        one case = one voucher + one note: demand ids, voucher SL/date, status, note no.
  cases/<id>/out/             generated voucher PDF, renamed demand PDFs for D-Nothi, note paragraphs
"""
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CASES = ROOT / "cases"
DEMANDS = ROOT / "demands"
REGISTRY = CASES / "demands.json"
BANK = ROOT / "private" / "handwriting" / "bank.json"

STATUSES = ["draft", "voucher", "x0_sent", "x1_received", "approved", "pass_letter", "reimbursed"]


# ---------- files ----------

def load(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def settings():
    return load(DATA / "settings.json")


def heads(fy=None):
    fy = fy or settings()["fiscal_year"]
    return load(DATA / "heads.json")["fiscal_years"][fy]


def schedule_name():
    return load(DATA / "heads.json")["schedule"]


def parts():
    return load(DATA / "parts.json")["parts"]


# ---------- handwriting bank ----------

def bank_words():
    """Words that have a hand-written sample (empty when private/ isn't on this computer)."""
    words = set(load(BANK, {}))
    if "যে," in words:
        words.add(",")  # compose.Bank cuts the comma off the "যে," samples
    return words


def hand_missing(text, bank=None):
    """Words of `text` the attestation can't write, in order; mirrors compose.Bank.tokens (trailing , । peeled off)."""
    bank = bank_words() if bank is None else bank
    missing = []
    for w in text.split():
        while w not in bank and w and w[-1] in ",।":
            if w[-1] not in bank and w[-1] not in missing:
                missing.append(w[-1])
            w = w[:-1]
        if w and w not in bank and w not in missing:
            missing.append(w)
    return missing


def parts_view():
    """Catalogue plus which parts the hand-written attestation can name."""
    bank = bank_words()
    return {k: {**p, "hand_missing": hand_missing(p["bn"], bank)} for k, p in parts().items()}


def missing_hand_words():
    """Every word the catalogue, heads and known wings need that isn't in the bank yet: the top-up list."""
    bank = bank_words()
    texts = [p["bn"] for p in parts().values()]
    texts += [h["attestation"].replace("{units}", "").replace("{parts}", "") for h in heads().values()]
    texts += [d["wing"] for d in registry()["demands"].values() if d.get("wing")]
    return list(dict.fromkeys(w for t in texts for w in hand_missing(t, bank)))


# ---------- Bangla numbers ----------

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_1_99 = ("এক দুই তিন চার পাঁচ ছয় সাত আট নয় দশ এগারো বারো তেরো চৌদ্দ পনেরো ষোলো সতেরো আঠারো উনিশ বিশ "
           "একুশ বাইশ তেইশ চব্বিশ পঁচিশ ছাব্বিশ সাতাশ আটাশ ঊনত্রিশ ত্রিশ একত্রিশ বত্রিশ তেত্রিশ চৌত্রিশ পঁয়ত্রিশ "
           "ছত্রিশ সাঁইত্রিশ আটত্রিশ ঊনচল্লিশ চল্লিশ একচল্লিশ বিয়াল্লিশ তেতাল্লিশ চুয়াল্লিশ পঁয়তাল্লিশ ছেচল্লিশ "
           "সাতচল্লিশ আটচল্লিশ ঊনপঞ্চাশ পঞ্চাশ একান্ন বাহান্ন তিপ্পান্ন চুয়ান্ন পঞ্চান্ন ছাপ্পান্ন সাতান্ন আটান্ন "
           "ঊনষাট ষাট একষট্টি বাষট্টি তেষট্টি চৌষট্টি পঁয়ষট্টি ছেষট্টি সাতষট্টি আটষট্টি ঊনসত্তর সত্তর একাত্তর "
           "বাহাত্তর তিয়াত্তর চুয়াত্তর পঁচাত্তর ছিয়াত্তর সাতাত্তর আটাত্তর ঊনআশি আশি একাশি বিরাশি তিরাশি চুরাশি "
           "পঁচাশি ছিয়াশি সাতাশি আটাশি ঊননব্বই নব্বই একানব্বই বিরানব্বই তিরানব্বই চুরানব্বই পঁচানব্বই ছিয়ানব্বই "
           "সাতানব্বই আটানব্বই নিরানব্বই").split()
assert len(BN_1_99) == 99


def bn(x):
    """Latin digits → Bangla digits."""
    return str(x).translate(BN_DIGITS)


def group(n):
    """1,25,000 grouping (lakh/crore)."""
    s = str(int(n))
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail]) if groups else tail


def taka_bn(n):
    """১৭,৫০০ (Bangla digits, lakh grouping)."""
    return bn(group(n))


def words_bn(n):
    """Bangla number words: 17500 → 'সতেরো হাজার পাঁচশত'."""
    n = int(n)
    if n == 0:
        return "শূন্য"
    out = []
    for size, name in ((10**7, "কোটি"), (10**5, "লক্ষ"), (10**3, "হাজার")):
        if n >= size:
            out.append(f"{words_bn(n // size)} {name}")
            n %= size
    if n >= 100:
        out.append(BN_1_99[n // 100 - 1] + "শত")
        n %= 100
    if n:
        out.append(BN_1_99[n - 1])
    return " ".join(out)


def join_bn(items):
    """['ক', 'খ', 'গ'] → 'ক, খ ও গ'."""
    items = [i for i in items if i]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " ও " + items[-1]


def count_bn(n):
    """২ → 'দুইটি'."""
    return words_bn(n) + "টি"


# ---------- demands ----------

def registry():
    return load(REGISTRY, {"demands": {}})


def demand_id(path):
    rel = path.relative_to(DEMANDS).with_suffix("")
    return re.sub(r"[^\w.-]+", "-", str(rel)).strip("-").lower()


def scan_inbox():
    """Add a blank record for every demand PDF/image under demands/ that isn't registered yet."""
    reg = registry()
    known = {d["file"] for d in reg["demands"].values()}
    added = []
    for path in sorted(DEMANDS.rglob("*")):
        if path.suffix.lower() not in (".pdf", ".jpg", ".jpeg", ".png") or not path.is_file():
            continue
        rel = str(path.relative_to(ROOT))
        if rel in known:
            continue
        did = demand_id(path)
        reg["demands"][did] = blank_demand(did, rel)
        added.append(did)
    if added:
        save(REGISTRY, reg)
    return added


def blank_demand(did, rel):
    return {"id": did, "file": rel, "date": "", "wing": "", "who": "", "thing": "ব্যবহৃত একটি কম্পিউটার",
            "state": "অকেজো", "label": "", "diagnosis": "", "head": "", "items": [],
            "service_charge": settings()["service_charge"], "case": None, "notes": ""}


def demand_head(d):
    """The demand's expense head: explicit override, else the head of its first part."""
    if d.get("head"):
        return d["head"]
    catalogue = parts()
    for it in d.get("items", []):
        if it.get("part") in catalogue:
            return catalogue[it["part"]]["head"]
    return None


def demand_total(d):
    if not d.get("items"):
        return 0
    return sum(int(it.get("qty") or 1) * int(it.get("rate") or 0) for it in d.get("items", [])) + int(d.get("service_charge") or 0)


def demand_problems(d):
    """What still blocks this demand from going into a case."""
    missing = [f for f in ("wing", "who", "label") if not d.get(f)]
    if not d.get("items"):
        missing.append("items")
    elif not demand_head(d):
        missing.append("head")
    return missing


def update_demand(did, fields):
    reg = registry()
    d = reg["demands"][did]
    allowed = set(blank_demand("", "")) - {"id", "file", "case"}
    d.update({k: v for k, v in fields.items() if k in allowed})
    save(REGISTRY, reg)
    remember_prices(d)
    return d


def remember_prices(d):
    """Keep the last price and model per part, so the next form pre-fills them."""
    path = DATA / "parts.json"
    cat = load(path)
    changed = False
    for it in d.get("items", []):
        p = cat["parts"].get(it.get("part"))
        if p and it.get("rate") and int(it["rate"]) != p.get("rate"):
            p["rate"] = int(it["rate"])
            changed = True
        if p and it.get("detail") and it["detail"] != p.get("detail"):
            p["detail"] = it["detail"]
            changed = True
        for o in (p or {}).get("options", []):  # a listed model keeps its own last price
            if o["detail"] == it.get("detail") and it.get("rate") and int(it["rate"]) != o["rate"]:
                o["rate"] = int(it["rate"])
                changed = True
    if changed:  # one part per line keeps the file readable and its diffs small
        body = ",\n".join(f"    {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in cat["parts"].items())
        path.write_text('{\n  "_comment": ' + json.dumps(cat["_comment"], ensure_ascii=False) + ',\n  "parts": {\n' + body + "\n  }\n}\n",
                        encoding="utf-8")


# ---------- grouping ----------

def ceiling(head_key):
    """Most one case of this head may total: the Director (Admin) cap, or the PPR ceiling from settings (None = no cap)."""
    h = heads()[head_key]
    return h["limit"] if h["limit"] is not None else settings().get("ppr_ceiling")


def check_group(demands):
    """Errors that forbid putting these demands into one case."""
    errors = []
    for d in demands:
        if (p := demand_problems(d)):
            errors.append(f"{d['label'] or d['id']}: missing {', '.join(p)}")
    hs = {demand_head(d) for d in demands}
    if len(hs) > 1:
        errors.append("different expense heads: " + " / ".join(heads()[h]["khat"] for h in hs if h in heads()))
    if len(hs) == 1 and (h := hs.pop()) and (cap := ceiling(h)) is not None:
        total = sum(demand_total(d) for d in demands)
        if total > cap:
            errors.append(f"total {group(total)} exceeds the limit {group(cap)} for {heads()[h]['khat']}")
    return errors


def suggest_cases():
    """Pack ready, unassigned demands into as few cases as the rules allow: same head, total within the ceiling."""
    reg = registry()
    ready = [d for d in reg["demands"].values() if not d.get("case") and not demand_problems(d)]
    by_head = {}
    for d in ready:
        by_head.setdefault(demand_head(d), []).append(d)
    proposals = []
    for h, ds in by_head.items():
        cap = ceiling(h)
        bins = []
        for d in sorted(ds, key=demand_total, reverse=True):  # first-fit decreasing
            t = demand_total(d)
            for b in bins:
                if cap is None or b["total"] + t <= cap:
                    b["ids"].append(d["id"])
                    b["total"] += t
                    break
            else:
                bins.append({"head": h, "ids": [d["id"]], "total": t})
        proposals += bins
    return proposals


# ---------- cases ----------

def case_dir(cid):
    return CASES / cid


def list_cases():
    return [load(p) for p in sorted(CASES.glob("*/case.json"))]


def get_case(cid):
    return load(case_dir(cid) / "case.json")


def case_demands(case):
    reg = registry()["demands"]
    return [reg[i] for i in case["demands"] if i in reg]


def create_case(ids):
    reg = registry()
    demands = [reg["demands"][i] for i in ids]
    if any(d.get("case") for d in demands):
        raise ValueError("a demand is already in a case")
    if (errors := check_group(demands)):
        raise ValueError("; ".join(errors))
    s = settings()
    fy = s["fiscal_year"]
    n = 1 + max([int(c["id"].rsplit("-", 1)[1]) for c in list_cases() if c["id"].startswith(fy)] or [0])
    cid = f"{fy}-{n:03d}"
    case = {"id": cid, "fy": fy, "head": demand_head(demands[0]), "demands": ids, "status": "draft",
            "voucher": {"sl_no": s["next_voucher_sl"], "date": date.today().isoformat()},
            "note": {"no": None, "audit_para": None}, "created": date.today().isoformat()}
    s["next_voucher_sl"] += 1
    save(DATA / "settings.json", s)
    for d in demands:
        d["case"] = cid
    save(REGISTRY, reg)
    save(case_dir(cid) / "case.json", case)
    return case


def update_case(cid, fields):
    case = get_case(cid)
    for k in ("status", "voucher", "note"):
        if k in fields:
            case[k] = {**case[k], **fields[k]} if isinstance(case[k], dict) else fields[k]
    save(case_dir(cid) / "case.json", case)
    return case


def dissolve_case(cid):
    """Send the demands back to the inbox and delete the case folder (generated files included)."""
    reg = registry()
    for d in reg["demands"].values():
        if d.get("case") == cid:
            d["case"] = None
    save(REGISTRY, reg)
    shutil.rmtree(case_dir(cid))


def totals(case):
    """Case total plus the audit-branch deductions, using the head's rates and the configured VAT method."""
    h = heads(case["fy"])[case["head"]]
    total = sum(demand_total(d) for d in case_demands(case))
    if settings()["vat_method"] == "gross":
        vat, tax = round(total * h["vat"]), round(total * h["tax"])
        base = total - vat
    else:
        base = round(total / (1 + h["vat"]))
        vat, tax = total - base, round(base * h["tax"])
    return {"total": total, "base": base, "vat": vat, "tax": tax, "payable": total - vat - tax}


# ---------- voucher ----------

def voucher_items(demands):
    """Merge identical parts across demands into one line (qty adds up); one service-charge line."""
    cat = parts()
    lines = {}
    for d in demands:
        for it in d["items"]:
            key = (it["part"], it.get("detail", ""), int(it["rate"]))
            if key in lines:
                lines[key]["qty"] += int(it.get("qty") or 1)
            else:
                lines[key] = {"description": cat.get(it["part"], {}).get("en", it["part"]), "detail": it.get("detail", ""),
                              "qty": int(it.get("qty") or 1), "rate": int(it["rate"])}
    items = list(lines.values())
    charges = [int(d.get("service_charge") or 0) for d in demands if d.get("service_charge")]
    if charges:
        if len(set(charges)) == 1:
            items.append({"description": "Service Charge", "qty": len(charges), "rate": charges[0]})
        else:
            items.append({"description": "Service Charge", "qty": None, "rate": None, "amount": sum(charges)})
    return items


def wings_phrase(demands, head, sep):
    """'সিএম উইং এর একটি ও রসায়ন পরীক্ষণ উইং এর একটি' (count_devices) or 'সিএম উইং ও রসায়ন পরীক্ষণ উইং এর'."""
    counts = {}
    for d in demands:
        counts[d["wing"]] = counts.get(d["wing"], 0) + 1
    if head.get("count_devices") and all(c == 1 for c in counts.values()):
        return join_bn([f"{w}{sep} একটি" for w in counts])
    if head.get("count_devices"):
        return join_bn([f"{w}{sep} {count_bn(c)}" for w, c in counts.items()])
    return join_bn(list(counts)) + sep


def parts_phrase(demands, joiner=join_bn):
    cat = parts()
    names = []
    for d in demands:
        for it in d["items"]:
            name = cat.get(it["part"], {}).get("bn", it["part"])
            if name not in names:
                names.append(name)
    return joiner(names)


def attestation_text(case, demands):
    h = heads(case["fy"])[case["head"]]
    units = wings_phrase(demands, {**h, "count_devices": h["count_devices"] and len(demands) > 1}, " এর")
    return h["attestation"].format(units=units, parts=parts_phrase(demands))


def voucher_case(case):
    s = settings()
    demands = case_demands(case)
    y, m, d = case["voucher"]["date"].split("-")
    return {"sl_no": case["voucher"]["sl_no"], "date": f"{d}/{m}/{y}", "customer": s["customer"],
            "attestation": {"text": attestation_text(case, demands)}, "items": voucher_items(demands)}


# ---------- D-Nothi note ----------

def attachment_name(d):
    return f"চাহিদাপত্র - {d['label']}.pdf"


def note_texts(case):
    """Paragraph X.0 (asks the audit branch) and X.2 (final proposal), plus the note subject and attachment list."""
    h = heads(case["fy"])[case["head"]]
    demands = case_demands(case)
    s = settings()
    n = len(demands)
    t = totals(case)["total"]
    amount = f"{taka_bn(t)}/- ({words_bn(t)} টাকা) মাত্র"
    voucher = s["note"]["voucher_attachment"]
    citation = (f"{h['approver']} মহোদয়ের আর্থিক ক্ষমতার ক্রমিক নং-{bn(h['serial'])} ({schedule_name()}) "
                f"মোতাবেক '{h['khat']}' ক্রয় খাত থেকে পোস্ট ফ্যাক্টো মঞ্জুরির প্রস্তাব")
    device = h["device"]

    subject = "বিএসটিআই'র " + h["subject"].format(units=wings_phrase(demands, h, "-এর"))

    files = [attachment_name(d) for d in demands]
    states = {d["state"] for d in demands}
    if len(states) == 1:
        who = join_bn([f"{d['who']} {d['thing']}" for d in demands]) + f" {states.pop()}"
    else:
        who = join_bn([f"{d['who']} {d['thing']} {d['state']}" for d in demands])
    letters = "একটি চাহিদাপত্র" if n == 1 else f"{bn(n)}টি চাহিদাপত্র"
    p1 = (f"বিএসটিআই'র {who} থাকায় দাপ্তরিক কার্যক্রম সম্পাদনে অসুবিধা হচ্ছে এই মর্মে {letters} পাওয়া গিয়েছে "
          f"(সংযুক্তি: {join_bn(files)}{' সদয় দ্রষ্টব্য' if n > 1 else ''})।")

    if n == 1:
        pp = parts_phrase(demands)
        p2 = (f"পরবর্তীতে সমস্যা নির্ণয়ের পর {device}ের {pp} ত্রুটিযুক্ত পাওয়ায় দাপ্তরিক কার্যক্রমের গুরুত্ব "
                                f"বিবেচনায় একটি নতুন {pp} প্রতিস্থাপন/সংযুক্ত করে দ্রুততর সময়ে মেরামত করা হয়।")
        repaired = f"ইতোমধ্যে মেরামতকৃত {device}টির"
        lead = "এমতাবস্থায়, "
    else:
        bullets = [f"• {d['diagnosis'] or default_diagnosis(d, device)}" for d in demands]
        p2 = "পরবর্তীতে সমস্যা নির্ণয়ের পর নিম্নবর্ণিত ত্রুটিসমূহ পরীলক্ষিত হয়ঃ\n" + "\n".join(bullets)
        repaired = f"ইতোমধ্যে মেরামতকৃত {device} {bn(n)}টির"
        lead = (f"এমতাবস্থায়, দাপ্তরিক কার্যক্রমের গুরুত্ব বিবেচনায় {device} {count_bn(n)} দ্রুততর সময়ে মেরামত করা হয়। ")

    body = f"{repaired} যন্ত্রাংশ ক্রয় ও সার্ভিস চার্জ বাবদ ভ্যাট ও ট্যাক্সসহ সর্বমোট {amount} (সংযুক্তি: {voucher}) {citation}"
    if n == 1:
        p3_x0 = f"এমতাবস্থায়, {body} অনুমোদনের পূর্বে নিরীক্ষা শাখার মতামত নেয়া যেতে পারে।"
    else:
        p3_x0 = f"{lead}{body} অনুমোদনের পূর্বে নিরীক্ষা শাখার মতামত নেয়া যেতে পারে।"
    note_no = case["note"].get("no")
    audit = case["note"].get("audit_para") or (f"{note_no}.1" if note_no else "X.1")
    p3_x2 = f"এমতাবস্থায়, নোট অনুচ্ছেদ {bn(audit)} এর নিরীক্ষা শাখার মতামতের আলোকে {body}টি সদয় অনুমোদনের জন্য পেশ করা হলো।"
    x0 = "\n\n".join([p1, p2, p3_x0, "সদয় অনুমোদনের জন্য পেশ করা হলো।"])
    x2 = "\n\n".join([p1, p2, p3_x2])
    return {"subject": subject, "x0": x0, "x2": x2, "attachments": files + [voucher]}


def default_diagnosis(d, device):
    pp = parts_phrase([d])
    return f"{d['wing']} এর {device}ের {pp} ত্রুটিযুক্ত। নতুন {pp} প্রতিস্থাপন করা প্রয়োজন।"


# ---------- output ----------

def generate(cid):
    """Voucher PDF, demand PDFs renamed for D-Nothi upload, note paragraphs. Returns paths and warnings."""
    case = get_case(cid)
    out = case_dir(cid) / "out"
    out.mkdir(parents=True, exist_ok=True)
    warnings = []

    sys.path.insert(0, str(ROOT / "voucher"))
    import make_voucher
    v = voucher_case(case)
    pdf = out / settings()["note"]["voucher_attachment"]
    bare = [d["label"] + ": " + parts().get(it["part"], {}).get("en", it["part"]) for d in case_demands(case)
            for it in d["items"] if not it.get("detail", "").strip()]
    if bare:
        warnings.append("No model/detail on the voucher for " + "; ".join(bare) + " — pick a model under each part in the demand form.")
    missing = hand_missing(v["attestation"]["text"])
    if missing:  # leave the attestation blank rather than fail; the user hand-writes it or tops up the bank
        warnings.append("Voucher has NO hand-written attestation: no handwriting sample for "
                        + ", ".join(missing) + ". Add these words via Settings → Handwriting top-up and regenerate, "
                        "or write the attestation by hand on the printed voucher.")
        v.pop("attestation")
    try:
        make_voucher.render(v, pdf)
    except KeyError as e:  # the bank still couldn't write something: never block the voucher on it
        warnings.append(f"Voucher has NO hand-written attestation ({e.args[0]}).")
        v.pop("attestation", None)
        make_voucher.render(v, pdf)

    for d in case_demands(case):
        src = ROOT / d["file"]
        if src.suffix.lower() == ".pdf":
            shutil.copyfile(src, out / attachment_name(d))
        else:
            warnings.append(f"{d['file']} is an image; convert it to PDF before uploading")

    texts = note_texts(case)
    (out / "note.txt").write_text(
        f"নোটের বিষয়: {texts['subject']}\n\n--- অনুচ্ছেদ X.0 ---\n{texts['x0']}\n\n--- অনুচ্ছেদ X.2 ---\n{texts['x2']}\n\n"
        "সংযুক্তি:\n" + "\n".join(f"{bn(i)}। {a}" for i, a in enumerate(texts["attachments"], 1)) + "\n", encoding="utf-8")
    case = get_case(cid)
    case["warnings"] = warnings  # kept so the case page still shows them after a reload
    if case["status"] == "draft":
        case["status"] = "voucher"
    save(case_dir(cid) / "case.json", case)
    return {"files": sorted(p.name for p in out.iterdir()), "warnings": warnings}
