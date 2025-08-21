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
    sheet = client.open_by_key("1Wf8A8BkTPJGrQmJca35_Spsbj1HJxmZoLffkreqGkrM").sheet1  
    return sheet

sheet = connect_gsheets()

# --- Funzioni ---
def carica_dati():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

def salva_dato(tipo, data, importo, categoria=""):
    sheet.append_row([tipo, str(data), importo, categoria])

def clean_importo(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace("€", "")
        .str.replace(".", "", regex=False)   # elimina separatore migliaia
        .str.replace(",", ".", regex=False)  # converte la virgola in punto
        .str.strip(),
        errors="coerce"
    )

def format_currency(value):
    """Formatta il numero in stile italiano: 1.200,00"""
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- Carico i dati ---
df = carica_dati()
spese_importo = clean_importo(df[df["Tipo"] == "Spesa"]["Importo"]) if not df.empty else pd.Series(dtype=float)
totale_spese = spese_importo.sum() if not df.empty else 0.0

# --- Titolo ---
st.title("💰 Gestione Spese e Risparmi")

# --- Pallina sotto il titolo ---
st.markdown(
    """
    <style>
    @keyframes blink {
        50% { opacity: 0; }
    }
    .blinking {
        animation: blink 1s infinite;
    }
    </style>
    """,
    unsafe_allow_html=True
)

colore = "green" if totale_spese < 2000 else "red"
classe = "blinking" if colore == "red" else ""

st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:10px;margin-top:5px;">
        <div style="width:20px;height:20px;border-radius:50%;background:{colore};"
             class="{classe}"></div>
        <span style="font-size:16px;">Totale Spese: {format_currency(totale_spese)} €</span>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Form spese ---
st.subheader("➖ Aggiungi Spesa")
with st.form("spese_form", clear_on_submit=True):
    data_spesa = st.date_input("Data spesa")
    tipo_spesa = st.text_input("Categoria (es. affitto, cibo, bollette)")
    valore_spesa = st.number_input("Importo (€)", min_value=0.0, step=1.0)
    submitted_spesa = st.form_submit_button("Aggiungi Spesa")
    if submitted_spesa and valore_spesa > 0:
        salva_dato("Spesa", data_spesa, valore_spesa, tipo_spesa)
        st.success("Spesa registrata!")

# --- Form risparmi ---
st.subheader("➕ Aggiungi Risparmio")
with st.form("risparmi_form", clear_on_submit=True):
    data_risp = st.date_input("Data risparmio")
    valore_risp = st.number_input("Importo risparmiato (€)", min_value=0.0, step=1.0)
    submitted_risp = st.form_submit_button("Aggiungi Risparmio")
    if submitted_risp and valore_risp > 0:
        salva_dato("Risparmio", data_risp, valore_risp, "")
        st.success("Risparmio registrato!")

# --- Aggiorna dati ---
df = carica_dati()

# --- Tabelle e grafici ---
if not df.empty:
    st.subheader("📊 Riepilogo")
    st.dataframe(df)

    spese_importo = clean_importo(df[df["Tipo"] == "Spesa"]["Importo"])
    risparmi_importo = clean_importo(df[df["Tipo"] == "Risparmio"]["Importo"])

    totale_spese = spese_importo.sum()
    totale_risparmi = risparmi_importo.sum()

    col1, col2 = st.columns(2)
    col1.metric("Totale Spese", format_currency(totale_spese) + " €")
    col2.metric("Totale Risparmi", format_currency(totale_risparmi) + " €")

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Mese"] = df["Data"].dt.to_period("M")

    spese_mensili = spese_importo.groupby(df.loc[df["Tipo"] == "Spesa", "Mese"]).sum()
    risparmi_mensili = risparmi_importo.groupby(df.loc[df["Tipo"] == "Risparmio", "Mese"]).sum()

    st.subheader("📈 Andamento Mensile")
    fig, ax = plt.subplots()
    spese_mensili.plot(kind="bar", ax=ax, color="red", alpha=0.6, label="Spese")
    risparmi_mensili.plot(kind="bar", ax=ax, color="green", alpha=0.6, label="Risparmi")
    ax.legend()
    st.pyplot(fig)

    st.subheader("📋 Conteggio Movimenti")
    col3, col4 = st.columns(2)
    col3.metric("Numero Spese", len(df[df["Tipo"] == "Spesa"]))
    col4.metric("Numero Risparmi", len(df[df["Tipo"] == "Risparmio"]))

else:
    st.info("Nessun dato ancora inserito.")
