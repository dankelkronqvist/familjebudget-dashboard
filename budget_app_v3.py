import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

# =========================
# App config
# =========================
st.set_page_config(
    page_title="Familjebudget",
    layout="wide"
)

# =========================
# Database
# =========================
conn = sqlite3.connect("budget.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS budget_items (
    user TEXT,
    month TEXT,
    category TEXT,
    subcategory TEXT,
    budget REAL,
    actual REAL,
    entry_date TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS income (
    user TEXT,
    month TEXT,
    name TEXT,
    amount REAL,
    pay_date TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS notes (
    user TEXT,
    month TEXT,
    title TEXT,
    content TEXT
)
""")

conn.commit()

# =========================
# Login
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

if not st.session_state.logged_in:
    st.title("🔐 Logga in")
    user = st.text_input("Användarnamn")

    if st.button("Logga in"):
        if user:
            c.execute("INSERT OR IGNORE INTO users VALUES (?)", (user,))
            conn.commit()
            st.session_state.logged_in = True
            st.session_state.user = user
            st.rerun()
    st.stop()

USER = st.session_state.user

# =========================
# Sidebar – Layout control
# =========================
with st.sidebar:
    st.header("📅 Månader")
    months = [
        "Januari","Februari","Mars","April","Maj","Juni",
        "Juli","Augusti","September","Oktober","November","December"
    ]
    month = st.selectbox("Välj månad", months)

    st.divider()
    st.header("🧩 Visa sektioner")
    show_overview = st.checkbox("Månadsöversikt", True)
    show_cashflow = st.checkbox("Kassaflöde", True)
    show_year = st.checkbox("Årsöversikt", True)
    show_notes = st.checkbox("Anteckningar", True)

    st.divider()
    if st.button("🚪 Logga ut"):
        st.session_state.clear()
        st.rerun()

# =========================
# Helper functions
# =========================
def load_budget():
    return pd.read_sql("""
        SELECT * FROM budget_items
        WHERE user=? AND month=?
    """, conn, params=(USER, month))

def load_income():
    return pd.read_sql("""
        SELECT * FROM income
        WHERE user=? AND month=?
        ORDER BY pay_date
    """, conn, params=(USER, month))

# =========================
# MAIN
# =========================
st.title(f"📊 Familjebudget – {month}")

# =========================
# Budget input
# =========================
with st.expander("➕ Lägg till budget / kostnad", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        category = st.text_input("Rubrik (t.ex. Inkomst / Boende)")
    with col2:
        subcategory = st.text_input("Underrubrik")
    with col3:
        budget = st.number_input("Budget", 0.0, step=10.0)
    with col4:
        actual = st.number_input("Faktisk", 0.0, step=10.0)

    entry_date = st.date_input("Datum", value=date.today())

    if st.button("💾 Spara post"):
        c.execute("""
            INSERT INTO budget_items
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            USER, month, category, subcategory,
            budget, actual, entry_date.isoformat()
        ))
        conn.commit()
        st.success("Sparat")

# =========================
# Overview
# =========================
df = load_budget()

if show_overview:
    st.subheader("📌 Månadsöversikt")

    if not df.empty:
        summary = df.groupby("category")[["budget", "actual"]].sum().reset_index()
        summary["diff"] = summary["budget"] - summary["actual"]

        def color_row(row):
            if row["category"].lower() == "inkomst":
                return ["background-color: lightgreen"] * len(row)
            return ["background-color: lightcoral" if row["diff"] < 0 else "" ] * len(row)

        st.dataframe(
            summary.style.apply(color_row, axis=1),
            use_container_width=True
        )

# =========================
# Cashflow
# =========================
if show_cashflow:
    st.subheader("💸 Kassaflöde")

    df_income = load_income()

    with st.expander("➕ Lägg till inkomst"):
        name = st.text_input("Inkomstnamn")
        amount = st.number_input("Belopp", 0.0, step=10.0)
        pay_date = st.date_input("Utbetalningsdatum")

        if st.button("Spara inkomst"):
            c.execute("""
                INSERT INTO income VALUES (?, ?, ?, ?, ?)
            """, (USER, month, name, amount, pay_date.isoformat()))
            conn.commit()
            st.success("Inkomst sparad")

    if not df_income.empty:
        st.dataframe(df_income, use_container_width=True)
        st.line_chart(df_income.set_index("pay_date")["amount"])

# =========================
# Year overview
# =========================
if show_year:
    st.subheader("📆 Årsöversikt")
    year_df = pd.read_sql("""
        SELECT month, SUM(actual) AS total
        FROM budget_items
        WHERE user=?
        GROUP BY month
    """, conn, params=(USER,))
    if not year_df.empty:
        st.bar_chart(year_df.set_index("month"))

# =========================
# Notes
# =========================
if show_notes:
    st.subheader(f"📝 Anteckningar – {month}")

    note_title = st.text_input("Rubrik")
    note_text = st.text_area("Anteckning")

    if st.button("Spara anteckning"):
        c.execute("""
            INSERT INTO notes VALUES (?, ?, ?, ?)
        """, (USER, month, note_title, note_text))
        conn.commit()

    notes_df = pd.read_sql("""
        SELECT title, content FROM notes
        WHERE user=? AND month=?
    """, conn, params=(USER, month))

    if not notes_df.empty:
        for _, r in notes_df.iterrows():
            with st.expander(r["title"]):
                st.write(r["content"])
