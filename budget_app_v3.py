import streamlit as st
import sqlite3
import pandas as pd
import altair as alt

# =========================
# Grundinställningar
# =========================
st.set_page_config(layout="wide")

# =========================
# CSS – färger
# =========================
st.markdown("""
<style>
input.budget { background-color: #eeeeee !important; }
input.actual { background-color: #fff3b0 !important; }
.red-row { background-color: #ffcccc !important; padding: 6px; border-radius:6px; }
.green-row { background-color: #ccffcc !important; padding: 6px; border-radius:6px; }
</style>
""", unsafe_allow_html=True)

def colored_number(label, value, key, css_class):
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

# =========================
# Login
# =========================
USERS = {"admin": "1234"}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Logga in")
    u = st.text_input("Användarnamn")
    p = st.text_input("Lösenord", type="password")
    if st.button("Logga in"):
        if u in USERS and p == USERS[u]:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Fel uppgifter")
    st.stop()

# =========================
# SQLite
# =========================
conn = sqlite3.connect("budget.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT,
    name TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT,
    category TEXT,
    name TEXT,
    budget REAL,
    actual REAL
)
""")

conn.commit()

# =========================
# Vänsterpanel
# =========================
with st.sidebar:
    st.header("📅 Månad")
    months = [
        "Januari","Februari","Mars","April","Maj","Juni",
        "Juli","Augusti","September","Oktober","November","December"
    ]
    month = st.radio("", months)

    st.divider()
    st.subheader("👁 Visning")
    show_cashflow = st.checkbox("Visa kassaflöde", True)
    show_year = st.checkbox("Visa årsöversikt", True)

    st.divider()
    if st.button("🚪 Logga ut"):
        st.session_state.clear()
        st.rerun()

# =========================
# Lägg till rubrik
# =========================
st.subheader("➕ Lägg till rubrik")
new_cat = st.text_input("Ny rubrik")
if st.button("Lägg till"):
    if new_cat:
        c.execute("INSERT INTO categories (month,name) VALUES (?,?)", (month,new_cat))
        conn.commit()
        st.rerun()

# =========================
# Huvudsida – RUBRIKER I KOLUMNER
# =========================
c.execute("SELECT name FROM categories WHERE month=? ORDER BY id", (month,))
categories = [r[0] for r in c.fetchall()]

total_income_b = total_income_a = 0
total_cost_b = total_cost_a = 0

if categories:
    cols = st.columns(len(categories))
else:
    cols = []

for i, cat in enumerate(categories):
    with cols[i]:
        with st.expander(cat, expanded=False):

            # Lägg till underrubrik
            new_item = st.text_input("Ny underrubrik", key=f"new_{cat}")
            if st.button("Lägg till", key=f"btn_{cat}"):
                if new_item:
                    c.execute("""
                        INSERT INTO items (month,category,name,budget,actual)
                        VALUES (?,?,?,?,?)
                    """, (month,cat,new_item,0.0,0.0))
                    conn.commit()
                    st.rerun()

            c.execute("""
                SELECT name,budget,actual FROM items
                WHERE month=? AND category=?
                ORDER BY id
            """, (month,cat))
            items = c.fetchall()

            cat_b = cat_a = 0

            for name,b,a in items:
                # Regel: inkomster alltid grön om a >= b
                if cat.lower() == "inkomster":
                    row_class = "green-row" if a >= b else "red-row"
                else:
                    row_class = "green-row" if a <= b else "red-row"

                st.markdown(f"<div class='{row_class}'>", unsafe_allow_html=True)
                c1,c2 = st.columns(2)

                with c1:
                    colored_number(
                        f"{name} – Budget (€)",
                        b,
                        f"{month}_{cat}_{name}_b",
                        "budget"
                    )
                with c2:
                    colored_number(
                        f"{name} – Faktiskt (€)",
                        a,
                        f"{month}_{cat}_{name}_a",
                        "actual"
                    )

                b_new = st.session_state[f"{month}_{cat}_{name}_b"]
                a_new = st.session_state[f"{month}_{cat}_{name}_a"]

                if b_new != b or a_new != a:
                    c.execute("""
                        UPDATE items SET budget=?, actual=?
                        WHERE month=? AND category=? AND name=?
                    """, (b_new,a_new,month,cat,name))
                    conn.commit()

                cat_b += b_new
                cat_a += a_new
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(f"**Summa budget:** €{cat_b:.2f}")
            st.markdown(f"**Summa faktiskt:** €{cat_a:.2f}")

            if cat.lower() == "inkomster":
                total_income_b += cat_b
                total_income_a += cat_a
            else:
                total_cost_b += cat_b
                total_cost_a += cat_a

# =========================
# Sammanfattning
# =========================
st.divider()
c1,c2,c3 = st.columns(3)
c1.metric("Totalt budget", f"€{total_income_b-total_cost_b:.2f}")
c2.metric("Totalt faktiskt", f"€{total_income_a-total_cost_a:.2f}")
c3.metric("💰 Kvar att använda", f"€{total_income_a-total_cost_a:.2f}")

# =========================
# Kassaflöde
# =========================
if show_cashflow:
    st.subheader("📈 Kassaflöde")
    df = pd.DataFrame({
        "Typ": ["Budget","Faktiskt"],
        "Kvar": [
            total_income_b-total_cost_b,
            total_income_a-total_cost_a
        ]
    })
    chart = alt.Chart(df).mark_bar().encode(
        x="Typ:N",
        y="Kvar:Q",
        color="Typ:N"
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

# =========================
# Årsöversikt
# =========================
if show_year:
    st.subheader("📅 Årsöversikt")
    rows = []
    for m in months:
        c.execute("SELECT SUM(actual),SUM(budget) FROM items WHERE month=?", (m,))
        a,b = c.fetchone()
        rows.append({
            "Månad": m,
            "Budget": b or 0,
            "Faktiskt": a or 0
        })
    dfy = pd.DataFrame(rows)
    st.dataframe(dfy, use_container_width=True)
