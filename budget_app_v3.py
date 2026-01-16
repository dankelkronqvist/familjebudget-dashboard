
import streamlit as st
import pandas as pd
import json, os
from io import BytesIO

st.set_page_config(page_title="Familjebudget Dashboard v7", layout="wide")

# -----------------------
# 1️⃣ Session state för login
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# -----------------------
# 2️⃣ Användare via JSON
# -----------------------
USER_FILE = "users.json"
if not os.path.exists(USER_FILE):
    users = {"Anki":"1234","Dani":"1234"}
    with open(USER_FILE,"w") as f:
        json.dump(users,f)
else:
    with open(USER_FILE,"r") as f:
        users = json.load(f)

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.experimental_rerun()  # säker logout

# -----------------------
# 3️⃣ Login
# -----------------------
if not st.session_state.logged_in:
    st.title("💶 Familjebudget – Logga in")
    user = st.text_input("Användarnamn")
    password = st.text_input("Lösenord", type="password")
    if st.button("Logga in"):
        if user in users and password == users[user]:
            st.session_state.logged_in = True
            st.session_state.username = user
            st.success("Inloggning lyckades! Ladda om sidan...")
            st.stop()  # Stoppar scriptet här, laddar om med logged_in=True
        else:
            st.error("Fel användarnamn eller lösenord")

