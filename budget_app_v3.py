import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import date

# =========================
# SQLite Setup
# =========================
DB_FILE = "budget.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# Skapa tabeller om de inte finns
c.execute("""CREATE TABLE IF NOT EXISTS categories (
    month TEXT,
    cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    order_num INTEGER
)""")
c.execute("""CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT,
    category TEXT,
    name TEXT,
    budget REAL,
    actual REAL,
    date TEXT
)""")
c.execute("""CREATE TABLE IF NOT EXISTS notes (
    month TEXT PRIMARY KEY,
    content TEXT
)""")
c.execute("""CREATE TABLE IF NOT EXISTS cashflow (
    user TEXT,
    month TEXT,
    name TEXT,
    amount REAL,
    pay_date TEXT,
    PRIMARY KEY(user, month, name)
)""")
conn.commit()

# =========================
# Login
# =========================
users = {"admin": "1234"}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 Logga in")
    u = st.text_input("Användarnamn")
    p = st.text_input("Lösenord", type="password")
    if st.button("Logga in"):
        if u in users and p == users[u]:
            st.session_state.logged_in = True
            st.session_state.username = u
            st.stop()  # uppdaterar sidan
        else:
            st.error("Fel användarnamn eller lösenord")
    st.stop()

# =========================
# Layout
# =========================
st.set_page_config(layout="wide")
left_col, main_col = st.columns([1,3])

with left_col:
    st.header("Meny")
    # Månadsval
    months = ["Januari","Februari","Mars","April","Maj","Juni",
              "Juli","Augusti","September","Oktober","November","December"]
    selected_month = st.selectbox("📅 Välj månad", months)
    
    # Lägg till rubrik
    new_cat = st.text_input("➕ Ny rubrik")
    if st.button("Lägg till rubrik"):
        if new_cat:
            c.execute("SELECT MAX(order_num) FROM categories WHERE month=?", (selected_month,))
            max_order = c.fetchone()[0] or 0
            c.execute("INSERT INTO categories(month,name,order_num) VALUES (?,?,?)",
                      (selected_month,new_cat,max_order+1))
            conn.commit()
            st.stop()
    
    # Visa rubriker + underrubriker
    c.execute("SELECT name FROM categories WHERE month=? ORDER BY order_num", (selected_month,))
    categories = [r[0] for r in c.fetchall()]
    
    cat_selection = st.selectbox("Välj rubrik att visa på huvudsidan", ["Alla"]+categories)

    # Checkboxar för extra visning
    show_cashflow = st.checkbox("Visa kassaflöde", True)
    show_year_overview = st.checkbox("Visa årsöversikt", True)
    show_notes = st.checkbox("Visa anteckningar", True)
    
    st.markdown("---")
    if st.button("Logga ut"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.stop()

# =========================
# Anteckningar
# =========================
with main_col:
    if show_notes:
        c.execute("SELECT content FROM notes WHERE month=?", (selected_month,))
        row = c.fetchone()
        note_text = row[0] if row else ""
        new_note = st.text_area(f"📝 Anteckningar för {selected_month}", value=note_text, height=120)
        if new_note != note_text:
            c.execute("INSERT OR REPLACE INTO notes(month, content) VALUES (?,?)", (selected_month, new_note))
            conn.commit()

# =========================
# Visa rubriker & underrubriker med budget/faktiskt
# =========================
def colored_input(label, value, key, css_class):
    st.number_input(label, value=value, key=key)
    st.markdown(f"""
    <script>
    document.querySelectorAll('input').forEach(el => {{
        if (el.getAttribute('aria-label') === "{label}") {{
            el.classList.add("{css_class}");
        }}
    }});
    </script>
    """, unsafe_allow_html=True)

st.markdown("---")
total_income_budget = total_income_actual = total_cost_budget = total_cost_actual = 0

for cat in categories:
    if cat_selection != "Alla" and cat_selection != cat:
        continue
    with st.expander(f"{cat}"):
        # Lägg till underrubrik
        new_item = st.text_input(f"Ny underrubrik under {cat}", key=f"add_{cat}")
        if st.button(f"Lägg till {cat}", key=f"btn_{cat}"):
            if new_item:
                c.execute("INSERT INTO items(month,category,name,budget,actual,date) VALUES(?,?,?,?,?,?)",
                          (selected_month, cat, new_item, 0.0, 0.0, date.today().isoformat()))
                conn.commit()
                st.stop()
        
        # Hämta underrubriker
        c.execute("SELECT name,budget,actual FROM items WHERE month=? AND category=? ORDER BY item_id",
                  (selected_month, cat))
        items = c.fetchall()
        cat_budget = cat_actual = 0
        for item_name, budget_val, actual_val in items:
            # Färglogik
            if cat.lower() == "inkomster":
                row_class = "green-row" if actual_val >= budget_val else "red-row"
            else:
                row_class = "green-row" if actual_val <= budget_val else "red-row"
            
            col1, col2 = st.columns(2)
            with col1:
                new_b = st.number_input(f"{item_name} – Budget (€)", value=budget_val, key=f"{selected_month}_{cat}_{item_name}_b")
            with col2:
                new_a = st.number_input(f"{item_name} – Faktiskt (€)", value=actual_val, key=f"{selected_month}_{cat}_{item_name}_a")
            
            if new_b != budget_val or new_a != actual_val:
                c.execute("UPDATE items SET budget=?, actual=? WHERE month=? AND category=? AND name=?",
                          (new_b, new_a, selected_month, cat, item_name))
                conn.commit()
            
            cat_budget += new_b
            cat_actual += new_a
        
        st.markdown(f"**Summa budget:** €{cat_budget:.2f} | **Summa faktiskt:** €{cat_actual:.2f}")
        if cat.lower() == "inkomster":
            total_income_budget += cat_budget
            total_income_actual += cat_actual
        else:
            total_cost_budget += cat_budget
            total_cost_actual += cat_actual

# =========================
# Sammanfattning
# =========================
st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("Totala inkomster", f"€{total_income_actual:.2f}", f"Budget: €{total_income_budget:.2f}")
col2.metric("Totala kostnader", f"€{total_cost_actual:.2f}", f"Budget: €{total_cost_budget:.2f}")
col3.metric("💰 Kvar att använda / spara", f"€{total_income_actual - total_cost_actual:.2f}",
            f"Budget: €{total_income_budget - total_cost_budget:.2f}")

# =========================
# Diagram: Totala per månad
# =========================
df_chart = pd.DataFrame({
    "Kategori": ["Inkomster", "Kostnader", "Kvar att spara"],
    "Budget": [total_income_budget, total_cost_budget, total_income_budget - total_cost_budget],
    "Faktiskt": [total_income_actual, total_cost_actual, total_income_actual - total_cost_actual]
})
df_melted = df_chart.melt(id_vars="Kategori", var_name="Typ", value_name="€")
chart = alt.Chart(df_melted).mark_bar().encode(
    x='Kategori:N',
    y='€:Q',
    color=alt.Color('Typ:N', scale=alt.Scale(range=['#87CEFA','#FFB347'])),
    tooltip=['Kategori','Typ','€']
).properties(width=600, height=400)
st.altair_chart(chart, use_container_width=True)
