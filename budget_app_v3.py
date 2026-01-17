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

# Logout-knapp
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

# Skapa tabeller
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
c.execute("""
CREATE TABLE IF NOT EXISTS sections (
    month TEXT,
    name TEXT,
    position INTEGER,
    visible INTEGER DEFAULT 1,
    PRIMARY KEY(month,name)
)
""")
conn.commit()

# =========================
# Månad
# =========================
months = [
    "Januari","Februari","Mars","April","Maj","Juni",
    "Juli","Augusti","September","Oktober","November","December"
]
st.sidebar.subheader("📅 Månader")
month = st.sidebar.selectbox("Månad", months, index=0)
st.title(f"📌 {month}")

# =========================
# Standard sektioner
# =========================
default_sections = ["Anteckningar", "Kassaflöde", "Årsöversikt", "Veckoplanering", "Kalender", "Månadsöversikt"]
for sec in default_sections:
    c.execute("INSERT OR IGNORE INTO sections (month,name,position,visible) VALUES (?,?,?,?)",
              (month, sec, default_sections.index(sec), 1))
conn.commit()

# =========================
# Vänsterpanel – Flyttbara sektioner + synlighet
# =========================
st.sidebar.subheader("Sektioner")
c.execute("SELECT name, position, visible FROM sections WHERE month=? ORDER BY position", (month,))
sections = c.fetchall()

section_order = []
section_visibility = {}

for name, pos, vis in sections:
    col1, col2, col3 = st.sidebar.columns([1,1,4])
    with col1:
        if st.button("⬆", key=f"up_{name}"):
            if pos>0:
                c.execute("UPDATE sections SET position=? WHERE month=? AND position=?",(pos-1,month,pos-1))
                c.execute("UPDATE sections SET position=? WHERE month=? AND name=?",(pos,month,name))
                conn.commit()
                st.session_state["reload"] = not st.session_state.get("reload", False)
                st.stop()
    with col2:
        if st.button("⬇", key=f"down_{name}"):
            c.execute("SELECT MAX(position) FROM sections WHERE month=?",(month,))
            max_pos = c.fetchone()[0]
            if pos<max_pos:
                c.execute("UPDATE sections SET position=? WHERE month=? AND position=?",(pos+1,month,pos+1))
                c.execute("UPDATE sections SET position=? WHERE month=? AND name=?",(pos,month,name))
                conn.commit()
                st.session_state["reload"] = not st.session_state.get("reload", False)
                st.stop()
    with col3:
        visible = st.checkbox(name, value=bool(vis), key=f"chk_{name}")
        c.execute("UPDATE sections SET visible=? WHERE month=? AND name=?",(1 if visible else 0, month, name))
        conn.commit()
    section_order.append(name)
    section_visibility[name] = visible

# =========================
# Funktion för färgkod
# =========================
def get_row_class(cat_name, actual, budget):
    if cat_name.lower()=="inkomster":
        return "green-row" if actual >= budget else "red-row"
    else:
        return "green-row" if actual <= budget else "red-row"

# =========================
# Huvudpanelen – sektioner i vänsterpanelens ordning
# =========================
total_income_budget = 0
total_income_actual = 0
total_cost_budget = 0
total_cost_actual = 0

