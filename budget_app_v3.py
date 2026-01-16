import streamlit as st
import pandas as pd
import json, os
from io import BytesIO

st.set_page_config(page_title="Familjebudget Dashboard v4", layout="wide")
st.title("💶 Familjebudget – Dashboard v4")

# -----------------------
# 5️⃣ Fler användare via JSON
# -----------------------
USER_FILE = "users.json"
if not os.path.exists(USER_FILE):
    # Standardanvändare första gången
    users = {"Anki":"1234","Dani":"1234"}
    with open(USER_FILE,"w") as f:
        json.dump(users,f)
else:
    with open(USER_FILE,"r") as f:
        users = json.load(f)

user = st.text_input("Användarnamn")
password = st.text_input("Lösenord", type="password")

if user not in users or password != users[user]:
    st.warning("Fel användare eller lösenord")
    st.stop()

# -----------------------
# 1️⃣ Månadsval
# -----------------------
months = ["Januari","Februari","Mars","April","Maj","Juni",
          "Juli","Augusti","September","Oktober","November","December"]

month = st.selectbox("Välj månad", months)

# -----------------------
# Kategorier & underrubriker
# -----------------------
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

# -----------------------
# 2️⃣ Spara data (JSON)
# -----------------------
DATA_FILE = "budget_data_v4.json"
if os.path.exists(DATA_FILE):
    with open(DATA_FILE,"r") as f:
        budget_data = json.load(f)
else:
    budget_data = {}

if month not in budget_data:
    budget_data[month] = {}

# -----------------------
# 6️⃣ Budgetinmatning
# -----------------------
total_income = 0
total_expenses = 0
summary = []

for category, items in categories.items():
    with st.expander(category, expanded=True):
        if category not in budget_data[month]:
            budget_data[month][category] = {}

        rows = []
        for item in items + ["", "", ""]:
            key = f"{item or 'Tom'}"
            prev_budget = budget_data[month][category].get(key, {}).get("Budget",0)
            prev_actual = budget_data[month][category].get(key, {}).get("Faktiskt",0)
            
            col1, col2 = st.columns([1,1])
            with col1:
                budget = st.number_input(f"{item or '—'} Budget (€)", min_value=0.0, step=10.0, value=prev_budget, key=f"{month}_{category}_{key}_B")
            with col2:
                actual = st.number_input(f"{item or '—'} Faktiskt (€)", min_value=0.0, step=10.0, value=prev_actual, key=f"{month}_{category}_{key}_A")
            
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

# -----------------------
# Spara JSON
# -----------------------
with open(DATA_FILE,"w") as f:
    json.dump(budget_data,f,indent=4)

# -----------------------
# 3️⃣ Årssammanställning
# -----------------------
st.divider()
st.header("📊 Årssammanställning")

# Skapa DataFrame med månader x kategorier
df_year = pd.DataFrame(index=months, columns=categories.keys())
for m in months:
    for cat in categories.keys():
        if m in budget_data and cat in budget_data[m]:
            df_year.loc[m,cat] = sum([v["Faktiskt"] for v in budget_data[m][cat].values()])
        else:
            df_year.loc[m,cat] = 0
df_year = df_year.fillna(0).astype(float)

st.bar_chart(df_year)

# -----------------------
# 2️⃣ Dashboard – månad för månad
# -----------------------
st.divider()
st.header("📈 Dashboard per kategori")

for cat in categories.keys():
    st.subheader(cat)
    chart_df = df_year[[cat]]
    st.line_chart(chart_df)
    latest_val = chart_df[cat].iloc[-1]
    budget_estimate = chart_df[cat].max()
    if latest_val > budget_estimate:
        st.markdown(f"**⚠️ {cat} är över budget denna månad!**")
    else:
        st.markdown(f"**✅ {cat} är inom budget denna månad.**")

# -----------------------
# Överskott / underskott diagram
# -----------------------
st.divider()
st.header("💰 Månatligt överskott / underskott")

df_year["Totalt"] = df_year[categories.keys()].sum(axis=1)
# Inkomster minus utgifter
df_year["Resultat"] = df_year["Inkomster"] - (df_year["Totalt"] - df_year["Inkomster"])
st.bar_chart(df_year["Resultat"])

# -----------------------
# 2️⃣ Exportera Excel med röd/grön färg
# -----------------------
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
                    for item, vals in items_dict.items():
                        month_df.append([cat,item,vals["Budget"],vals["Faktiskt"]])
                df_month = pd.DataFrame(month_df, columns=["Kategori","Post","Budget","Faktiskt"])
                df_month.to_excel(writer, sheet_name=m[:31], index=False)
                
                # Conditional formatting
                workbook = writer.book
                worksheet = writer.sheets[m[:31]]
                red_format = workbook.add_format({'bg_color':'#FFC7CE'})
                green_format = workbook.add_format({'bg_color':'#C6EFCE'})
                # Kolumn D = Faktiskt
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
                for item, vals in items_dict.items():
                    combined.append([m,cat,item,vals["Budget"],vals["Faktiskt"]])
    df_csv = pd.DataFrame(combined, columns=["Månad","Kategori","Post","Budget","Faktiskt"])
    st.download_button(label="Ladda ner CSV", data=df_csv.to_csv(index=False), file_name="Familjebudget.csv")
