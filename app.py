from decimal import Decimal, ROUND_HALF_UP, getcontext
from flask import Flask, render_template, request, session, redirect, url_for

getcontext().prec = 28
app = Flask(__name__)
app.secret_key = "change-this-key"  # set to an env var in production

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
    q = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"${q:,.2f}"

@app.after_request
def no_store(resp):
    # prevent browser from caching or restoring form values
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/", methods=["GET"])
def index():
    # default empty form
    return render_template("index.html", procedures=COMMON_PROCEDURES, prefill_rows=None, prefill=False)

@app.route("/edit", methods=["GET"])
def edit():
    data = session.get("last_form")
    if not data:
        return redirect(url_for("index"))
    # render form prefilled
    return render_template(
        "index.html",
        procedures=COMMON_PROCEDURES,
        prefill_rows=data["rows"],
        prefill=True,
        patient_name=data.get("patient_name",""),
        insurance_max=data.get("insurance_max",""),
        notes=data.get("notes","")
    )

@app.route("/plan", methods=["POST"])
def plan():
    patient_name = request.form.get("patient_name","").strip()
    insurance_max = to_decimal(request.form.get("insurance_max","0"))
    notes = request.form.get("notes","").strip()

    names     = request.form.getlist("procedure_name[]")
    customs   = request.form.getlist("custom_name[]")
    teeth     = request.form.getlist("tooth_number[]")
    reasons   = request.form.getlist("reason[]")
    costs     = request.form.getlist("cost[]")
    coverages = request.form.getlist("coverage_percent[]")

    # Save raw strings so we can edit later
    prefill_rows = []
    for i in range(len(names)):
        prefill_rows.append({
            "procedure_name": names[i] if i < len(names) else "",
            "custom_name":    customs[i] if i < len(customs) else "",
            "tooth_number":   teeth[i] if i < len(teeth) else "",
            "reason":         reasons[i] if i < len(reasons) else "",
            "cost":           costs[i] if i < len(costs) else "",
            "coverage":       coverages[i] if i < len(coverages) else ""
        })

    session["last_form"] = {
        "patient_name": patient_name,
        "insurance_max": str(insurance_max),
        "notes": notes,
        "rows": prefill_rows
    }

    # Build rows for math
    rows = []
    for r in prefill_rows:
        sel = r["procedure_name"]
        custom = r["custom_name"]
        name = custom.strip() if sel == "Custom" else sel
        if not name:
            continue
        rows.append({
            "display_name": name,
            "tooth": r["tooth_number"].strip(),
            "reason": r["reason"].strip(),
            "cost": to_decimal(r["cost"], "0"),
            "coverage": to_percent_decimal(r["coverage"])
        })

    remaining_max = insurance_max
    computed = []
    insurance_total = Decimal("0")
    patient_total = Decimal("0")

    APR = Decimal("0.15")
    N = Decimal("48")
    r = APR / Decimal("12")  # monthly rate

    for row in rows:
        allowed = row["cost"] * row["coverage"]
        insurance_pay = min(allowed, remaining_max)
        patient_pay = row["cost"] - insurance_pay

        remaining_max -= insurance_pay
        insurance_total += insurance_pay
        patient_total += patient_pay

        if patient_pay > 0:
            denom = (Decimal("1") - (Decimal("1") + r) ** (-N))
            monthly = (r * patient_pay) / denom if denom != 0 else patient_pay / N
        else:
            monthly = Decimal("0")

        computed.append({
            "display_name": row["display_name"],
            "tooth": row["tooth"],
            "reason": row["reason"],
            "cost": money(row["cost"]),
            "insurance_pay": money(insurance_pay),
            "patient_pay": money(patient_pay),
            "monthly_est": money(monthly)
        })

    context = {
        "patient_name": patient_name,
        "insurance_max": money(insurance_max),
        "rows": computed,
        "insurance_total": money(insurance_total),
        "patient_total": money(patient_total),
        "notes": notes,
        "max_reached": remaining_max <= Decimal("0")
    }
    return render_template("plan.html", **context)

if __name__ == "__main__":
    app.run(debug=True)