# -----------------------
# 4️⃣ Huvudapp efter login
# -----------------------
else:
    # Logga ut knapp
    st.sidebar.button("Logga ut", on_click=logout)
    st.title(f"💶 Familjebudget – Välkommen {st.session_state.username}")

    # Månadsval
    months = ["Januari","Februari","Mars","April","Maj","Juni",
              "Juli","Augusti","September","Oktober","November","December"]
    month = st.selectbox("Välj månad", months)

    # Kategorier & underrubriker
    categories = {
        "Inkomster": ["Danis lön","Ankis lön","Hästförsäljning",
                       "Barnbidrag (Kela)","Mammapeng (Kela)","Hemvårdsstöd (Kela)"],
        "Fasta kostnader": ["Försäkringar","El","Internet/TV","Telefon","Ekorosk","Fastighetsskatt","Vatten/Avlopp"],
        "Rörliga utgifter": ["Mat","Gåvor","Barnkonto","Utemat","Anki","Dani","Reparation"],
        "Bilen": ["Bränsle","Försäkringar","Service","Dieselskatt","Avbetalning"],
        "Avbetalningar": ["Moas Telefon","Ottos Klocka","Ankis Telefon","Danis Klocka","Fyrhjulingen"],
        "Bank & Lån": ["Bostadslån","Husvagnslån","Kredit"],
        "Kontoskötsel avgifter": ["Anki","Dani","Spar","Leo","Otto","Moa","Räknekonto"],
        "Sparande": ["Aktia Fonder","S-Gruppens Fonder","Buffert","Nordnet Aktier"]
    }

    # Ladda eller skapa budget-data och anteckningar
    DATA_FILE = "budget_data_v7.json"
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,"r") as f:
            budget_data = json.load(f)
    else:
        budget_data = {}

    if month not in budget_data:
        budget_data[month] = {"notes":""}

    # Anteckningsruta (synlig hela tiden)
    if "notes" not in budget_data[month]:
        budget_data[month]["notes"] = ""
    st.subheader("📝 Anteckningar")
    notes = st.text_area("Skriv här", value=budget_data[month]["notes"], height=150)
    budget_data[month]["notes"] = notes

    # Inmatning – dropdowns per kategori
    total_income = 0
    total_expenses = 0
    summary = []

    for category, items in categories.items():
        # Skapa rubrik med totalsumma
        category_sum = 0
        if category in budget_data[month]:
            category_sum = sum([v.get("Faktiskt",0) for v in budget_data[month][category].values()])
        else:
            budget_data[month][category] = {}

        expander = st.expander(f"{category}: {category_sum:.2f} €", expanded=False)
        with expander:
            rows = []
            for idx, item in enumerate(items + ["", "", ""]):
                key = f"{item or 'Tom'}_{idx}"

                try:
                    prev_budget = float(budget_data[month][category].get(key, {}).get("Budget",0))
                except (TypeError, ValueError):
                    prev_budget = 0.0
                try:
                    prev_actual = float(budget_data[month][category].get(key, {}).get("Faktiskt",0))
                except (TypeError, ValueError):
                    prev_actual = 0.0

                col1, col2 = st.columns([1,1])
                with col1:
                    budget = st.number_input(
                        f"{item or '—'} Budget (€)",
                        min_value=0.0,
                        step=10.0,
                        value=prev_budget,
                        key=f"{month}_{category}_{key}_B"
                    )
                with col2:
                    actual = st.number_input(
                        f"{item or '—'} Faktiskt (€)",
                        min_value=0.0,
                        step=10.0,
                        value=prev_actual,
                        key=f"{month}_{category}_{key}_A"
                    )

                budget_data[month][category][key] = {"Budget":budget,"Faktiskt":actual}
                rows.append({"Post":item or "Tom","Budget":budget,"Faktiskt":actual})

            df = pd.DataFrame(rows)
            budget_sum = df["Budget"].sum()
            actual_sum = df["Faktiskt"].sum()
            diff = budget_sum - actual_sum

            if category=="Inkomster":
                total_income += actual_sum
            else:
                total_expenses += actual_sum

            if diff>=0:
                st.success(f"Totalt {category}: {actual_sum:.2f} € (inom budget)")
            else:
                st.error(f"Totalt {category}: {actual_sum:.2f} € (över budget)")

            summary.append([category,budget_sum,actual_sum])

    # Beräkna kvar att använda/spara
    kvar = total_income - total_expenses
    st.divider()
    st.subheader("💰 Totala inkomster & kvar att använda")
    st.metric("Totala inkomster", f"{total_income:.2f} €")
    st.metric("Totala kostnader", f"{total_expenses:.2f} €")
    st.metric("Kvar att använda / spara", f"{kvar:.2f} €")

    # Spara JSON
    with open(DATA_FILE,"w") as f:
        json.dump(budget_data,f,indent=4)

    # Exportera Excel / CSV
    st.divider()
    st.header("💾 Exportera data")
    export_format = st.radio("Välj format:", ["Excel (.xlsx)","CSV (.csv)"])
    if export_format=="Excel (.xlsx)":
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            for m in months:
                month_df = []
                if m in budget_data:
                    for cat, items_dict in budget_data[m].items():
                        if cat=="notes":
                            continue
                        for item, vals in items_dict.items():
                            month_df.append([cat,item,vals["Budget"],vals["Faktiskt"]])
                    df_month = pd.DataFrame(month_df, columns=["Kategori","Post","Budget","Faktiskt"])
                    df_month.to_excel(writer, sheet_name=m[:31], index=False)

                    workbook = writer.book
                    worksheet = writer.sheets[m[:31]]
                    red_format = workbook.add_format({'bg_color':'#FFC7CE'})
                    green_format = workbook.add_format({'bg_color':'#C6EFCE'})
                    worksheet.conditional_format('D2:D1000', {'type':'cell','criteria':'>','value': 'C2','format':red_format})
                    worksheet.conditional_format('D2:D1000', {'type':'cell','criteria':'<=','value':'C2','format':green_format})
            writer.save()
            processed_data = output.getvalue()
        st.download_button(label="Ladda ner Excel", data=processed_data, file_name="Familjebudget.xlsx")
    else:
        combined = []
        for m in months:
            if m in budget_data:
                for cat, items_dict in budget_data[m].items():
                    if cat=="notes":
                        continue
                    for item, vals in items_dict.items():
                        combined.append([m,cat,item,vals["Budget"],vals["Faktiskt"]])
        df_csv = pd.DataFrame(combined, columns=["Månad","Kategori","Post","Budget","Faktiskt"])
        st.download_button(label="Ladda ner CSV", data=df_csv.to_csv(index=False), file_name="Familjebudget.csv")
