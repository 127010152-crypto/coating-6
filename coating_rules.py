"""
Rule-based Edible Coating Advisor  (pure Python, no web page needed)
--------------------------------------------------------------------
Files in the same folder:
  fruit_coating_database.csv  -> fruit info + research data (one row per coating study)
  coating_rules.csv           -> the IF-THEN rules (edit this file to change the advice)

Run:  python coating_rules.py
"""

import csv
import os
import re

# folder this file lives in, so the CSV files are found even if the program is started elsewhere
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NA_WORDS = ("", "not reported", "data not available")


def has_data(text):
    """True if a cell really has information."""
    return (text or "").strip().lower() not in NA_WORDS and \
           not (text or "").lower().startswith("not reported")


def number(text):
    """First number in a text, or None."""
    m = re.search(r"\d+\.?\d*", text or "")
    return float(m.group()) if m else None


# ---------------- load files ----------------
def read_csv(name):
    with open(os.path.join(BASE_DIR, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

rows = read_csv("fruit_coating_database.csv")
rules = sorted(read_csv("coating_rules.csv"), key=lambda r: int(r["priority"]))

fruits = {}       # fruit_id -> fruit info (first row of that fruit)
studies = []      # only rows that really have a coating
for r in rows:
    fruits.setdefault(r["fruit_id"], r)
    if has_data(r["coating_name"]):
        studies.append(r)


# ---------------- searching ----------------
def find_fruit(name):
    """Case-insensitive search by common, scientific or alternative name."""
    name = name.strip().lower()
    for f in fruits.values():
        names = [f["fruit_name"].lower(), f["scientific_name"].lower()]
        names += [n.strip().lower() for n in f["alt_names"].split(";")]
        if name in names:
            return f
    return None


# ---------------- RULE 1: which general rule fires? ----------------
def rule_matches(rule, fruit):
    """A rule fires if every condition that is not '*' is true for the fruit."""
    if rule["if_fruit_names"] != "*":
        if fruit["fruit_name"].lower() not in rule["if_fruit_names"].lower().split(";"):
            return False
    if rule["if_item_type"] != "*" and rule["if_item_type"] != fruit["item_type"]:
        return False
    if rule["if_climacteric"] != "*":
        if not fruit["climacteric_status"].lower().startswith(rule["if_climacteric"].lower()):
            return False
    return True


def first_matching_rule(fruit):
    for rule in rules:                 # rules are sorted: most specific first
        if rule_matches(rule, fruit):
            return rule


# ---------------- RULE 2: score each researched coating (out of 100) ----------------
GOOD_WORDS = ["lower", "reduc", "delay", "maintain", "retain", "better", "slow", "best", "kept", "less", "higher"]
EFFECTS = ["weight_loss_effect", "firmness_effect", "antimicrobial_effect",
           "antioxidant_effect", "ripening_effect"]


def score(study):
    """
    Scoring rules:
      +0 to 25  shelf-life improvement % (capped at 100%)
      +10 / +5  each quality effect that is clearly good / just reported
      +10       natural-origin ingredients (safety)
      +10       experimental evidence, +5 if a DOI is given
    A study needs a shelf-life number and 3+ reported results to be compared.
    """
    pts, data_points, why = 0, 0, []
    pct = number(study["shelf_life_improvement_percentage"])
    if pct is not None:
        pts += min(pct, 100) / 100 * 25
        data_points += 1
        why.append(f"shelf life +{pct:g}%")
    for field in EFFECTS:
        text = study[field]
        if has_data(text):
            data_points += 1
            if any(w in text.lower() for w in GOOD_WORDS):
                pts += 10
                why.append("good " + field.replace("_effect", "").replace("_", " "))
            else:
                pts += 5
    if study["origin"].lower().startswith("natural"):
        pts += 10
        why.append("natural ingredients")
    if study["source_type"].lower().startswith("experimental"):
        pts += 10
    if has_data(study["doi"]):
        pts += 5
    has_shelf_life = number(study["coated_shelf_life_days"]) is not None or pct is not None
    comparable = has_shelf_life and data_points >= 3
    return pts, comparable, why


# ---------------- printing ----------------
def line(label, value):
    print(f"  {label}: {value if has_data(value) else 'Not reported'}")


def show_report(fruit):
    print("\n" + "=" * 60)
    print(f"{fruit['fruit_name']}  ({fruit['scientific_name']})")
    print("=" * 60)
    line("Type", f"{fruit['item_type']} | {fruit['fruit_category']} | {fruit['climacteric_status']}")
    line("Perishability", fruit["perishability"])
    line("Common problems", fruit["postharvest_problems"])
    line("Causes of deterioration", fruit["deterioration_causes"])

    mine = [s for s in studies if s["fruit_id"] == fruit["fruit_id"]]

    # ---- researched coatings ----
    print(f"\nRESEARCHED COATINGS ({len(mine)})")
    for i, s in enumerate(mine, 1):
        print(f"\n {i}. {s['coating_name']}")
        for label, key in [("Materials", "coating_materials"), ("Concentration", "concentration"),
                           ("Method", "application_method"), ("Temperature", "storage_temperature"),
                           ("Conditions", "storage_conditions"), ("Control (days)", "control_shelf_life_days"),
                           ("Coated (days)", "coated_shelf_life_days"), ("Extra days", "additional_shelf_life_days"),
                           ("Weight loss", "weight_loss_effect"), ("Firmness", "firmness_effect"),
                           ("Antimicrobial", "antimicrobial_effect"), ("Limitations", "limitations"),
                           ("Evidence", "source_type"), ("Reference", "reference"), ("DOI", "doi")]:
            line(label, s[key])
    if not mine:
        print("  No research studies added for this crop yet.")

    # ---- best coating by scoring rules ----
    print("\nBEST RECOMMENDED COATING")
    scored = sorted(((score(s), s) for s in mine), key=lambda x: x[0][0], reverse=True)
    comparable = [x for x in scored if x[0][1]]
    if len(comparable) >= 2:
        (pts, _, why), s = comparable[0]
        print(f"  {s['coating_name']}  (score {pts:.0f}/100)")
        line("Materials", s["coating_materials"])
        line("Storage", f"{s['storage_temperature']} | {s['storage_conditions']}")
        line("Shelf life (days) coated / control", f"{s['coated_shelf_life_days']} / {s['control_shelf_life_days']}")
        print("  Why:", "; ".join(why))
        line("Reference", s["reference"])
    elif scored:
        s = scored[0][1]
        print("  Evidence is insufficient to pick one confident best coating.")
        print(f"  Best available option (limited evidence): {s['coating_name']}")
        line("Reference", s["reference"])
    else:
        print("  No research data for this crop, see the rule-based suggestion below.")

    # ---- general IF-THEN rule ----
    rule = first_matching_rule(fruit)
    print("\nSUGGESTED COATING MATERIAL AND METHOD (rule-based)")
    line("Material", rule["then_material"])
    line("Concentration", rule["then_concentration"])
    line("Method", rule["then_method"])
    line("Storage tip", rule["then_storage"])
    line("Based on", rule["basis"])
    line("Confidence", rule["confidence"])
    print(f"  Rule used: {rule['rule_id']} (see coating_rules.csv)")
    print("  Note: general rule, not an experiment on this exact crop. Test a small batch first.")


def main():
    print("Rule-based Edible Coating Advisor")
    print(f"{len(fruits)} fruits/vegetables, {len(studies)} researched coatings, {len(rules)} rules")
    while True:
        name = input("\nEnter a fruit or vegetable (or 'quit'): ")
        if name.strip().lower() in ("quit", "exit", "q"):
            break
        fruit = find_fruit(name)
        if fruit is None:
            print("Fruit not found in database")
        else:
            show_report(fruit)


if __name__ == "__main__":
    main()