for sec_name in section_order:
    if not section_visibility.get(sec_name, True):
        continue

    if sec_name=="Anteckningar":
        st.subheader("📝 Anteckningar")
        c.execute("SELECT content FROM notes WHERE month=?",(month,))
        row = c.fetchone()
        note_text = row[0] if row else ""
        new_note = st.text_area("Anteckningar", value=note_text, height=120)
        if new_note != note_text:
            c.execute("INSERT OR REPLACE INTO notes (month, content) VALUES (?,?)",(month,new_note))
            conn.commit()

    elif sec_name=="Kassaflöde":
        st.subheader("💵 Kassaflöde")
        c.execute("SELECT name,budget,actual FROM items WHERE month=?",(month,))
        items = c.fetchall()
        for name, b, a in items:
            st.write(f"{name}: Budget €{b} | Faktiskt €{a}")

    elif sec_name=="Årsöversikt":
        st.subheader("📊 Årsöversikt")
        summary_list = []
        for m in months:
            c.execute("SELECT SUM(actual), SUM(budget) FROM items WHERE month=? AND category='Inkomster'",(m,))
            income_row = c.fetchone()
            income_actual = income_row[0] or 0
            income_budget = income_row[1] or 0
            c.execute("SELECT SUM(actual), SUM(budget) FROM items WHERE month=? AND category<>'Inkomster'",(m,))
            cost_row = c.fetchone()
            cost_actual = cost_row[0] or 0
            cost_budget = cost_row[1] or 0
            summary_list.append({"Månad":m,"Inkomster_Budget":income_budget,"Inkomster_Faktiskt":income_actual,
                                 "Kostnader_Budget":cost_budget,"Kostnader_Faktiskt":cost_actual,
                                 "Kvar_Budget":income_budget-cost_budget,"Kvar_Faktiskt":income_actual-cost_actual})
        df_year = pd.DataFrame(summary_list)
        df_melted_year = df_year.melt(id_vars="Månad",
                                      value_vars=["Inkomster_Budget","Inkomster_Faktiskt",
                                                  "Kostnader_Budget","Kostnader_Faktiskt",
                                                  "Kvar_Budget","Kvar_Faktiskt"],
                                      var_name="Typ", value_name="€")
        chart_year = alt.Chart(df_melted_year).mark_bar().encode(
            x='Månad:N',
            y='€:Q',
            color='Typ:N',
            tooltip=['Månad','Typ','€']
        ).properties(width=700,height=350)
        st.altair_chart(chart_year, use_container_width=True)

    elif sec_name=="Veckoplanering":
        st.subheader("📅 Veckoplanering")
        days = ["Måndag","Tisdag","Onsdag","Torsdag","Fredag","Lördag","Söndag"]
        for day in days:
            c.execute("SELECT meal FROM meals WHERE month=? AND day=?",(month,day))
            row = c.fetchone()
            meal_text = row[0] if row else ""
            new_meal = st.text_input(f"{day}", value=meal_text, key=f"meal_{day}")
            if new_meal != meal_text:
                c.execute("INSERT OR REPLACE INTO meals (month, day, meal) VALUES (?,?,?)",(month,day,new_meal))
                conn.commit()

    elif sec_name=="Kalender":
        st.subheader("📆 Kalender")
        today = datetime.date.today()
        cal_date = st.date_input("Välj datum", value=today, key="calendar_date")
        c.execute("SELECT description FROM events WHERE month=? AND date=?",(month,cal_date))
        row = c.fetchone()
        desc_text = row[0] if row else ""
        new_desc = st.text_input("Händelse", value=desc_text, key=f"event_{cal_date}")
        if new_desc != desc_text:
            c.execute("INSERT OR REPLACE INTO events (month, date, description) VALUES (?,?,?)",(month,cal_date,new_desc))
            conn.commit()

    elif sec_name=="Månadsöversikt":
        st.subheader("📈 Månadsöversikt")
        summary_list = []
        for m in months:
            c.execute("SELECT SUM(actual), SUM(budget) FROM items WHERE month=? AND category='Inkomster'",(m,))
            income_row = c.fetchone()
            income_actual = income_row[0] or 0
            income_budget = income_row[1] or 0
            c.execute("SELECT SUM(actual), SUM(budget) FROM items WHERE month=? AND category<>'Inkomster'",(m,))
            cost_row = c.fetchone()
            cost_actual = cost_row[0] or 0
            cost_budget = cost_row[1] or 0
            summary_list.append({"Månad":m,"Inkomster_Budget":income_budget,"Inkomster_Faktiskt":income_actual,
                                 "Kostnader_Budget":cost_budget,"Kostnader_Faktiskt":cost_actual,
                                 "Kvar_Budget":income_budget-cost_budget,"Kvar_Faktiskt":income_actual-cost_actual})
        df_month = pd.DataFrame(summary_list)
        chart_month = alt.Chart(df_month).transform_fold(
            ["Inkomster_Budget","Inkomster_Faktiskt","Kostnader_Budget","Kostnader_Faktiskt","Kvar_Budget","Kvar_Faktiskt"],
            as_=['Typ','€']
        ).mark_bar().encode(
            x='Månad:N',
            y='€:Q',
            color='Typ:N',
            tooltip=['Månad','Typ','€']
        ).properties(width=700,height=350)
        st.altair_chart(chart_month,use_container_width=True)
