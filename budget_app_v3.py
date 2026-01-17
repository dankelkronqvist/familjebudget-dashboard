import streamlit as st
import sqlite3
from sqlite3 import Error

# =========================
# CSS – färger
# =========================
st.markdown("""
<style>
input.budget { background-color: #eeeeee !important; }
input.actual { background-color: #fff3b0 !important; }
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

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
    except Error as e:
        st.error(e)
    return conn

conn = create_connection(DB_FILE)
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
    actual REAL
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
# Månadsval
# =========================
months = [
    "Januari","Februari","Mars","April","Maj","Juni",
    "Juli","Augusti","September","Oktober","November","December"
]

month = st.selectbox("📅 Välj månad", months)

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

# Hämta rubriker från DB
c.execute("SELECT name FROM categories WHERE month=? ORDER BY cat_id", (month,))
rows = c.fetchall()
categories = [r[0] for r in rows] if rows else []

# Lägg till rubrik
new_cat = st.text_input("Ny rubrik")
if st.button("Lägg till rubrik"):
    if new_cat and new_cat not in categories:
        c.execute("INSERT INTO categories (month, name) VALUES (?,?)", (month,new_cat))
        conn.commit()
        st.experimental_rerun()

# =========================
# Dropdown-rubriker på rad
# =========================
if categories:
    cols = st.columns(len(categories))
else:
    cols = []

total_income = 0
total_cost = 0

for idx, cat in enumerate(categories):
    with cols[idx]:
        # Byt namn
        new_name = st.text_input("Byt namn på rubrik", value=cat, key=f"rename_{cat}")
        if new_name != cat and new_name:
            c.execute("UPDATE categories SET name=? WHERE month=? AND name=?", (new_name, month, cat))
            c.execute("UPDATE items SET category=? WHERE month=? AND category=?", (new_name, month, cat))
            conn.commit()
            st.experimental_rerun()

        with st.expander(f"{cat}"):

            # Lägg till underrubrik
            new_item = st.text_input("Ny underrubrik", key=f"add_{cat}")
            if st.button("Lägg till underrubrik", key=f"btn_{cat}"):
                if new_item:
                    c.execute("INSERT INTO items (month, category, name, budget, actual) VALUES (?,?,?,?,?)",
                              (month, cat, new_item, 0.0, 0.0))
                    conn.commit()
                    st.experimental_rerun()

            # Hämta alla items
            c.execute("SELECT name,budget,actual FROM items WHERE month=? AND category=? ORDER BY item_id", (month,cat))
            items = c.fetchall()

            cat_budget = 0
            cat_actual = 0

            for item_name, budget_val, actual_val in items:
                col_b, col_a = st.columns(2)
                with col_b:
                    colored_input(f"{item_name} – Budget (€)", budget_val, f"{month}_{cat}_{item_name}_b", "budget")
                with col_a:
                    colored_input(f"{item_name} – Faktiskt (€)", actual_val, f"{month}_{cat}_{item_name}_a", "actual")

                # Spara direkt i DB om ändrat
                b_new = st.session_state[f"{month}_{cat}_{item_name}_b"]
                a_new = st.session_state[f"{month}_{cat}_{item_name}_a"]
                if b_new != budget_val or a_new != actual_val:
                    c.execute("UPDATE items SET budget=?, actual=? WHERE month=? AND category=? AND name=?",
                              (b_new, a_new, month, cat, item_name))
                    conn.commit()

                cat_budget += b_new
                cat_actual += a_new

            st.markdown(f"**Summa budget:** €{cat_budget:.2f}")
            st.markdown(f"**Summa faktiskt:** €{cat_actual:.2f}")

            if cat.lower() in ["inkomster"]:
                total_income += cat_actual
            else:
                total_cost += cat_actual

# =========================
# Sammanfattning
# =========================
st.divider()
st.subheader("📊 Sammanfattning")
st.metric("Totala inkomster", f"€{total_income:.2f}")
st.metric("Totala kostnader", f"€{total_cost:.2f}")
st.metric("💰 Kvar att använda / spara", f"€{total_income - total_cost:.2f}")
