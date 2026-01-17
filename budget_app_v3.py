import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

st.set_page_config(page_title="Familjebudget", layout="wide")

# =========================
# Database
# =========================
conn = sqlite3.connect("budget.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY)""")
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

if not st.session_state.logged_in:
    st.title("🔐 Logga in")
    user = st.text_input("Användarnamn")
    if st.button("Logga in") and user:
        c.execute("INSERT OR IGNORE INTO users VALUES (?)", (user,))
        conn.commit()
        st.session_state.logged_in = True
        st.session_state.user = user
        st.rerun()
    st.stop()

USER = st.session_state.user

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
    st.header("👁 Visa sektioner")
    show_overview = st.checkbox("Månadsöversikt", True)
    show_budget = st.checkbox("Budget & kostnader", True)
    show_cashflow = st.checkbox("Kassaflöde", True)
    show_year = st.checkbox("Årsöversikt", True)
    show_notes = st.checkbox("Anteckningar", True)

    st.divider()
    if st.button("🚪 Logga ut"):
        st.session_state.clear()
        st.rerun()

# =========================
# Helpers
# =========================
def load_budget():
    return pd.read_sql(
        "SELECT * FROM budget_items WHERE user=? AND month=?",
        conn, params=(USER, month)
    )

def load_income():
    return pd.read_sql(
        "SELECT * FROM income WHERE user=? AND month=? ORDER BY pay_date",
        conn, params=(USER, month)
    )

df = load_budget()

st.title(f"📊 Familjebudget – {month}")

# =========================
# Månadsöversikt (DROPDOWN)
# =========================
if show_overview:
    with st.expander("📌 Månadsöversikt", expanded=True):
        if not df.empty:
            summary = df.groupby("category")[["budget","actual"]].sum().reset_index()
            summary["diff"] = summary["budget"] - summary["actual"]

            def style_row(row):
                if row["category"].lower() == "inkomst":
                    return ["background-color:#d4f8d4"] * len(row)
                if row["diff"] < 0:
                    return ["background-color:#ffd6d6"] * len(row)
                return [""] * len(row)

            st.dataframe(
                summary.style.apply(style_row, axis=1),
                use_container_width=True
            )
        else:
            st.info("Ingen data ännu")

# =========================
# Budget & kostnader
# =========================
if show_budget:
    with st.expander("💰 Budget & kostnader", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        category = col1.text_input("Rubrik")
        subcategory = col2.text_input("Underrubrik")
        budget = col3.number_input("Budget", 0.0, step=10.0)
        actual = col4.number_input("Faktisk", 0.0, step=10.0)
        entry_date = st.date_input("Datum", value=date.today())

        if st.button("💾 Spara"):
            c.execute("""
                INSERT INTO budget_items VALUES (?,?,?,?,?,?,?)
            """, (
                USER, month, category, subcategory,
                budget, actual, entry_date.isoformat()
            ))
            conn.commit()
            st.success("Sparat")

        if not df.empty:
            for cat in df["category"].unique():
                with st.expander(cat):
                    st.dataframe(
                        df[df["category"] == cat][
                            ["subcategory","budget","actual","entry_date"]
                        ],
                        use_container_width=True
                    )

# =========================
# Kassaflöde
# =========================
if show_cashflow:
    with st.expander("💸 Kassaflöde", expanded=False):
        name = st.text_input("Inkomstnamn")
        amount = st.number_input("Belopp", 0.0, step=100.0)
        pay_date = st.date_input("Utbetalningsdatum")

        if st.button("Spara inkomst"):
            c.execute(
                "INSERT INTO income VALUES (?,?,?,?,?)",
                (USER, month, name, amount, pay_date.isoformat())
            )
            conn.commit()
            st.success("Inkomst sparad")

        income_df = load_income()
        if not income_df.empty:
            st.dataframe(income_df, use_container_width=True)
            st.line_chart(income_df.set_index("pay_date")["amount"])

# =========================
# Årsöversikt
# =========================
if show_year:
    with st.expander("📆 Årsöversikt", expanded=False):
        year_df = pd.read_sql("""
            SELECT month, SUM(actual) AS total
            FROM budget_items
            WHERE user=?
            GROUP BY month
        """, conn, params=(USER,))
        if not year_df.empty:
            st.bar_chart(year_df.set_index("month"))

# =========================
# Anteckningar
# =========================
if show_notes:
    with st.expander("📝 Anteckningar", expanded=True):
        title = st.text_input("Rubrik")
        content = st.text_area("Anteckning")

        if st.button("Spara anteckning"):
            c.execute(
                "INSERT INTO notes VALUES (?,?,?,?)",
                (USER, month, title, content)
            )
            conn.commit()
            st.success("Anteckning sparad")

        notes = pd.read_sql(
            "SELECT title, content FROM notes WHERE user=? AND month=?",
            conn, params=(USER, month)
        )

        for _, n in notes.iterrows():
            with st.expander(n["title"]):
                st.write(n["content"])
