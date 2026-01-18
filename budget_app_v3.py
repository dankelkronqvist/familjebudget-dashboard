import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
import datetime

# =========================
# CSS – färger
# =========================
st.markdown("""
<style>
input.budget { background-color: #eeeeee !important; }
input.actual { background-color: #fff3b0 !important; }
.red-row { background-color: #ffcccc !important; padding: 5px; border-radius:5px; }
.green-row { background-color: #ccffcc !important; padding: 5px; border-radius:5px; }
</style>
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
with st.sidebar:
    if st.button("Logga ut"):
        st.session_state.clear()
        st.stop()

# =========================
# SQLite Setup
# =========================
DB_FILE = "budget.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS categories (
    month TEXT,
    cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    position INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT,
    category TEXT,
    name TEXT,
    budget REAL,
    actual REAL,
    date DATE
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS notes (
    month TEXT PRIMARY KEY,
    content TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS meals (
    month TEXT,
    day TEXT,
    meal TEXT,
    PRIMARY KEY(month, day)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS events (
    month TEXT,
    date DATE,
    description TEXT,
    PRIMARY KEY(month, date)
)
""")

conn.commit()

# =========================
# Månad Dropdown
# =========================
months = [
    "Januari","Februari","Mars","April","Maj","Juni",
    "Juli","Augusti","September","Oktober","November","December"
]

st.sidebar.subheader("📅 Välj månad")
month = st.sidebar.selectbox("Månad", months, index=0)
st.title(f"📌 {month}")

# =========================
# Lägg till rubrik
# =========================
st.sidebar.subheader("➕ Hantera rubriker")
new_cat = st.sidebar.text_input("Ny rubrik")
if st.sidebar.button("Lägg till rubrik"):
    c.execute("SELECT name FROM categories WHERE month=?", (month,))
    existing = [r[0] for r in c.fetchall()]
    if new_cat and new_cat not in existing:
        c.execute(
            "INSERT INTO categories (month, name, position) VALUES (?,?,?)",
            (month, new_cat, len(existing))
        )
        conn.commit()
        st.stop()

# =========================
# Toggle sektioner
# =========================
st.sidebar.subheader("Visa / Dölj sektioner")
show_cashflow = st.sidebar.checkbox("Kassaflöde", value=True)
show_year = st.sidebar.checkbox("Årsöversikt", value=True)
show_meals = st.sidebar.checkbox("Veckoplanering", value=True)
show_notes = st.sidebar.checkbox("Anteckningar", value=True)
show_calendar = st.sidebar.checkbox("Kalender", value=True)

# =========================
# Hämta rubriker
# =========================
c.execute(
    "SELECT name, position FROM categories WHERE month=? ORDER BY position",
    (month,)
)
categories = c.fetchall()

# =========================
# VÄNSTERPANEL – RUBRIKER + TA BORT (NYTT)
# =========================
st.sidebar.subheader("📂 Rubriker")

for cat_name, pos in categories:
    col1, col2 = st.sidebar.columns([4, 1])

    with col1:
        st.write(cat_name)

    with col2:
        if st.button("🗑", key=f"delete_cat_{cat_name}"):
            c.execute(
                "DELETE FROM categories WHERE month=? AND name=?",
                (month, cat_name)
            )
            c.execute(
                "DELETE FROM items WHERE month=? AND category=?",
                (month, cat_name)
            )
            conn.commit()
            st.stop()

# =========================
# Anteckningar
# =========================
if show_notes:
    st.subheader("📝 Anteckningar")
    c.execute("SELECT content FROM notes WHERE month=?", (month,))
    row = c.fetchone()
    note_text = row[0] if row else ""
    new_note = st.text_area("Anteckningar", value=note_text, height=120)
    if new_note != note_text:
        c.execute(
            "INSERT OR REPLACE INTO notes (month, content) VALUES (?,?)",
            (month, new_note)
        )
        conn.commit()

# =========================
# Rubriker & Underrubriker – huvudpanel
# =========================
total_income_budget = 0
total_income_actual = 0
total_cost_budget = 0
total_cost_actual = 0

for cat_name, pos in categories:
    with st.expander(cat_name):
        c.execute(
            "SELECT item_id, name, budget, actual, date FROM items "
            "WHERE month=? AND category=? ORDER BY item_id",
            (month, cat_name)
        )
        items = c.fetchall()

        for item_id, item_name, budget_val, actual_val, date_val in items:
            col_b, col_a, col_d = st.columns(3)

            with col_b:
                b_new = st.number_input(
                    f"{item_name} – Budget (€)",
                    value=budget_val,
                    key=f"{month}_{item_id}_b"
                )

            with col_a:
                a_new = st.number_input(
                    f"{item_name} – Faktiskt (€)",
                    value=actual_val,
                    key=f"{month}_{item_id}_a"
                )

            with col_d:
                d_new = st.date_input(
                    "Datum",
                    value=datetime.datetime.strptime(
                        date_val, "%Y-%m-%d"
                    ).date() if date_val else datetime.date.today(),
                    key=f"{month}_{item_id}_d"
                )

            if b_new != budget_val or a_new != actual_val or d_new != date_val:
                c.execute(
                    "UPDATE items SET budget=?, actual=?, date=? "
                    "WHERE month=? AND item_id=?",
                    (b_new, a_new, d_new, month, item_id)
                )

                for m in months:
                    if m != month:
                        c.execute(
                            "UPDATE items SET budget=? "
                            "WHERE month=? AND category=? AND name=?",
                            (b_new, m, cat_name, item_name)
                        )
                conn.commit()

            if cat_name.lower() == "inkomster":
                row_class = "green-row" if a_new >= b_new else "red-row"
                total_income_budget += b_new
                total_income_actual += a_new
            else:
                row_class = "green-row" if a_new <= b_new else "red-row"
                total_cost_budget += b_new
                total_cost_actual += a_new

            st.markdown(
                f'<div class="{row_class}">{item_name} – '
                f'Budget: {b_new} | Faktiskt: {a_new} | Datum: {d_new}</div>',
                unsafe_allow_html=True
            )

# =========================
# Sammanfattning
# =========================
st.subheader("📊 Sammanfattning")
col1, col2, col3 = st.columns(3)

col1.metric(
    "Totala inkomster",
    f"€{total_income_actual:.2f}",
    f"Budget: €{total_income_budget:.2f}"
)

col2.metric(
    "Totala kostnader",
    f"€{total_cost_actual:.2f}",
    f"Budget: €{total_cost_budget:.2f}"
)

col3.metric(
    "💰 Kvar att använda / spara",
    f"€{total_income_actual - total_cost_actual:.2f}",
    f"Budget: €{total_income_budget - total_cost_budget:.2f}"
)
