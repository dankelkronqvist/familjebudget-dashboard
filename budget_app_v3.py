import streamlit as st
import pandas as pd

# =========================
# CSS – färger på inputs
# =========================
st.markdown("""
<style>
div[data-testid="stNumberInput"] input.budget {
    background-color: #eeeeee !important;
}
div[data-testid="stNumberInput"] input.actual {
    background-color: #fff3b0 !important;
}
div[data-testid="stNumberInput"] input {
    border-radius: 6px;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# =========================
# Hjälpfunktion för färgade inputs
# =========================
def colored_number_input(label, value, key, css_class):
    st.number_input(label, value=value, key=key)
    st.markdown(
        f"""
        <script>
        const inputs = window.parent.document.querySelectorAll('input');
        inputs.forEach(el => {{
            if (el.getAttribute('aria-label') === "{label}") {{
                el.classList.add("{css_class}");
            }}
        }});
        </script>
        """,
        unsafe_allow_html=True
    )

# =========================
# Login
# =========================
users = {"admin": "1234"}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Logga in")
    user = st.text_input("Användarnamn")
    pw = st.text_input("Lösenord", type="password")
    if st.button("Logga in"):
        if user in users and pw == users[user]:
            st.session_state.logged_in = True
            st.stop()
        else:
            st.error("Fel uppgifter")
    st.stop()

# =========================
# Logga ut
# =========================
col_l, col_r = st.columns([6,1])
with col_r:
    if st.button("Logga ut"):
        st.session_state.clear()
        st.stop()

# =========================
# Data-struktur
# =========================
months = [
    "Januari","Februari","Mars","April","Maj","Juni",
    "Juli","Augusti","September","Oktober","November","December"
]

categories = {
    "Inkomster": ["Lön 1", "Lön 2"],
    "Fasta kostnader": ["El", "Internet"],
    "Rörliga utgifter": ["Mat", "Utemat"],
    "Sparande": ["Buffert"]
}

if "data" not in st.session_state:
    st.session_state.data = {}

month = st.selectbox("📅 Välj månad", months)

if month not in st.session_state.data:
    st.session_state.data[month] = {
        "notes": "",
        "categories": {}
    }
    for c, items in categories.items():
        st.session_state.data[month]["categories"][c] = {
            i: {"budget": 0.0, "actual": 0.0} for i in items
        }

data = st.session_state.data[month]["categories"]

# =========================
# Anteckningar (syns alltid)
# =========================
st.subheader("📝 Anteckningar")
st.session_state.data[month]["notes"] = st.text_area(
    "Anteckningar",
    value=st.session_state.data[month]["notes"],
    height=120
)

# =========================
# Dropdown-rubriker i en rad
# =========================
st.divider()
st.subheader("📂 Budget")

cols = st.columns(len(data))

total_income_budget = 0
total_income_actual = 0
total_cost_budget = 0
total_cost_actual = 0

for idx, (category, items) in enumerate(data.items()):
    with cols[idx]:
        with st.expander(category, expanded=False):
            cat_budget = 0
            cat_actual = 0

            for item, vals in items.items():
                colored_number_input(
                    f"{item} – Budget (€)",
                    vals["budget"],
                    f"{month}_{category}_{item}_B",
                    "budget"
                )
                colored_number_input(
                    f"{item} – Faktiskt (€)",
                    vals["actual"],
                    f"{month}_{category}_{item}_A",
                    "actual"
                )

                vals["budget"] = st.session_state[f"{month}_{category}_{item}_B"]
                vals["actual"] = st.session_state[f"{month}_{category}_{item}_A"]

                cat_budget += vals["budget"]
                cat_actual += vals["actual"]

            st.markdown(f"**Summa budget:** €{cat_budget:.2f}")
            st.markdown(f"**Summa faktiskt:** €{cat_actual:.2f}")

            if category == "Inkomster":
                total_income_budget += cat_budget
                total_income_actual += cat_actual
            else:
                total_cost_budget += cat_budget
                total_cost_actual += cat_actual

# =========================
# Sammanfattning
# =========================
st.divider()
st.subheader("📊 Sammanfattning")

st.metric("Totala inkomster (Budget)", f"€{total_income_budget:.2f}")
st.metric("Totala inkomster (Faktiskt)", f"€{total_income_actual:.2f}")

st.metric("Totala kostnader (Budget)", f"€{total_cost_budget:.2f}")
st.metric("Totala kostnader (Faktiskt)", f"€{total_cost_actual:.2f}")

st.metric(
    "💰 Kvar att använda / spara (Faktiskt)",
    f"€{(total_income_actual - total_cost_actual):.2f}"
)

