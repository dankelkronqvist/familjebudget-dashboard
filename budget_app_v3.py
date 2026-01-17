import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import date

# =========================
# Streamlit setup
# =========================
st.set_page_config(page_title="Familjebudget", layout="wide")

# =========================
# CSS
# =========================
st.markdown("""
<style>
input { border-radius: 6px !important; }
.budget { background-color: #eeeeee !important; }
.actual { background-color: #fff3b0 !important; }
.green-row { background-color: #e8ffe8; padding:6px; border-radius:6px; }
.red-row { background-color: #ffe8e8; padding:6px; border-radius:6px; }
.sidebar-bottom { position: fixed; bottom: 20px; width: 90%; }
</style>
""", unsafe_allow_html=True)

# =========================
# Login
# =========================
USERS = {"admin": "1234"}
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 Logga in")
    u = st.text_input("Användarnamn")
    p = st.text_input("Lösenord", type="password")
    if st.button("Logga in"):
        if USERS.get(u) == p:
            st.session_state.logged_in = True
            st.session_state.username = u
            st.rerun()
        else:
            st.error("Fel uppgifter")
    st.stop()

# =========================
# Database
# =========================
conn = sqlite3.connect("budget.db", check_same_thread=False)
c = conn.cursor()

# Tables
c.execute("""
CREATE TABLE IF NOT EXISTS categories (
    user TEXT,
    month TEXT,
    category TEXT,
    PRIMARY KEY(user, month, category)
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS items (
    user TEXT,
    month TEXT,
    category TEXT,
    name TEXT,
    budget REAL,
    actual REAL,
    PRIMARY KEY(user, month, category, name)
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS notes (
    user TEXT,
    month TEXT,
    content TEXT,
    PRIMARY KEY(user, month)
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS cashflow (
    user TEXT,
    month TEXT,
    name TEXT,
    amount REAL,
    pay_date TEXT,
    PRIMARY KEY(user, month, name)
)
""")
conn.commit()

# =========================
# Sidebar
# =========================
with st.sidebar:
    st.header("📅 Månad")
    months = ["Januari","Februari","Mars","April","Maj","Juni",
              "Juli","Augusti","September","Oktober","November","December"]
    month = st.selectbox("Välj månad", months)

    st.divider()
    st.subheader("Rubriker & Underrubriker")

    # Ladda rubriker
    c.execute("SELECT category FROM categories WHERE user=? AND month=? ORDER BY category",(st.session_state.username, month))
    rows = c.fetchall()
    categories = [r[0] for r in rows]

    # Lägg till rubrik
    new_cat = st.text_input("Ny rubrik")
    if st.button("Lägg till rubrik"):
        if new_cat and new_cat not in categories:
            c.execute("INSERT INTO categories(user, month, category) VALUES(?,?,?)",
                      (st.session_state.username, month, new_cat))
            conn.commit()
            st.experimental_rerun()

    # Dropdown per rubrik
    selected_cat = st.selectbox("Välj rubrik för sammanfattning", ["Totalt"] + categories)

    # Underrubriker för vald rubrik
    selected_item = None
    if selected_cat != "Totalt":
        c.execute("SELECT name FROM items WHERE user=? AND month=? AND category=? ORDER BY name",
                  (st.session_state.username, month, selected_cat))
        items = [r[0] for r in c.fetchall()]
        if items:
            selected_item = st.selectbox("Välj underrubrik för sammanfattning", ["Alla"] + items)

    st.divider()
    show_summary = st.checkbox("Visa sammanfattning", True)
    show_cashflow = st.checkbox("Visa kassaflöde", True)
    show_notes = st.checkbox("Visa anteckningar", True)
    st.markdown("---")
    if st.button("Logga ut"):
        st.session_state.clear()
        st.rerun()

