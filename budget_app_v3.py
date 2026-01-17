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

def colored_input(label, value, key, css):
    st.number_input(label, value=value, key=key)
    st.markdown(f"""
    <script>
    document.querySelectorAll('input').forEach(el => {{
        if (el.getAttribute('aria-label') === "{label}") {{
            el.classList.add("{css}");
        }}
    }});
    </script>
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
# Lägg till rubrik & upp/ner
# =========================
st.sidebar.subheader("➕ Hantera rubriker")
new_cat = st.sidebar.text_input("Ny rubrik")
if st.sidebar.button("Lägg till rubrik"):
    c.execute("SELECT name FROM categories WHERE month=?", (month,))
    existing = [r[0] for r in c.fetchall()]
    if new_cat and new_cat not in existing:
        c.execute("INSERT INTO categories (month, name, position) VALUES (?,?,?)",
                  (month, new_cat, len(existing)))
        conn.commit()
        st.experimental_rerun()

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
c.execute("SELECT name, position FROM categories WHERE month=? ORDER BY position", (month,))
categories = c.fetchall()

# =========================
# Vänsterpanel – Rubrik och underrubriker
# =========================
st.sidebar.subheader("Rubriker & Underrubriker")
for cat_name, pos in categories:
    with st.sidebar.expander(f"{cat_name}"):
        # Upp/Ner-knappar
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬆", key=f"up_{cat_name}"):
                if pos>0:
                    c.execute("UPDATE categories SET position=? WHERE month=? AND position=?",
                              (pos-1, month, pos-1))
                    c.execute("UPDATE categories SET position=? WHERE month=? AND name=?",
                              (pos-1, month, cat_name))
                    conn.commit()
                    st.experimental_rerun()
        with col2:
            if st.button("⬇", key=f"down_{cat_name}"):
                c.execute("SELECT MAX(position) FROM categories WHERE month=?", (month,))
                max_pos = c.fetchone()[0]
                if pos<max_pos:
                    c.execute("UPDATE categories SET position=? WHERE month=? AND position=?",
                              (pos+1, month, pos+1))
                    c.execute("UPDATE categories SET position=? WHERE month=? AND name=?",
                              (pos+1, month, cat_name))
                    conn.commit()
                    st.experimental_rerun()

        # Lägg till underrubrik
        new_item = st.text_input(f"Lägg till underrubrik {cat_name}", key=f"newitem_{cat_name}")
        if st.button("➕ Lägg till", key=f"btn_item_{cat_name}"):
            if new_item:
                for m in months:
                    c.execute("""INSERT INTO items (month, category, name, budget, actual, date)
                                 VALUES (?,?,?,?,?,?)""", (m, cat_name, new_item, 0,0, datetime.date.today()))
                conn.commit()
                st.experimental_rerun()

        # Visa underrubriker
        c.execute("SELECT item_id, name, budget, actual FROM items WHERE month=? AND category=? ORDER BY item_id", (month, cat_name))
        items = c.fetchall()
        for item_id, item_name, budget_val, actual_val in items:
            col_b, col_a, col_del = st.columns([2,2,1])
            with col_b:
                st.number_input(f"{item_name} – Budget (€)", value=budget_val,
                                key=f"{month}_{cat_name}_{item_id}_b")
            with col_a:
                st.number_input(f"{item_name} – Faktiskt (€)", value=actual_val,
                                key=f"{month}_{cat_name}_{item_id}_a")
            with col_del:
                if st.button("🗑", key=f"del_{item_id}"):
                    for m in months:
                        c.execute("DELETE FROM items WHERE month=? AND item_id=?", (m, item_id))
                    conn.commit()
                    st.experimental_rerun()

# =========================
# Huvudpanel – Anteckningar
# =========================
if show_notes:
    st.subheader("📝 Anteckningar")
    c.execute("SELECT content FROM notes WHERE month=?", (month,))
    row = c.fetchone()
    note_text = row[0] if row else ""
    new_note = st.text_area("Anteckningar", value=note_text, height=120)
    if new_note != note_text:
        c.execute("INSERT OR REPLACE INTO notes (month, content) VALUES (?,?)", (month, new_note))
        conn.commit()

# =========================
# Kalender
# =========================
if show_calendar:
    st.subheader("📅 Kalender")
    cal_date = st.date_input("Välj datum")
    c.execute("SELECT description FROM events WHERE month=? AND date=?", (month, cal_date))
    row = c.fetchone()
    event_text = row[0] if row else ""
    new_event = st.text_input("Händelse", value=event_text)
    if new_event != event_text:
        c.execute("INSERT OR REPLACE INTO events (month, date, description) VALUES (?,?,?)",
                  (month, cal_date, new_event))
        conn.commit()

# =========================
# Veckoplanering
# =========================
if show_meals:
    st.subheader("🥗 Veckoplanering")
    days = ["Måndag","Tisdag","Onsdag","Torsdag","Fredag","Lördag","Söndag"]
    for d in days:
        c.execute("SELECT meal FROM meals WHERE month=? AND day=?", (month,d))
        row = c.fetchone()
        meal_text = row[0] if row else ""
        new_meal = st.text_input(d, value=meal_text, key=f"meal_{d}")
        if new_meal != meal_text:
            c.execute("INSERT OR REPLACE INTO meals (month, day, meal) VALUES (?,?,?)", (month,d,new_meal))
            conn.commit()

# =========================
# Kassaflöde
# =========================
if show_cashflow:
    st.subheader("💸 Kassaflöde")
    c.execute("SELECT name, actual, date FROM items WHERE month=?", (month,))
    rows = c.fetchall()
    if rows:
        df_cashflow = pd.DataFrame(rows, columns=["Beskrivning","Belopp","Datum"])
        df_cashflow["Datum"] = pd.to_datetime(df_cashflow["Datum"])
        df_cashflow["Saldo"] = df_cashflow["Belopp"].cumsum()
        st.dataframe(df_cashflow)
        chart_cashflow = alt.Chart(df_cashflow).mark_line(point=True).encode(
            x=alt.X("Datum:T"),
            y=alt.Y("Saldo:Q"),
            tooltip=["Datum","Beskrivning","Belopp","Saldo"]
        )
        st.altair_chart(chart_cashflow, use_container_width=True)

# =========================
# Årsöversikt
# =========================
if show_year:
    st.subheader("📊 Årsöversikt")
    summary_list = []
    for m in months:
        c.execute("SELECT SUM(actual), SUM(budget) FROM items WHERE month=? AND category='Inkomster'", (m,))
        inc_row = c.fetchone()
        inc_actual = inc_row[0] or 0
        inc_budget = inc_row[1] or 0

        c.execute("SELECT SUM(actual), SUM(budget) FROM items WHERE month=? AND category<>'Inkomster'", (m,))
        cost_row = c.fetchone()
        cost_actual = cost_row[0] or 0
        cost_budget = cost_row[1] or 0

        summary_list.append({
            "Månad": m,
            "Inkomster_Budget": inc_budget,
            "Inkomster_Faktiskt": inc_actual,
            "Kostnader_Budget": cost_budget,
            "Kostnader_Faktiskt": cost_actual,
            "Kvar_Budget": inc_budget - cost_budget,
            "Kvar_Faktiskt": inc_actual - cost_actual
        })

    df_year = pd.DataFrame(summary_list)
    df_melted = df_year.melt(id_vars="Månad", var_name="Typ", value_name="€")
    chart_year = alt.Chart(df_melted).mark_bar().encode(
        x="Månad:N",
        y="€:Q",
        color="Typ:N",
        tooltip=["Månad","Typ","€"]
    )
    st.altair_chart(chart_year, use_container_width=True)
