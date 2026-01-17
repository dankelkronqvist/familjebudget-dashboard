import streamlit as st
import json, os
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Familjebudget v8", layout="wide")

# -------------------------
# SESSION STATE
# -------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = ""

# -------------------------
# USERS
# -------------------------
USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({"Anki": "1234", "Dani": "1234"}, f)

with open(USERS_FILE) as f:
    USERS = json.load(f)

def logout():
    st.session_state.logged_in = False
    st.session_state.user = ""
    st.stop()

# -------------------------
# LOGIN
# -------------------------
if not st.session_state.logged_in:
    st.title("🔐 Logga in")
    u = st.text_input("Användarnamn")
    p = st.text_input("Lösenord", type="password")
    if st.button("Logga in"):
        if u in USERS and USERS[u] == p:
            st.session_state.logged_in = True
            st.session_state.user = u
            st.stop()
        else:
            st.error("Fel inloggning")
    st.stop()

# -------------------------
# FILES
# -------------------------
STRUCTURE_FILE = "structure.json"
DATA_FILE = "data.json"

if not os.path.exists(STRUCTURE_FILE):
    structure = {
        "Inkomster": ["Lön", "Bidrag"],
        "Fasta kostnader": ["El", "Internet"],
        "Rörliga utgifter": ["Mat", "Utemat"]
    }
    with open(STRUCTURE_FILE, "w") as f:
        json.dump(structure, f, indent=2)
else:
    with open(STRUCTURE_FILE) as f:
        structure = json.load(f)

if not os.path.exists(DATA_FILE):
    data = {}
else:
    with open(DATA_FILE) as f:
        data = json.load(f)

# -------------------------
# TOP BAR
# -------------------------
st.sidebar.button("🚪 Logga ut", on_click=logout)
st.title("💶 Familjebudget")

month = st.selectbox(
    "Månad",
    ["Januari","Februari","Mars","April","Maj","Juni",
     "Juli","Augusti","September","Oktober","November","December"]
)

if month not in data:
    data[month] = {"notes": {}, "values": {}}

# -------------------------
# NOTES
# -------------------------
st.subheader("📝 Anteckningar")
data[month]["notes"] = st.text_area(
    "Anteckningar",
    value=data[month]["notes"].get("text", ""),
    height=120
)
data[month]["notes"] = {"text": data[month]["notes"]}

# -------------------------
# CATEGORY MENUS (ONE ROW)
# -------------------------
st.subheader("📂 Budget")

cols = st.columns(len(structure))
total_income = 0
total_expense = 0

for col, (cat, items) in zip(cols, structure.items()):
    with col:
        with st.expander(cat, expanded=False):
            cat_sum = 0
            for item in items:
                key = f"{month}_{cat}_{item}"
                if key not in data[month]["values"]:
                    data[month]["values"][key] = {"budget": 0.0, "actual": 0.0}

                b = st.number_input(
                    f"{item} – Budget (€)",
                    min_value=0.0,
                    value=data[month]["values"][key]["budget"],
                    key=key+"_b"
                )
                a = st.number_input(
                    f"{item} – Faktiskt (€)",
                    min_value=0.0,
                    value=data[month]["values"][key]["actual"],
                    key=key+"_a"
                )

                data[month]["values"][key] = {"budget": b, "actual": a}
                cat_sum += a

            st.markdown(f"**Summa: {cat_sum:.2f} €**")

            if cat.lower().startswith("inkomst"):
                total_income += cat_sum
            else:
                total_expense += cat_sum

# -------------------------
# SUMMARY
# -------------------------
st.divider()
kvar = total_income - total_expense

c1, c2, c3 = st.columns(3)
c1.metric("Totala inkomster", f"{total_income:.2f} €")
c2.metric("Totala kostnader", f"{total_expense:.2f} €")
c3.metric("Kvar att använda / spara", f"{kvar:.2f} €")

# -------------------------
# EDIT STRUCTURE
# -------------------------
st.sidebar.divider()
st.sidebar.subheader("⚙️ Redigera rubriker")

for cat in list(structure.keys()):
    new_cat = st.sidebar.text_input("Rubrik", value=cat, key="cat_"+cat)
    if new_cat != cat:
        structure[new_cat] = structure.pop(cat)

    for i, item in enumerate(structure[new_cat]):
        structure[new_cat][i] = st.sidebar.text_input(
            "Underrubrik",
            value=item,
            key=f"{new_cat}_{i}"
        )

    if st.sidebar.button(f"+ Lägg till underrubrik ({new_cat})"):
        structure[new_cat].append("Ny post")

# Save structure + data
with open(STRUCTURE_FILE, "w") as f:
    json.dump(structure, f, indent=2)
with open(DATA_FILE, "w") as f:
    json.dump(data, f, indent=2)
