import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import date, datetime

# =========================
# CSS
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
    name TEXT,
    order_num INTEGER DEFAULT 0
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
    due_date TEXT
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
users = {"admin":"1234", "dani":"pass"}  # Exempel multi-user
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
            st.experimental_rerun()
        else:
            st.error("Fel uppgifter")
    st.stop()

# =========================
# Vänsterpanel
# =========================
with st.sidebar:
    st.header("Månad / Rubriker")
    months = ["Januari","Februari","Mars","April","Maj","Juni","Juli","Augusti","September","Oktober","November","December"]
    month = st.selectbox("Välj månad", months)

    # Hantera rubriker
    c.execute("SELECT name,order_num FROM categories WHERE month=? ORDER BY order_num", (month,))
    categories = c.fetchall()
    category_names = [c[0] for c in categories]

    new_cat = st.text_input("Ny rubrik")
    if st.button("Lägg till rubrik"):
        if new_cat and new_cat not in category_names:
            max_order = max([c[1] for c in categories], default=0)
            c.execute("INSERT INTO categories(month,name,order_num) VALUES(?,?,?)",(month,new_cat,max_order+1))
            conn.commit()
            st.experimental_rerun()

    # Toggle för vad som syns på huvudsidan
    show_summary = st.checkbox("Visa Sammanfattning", value=True)
    show_cashflow = st.checkbox("Visa Kassaflöde", value=True)
    show_year = st.checkbox("Visa Årsöversikt", value=True)
    show_notes = st.checkbox("Visa Anteckningar", value=True)
    show_mealplan = st.checkbox("Visa Veckoplanering", value=True)

    st.markdown("---")
    if st.button("Logga ut"):
        st.session_state.clear()
        st.experimental_rerun()

# =========================
# Anteckningar
# =========================
if show_notes:
    c.execute("SELECT content FROM notes WHERE month=?", (month,))
    note_text = c.fetchone()
    note_text = note_text[0] if note_text else ""
    new_note = st.text_area(f"📝 Anteckningar - {month}", value=note_text, height=120)
    if new_note != note_text:
        c.execute("INSERT OR REPLACE INTO notes(month,content) VALUES(?,?)",(month,new_note))
        conn.commit()

# =========================
# Huvudsida – Rubriker och underrubriker
# =========================
st.header(f"💼 Budget – {month}")

total_income_budget = 0
total_income_actual = 0
total_cost_budget = 0
total_cost_actual = 0

for cat, order in categories:
    c.execute("SELECT item_id,name,budget,actual,due_date FROM items WHERE month=? AND category=? ORDER BY item_id",(month,cat))
    items = c.fetchall()
    with st.expander(cat):
        # Lägg till ny underrubrik
        new_item = st.text_input(f"Lägg till underrubrik under {cat}", key=f"add_{cat}")
        if st.button(f"Lägg till {cat}", key=f"btn_{cat}"):
            if new_item:
                c.execute("INSERT INTO items(month,category,name,budget,actual) VALUES(?,?,?,?,?)",(month,cat,new_item,0.0,0.0))
                conn.commit()
                st.experimental_rerun()

        cat_budget = 0
        cat_actual = 0
        for item_id, item_name, budget_val, actual_val, due_date in items:
            row_class = "green-row" if (cat.lower()=="inkomster" and actual_val>=budget_val) or (cat.lower()!="inkomster" and actual_val<=budget_val) else "red-row"
            col_b, col_a, col_date = st.columns([2,2,2])
            with col_b:
                b_new = st.number_input(f"{item_name} – Budget (€)", value=budget_val, key=f"{month}_{cat}_{item_id}_b")
            with col_a:
                a_new = st.number_input(f"{item_name} – Faktiskt (€)", value=actual_val, key=f"{month}_{cat}_{item_id}_a")
            with col_date:
                date_new = st.date_input(f"Förfallodatum", value=datetime.today() if not due_date else datetime.strptime(due_date,"%Y-%m-%d"), key=f"{month}_{cat}_{item_id}_d")
            if b_new!=budget_val or a_new!=actual_val or date_new.strftime("%Y-%m-%d")!=due_date:
                c.execute("UPDATE items SET budget=?,actual=?,due_date=? WHERE item_id=?",(b_new,a_new,date_new.strftime("%Y-%m-%d"),item_id))
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
# Sammanfattning
# =========================
if show_summary:
    st.divider()
    st.subheader("📊 Sammanfattning")
    col1,col2,col3 = st.columns(3)
    col1.metric("Totalt Budget", f"€{total_income_budget+total_cost_budget:.2f}")
    col2.metric("Totalt Faktiskt", f"€{total_income_actual+total_cost_actual:.2f}")
    col3.metric("Kvar att använda", f"€{total_income_actual-total_cost_actual:.2f}", f"Budget: €{total_income_budget-total_cost_budget:.2f}")

# =========================
# Kassaflöde
# =========================
if show_cashflow:
    st.divider()
    st.subheader("💰 Kassaflöde")
    c.execute("SELECT name,amount,pay_date FROM cashflow WHERE user=? AND month=?",(st.session_state.username,month))
    rows = c.fetchall()
    if rows:
        df_cash = pd.DataFrame(rows,columns=["Beskrivning","Belopp","Datum"])
        st.table(df_cash)
        st.markdown(f"Totala inkomster: €{df_cash['Belopp'].sum():.2f}")

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
