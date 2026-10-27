"""Local web UI for the repair cases. Listens on 127.0.0.1 only, so nothing leaves this computer.

Run: .venv/bin/python app/server.py   then open http://127.0.0.1:5050
"""
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file

import core

app = Flask(__name__, static_folder=None)
HERE = Path(__file__).parent


def demand_view(d):
    return {**d, "total": core.demand_total(d), "head_key": core.demand_head(d), "problems": core.demand_problems(d)}


def case_view(c):
    demands = core.case_demands(c)
    out = core.case_dir(c["id"]) / "out"
    return {**c, "totals": core.totals(c), "errors": core.check_group(demands),
            "labels": [d["label"] for d in demands], "files": sorted(p.name for p in out.iterdir()) if out.exists() else []}


@app.get("/")
def index():
    return send_file(HERE / "index.html")


@app.get("/api/state")
def state():
    reg = core.registry()["demands"]
    return jsonify(demands=[demand_view(d) for d in reg.values()], cases=[case_view(c) for c in core.list_cases()],
                   heads=core.heads(), parts=core.parts(), hand_missing=core.missing_hand_words(), settings=core.settings(), statuses=core.STATUSES)


@app.post("/api/scan")
def scan():
    return jsonify(added=core.scan_inbox())


@app.put("/api/demands/<did>")
def put_demand(did):
    return jsonify(demand_view(core.update_demand(did, request.json)))


@app.get("/api/proposals")
def proposals():
    return jsonify(core.suggest_cases())


@app.post("/api/cases")
def post_case():
    try:
        return jsonify(core.create_case(request.json["ids"]))
    except ValueError as e:
        return jsonify(error=str(e)), 400


@app.put("/api/cases/<cid>")
def put_case(cid):
    return jsonify(case_view(core.update_case(cid, request.json)))


@app.delete("/api/cases/<cid>")
def delete_case(cid):
    core.dissolve_case(cid)
    return jsonify(ok=True)


@app.post("/api/cases/<cid>/generate")
def generate(cid):
    try:
        return jsonify(core.generate(cid))
    except Exception as e:  # show the reason in the UI rather than a bare 500
        return jsonify(error=f"{type(e).__name__}: {e}"), 500


@app.get("/api/cases/<cid>/note")
def note(cid):
    return jsonify(core.note_texts(core.get_case(cid)))


@app.get("/api/handwriting-sheet")
def handwriting_sheet():
    """A one-page top-up sheet for the words the bank is missing (needs `npm install` once)."""
    import subprocess
    words = request.args.get("words", "").split() or core.missing_hand_words()
    out = core.ROOT / "output" / "handwriting-topup.docx"
    r = subprocess.run(["node", str(core.ROOT / "scripts" / "make_handwriting_sheet.js"), str(out), "--words", *words],
                       cwd=core.ROOT, capture_output=True, text=True)
    if r.returncode:
        return jsonify(error=r.stderr.strip()[-500:]), 500
    return send_file(out, as_attachment=True, download_name="handwriting-topup.docx")


@app.put("/api/settings")
def put_settings():
    s = core.settings()
    for k in ("ppr_ceiling", "vat_method", "next_voucher_sl", "service_charge"):
        if k in request.json:
            s[k] = request.json[k]
    core.save(core.DATA / "settings.json", s)
    return jsonify(s)


@app.get("/file/<path:rel>")
def file(rel):
    """Serve a demand scan or a generated file; only from demands/ and cases/."""
    path = (core.ROOT / rel).resolve()
    if not any(path.is_relative_to(base.resolve()) for base in (core.DEMANDS, core.CASES)) or not path.is_file():
        abort(404)
    return send_file(path)


if __name__ == "__main__":
    core.scan_inbox()
    app.run(host="127.0.0.1", port=5050, debug=False)
