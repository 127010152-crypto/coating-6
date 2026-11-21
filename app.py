"""
Streamlit web app for the rule-based Edible Coating Advisor.
Run locally:  streamlit run app.py
(On Streamlit Cloud set the main file to app.py - NOT coating_rules.py)
"""
import streamlit as st

import coating_rules as cr     # our rules, scoring and data loading

st.set_page_config(page_title="Edible Coating Advisor", page_icon="🍓")
st.title("🍓 Rule-Based Edible Coating Advisor")
st.caption("Enter a fruit or vegetable to see researched coatings, the best coating, "
           "and a rule-based suggestion of coating material and method.")


def show(v):
    return v if cr.has_data(v) else "Not reported"


name = st.text_input("Fruit or vegetable", value="Strawberry", placeholder="e.g. mango, kela, lauki")
if not name.strip():
    st.stop()

fruit = cr.find_fruit(name)
if fruit is None:
    st.error("Fruit not found in database")
    st.stop()

# ---- fruit info ----
st.header(f"{fruit['fruit_name']} *({fruit['scientific_name']})*")
st.write(f"**Type:** {fruit['item_type']} | {fruit['fruit_category']} | {fruit['climacteric_status']}")
st.write(f"**Perishability:** {fruit['perishability']}")
st.write(f"**Common problems:** {fruit['postharvest_problems']}")
st.write(f"**Causes of deterioration:** {fruit['deterioration_causes']}")

mine = [s for s in cr.studies if s["fruit_id"] == fruit["fruit_id"]]
scored = sorted(((cr.score(s), s) for s in mine), key=lambda x: x[0][0], reverse=True)
comparable = [x for x in scored if x[0][1]]

# ---- best coating (scoring rules) ----
st.subheader("Best recommended coating")
if len(comparable) >= 2:
    (pts, _, why), s = comparable[0]
    st.success(f"**{s['coating_name']}** (score {pts:.0f}/100)")
    st.write(f"**Materials:** {show(s['coating_materials'])}")
    st.write(f"**Storage:** {show(s['storage_temperature'])} | {show(s['storage_conditions'])}")
    st.write(f"**Shelf life coated / control (days):** {show(s['coated_shelf_life_days'])} / {show(s['control_shelf_life_days'])}")
    st.write("**Why:** " + "; ".join(why))
    st.write(f"**Reference:** {show(s['reference'])}")
elif scored:
    s = scored[0][1]
    st.warning("Evidence is insufficient to pick one confident best coating. "
               f"Best available option (limited evidence): **{s['coating_name']}**")
else:
    st.info("No research studies added for this crop yet. See the rule-based suggestion below.")

# ---- IF-THEN rule ----
rule = cr.first_matching_rule(fruit)
st.subheader("Suggested coating material and method (rule-based)")
st.info(f"**{rule['then_material']}**")
st.write(f"**Concentration:** {show(rule['then_concentration'])}")
st.write(f"**Method:** {show(rule['then_method'])}")
st.write(f"**Storage tip:** {show(rule['then_storage'])}")
st.write(f"**Based on:** {show(rule['basis'])}")
st.write(f"**Confidence:** {show(rule['confidence'])}")
st.caption(f"Rule used: {rule['rule_id']} (see coating_rules.csv). General rule, not an experiment "
           "on this exact crop. Test a small batch first.")

# ---- all researched coatings ----
if mine:
    st.subheader(f"All researched coatings ({len(mine)})")
    for s in mine:
        with st.expander(s["coating_name"]):
            for label, key in [("Materials", "coating_materials"), ("Concentration", "concentration"),
                               ("Method", "application_method"), ("Temperature", "storage_temperature"),
                               ("Conditions", "storage_conditions"), ("Control (days)", "control_shelf_life_days"),
                               ("Coated (days)", "coated_shelf_life_days"), ("Extra days", "additional_shelf_life_days"),
                               ("Weight loss", "weight_loss_effect"), ("Firmness", "firmness_effect"),
                               ("Antimicrobial", "antimicrobial_effect"), ("Limitations", "limitations"),
                               ("Evidence", "source_type"), ("Reference", "reference"), ("DOI", "doi")]:
                st.write(f"**{label}:** {show(s[key])}")
