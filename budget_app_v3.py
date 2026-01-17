import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import date

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
# SQLite Setup
# =========================
DB_FILE = "budget.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# Tabeller
c.execute("""
CREATE TABLE IF NOT EXISTS categories (
    month TEXT,
    cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
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
    PRIMARY KEY(user, month, name)
)
""")
conn.commit()

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
            st.session_state.username = u
            st.stop()
        else:
            st.error("Fel uppgifter")
    st.stop()

# =========================
# Layout: Vänsterpanel
# =========================
with st.sidebar:
    st.header("Välj månad")
    months = ["Januari","Februari","Mars","April","Maj","Juni","Juli","Augusti","September","Oktober","November","December"]
    month = st.selectbox("Månad", months)

    st.divider()
    st.header("Rubriker")
    c.execute("SELECT name FROM categories WHERE month=? ORDER BY cat_id", (month,))
    categories = [r[0] for r in c.fetchall()]
    selected_summary = st.selectbox("Visa sammanfattning för:", ["Alla"] + categories)
    
    st.divider()
    show_cashflow = st.checkbox("Visa kassaflöde", value=True)
    show_year = st.checkbox("Visa årsöversikt", value=True)
    show_notes = st.checkbox("Visa anteckningar", value=True)
    
    st.divider()
    if st.button("Logga ut"):
        st.session_state.clear()
        st.stop()

# =========================
# Anteckningar
# =========================
if show_notes:
    c.execute("SELECT content FROM notes WHERE month=?", (month,))
    note_text = c.fetchone()
    note_text = note_text[0] if note_text else ""
    new_note = st.text_area(f"📝 Anteckningar - {month}", value=note_text, height=120)
    if new_note != note_text:
        c.execute("INSERT OR REPLACE INTO notes (month, content) VALUES (?,?)", (month, new_note))
        conn.commit()

# =========================
# Hantera rubriker / underrubriker
# =========================
st.subheader("Rubriker / Underrubriker")
new_cat = st.text_input("Ny rubrik")
if st.button("Lägg till rubrik") and new_cat:
    if new_cat not in categories:
        c.execute("INSERT INTO categories(month,name) VALUES(?,?)",(month,new_cat))
        conn.commit()
        st.experimental_rerun()

# Visa rubriker och underrubriker på huvudsidan
total_income_budget = 0
total_income_actual = 0
total_cost_budget = 0
total_cost_actual = 0

for cat in categories:
    c.execute("SELECT name,budget,actual FROM items WHERE month=? AND category=? ORDER BY item_id",(month,cat))
    items = c.fetchall()
    with st.expander(f"{cat}"):
        new_item = st.text_input(f"Lägg till underrubrik under {cat}", key=f"add_{cat}")
        if st.button(f"Lägg till {cat}", key=f"btn_{cat}"):
            if new_item:
                c.execute("INSERT INTO items(month,category,name,budget,actual) VALUES(?,?,?,?,?)",
                          (month, cat, new_item,0.0,0.0))
                conn.commit()
                st.experimental_rerun()
        
        cat_budget = 0
        cat_actual = 0
        for item_name, budget_val, actual_val in items:
            row_class = "green-row" if (cat.lower()=="inkomster" and actual_val>=budget_val) or (cat.lower()!="inkomster" and actual_val<=budget_val) else "red-row"
            col_b, col_a = st.columns(2)
            with col_b:
                b_new = st.number_input(f"{item_name} – Budget (€)", value=budget_val, key=f"{month}_{cat}_{item_name}_b")
            with col_a:
                a_new = st.number_input(f"{item_name} – Faktiskt (€)", value=actual_val, key=f"{month}_{cat}_{item_name}_a")
            # Spara i DB om ändrat
            if b_new!=budget_val or a_new!=actual_val:
                c.execute("UPDATE items SET budget=?, actual=? WHERE month=? AND category=? AND name=?",
                          (b_new,a_new,month,cat,item_name))
                conn.commit()
            cat_budget += b_new
            cat_actual += a_new
        st.markdown(f"**Summa budget {cat}:** €{cat_budget:.2f}")
        st.markdown(f"**Summa faktiskt {cat}:** €{cat_actual:.2f}")
        if cat.lower()=="inkomster":
            total_income_budget += cat_budget
            total_income_actual += cat_actual
        else:
            total_cost_budget += cat_budget
            total_cost_actual += cat_actual

