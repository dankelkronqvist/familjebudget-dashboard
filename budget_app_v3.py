import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import date

# =========================
# Grundinställningar
# =========================
st.set_page_config(page_title="Familjebudget", layout="wide")

# =========================
# CSS
# =========================
st.markdown("""
<style>
input.budget { background-color: #eeeeee !important; }
input.actual { background-color: #fff3b0 !important; }
.green-row { background-color: #e6ffe6; padding:6px; border-radius:6px; }
.red-row { background-color: #ffe6e6; padding:6px; border-radius:6px; }
.sidebar-bottom {
    position: fixed;
    bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# Login
# =========================
USERS = {"admin": "1234"}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Logga in")
    u = st.text_input("Användarnamn")
    p = st.text_input("Lösenord", type="password")
    if st.button("Logga in"):
        if USERS.get(u) == p:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Fel uppgifter")
    st.stop()

# =========================
# Databas
# =========================
conn = sqlite3.connect("budget.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS items (
    month TEXT,
    category TEXT,
    name TEXT,
    budget REAL,
    actual REAL,
    pay_date TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS notes (
    month TEXT PRIMARY KEY,
    content TEXT
)
""")

conn.commit()

# =========================
# Sidebar
# =========================
with st.sidebar:
    st.header("📅 Månader")
    months = [
        "Januari","Februari","Mars","April","Maj","Juni",
        "Juli","Augusti","September","Oktober","November","December"
    ]
    month = st.selectbox("Välj månad", months)

    st.divider()
    st.header("👁️ Visa / Dölj")

    show_summary = st.toggle("Sammanfattning", True)
    show_budget_items = st.toggle("Visa budgeterade underrubriker", False)
    show_cashflow = st.toggle("Kassaflöde", True)
    show_month = st.toggle("Månadsöversikt", True)
    show_year = st.toggle("Årsöversikt", True)
    show_notes = st.toggle("Anteckningar", True)
    show_meals = st.toggle("Måltidsplanering", False)

    st.divider()
    st.markdown("<div class='sidebar-bottom'>", unsafe_allow_html=True)
    if st.button("🚪 Logga ut"):
        st.session_state.clear()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# Hämta data
# =========================
df = pd.read_sql(
    "SELECT * FROM items WHERE month=?",
    conn,
    params=(month,)
)

categories = sorted(df["category"].unique()) if not df.empty else []

# =========================
# Anteckningar
# =========================
if show_notes:
    st.subheader(f"📝 Anteckningar – {month}")
    row = c.execute("SELECT content FROM notes WHERE month=?", (month,)).fetchone()
    note = row[0] if row else ""
    new_note = st.text_area("Anteckningar", note, height=120)
    if new_note != note:
        c.execute("INSERT OR REPLACE INTO notes VALUES (?,?)", (month, new_note))
        conn.commit()

# =========================
# Budget & Utgifter
# =========================
total_income_budget = total_income_actual = 0
total_cost_budget = total_cost_actual = 0

for cat in categories:
    with st.expander(cat, expanded=True):
        cat_df = df[df["category"] == cat]

        for _, r in cat_df.iterrows():
            is_income = cat.lower() == "inkomster"
            over = r["actual"] > r["budget"]
            row_class = "green-row" if (is_income or not over) else "red-row"

            st.markdown(f"<div class='{row_class}'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([3,1,1])
            with c1:
                st.write(f"**{r['name']}**")
                pay = st.date_input(
                    "Betalningsdatum",
                    value=date.fromisoformat(r["pay_date"]) if r["pay_date"] else date.today(),
                    key=f"d_{cat}_{r['name']}"
                )
            with c2:
                b = st.number_input(
                    "Budget",
                    value=float(r["budget"]),
                    step=10.0,
                    key=f"b_{cat}_{r['name']}"
                )
            with c3:
                a = st.number_input(
                    "Faktiskt",
                    value=float(r["actual"]),
                    step=10.0,
                    key=f"a_{cat}_{r['name']}"
                )

            if (b,a,str(pay)) != (r["budget"], r["actual"], r["pay_date"]):
                c.execute("""
                UPDATE items SET budget=?, actual=?, pay_date=?
                WHERE month=? AND category=? AND name=?
                """,(b,a,str(pay),month,cat,r["name"]))
                conn.commit()

            if is_income:
                total_income_budget += b
                total_income_actual += a
            else:
                total_cost_budget += b
                total_cost_actual += a

            st.markdown("</div>", unsafe_allow_html=True)

# =========================
# Sammanfattning
# =========================
if show_summary:
    st.divider()
    st.subheader("📊 Sammanfattning")
    c1,c2,c3 = st.columns(3)
    c1.metric("Inkomster", f"€{total_income_actual:.2f}", f"Budget €{total_income_budget:.2f}")
    c2.metric("Utgifter", f"€{total_cost_actual:.2f}", f"Budget €{total_cost_budget:.2f}")
    c3.metric("💰 Kvar att spara",
              f"€{total_income_actual-total_cost_actual:.2f}",
              f"Budget €{total_income_budget-total_cost_budget:.2f}")

# =========================
# Diagram
# =========================
if show_month:
    st.divider()
    st.subheader("📈 Månadsöversikt")

    chart_df = pd.DataFrame({
        "Typ":["Inkomster","Utgifter","Kvar"],
        "Budget":[total_income_budget,total_cost_budget,total_income_budget-total_cost_budget],
        "Faktiskt":[total_income_actual,total_cost_actual,total_income_actual-total_cost_actual]
    }).melt("Typ", var_name="Kategori", value_name="€")

    chart = alt.Chart(chart_df).mark_bar().encode(
        x="Typ:N",
        y="€:Q",
        color="Kategori:N",
        tooltip=["Typ","Kategori","€"]
    ).properties(height=350)

    st.altair_chart(chart, use_container_width=True)

# =========================
# Årsöversikt
# =========================
if show_year:
    st.divider()
    st.subheader("📅 Årsöversikt")
    year_data = []
    for m in months:
        d = pd.read_sql("SELECT * FROM items WHERE month=?", conn, params=(m,))
        inc = d[d.category=="Inkomster"]
        cost = d[d.category!="Inkomster"]
        year_data.append({
            "Månad":m,
            "Inkomster":inc.actual.sum(),
            "Utgifter":cost.actual.sum(),
            "Kvar":inc.actual.sum()-cost.actual.sum()
        })
    st.dataframe(pd.DataFrame(year_data), use_container_width=True)

# =========================
# Måltidsplanering
# =========================
if show_meals:
    st.divider()
    st.subheader("🍽 Veckomeny")
    days = ["Mån","Tis","Ons","Tor","Fre","Lör","Sön"]
    cols = st.columns(7)
    for i,d in enumerate(days):
        with cols[i]:
            st.text_area(d, height=80)
