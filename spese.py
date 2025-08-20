import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Connessione a Google Sheets ---
@st.cache_resource
def connect_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    # Sostituisci con l’ID del tuo Google Sheet
    sheet = client.open_by_key("1Wf8A8BkTPJGrQmJca35_Spsbj1HJxmZoLffkreqGkrM").sheet1  
    return sheet

sheet = connect_gsheets()

# --- Funzioni ---
def carica_dati():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

def salva_dato(tipo, data, importo, categoria=""):
    sheet.append_row([tipo, str(data), importo, categoria])

# --- Interfaccia ---
st.title("💰 Gestione Spese e Risparmi")

# Carico i dati esistenti
df = carica_dati()

# Form spese
st.subheader("➖ Aggiungi Spesa")
with st.form("spese_form", clear_on_submit=True):
    data_spesa = st.date_input("Data spesa")
    tipo_spesa = st.text_input("Categoria (es. affitto, cibo, bollette)")
    valore_spesa = st.number_input("Importo (€)", min_value=0.0, step=1.0)
    submitted_spesa = st.form_submit_button("Aggiungi Spesa")
    if submitted_spesa and valore_spesa > 0:
        salva_dato("Spesa", data_spesa, valore_spesa, tipo_spesa)
        st.success("Spesa registrata!")

# Form risparmi
st.subheader("➕ Aggiungi Risparmio")
with st.form("risparmi_form", clear_on_submit=True):
    data_risp = st.date_input("Data risparmio")
    valore_risp = st.number_input("Importo risparmiato (€)", min_value=0.0, step=1.0)
    submitted_risp = st.form_submit_button("Aggiungi Risparmio")
    if submitted_risp and valore_risp > 0:
        salva_dato("Risparmio", data_risp, valore_risp, "")
        st.success("Risparmio registrato!")

# Aggiorna dataframe
df = carica_dati()

# --- Tabelle ---
if not df.empty:
    st.subheader("📊 Riepilogo")
    st.dataframe(df)

    totale_spese = df[df["Tipo"]=="Spesa"]["Importo"].sum()
    totale_risparmi = df[df["Tipo"]=="Risparmio"]["Importo"].sum()

    col1, col2 = st.columns(2)
    col1.metric("Totale Spese", f"{totale_spese:.2f} €")
    col2.metric("Totale Risparmi", f"{totale_risparmi:.2f} €")

    # --- Grafico mensile ---
    df["Data"] = pd.to_datetime(df["Data"])
    df["Mese"] = df["Data"].dt.to_period("M")
    spese_mensili = df[df["Tipo"]=="Spesa"].groupby("Mese")["Importo"].sum()
    risparmi_mensili = df[df["Tipo"]=="Risparmio"].groupby("Mese")["Importo"].sum()

    st.subheader("📈 Andamento Mensile")
    fig, ax = plt.subplots()
    spese_mensili.plot(kind="bar", ax=ax, color="red", alpha=0.6, label="Spese")
    risparmi_mensili.plot(kind="bar", ax=ax, color="green", alpha=0.6, label="Risparmi")
    ax.legend()
    st.pyplot(fig)
else:
    st.info("Nessun dato ancora inserito.")

