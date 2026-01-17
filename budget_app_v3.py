import streamlit as st

# =========================
# CSS
# =========================
st.markdown("""
<style>
input.budget { background-color: #eeeeee !important; }
input.actual { background-color: #fff3b0 !important; }
</style>
""", unsafe_allow_html=True)

def colored_input(label, value, key, css):
    st.number_input(label, value=value, key=key)
    st.markdown(f"""
    <script>
    document.querySelectorAll('input').forEach(el => {{
        if (el.getAttribute('aria-label') === "{label}") {{
            el.classList.add("{css}");
        }}
    }});
    </script>
    """, unsafe_allow_html=True)

# =========================
# Login
# =========================
users = {"admin": "1234"}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Logga in")
    u = st.text_input("Användarnamn")
    p = st.text_input("Lösenord", type="password")
    if st.button("Logga in"):
        if u in users and p == users[u]:
            st.session_state.logged_in = True
            st.stop()
        else:
            st.error("Fel uppgifter")
    st.stop()

# Logout
col1, col2 = st.columns([6,1])
with col2:
    if st.button("Logga ut"):
        st.session_state.clear()
        st.stop()

# =========================
# Init data
# =========================
months = [
    "Januari","Februari","Mars","April","Maj","Juni",
    "Juli","Augusti","September","Oktober","November","December"
]

if "budget" not in st.session_state:
    st.session_state.budget = {}

month = st.selectbox("📅 Månad", months)

if month not in st.session_state.budget:
    st.session_state.budget[month] = {
        "notes": "",
        "categories": {
            "Inkomster": {},
            "Fasta kostnader": {}
        }
    }

data = st.session_state.budget[month]["categories"]

# =========================
# Anteckningar
# =========================
st.subheader("📝 Anteckningar")
st.session_state.budget[month]["notes"] = st.text_area(
    "Anteckningar",
    value=st.session_state.budget[month]["notes"],
    height=120
)

# =========================
# Lägg till rubrik
# =========================
st.divider()
st.subheader("➕ Hantera rubriker")

new_cat = st.text_input("Ny rubrik")
if st.button("Lägg till rubrik"):
    if new_cat and new_cat not in data:
        data[new_cat] = {}

# =========================
# Dropdown-rubriker på en rad
# =========================
cols = st.columns(len(data))

total_income = total_cost = 0

for idx, (cat, items) in enumerate(list(data.items())):
    with cols[idx]:
        cat_budget = sum(v["budget"] for v in items.values()) if items else 0
        cat_actual = sum(v["actual"] for v in items.values()) if items else 0

        with st.expander(f"{cat} (€{cat_actual:.2f})"):
            # Byt namn
            new_name = st.text_input("Byt namn", value=cat, key=f"rename_{cat}")
            if new_name != cat:
                data[new_name] = data.pop(cat)
                st.stop()

            # Lägg till underrubrik
            new_item = st.text_input("Ny underrubrik", key=f"add_{cat}")
            if st.button("Lägg till", key=f"btn_{cat}"):
                if new_item:
                    items[new_item] = {"budget": 0.0, "actual": 0.0}

            for item, vals in items.items():
                colored_input(f"{item} Budget (€)", vals["budget"], f"{month}_{cat}_{item}_b", "budget")
                colored_input(f"{item} Faktiskt (€)", vals["actual"], f"{month}_{cat}_{item}_a", "actual")
                vals["budget"] = st.session_state[f"{month}_{cat}_{item}_b"]
                vals["actual"] = st.session_state[f"{month}_{cat}_{item}_a"]

            st.markdown(f"**Summa budget:** €{cat_budget:.2f}")
            st.markdown(f"**Summa faktiskt:** €{cat_actual:.2f}")

            if cat == "Inkomster":
                total_income += cat_actual
            else:
                total_cost += cat_actual

# =========================
# Sammanfattning
# =========================
st.divider()
st.subheader("📊 Sammanfattning")
st.metric("Totala inkomster", f"€{total_income:.2f}")
st.metric("Totala kostnader", f"€{total_cost:.2f}")
st.metric("💰 Kvar att använda / spara", f"€{total_income - total_cost:.2f}")

