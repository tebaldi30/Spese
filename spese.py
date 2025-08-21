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
    return pd.to_numeric(series.astype(str).str.replace("€", "").str.replace(",", ".").str.strip(), errors='coerce')

def format_currency(value):
    """Mostra i numeri in formato italiano 1.200,00"""
    try:
        return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return value

# --- Interfaccia ---
st.title("💰 Gestione Spese e Risparmi")

# Carico i dati esistenti
df = carica_dati()

# --- Pallina Allerta ---
if not df.empty:
    spese_importo = clean_importo(df[df["Tipo"] == "Spesa"]["Importo"])
    totale_spese = spese_importo.sum()
    colore = "green" if totale_spese < 2000 else "red"
    animazione = "animation: blink 1s infinite;" if colore == "red" else ""
    st.markdown(
        f"""
        <style>
        @keyframes blink {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}
        </style>
        <div style="display:flex;align-items:center;gap:10px;margin-top:10px;">
            <div style="width:20px;height:20px;border-radius:50%;background:{colore};{animazione}"></div>
            <span style="font-size:18px;">Allerta Spese: {format_currency(totale_spese)} €</span>
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

# --- Form risparmi (aggiungi e togli) ---
st.subheader("➕➖ Gestione Risparmi")
with st.form("risparmi_form", clear_on_submit=True):
    data_risp = st.date_input("Data movimento")
    valore_risp = st.number_input("Importo (€)", min_value=0.0, step=1.0)
    tipo_mov = st.radio("Tipo movimento", ["Aggiungi", "Togli"])
    submitted_risp = st.form_submit_button("Salva")
    if submitted_risp and valore_risp > 0:
        importo_finale = valore_risp if tipo_mov == "Aggiungi" else -valore_risp
        salva_dato("Risparmio", data_risp, importo_finale, "")
        st.success("Movimento risparmio registrato!")

# Aggiorna dataframe
df = carica_dati()

# --- Tabelle e Grafici ---
if not df.empty:
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Mese"] = df["Data"].dt.to_period("M")

    # --- Sezione SPESE ---
    st.header("📊 Riepilogo Spese")
    spese = df[df["Tipo"] == "Spesa"].copy()
    if not spese.empty:
        spese["Importo"] = clean_importo(spese["Importo"])
        totale_spese = spese["Importo"].sum()
        col1, col2 = st.columns(2)
        col1.metric("Totale Spese", format_currency(totale_spese))

        spese["Importo"] = spese["Importo"].apply(format_currency)
        st.dataframe(spese)

        spese_mensili = spese.groupby("Mese")["Importo"].apply(lambda x: pd.to_numeric(x.str.replace(".", "").str.replace(",", ".").astype(float))).sum(level=0)
        st.subheader("📈 Andamento Spese")
        fig, ax = plt.subplots()
        spese_mensili.plot(kind="bar", ax=ax, color="red", alpha=0.6)
        st.pyplot(fig)

    # --- Sezione RISPARMI ---
    st.header("💹 Riepilogo Risparmi")
    risp = df[df["Tipo"] == "Risparmio"].copy()
    if not risp.empty:
        risp["Importo"] = clean_importo(risp["Importo"])
        totale_risparmi = risp["Importo"].sum()
        col3, col4 = st.columns(2)
        col3.metric("Totale Risparmi", format_currency(totale_risparmi))

        risp["Importo"] = risp["Importo"].apply(format_currency)
        st.dataframe(risp)

        risp_mensili = risp.groupby("Mese")["Importo"].apply(lambda x: pd.to_numeric(x.str.replace(".", "").str.replace(",", ".").astype(float))).sum(level=0)
        st.subheader("📈 Andamento Risparmi")
        fig, ax = plt.subplots()
        risp_mensili.plot(kind="bar", ax=ax, color="green", alpha=0.6)
        st.pyplot(fig)

else:
    st.info("Nessun dato ancora inserito.")
