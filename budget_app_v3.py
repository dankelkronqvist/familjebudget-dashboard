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
col_l, col_r = st.columns([6,1])
with col_r:
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
    date DATE
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS notes (
    month TEXT PRIMARY KEY,
    content TEXT
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

if "month" not in st.session_state:
    st.session_state["month"] = "Januari"

st.subheader("📅 Välj månad")
month_cols = st.columns(len(months))
for idx, m in enumerate(months):
    if month_cols[idx].button(m):
        st.session_state["month"] = m
month = st.session_state["month"]
st.markdown(f"**Vald månad:** {month}")

# =========================
# Anteckningar
# =========================
c.execute("SELECT content FROM notes WHERE month=?", (month,))
row = c.fetchone()
note_text = row[0] if row else ""
new_note = st.text_area("📝 Anteckningar", value=note_text, height=120)
if new_note != note_text:
    c.execute("INSERT OR REPLACE INTO notes (month, content) VALUES (?,?)", (month, new_note))
    conn.commit()

# =========================
# Hantera rubriker
# =========================
st.divider()
st.subheader("➕ Hantera rubriker")
c.execute("SELECT name FROM categories WHERE month=? ORDER BY cat_id", (month,))
rows = c.fetchall()
categories = [r[0] for r in rows] if rows else []

new_cat = st.text_input("Ny rubrik")
if st.button("Lägg till rubrik"):
    if new_cat and new_cat not in categories:
        c.execute("INSERT INTO categories (month, name) VALUES (?,?)", (month,new_cat))
        conn.commit()
        st.experimental_rerun()

# =========================
# Dashboard – rubriker på rad
# =========================
if categories:
    cols = st.columns(len(categories))
else:
    cols = []

total_income_budget = 0
total_income_actual = 0
total_cost_budget = 0
total_cost_actual = 0

for idx, cat in enumerate(categories):
    with cols[idx]:
        new_name = st.text_input("Byt namn på rubrik", value=cat, key=f"rename_{cat}")
        if new_name != cat and new_name:
            c.execute("UPDATE categories SET name=? WHERE month=? AND name=?", (new_name, month, cat))
            c.execute("UPDATE items SET category=? WHERE month=? AND category=?", (new_name, month, cat))
            conn.commit()
            st.experimental_rerun()

        with st.expander(f"{cat}"):
            new_item = st.text_input("Ny underrubrik", key=f"add_{cat}")
            new_date = st.date_input("Datum", value=datetime.date.today(), key=f"date_{cat}")
            if st.button("Lägg till underrubrik", key=f"btn_{cat}"):
                if new_item:
                    c.execute("""
                        INSERT INTO items (month, category, name, budget, actual, date)
                        VALUES (?,?,?,?,?,?)
                    """, (month, cat, new_item, 0.0, 0.0, new_date))
                    conn.commit()
                    st.experimental_rerun()

            c.execute("SELECT item_id, name,budget,actual,date FROM items WHERE month=? AND category=? ORDER BY item_id", (month,cat))
            items = c.fetchall()

            cat_budget = 0
            cat_actual = 0

            for item_id, item_name, budget_val, actual_val, item_date in items:
                row_class = "green-row" if actual_val <= budget_val else "red-row"
                with st.container():
                    st.markdown(f'<div class="{row_class}">', unsafe_allow_html=True)
                    col_b, col_a = st.columns(2)
                    with col_b:
                        colored_input(f"{item_name} – Budget (€)", budget_val, f"{month}_{cat}_{item_id}_b", "budget")
                    with col_a:
                        colored_input(f"{item_name} – Faktiskt (€)", actual_val, f"{month}_{cat}_{item_id}_a", "actual")
                    st.markdown("</div>", unsafe_allow_html=True)

                    b_new = st.session_state[f"{month}_{cat}_{item_id}_b"]
                    a_new = st.session_state[f"{month}_{cat}_{item_id}_a"]
                    if b_new != budget_val or a_new != actual_val:
                        c.execute("UPDATE items SET budget=?, actual=? WHERE item_id=?",
                                  (b_new, a_new, item_id))
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
# Kassaflödesdiagram
# =========================
st.divider()
st.subheader("💸 Kassaflöde per datum")
c.execute("SELECT name, actual, date FROM items WHERE month=?", (month,))
rows = c.fetchall()
if rows:
    df_cashflow = pd.DataFrame(rows, columns=["Beskrivning", "Belopp", "Datum"])
    df_cashflow["Datum"] = pd.to_datetime(df_cashflow["Datum"])
    df_cashflow["Saldo"] = df_cashflow["Belopp"].cumsum()

    st.dataframe(df_cashflow)
    chart_cashflow = alt.Chart(df_cashflow).mark_line(point=True).encode(
        x=alt.X("Datum:T", title="Datum"),
        y=alt.Y("Saldo:Q", title="Löpande saldo (€)"),
        color=alt.condition(alt.datum.Saldo<0, alt.value("red"), alt.value("green")),
        tooltip=["Datum","Beskrivning","Belopp","Saldo"]
    ).properties(width='stretch', height=400)
    st.altair_chart(chart_cashflow, use_container_width=True)

# =========================
# Årsöversikt – alla månader
# =========================
st.divider()
st.subheader("📅 Årsöversikt")
summary_list = []
for m in months:
    c.execute("SELECT SUM(actual), SUM(budget) FROM items WHERE month=? AND category='Inkomster'", (m,))
    income_row = c.fetchone()
    income_actual = income_row[0] or 0
    income_budget = income_row[1] or 0

    c.execute("SELECT SUM(actual), SUM(budget) FROM items WHERE month=? AND category<>'Inkomster'", (m,))
    cost_row = c.fetchone()
    cost_actual = cost_row[0] or 0
    cost_budget = cost_row[1] or 0

    summary_list.append({
        "Månad": m,
        "Inkomster_Budget": income_budget,
        "Inkomster_Faktiskt": income_actual,
        "Kostnader_Budget": cost_budget,
        "Kostnader_Faktiskt": cost_actual,
        "Kvar_Budget": income_budget - cost_budget,
        "Kvar_Faktiskt": income_actual - cost_actual
    })

df_year = pd.DataFrame(summary_list)
df_melted_year = df_year.melt(id_vars="Månad",
                              value_vars=["Inkomster_Budget","Inkomster_Faktiskt",
                                          "Kostnader_Budget","Kostnader_Faktiskt",
                                          "Kvar_Budget","Kvar_Faktiskt"],
                              var_name="Typ", value_name="€")

chart_year = alt.Chart(df_melted_year).mark_bar().encode(
    x=alt.X('Månad:N', title="Månad"),
    y=alt.Y('€:Q', title="Belopp (€)"),
    color=alt.Color('Typ:N', scale=alt.Scale(range=['#87CEFA','#32CD32','#FFB347','#FF6347','#87CEFA','#32CD32'])),
    tooltip=['Månad','Typ','€']
).properties(width='stretch', height=400)

st.altair_chart(chart_year, use_container_width=True)
