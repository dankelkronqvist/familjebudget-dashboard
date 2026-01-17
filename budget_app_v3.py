import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import date

# =========================
# Session init
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

# =========================
# Users (login)
# =========================
users = {"admin": "1234"}

if not st.session_state.logged_in:
    st.title("🔐 Logga in")
    username_input = st.text_input("Användarnamn")
    password_input = st.text_input("Lösenord", type="password")
    if st.button("Logga in"):
        if username_input in users and password_input == users[username_input]:
            st.session_state.logged_in = True
            st.session_state.username = username_input
            st.stop()  # Stoppa render så sidan laddas om med inloggning
        else:
            st.error("Fel uppgifter")
    st.stop()

# =========================
# Layout: vänsterpanel + huvudsida
# =========================
sidebar_col, main_col = st.columns([1,3])

# =========================
# SQLite setup
# =========================
DB_FILE = "budget.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# Tabeller
c.execute("""
CREATE TABLE IF NOT EXISTS categories (
    month TEXT,
    cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    order_num INTEGER
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT,
    category TEXT,
    name TEXT,
    budget REAL,
    actual REAL
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS notes (
    month TEXT PRIMARY KEY,
    content TEXT
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS cashflow (
    user TEXT,
    month TEXT,
    name TEXT,
    amount REAL,
    pay_date TEXT,
    PRIMARY KEY(user,month,name)
)
""")
conn.commit()

# =========================
# Sidebar
# =========================
with sidebar_col:
    st.header("Kontrollpanel")
    # Månad
    months = ["Januari","Februari","Mars","April","Maj","Juni",
              "Juli","Augusti","September","Oktober","November","December"]
    month = st.selectbox("📅 Välj månad", months)

    # Lägg till rubrik
    st.subheader("➕ Rubriker")
    new_cat = st.text_input("Ny rubrik")
    if st.button("Lägg till rubrik"):
        if new_cat:
            c.execute("SELECT MAX(order_num) FROM categories WHERE month=?", (month,))
            max_order = c.fetchone()[0] or 0
            c.execute("INSERT INTO categories(month,name,order_num) VALUES(?,?,?)",
                      (month,new_cat,max_order+1))
            conn.commit()
            st.stop()  # Stoppa render för att sidan laddas om med ny rubrik

    # Hämta rubriker
    c.execute("SELECT name FROM categories WHERE month=? ORDER BY order_num", (month,))
    categories = [r[0] for r in c.fetchall()]

    # Lista rubriker med checkbox för visning
    st.subheader("Visa rubriker på huvudsida")
    show_rubrik = {}
    for cat in categories:
        show_rubrik[cat] = st.checkbox(cat, value=True)

    # Checkboxar för extra vyer
    st.divider()
    st.subheader("Extra vyer")
    show_cashflow = st.checkbox("Visa kassaflöde", value=True)
    show_yearly = st.checkbox("Visa årsöversikt", value=True)
    show_notes = st.checkbox("Visa anteckningar", value=True)

    st.divider()
    if st.button("Logga ut"):
        st.session_state.clear()
        st.stop()

# =========================
# Huvudsida
# =========================
with main_col:
    st.title(f"Månad: {month}")

    total_income_budget = 0
    total_income_actual = 0
    total_cost_budget = 0
    total_cost_actual = 0

    for cat in categories:
        if not show_rubrik.get(cat, True):
            continue  # Hoppa över rubrik som inte ska visas

        with st.expander(cat, expanded=True):
            # Lägg till underrubrik
            new_item = st.text_input(f"Lägg till underrubrik under {cat}", key=f"add_{cat}")
            if st.button(f"Lägg till {cat}", key=f"btn_{cat}"):
                if new_item:
                    c.execute("INSERT INTO items(month,category,name,budget,actual) VALUES(?,?,?,?,?)",
                              (month,cat,new_item,0.0,0.0))
                    conn.commit()
                    st.stop()

            # Hämta underrubriker
            c.execute("SELECT item_id,name,budget,actual FROM items WHERE month=? AND category=? ORDER BY item_id",
                      (month,cat))
            items = c.fetchall()

            cat_budget = 0
            cat_actual = 0

            for item_id, item_name, budget_val, actual_val in items:
                row_class = "green-row" if (cat.lower() == "inkomster" and actual_val >= budget_val) else \
                            "green-row" if actual_val <= budget_val else "red-row"

                col_b, col_a = st.columns(2)
                with col_b:
                    b_new = st.number_input(f"{item_name} – Budget (€)", value=budget_val,
                                            key=f"{month}_{cat}_{item_id}_b")
                with col_a:
                    a_new = st.number_input(f"{item_name} – Faktiskt (€)", value=actual_val,
                                            key=f"{month}_{cat}_{item_id}_a")

                # Spara ändringar
                if b_new != budget_val or a_new != actual_val:
                    c.execute("UPDATE items SET budget=?, actual=? WHERE item_id=?",
                              (b_new,a_new,item_id))
                    conn.commit()

                cat_budget += b_new
                cat_actual += a_new

            st.markdown(f"**Summa budget:** €{cat_budget:.2f}")
            st.markdown(f"**Summa faktiskt:** €{cat_actual:.2f}")

            if cat.lower() == "inkomster":
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
    col1, col2, col3 = st.columns(3)
    col1.metric("Totala inkomster", f"€{total_income_actual:.2f}", f"Budget: €{total_income_budget:.2f}")
    col2.metric("Totala kostnader", f"€{total_cost_actual:.2f}", f"Budget: €{total_cost_budget:.2f}")
    col3.metric("💰 Kvar att använda / spara", f"€{total_income_actual - total_cost_actual:.2f}",
                f"Budget: €{total_income_budget - total_cost_budget:.2f}")

    # =========================
    # Diagram
    # =========================
    st.divider()
    st.subheader("📈 Diagram: Budget vs Faktiskt")

    df_chart = pd.DataFrame({
        "Kategori": ["Inkomster","Kostnader","Kvar att spara"],
        "Budget": [total_income_budget,total_cost_budget,total_income_budget-total_cost_budget],
        "Faktiskt": [total_income_actual,total_cost_actual,total_income_actual-total_cost_actual]
    })
    df_melted = df_chart.melt(id_vars="Kategori", var_name="Typ", value_name="€")
    chart = alt.Chart(df_melted).mark_bar().encode(
        x='Kategori:N',
        y='€:Q',
        color=alt.Color('Typ:N', scale=alt.Scale(range=['#cccccc','#fff3b0'])),
        tooltip=['Kategori','Typ','€']
    ).properties(width=600, height=400)
    st.altair_chart(chart)

# =========================
# Anteckningar
# =========================
if show_notes:
    st.divider()
    st.subheader("📝 Anteckningar")
    c.execute("SELECT content FROM notes WHERE month=?", (month,))
    row = c.fetchone()
    note_text = row[0] if row else ""
    new_note = st.text_area("Anteckningar", value=note_text, height=120)
    if new_note != note_text:
        c.execute("INSERT OR REPLACE INTO notes(month,content) VALUES(?,?)", (month,new_note))
        conn.commit()

# =========================
# Kassaflöde
# =========================
if show_cashflow:
    st.divider()
    st.subheader("💰 Kassaflöde")
    st.info("Lägg till löner här, automatiskt betalningsförslag kommer sedan.")
