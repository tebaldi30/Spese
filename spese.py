import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- UTENTI E PASSWORD (esempio) ---
USERS = {"mario": "password123", "luca": "pass456"}

# --- Session state per login ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# --- Pagina di login ---
def login_page():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Benvenuto {username}!")
        else:
            st.error("Username o password errati")

# --- Connessione a Google Sheets (veloce con cache) ---
@st.cache_resource
def connect_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1Wf8A8BkTPJGrQmJca35_Spsbj1HJxmZoLffkreqGkrM").sheet1
    return sheet

# --- Carica dati in cache (veloce) ---
@st.cache_data(ttl=60)
def carica_dati(sheet):
    records = sheet.get_all_records()
    return pd.DataFrame(records)

# --- Funzioni ---
def salva_dato(sheet, tipo, data, importo, categoria=""):
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
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- Funzione principale app ---
def main_app(df, sheet):
    st.title(f"💰 Gestione Spese e Risparmi - Benvenuto {st.session_state.username}")

    # Logout
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        return

    # --- Pallina sotto il titolo ---
    totale_spese = clean_importo(df[df["Tipo"] == "Spesa"]["Importo"]).sum() if not df.empty else 0.0
    st.markdown(
        """
        <style>
        @keyframes blink {50% { opacity: 0; }}
        .blinking {animation: blink 1s infinite;}
        </style>
        """, unsafe_allow_html=True
    )
    colore = "green" if totale_spese < 2000 else "red"
    classe = "blinking" if colore == "red" else ""
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;margin-top:5px;">
            <div style="width:20px;height:20px;border-radius:50%;background:{colore};" class="{classe}"></div>
            <span style="font-size:16px;">Totale Spese: {format_currency(totale_spese)} €</span>
        </div>
        """, unsafe_allow_html=True
    )

    # --- Form spese ---
    st.subheader("➖ Aggiungi Spesa")
    with st.form("spese_form", clear_on_submit=True):
        data_spesa = st.date_input("Data spesa")
        tipo_spesa = st.text_input("Categoria (es. affitto, cibo, bollette)")
        valore_spesa = st.number_input("Importo (€)", min_value=0.0, step=1.0)
        if st.form_submit_button("Aggiungi Spesa") and valore_spesa > 0:
            salva_dato(sheet, "Spesa", data_spesa, valore_spesa, tipo_spesa)
            st.success("Spesa registrata!")

    # --- Form risparmi ---
    st.subheader("💵 Gestione Risparmi")
    with st.form("risparmi_form", clear_on_submit=True):
        data_risp = st.date_input("Data risparmio/prelievo")
        tipo_risp = st.radio("Tipo movimento", ["Risparmio", "Prelievo"])
        valore_risp = st.number_input("Importo (€)", min_value=0.0, step=1.0)
        if st.form_submit_button("Registra Movimento") and valore_risp > 0:
            if tipo_risp == "Prelievo":
                valore_risp = -valore_risp
            salva_dato(sheet, "Risparmio", data_risp, valore_risp, tipo_risp)
            st.success(f"{tipo_risp} registrato!")

    # --- Aggiorna dati ---
    df = carica_dati(sheet)

    # --- Riepilogo Spese ---
    if not df.empty:
        st.header("📊 Riepilogo Spese")
        spese = df[df["Tipo"] == "Spesa"].copy()
        if not spese.empty:
            spese["Importo_num"] = clean_importo(spese["Importo"])
            spese["Importo"] = spese["Importo_num"].apply(format_currency)
            st.dataframe(spese.drop(columns="Importo_num"))

            totale_spese = spese["Importo_num"].sum()
            st.metric("Totale Spese", format_currency(totale_spese) + " €")

            soglia_massima = 2000.0
            totale_spese_valore = min(totale_spese, soglia_massima)
            restante = soglia_massima - totale_spese_valore
            percent_speso = (totale_spese_valore / soglia_massima) * 100
            percent_disp = 100 - percent_speso

            valori = [totale_spese_valore, restante]
            colori = ["#e74c3c", "#27ae60"]

            st.subheader("📈 Andamento Mensile")
            fig, ax = plt.subplots()
            fig.patch.set_alpha(0.0)
            ax.patch.set_alpha(0.0)
            wedges, texts, autotexts = ax.pie(
                valori, colors=colori, autopct='%1.1f%%', pctdistance=1.1,
                labeldistance=1.2, startangle=90, counterclock=False,
                wedgeprops={'edgecolor': 'white', 'linewidth': 2},
                textprops={'color': 'black', 'weight': 'bold'}
            )
            for text in texts:
                text.set_text('')
            ax.axis('equal')
            st.pyplot(fig)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Speso", f"{percent_speso:.1f}%", delta=-totale_spese_valore)
                st.caption(f"{format_currency(totale_spese_valore)} € su {format_currency(soglia_massima)} €")
            with col2:
                st.metric("Disponibile", f"{percent_disp:.1f}%", delta=restante)
                st.caption(f"{format_currency(restante)} € disponibile")

        else:
            st.info("Nessuna spesa registrata.")

        # --- Riepilogo Risparmi ---
        st.header("💰 Riepilogo Risparmi")
        risp = df[df["Tipo"] == "Risparmio"].copy()
        if not risp.empty:
            risp["Importo_num"] = clean_importo(risp["Importo"])
            risp["Importo"] = risp["Importo_num"].apply(format_currency)
            st.dataframe(risp.drop(columns="Importo_num"))

            totale_risparmi = risp["Importo_num"].sum()
            st.metric("Saldo Risparmi", format_currency(totale_risparmi) + " €")

            obiettivo_risparmio = 40000.0
            percentuale_raggiunta = totale_risparmi / obiettivo_risparmio * 100
            st.subheader("🎯 Percentuale Obiettivo Risparmi")
            st.metric("Risparmio raggiunto", f"{percentuale_raggiunta:.1f}%", 
                      delta=f"{format_currency(totale_risparmi)} € su {format_currency(obiettivo_risparmio)} €")
        else:
            st.info("Nessun risparmio registrato.")
    else:
        st.info("Nessun dato ancora inserito.")

# --- Flusso principale ---
if not st.session_state.logged_in:
    login_page()
else:
    sheet = connect_gsheets()       # Cache della connessione
    df = carica_dati(sheet)         # Cache dei dati
    main_app(df, sheet)
