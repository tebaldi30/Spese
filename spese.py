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
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
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
st.subheader("💵 Gestione Risparmi")
with st.form("risparmi_form", clear_on_submit=True):
    data_risp = st.date_input("Data risparmio/prelievo")
    tipo_risp = st.radio("Tipo movimento", ["Risparmio", "Prelievo"])
    valore_risp = st.number_input("Importo (€)", min_value=0.0, step=1.0)
    submitted_risp = st.form_submit_button("Registra Movimento")
    if submitted_risp and valore_risp > 0:
        if tipo_risp == "Prelievo":
            valore_risp = -valore_risp
        salva_dato("Risparmio", data_risp, valore_risp, tipo_risp)
        st.success(f"{tipo_risp} registrato!")

# --- Aggiorna dati ---
df = carica_dati()

# --- RIEPILOGO SPESE ---
if not df.empty:
    st.header("📊 Riepilogo Spese")
    spese = df[df["Tipo"] == "Spesa"].copy()
    if not spese.empty:
        spese["Importo_num"] = clean_importo(spese["Importo"])
        spese["Importo"] = spese["Importo_num"].apply(format_currency)
        st.dataframe(spese.drop(columns="Importo_num"))

        totale_spese = spese["Importo_num"].sum()
        st.metric("Totale Spese", format_currency(totale_spese) + " €")

        # Effetto pillola sopra il grafico spese
        soglia_massima = 2000.0
        totale_spese_valore = totale_spese if totale_spese <= soglia_massima else soglia_massima
        restante = soglia_massima - totale_spese_valore

        pillola_html = f"""
        <div style="
            display: inline-block;
            background-color: #e7faf2;
            border-radius: 16px;
            padding: 6px 16px;
            font-weight: 600;
            color: #27ae60;
            font-size: 16px;
            font-family: inherit;
            white-space: nowrap;
            margin-bottom: 12px;
        ">
            {format_currency(totale_spese_valore)}&nbsp;€ su&nbsp;{format_currency(soglia_massima)}&nbsp;€
        </div>
        """
        st.markdown(pillola_html, unsafe_allow_html=True)

        # Grafico a torta spese vs budget 2000 € con etichette numeriche verdi senza testo aggiuntivo
        valori = [totale_spese_valore, restante]
        colori = ["#e74c3c", "#27ae60"]

        def get_label_text(importo, totale):
            return f"{format_currency(importo)}\u202f€ su {format_currency(totale)}\u202f€"

        etichette = [
            get_label_text(totale_spese_valore, soglia_massima),
            get_label_text(restante, soglia_massima)
        ]

        label_color = "#27ae60"

        fig, ax = plt.subplots()
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

        wedges, texts, autotexts = ax.pie(
            valori,
            labels=etichette,
            colors=colori,
            autopct="%1.1f%%",
            startangle=90,
            counterclock=False,
            wedgeprops={'edgecolor': 'white', 'linewidth': 2},
            textprops={'color': label_color, 'weight': 'bold'}
        )

        for text in texts:
            text.set_color(label_color)
            text.set_weight('bold')

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_weight('bold')

        ax.axis("equal")
        st.pyplot(fig)

    else:
        st.info("Nessuna spesa registrata.")

    # --- RIEPILOGO RISPARMI ---
    st.header("💰 Riepilogo Risparmi")
    risp = df[df["Tipo"] == "Risparmio"].copy()
    if not risp.empty:
        risp["Importo_num"] = clean_importo(risp["Importo"])
        risp["Importo"] = risp["Importo_num"].apply(format_currency)
        st.dataframe(risp.drop(columns="Importo_num"))

        totale_risparmi = risp["Importo_num"].sum()
        st.metric("Saldo Risparmi", format_currency(totale_risparmi) + " €")

        obiettivo_risparmio = 40000.0
        percentuale_raggiunta = totale_risparmi / obiettivo_risparmio * 100 if obiettivo_risparmio else 0

        st.subheader("🎯 Percentuale Obiettivo Risparmi")
        st.metric(
            label="Risparmio raggiunto",
            value=f"{percentuale_raggiunta:.1f}%",
            delta=f"{format_currency(totale_risparmi)} € su {format_currency(obiettivo_risparmio)} €"
        )
    else:
        st.info("Nessun risparmio registrato.")

else:
    st.info("Nessun dato ancora inserito.")