# =========================
# Sammanfattning (valbar rubrik/alla)
# =========================
st.divider()
st.subheader("📊 Sammanfattning")
if selected_summary=="Alla":
    sum_budget = total_income_budget + total_cost_budget
    sum_actual = total_income_actual + total_cost_actual
    kvar_budget = total_income_budget - total_cost_budget
    kvar_actual = total_income_actual - total_cost_actual
else:
    # Summera vald rubrik
    c.execute("SELECT SUM(budget),SUM(actual) FROM items WHERE month=? AND category=?",(month,selected_summary))
    row = c.fetchone()
    sum_budget = row[0] or 0
    sum_actual = row[1] or 0
    kvar_budget = sum_budget
    kvar_actual = sum_actual

col1,col2,col3 = st.columns(3)
col1.metric("Totalt Budget", f"€{sum_budget:.2f}")
col2.metric("Totalt Faktiskt", f"€{sum_actual:.2f}")
col3.metric("Kvar att använda", f"€{kvar_actual:.2f}", f"Budget: €{kvar_budget:.2f}")

# =========================
# Kassaflöde
# =========================
if show_cashflow:
    st.divider()
    st.subheader("💰 Kassaflöde / Lönedatum")
    # Tabell med inkomster per datum
    c.execute("SELECT name,amount,pay_date FROM cashflow WHERE user=? AND month=?",(st.session_state.username,month))
    cash_rows = c.fetchall()
    if cash_rows:
        df_cash = pd.DataFrame(cash_rows,columns=["Beskrivning","Belopp","Datum"])
        st.table(df_cash)
        total_cash = df_cash["Belopp"].sum()
        st.markdown(f"Totala inkomster: €{total_cash:.2f}")

# =========================
# Årsöversikt
# =========================
if show_year:
    st.divider()
    st.subheader("📅 Årsöversikt")
    summary_list=[]
    for m in months:
        c.execute("SELECT SUM(actual), SUM(budget) FROM items WHERE month=? AND category='Inkomster'",(m,))
        income_row = c.fetchone()
        income_actual = income_row[0] or 0
        income_budget = income_row[1] or 0
        c.execute("SELECT SUM(actual), SUM(budget) FROM items WHERE month=? AND category<>'Inkomster'",(m,))
        cost_row = c.fetchone()
        cost_actual = cost_row[0] or 0
        cost_budget = cost_row[1] or 0
        summary_list.append({
            "Månad":m,
            "Inkomster_Budget":income_budget,
            "Inkomster_Faktiskt":income_actual,
            "Kostnader_Budget":cost_budget,
            "Kostnader_Faktiskt":cost_actual,
            "Kvar_Budget":income_budget-cost_budget,
            "Kvar_Faktiskt":income_actual-cost_actual
        })
    df_year = pd.DataFrame(summary_list)
    df_melted = df_year.melt(id_vars="Månad", var_name="Typ", value_name="€")
    chart_year = alt.Chart(df_melted).mark_bar().encode(
        x=alt.X('Månad:N'),
        y=alt.Y('€:Q'),
        color=alt.Color('Typ:N', scale=alt.Scale(range=['#87CEFA','#32CD32','#FFB347','#FF6347','#87CEFA','#32CD32'])),
        tooltip=['Månad','Typ','€']
    ).properties(width=700, height=400)
    st.altair_chart(chart_year, use_container_width=True)
