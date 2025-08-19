from decimal import Decimal, ROUND_HALF_UP, getcontext
from flask import Flask, render_template, request, session, redirect, url_for
import os

getcontext().prec = 28
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

# Dropdown menu items
COMMON_PROCEDURES = [
    "Extraction",
    "Wisdom tooth extraction",
    "Sedation",
    "Fillings",
    "Invisalign",
    "Root Canal Treatment",
    "Crowns",
    "Bridges",
    "Gum Disease Treatment",
    "Laser surgery",
    "Whitening",
    "Sleep Apnea treatment",
    "Dentures",
    "Dental Implants",
    "Bone Graft",
    "Custom"
]

def to_decimal(val, default="0"):
    try:
        if val is None or str(val).strip() == "":
            return Decimal(default)
        return Decimal(str(val).replace("$","").replace(",","").strip())
    except Exception:
        return Decimal(default)

def to_percent_decimal(val):
    if val is None or str(val).strip() == "":
        return Decimal("0")
    s = str(val).strip().replace("%","")
    try:
        d = Decimal(s)
        if d > 1:
            d = d / Decimal("100")
        return d
    except Exception:
        return Decimal("0")

def money(d):
    if isinstance(d, str):
        d = to_decimal(d, "0")
    q = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"${q:,.2f}"

@app.after_request
def no_store(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html",
        procedures=COMMON_PROCEDURES,
        prefill_rows=None,
        prefill=False,
        apr_percent="15",
        term_months="48"
    )

@app.route("/edit", methods=["GET"])
def edit():
    data = session.get("last_form")
    if not data:
        return redirect(url_for("index"))
    return render_template(
        "index.html",
        procedures=COMMON_PROCEDURES,
        prefill_rows=data["rows"],
        prefill=True,
        patient_name=data.get("patient_name",""),
        insurance_max=data.get("insurance_max",""),
        notes=data.get("notes",""),
        apr_percent=data.get("apr_percent","15"),
        term_months=data.get("term_months","48")
    )

def compute_rows(prefill_rows):
    rows = []
    for i, r in enumerate(prefill_rows):
        sel = r.get("procedure_name", "")
        custom = r.get("custom_name", "")
        name = custom.strip() if sel == "Custom" else sel
        if not name:
            continue
        rows.append({
            "index": i,
            "display_name": name,
            "tooth": r.get("tooth_number","").strip(),
            "reason": r.get("reason","").strip(),
            "cost": to_decimal(r.get("cost"), "0"),
            "coverage": to_percent_decimal(r.get("coverage")),
            "no_finance": (r.get("no_finance") == "1")
        })
    return rows

def compute_plan(patient_name, insurance_max, notes, prefill_rows,
                 apr_percent="15", term_months="48",
                 overrides=None, header_labels=None):
    rows = compute_rows(prefill_rows)

    remaining_max = to_decimal(insurance_max, "0")
    computed = []
    ins_total = Decimal("0")
    pat_total = Decimal("0")
    mon_total = Decimal("0")

    # financing inputs
    APR = to_percent_decimal(apr_percent)  # 15 -> 0.15
    try:
        N = Decimal(str(int(term_months)))
    except Exception:
        N = Decimal("48")
    r = APR / Decimal("12")

    for idx, row in enumerate(rows):
        allowed = row["cost"] * row["coverage"]
        insurance_pay = min(allowed, remaining_max)
        patient_pay = row["cost"] - insurance_pay

        remaining_max -= insurance_pay
        ins_total += insurance_pay
        pat_total += patient_pay

        if patient_pay > 0 and not row["no_finance"]:
            denom = (Decimal("1") - (Decimal("1") + r) ** (-N))
            monthly = (r * patient_pay) / denom if denom != 0 else patient_pay / N
        else:
            monthly = Decimal("0")

        if overrides and "row" in overrides and idx < len(overrides["row"]):
            orow = overrides["row"][idx] or {}
            if orow.get("insurance"):
                insurance_pay = to_decimal(orow["insurance"], "0")
            if orow.get("patient"):
                patient_pay = to_decimal(orow["patient"], "0")
            if orow.get("monthly"):
                monthly = to_decimal(orow["monthly"], "0")

        mon_total += monthly

        computed.append({
            "display_name": row["display_name"],
            "tooth": row["tooth"],
            "reason": row["reason"],
            "cost": money(row["cost"]),
            "insurance_pay": money(insurance_pay),
            "patient_pay": money(patient_pay),
            "monthly_est": money(monthly),
            "monthly_disabled": row["no_finance"]
        })

    if overrides and "totals" in overrides:
        t = overrides["totals"]
        ins_total_display = money(t["insurance"]) if t.get("insurance") else money(ins_total)
        pat_total_display = money(t["patient"]) if t.get("patient") else money(pat_total)
        mon_total_display = money(t["monthly"]) if t.get("monthly") else money(mon_total)
    else:
        ins_total_display = money(ins_total)
        pat_total_display = money(pat_total)
        mon_total_display = money(mon_total)

    context = {
        "patient_name": patient_name,
        "insurance_max": money(to_decimal(insurance_max, "0")),
        "rows": computed,
        "insurance_total": ins_total_display,
        "patient_total": pat_total_display,
        "monthly_total": mon_total_display,
        "notes": notes,
        "max_reached": remaining_max <= Decimal("0"),
        "header_labels": header_labels or [],
        "apr_percent": str(Decimal(str(apr_percent)).quantize(Decimal("0.01")).normalize()).rstrip('0').rstrip('.') if '.' in str(apr_percent) else str(apr_percent),
        "term_months": str(int(term_months))
    }
    return context