# =========================
# Anteckningar
# =========================
if show_notes:
    st.subheader(f"📝 Anteckningar - {month}")
    c.execute("SELECT content FROM notes WHERE user=? AND month=?",
              (st.session_state.username, month))
    row = c.fetchone()
    note_text = row[0] if row else ""
    new_note = st.text_area("Anteckningar", value=note_text, height=120)
    if new_note != note_text:
        c.execute("INSERT OR REPLACE INTO notes(user, month, content) VALUES(?,?,?)",
                  (st.session_state.username, month, new_note))
        conn.commit()

# =========================
# Huvudsida: Rubriker & Underrubriker
# =========================
total_budget = 0
total_actual = 0

for cat in categories:
    with st.expander(cat, expanded=True):
        c.execute("SELECT name, budget, actual FROM items WHERE user=? AND month=? AND category=? ORDER BY name",
                  (st.session_state.username, month, cat))
        items = c.fetchall()

        cat_budget = 0
        cat_actual = 0
        for name, budget_val, actual_val in items:
            cols = st.columns(2)
            with cols[0]:
                b = st.number_input(f"{name} – Budget (€)", value=budget_val, key=f"{month}_{cat}_{name}_b", step=1.0)
            with cols[1]:
                a = st.number_input(f"{name} – Faktiskt (€)", value=actual_val, key=f"{month}_{cat}_{name}_a", step=1.0)

            # Spara ändringar
            if b != budget_val or a != actual_val:
                c.execute("INSERT OR REPLACE INTO items(user, month, category, name, budget, actual) VALUES(?,?,?,?,?)",
                          (st.session_state.username, month, cat, name, b, a))
                conn.commit()

            # Färglogik
            if cat.lower() == "inkomster":
                row_class = "green-row"  # alltid grön
            else:
                row_class = "green-row" if a <= b else "red-row"

            st.markdown(f'<div class="{row_class}">{name} - Budget: €{b} | Faktiskt: €{a}</div>', unsafe_allow_html=True)

            cat_budget += b
            cat_actual += a

        st.markdown(f"**Summa {cat} – Budget:** €{cat_budget} | Faktiskt: €{cat_actual}")

        total_budget += cat_budget
        total_actual += cat_actual

# =========================
# Sammanfattning
# =========================
if show_summary:
    st.subheader("📊 Sammanfattning")
    if selected_cat == "Totalt":
        st.metric("Totalt Budget", f"€{total_budget}", "Kvar: €{:.2f}".format(total_budget - total_actual))
        st.metric("Totalt Faktiskt", f"€{total_actual}")
    else:
        # Visa vald rubrik/underrubrik
        cat_budget = 0
        cat_actual = 0
        if selected_item in [None, "Alla"]:
            c.execute("SELECT SUM(budget), SUM(actual) FROM items WHERE user=? AND month=? AND category=?",
                      (st.session_state.username, month, selected_cat))
        else:
            c.execute("SELECT budget, actual FROM items WHERE user=? AND month=? AND category=? AND name=?",
                      (st.session_state.username, month, selected_cat, selected_item))
        row = c.fetchone()
        if row:
            if selected_item in [None, "Alla"]:
                cat_budget = row[0] or 0
                cat_actual = row[1] or 0
            else:
                cat_budget = row[0]
                cat_actual = row[1]
        st.metric(f"{selected_cat} – Budget", f"€{cat_budget}", "Kvar: €{:.2f}".format(cat_budget - cat_actual))
        st.metric(f"{selected_cat} – Faktiskt", f"€{cat_actual}")

# =========================
# Diagram: Budget vs Faktiskt
# =========================
df_chart = pd.DataFrame({
    "Kategori": ["Totalt"],
    "Budget": [total_budget],
    "Faktiskt": [total_actual]
})
df_melted = df_chart.melt(id_vars="Kategori", var_name="Typ", value_name="€")
chart = alt.Chart(df_melted).mark_bar().encode(
    x='Kategori:N',
    y='€:Q',
    color='Typ:N'
)
st.altair_chart(chart, use_container_width=True)
