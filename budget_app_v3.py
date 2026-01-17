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

def get_row_class(category_name, actual, budget):
    if category_name.lower() == "inkomster":
        return "green-row" if actual >= budget else "red-row"
    else:
        return "green-row" if actual <= budget else "red-row"

# =========================
# SQLite Setup
# =========================
DB_FILE = "budget.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# Skapa tabeller om de inte finns
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
    actual REAL,
    date TEXT
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS notes (
    month TEXT PRIMARY KEY,
    content TEXT
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS sections (
    name TEXT PRIMARY KEY,
    position INTEGER,
    visible INTEGER DEFAULT 1
)
""")
conn.commit()

# =========================
# Sektioner – standard
# =========================
default_sections = ["Anteckningar","Rubriker","Månadsöversikt","Kassaflöde","Årsöversikt","Veckoplanering","Kalender"]
for idx, sec in enumerate(default_sections):
    c.execute("INSERT OR IGNORE INTO sections (name,position,visible) VALUES (?,?,?)",(sec,idx,1))
conn.commit()

# =========================
# Login
# =========================
users = {"admin":"1234"}
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.title("🔐 Logga in")
    u = st.text_input("Användarnamn")
    p = st.text_input("Lösenord", type="password")
    if st.button("Logga in"):
        if u in users and p==users[u]:
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Fel uppgifter")
    st.stop()

# Logout
col_l,col_r = st.columns([6,1])
with col_r:
    if st.button("Logga ut"):
        st.session_state.clear()
        st.experimental_rerun()

# =========================
# Månad
# =========================
months = ["Januari","Februari","Mars","April","Maj","Juni","Juli","Augusti","September","Oktober","November","December"]
left_panel = st.sidebar
with left_panel:
    st.header("📅 Välj månad")
    month = st.selectbox("Månad", months)

    st.divider()
    st.subheader("➕ Hantera rubriker")
    new_cat = st.text_input("Ny rubrik")
    if st.button("Lägg till rubrik"):
        if new_cat:
            for m in months:
                c.execute("INSERT OR IGNORE INTO categories (month,name) VALUES (?,?)",(m,new_cat))
            conn.commit()
            st.experimental_rerun()

    # =========================
    # Hantera sektioner – upp/ner
    c.execute("SELECT name,position,visible FROM sections ORDER BY position")
    sections = c.fetchall()
    section_order = []
    section_visibility = {}
    for sec_name,pos,vis in sections:
        section_order.append(sec_name)
        section_visibility[sec_name] = bool(vis)
        cols = st.columns([1,1,1])
        with cols[0]:
            st.write(sec_name)
        with cols[1]:
            if st.button("⬆",key=f"up_{sec_name}") and pos>0:
                c.execute("UPDATE sections SET position=? WHERE name=?",(pos-1,sec_name))
                conn.commit()
                st.experimental_rerun()
        with cols[2]:
            if st.button("⬇",key=f"down_{sec_name}") and pos<len(sections)-1:
                c.execute("UPDATE sections SET position=? WHERE name=?",(pos+1,sec_name))
                conn.commit()
                st.experimental_rerun()
        # Synlighet
        vis = st.checkbox("Visa",value=bool(vis),key=f"vis_{sec_name}")
        c.execute("UPDATE sections SET visible=? WHERE name=?",(1 if vis else 0,sec_name))
    conn.commit()

# =========================
# Huvudpanelen – sektioner i vänsterpanelens ordning
# =========================
total_income_budget = 0
total_income_actual = 0
total_cost_budget = 0
total_cost_actual = 0

for sec_name in section_order:
    if not section_visibility.get(sec_name,True):
        continue

    if sec_name=="Anteckningar":
        st.subheader("📝 Anteckningar")
        c.execute("SELECT content FROM notes WHERE month=?",(month,))
        row = c.fetchone()
        note_text = row[0] if row else ""
        new_note = st.text_area("Anteckningar",value=note_text,height=120)
        if new_note!=note_text:
            c.execute("INSERT OR REPLACE INTO notes (month,content) VALUES (?,?)",(month,new_note))
            conn.commit()

    elif sec_name=="Rubriker":
        st.subheader("📂 Rubriker och underrubriker")
        c.execute("SELECT name FROM categories WHERE month=? ORDER BY cat_id",(month,))
        categories = [r[0] for r in c.fetchall()]
        for cat in categories:
            with st.expander(cat):
                new_item = st.text_input("Ny underrubrik",key=f"add_{cat}")
                if st.button("Lägg till underrubrik",key=f"btn_{cat}"):
                    if new_item:
                        for m in months:
                            c.execute("INSERT OR IGNORE INTO items (month,category,name,budget,actual,date) VALUES (?,?,?,?,?,?)",(m,cat,new_item,0.0,0.0,""))
                        conn.commit()
                        st.experimental_rerun()

                c.execute("SELECT item_id,name,budget,actual,date FROM items WHERE month=? AND category=? ORDER BY item_id",(month,cat))
                items = c.fetchall()
                for item_id,item_name,budget_val,actual_val,date_val in items:
                    budget_val = float(budget_val or 0)
                    actual_val = float(actual_val or 0)
                    date_val = date_val or ""
                    row_class = get_row_class(cat,actual_val,budget_val)
                    col_b,col_a,col_d = st.columns([2,2,2])
                    with col_b:
                        b_new = st.number_input(f"{item_name} – Budget (€)",value=budget_val,step=10.0,key=f"{month}_{cat}_{item_name}_b")
                    with col_a:
                        a_new = st.number_input(f"{item_name} – Faktiskt (€)",value=actual_val,step=10.0,key=f"{month}_{cat}_{item_name}_a")
                    with col_d:
                        d_new = st.date_input(f"{item_name} – Datum",value=date.fromisoformat(date_val) if date_val else date.today(),key=f"{month}_{cat}_{item_name}_d")
                    if b_new!=budget_val or a_new!=actual_val or d_new!=date_val:
                        c.execute("UPDATE items SET budget=?,actual=?,date=? WHERE month=? AND item_id=?",(b_new,a_new,d_new.isoformat(),month,item_id))
                        # Kopiera budget till alla månader
                        for m in months:
                            if m!=month:
                                c.execute("UPDATE items SET budget=? WHERE month=? AND category=? AND name=?",(b_new,m,cat,item_name))
                        conn.commit()

                    if cat.lower()=="inkomster":
                        total_income_budget += b_new
                        total_income_actual += a_new
                    else:
                        total_cost_budget += b_new
                        total_cost_actual += a_new

    elif sec_name=="Månadsöversikt":
        st.subheader("📊 Månadsöversikt")
        summary_list = []
        for m in months:
            c.execute("SELECT SUM(budget),SUM(actual) FROM items WHERE month=? AND category='Inkomster'",(m,))
            inc = c.fetchone()
            income_budget = float(inc[0] or 0)
            income_actual = float(inc[1] or 0)
            c.execute("SELECT SUM(budget),SUM(actual) FROM items WHERE month=? AND category<>'Inkomster'",(m,))
            cost = c.fetchone()
            cost_budget = float(cost[0] or 0)
            cost_actual = float(cost[1] or 0)
            summary_list.append({
                "Månad":m,
                "Inkomster_Budget":income_budget,
                "Inkomster_Faktiskt":income_actual,
                "Kostnader_Budget":cost_budget,
                "Kostnader_Faktiskt":cost_actual,
                "Kvar_Budget":income_budget-cost_budget,
                "Kvar_Faktiskt":income_actual-cost_actual
            })
        df_month = pd.DataFrame(summary_list).fillna(0)
        df_melted_month = df_month.melt(id_vars="Månad",
                                        value_vars=["Inkomster_Budget","Inkomster_Faktiskt",
                                                    "Kostnader_Budget","Kostnader_Faktiskt",
                                                    "Kvar_Budget","Kvar_Faktiskt"],
                                        var_name="Typ", value_name="€")
        chart_month = alt.Chart(df_melted_month).mark_bar().encode(
            x='Månad:N',
            y='€:Q',
            color='Typ:N',
            tooltip=['Månad','Typ','€']
        ).properties(width=700,height=350)
        st.altair_chart(chart_month,use_container_width=True)