@app.route("/plan", methods=["POST"])
def plan():
    patient_name = request.form.get("patient_name","").strip()
    insurance_max = to_decimal(request.form.get("insurance_max","0"))
    notes = request.form.get("notes","").strip()
    apr_percent = request.form.get("apr_percent","15").strip()
    term_months = request.form.get("term_months","48").strip()

    names     = request.form.getlist("procedure_name[]")
    customs   = request.form.getlist("custom_name[]")
    teeth     = request.form.getlist("tooth_number[]")
    reasons   = request.form.getlist("reason[]")
    costs     = request.form.getlist("cost[]")
    coverages = request.form.getlist("coverage_percent[]")

    exclude_idx_raw = request.form.getlist("exclude_idx[]")
    try:
        exclude_idx = {int(x) for x in exclude_idx_raw}
    except Exception:
        exclude_idx = set()

    prefill_rows = []
    for i in range(len(names)):
        prefill_rows.append({
            "procedure_name": names[i] if i < len(names) else "",
            "custom_name":    customs[i] if i < len(customs) else "",
            "tooth_number":   teeth[i] if i < len(teeth) else "",
            "reason":         reasons[i] if i < len(reasons) else "",
            "cost":           costs[i] if i < len(costs) else "",
            "coverage":       coverages[i] if i < len(coverages) else "",
            "no_finance":     "1" if i in exclude_idx else "0"
        })

    session["last_form"] = {
        "patient_name": patient_name,
        "insurance_max": str(insurance_max),
        "notes": notes,
        "rows": prefill_rows,
        "apr_percent": apr_percent,
        "term_months": term_months
    }
    session.pop("header_labels", None)

    ctx = compute_plan(patient_name, insurance_max, notes, prefill_rows,
                       apr_percent=apr_percent, term_months=term_months)
    return render_template("plan.html", **ctx)

@app.route("/plan-inline", methods=["POST"])
def plan_inline():
    last = session.get("last_form")
    if not last:
        return redirect(url_for("index"))

    patient_name = request.form.get("patient_name","").strip()
    insurance_max = request.form.get("insurance_max","0")
    notes = request.form.get("notes","").strip()

    names   = request.form.getlist("display_name[]")
    teeth   = request.form.getlist("tooth[]")
    reasons = request.form.getlist("reason[]")
    costs   = request.form.getlist("cost[]")

    ins_over = request.form.getlist("ins_override[]")
    pat_over = request.form.getlist("pat_override[]")
    mon_over = request.form.getlist("mon_override[]")

    header_labels = request.form.getlist("header_labels[]")
    if header_labels and len(header_labels) == 7:
        session["header_labels"] = header_labels
    else:
        header_labels = session.get("header_labels", [])

    apr_percent = last.get("apr_percent","15")
    term_months = last.get("term_months","48")

    old_rows = last.get("rows", [])
    L = min(len(names), len(old_rows))
    new_rows = []
    for i in range(L):
        old = old_rows[i]
        new_rows.append({
            "procedure_name": "Custom",
            "custom_name":    names[i],
            "tooth_number":   teeth[i],
            "reason":         reasons[i],
            "cost":           costs[i],
            "coverage":       old.get("coverage","0"),
            "no_finance":     old.get("no_finance","0")
        })

    row_overrides = []
    for i in range(L):
        row_overrides.append({
            "insurance": ins_over[i] if i < len(ins_over) and ins_over[i].strip() else None,
            "patient":   pat_over[i] if i < len(pat_over) and pat_over[i].strip() else None,
            "monthly":   mon_over[i] if i < len(mon_over) and mon_over[i].strip() else None
        })

    totals_override = {
        "insurance": request.form.get("total_ins_override","").strip() or None,
        "patient":   request.form.get("total_pat_override","").strip() or None,
        "monthly":   request.form.get("total_mon_override","").strip() or None
    }

    overrides = {"row": row_overrides, "totals": totals_override}

    session["last_form"] = {
        "patient_name": patient_name,
        "insurance_max": str(insurance_max),
        "notes": notes,
        "rows": new_rows,
        "apr_percent": apr_percent,
        "term_months": term_months
    }

    ctx = compute_plan(patient_name, insurance_max, notes, new_rows,
                       apr_percent=apr_percent, term_months=term_months,
                       overrides=overrides,
                       header_labels=session.get("header_labels", []))
    return render_template("plan.html", **ctx)

if __name__ == "__main__":
    app.run(debug=True)
