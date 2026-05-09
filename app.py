import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import io
import urllib.parse
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby7yJ-jjJYworKTL9w20Er0w_Av3U1xqUvLQi0oGlrYy70Sg1xK6BJysNGZIZlJ0DtM/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_CARNE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")
URL_NOMI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=ListaGrigliatori"

# LISTA UNICA E DEFINITIVA PER TUTTA L'APP
DATE_UFFICIALI = [
    "Sabato 09 maggio - Cena", 
    "Domenica 10 maggio - Pranzo", 
    "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio - Cena della costata", 
    "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Pranzo", 
    "Domenica 17 maggio - Cena",
    "Sabato 23 maggio - Cena", 
    "Domenica 24 maggio - Pranzo", 
    "Domenica 24 maggio - Cena"
]
PRODOTTI = ["Costicine", "Salsicce", "Braciole"]
COLORI_CARNE = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

# --- FUNZIONI ROBUSTE ---
def load_data(url):
    try:
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        # na_filter=False impedisce la creazione di "nan"
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        df = df.apply(lambda x: x.str.strip())
        return df
    except: return pd.DataFrame()

def save_data(sheet, data):
    try:
        res = requests.post(f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}", data=json.dumps(data), timeout=15)
        return res.status_code == 200
    except: return False

def delete_row(sheet, row_idx):
    try:
        url = f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}&deleteRow={int(row_idx) + 2}"
        requests.get(url, timeout=10)
        return True
    except: return False

# --- INTERFACCIA ---
st.title("🍖 Monitoraggio Carne Sagra 2026")

tab_monitor, tab_gestione = st.tabs(["📊 Monitor Produzione", "⚙️ Inserimento e Modifica"])

# Carichiamo i dati una volta sola
df_q = load_data(URL_CARNE)
if not df_q.empty:
    df_q.columns = ["Giorno", "Prodotto", "Quantita", "Ora"][:len(df_q.columns)]
    # Convertiamo la quantità in numero, se c'è errore mettiamo 0
    df_q["Quantita"] = pd.to_numeric(df_q["Quantita"], errors='coerce').fillna(0)

# --- TAB 1: I GRAFICI (MONITOR) ---
with tab_monitor:
    if not df_q.empty:
        # 1. TOTALONE SAGRA (Sempre visibile in alto)
        st.markdown("""<div style="background-color:#1d3557; padding:15px; border-radius:10px; margin-bottom:25px;">
                    <h2 style="color:white; text-align:center; margin:0;">🏆 PRODUZIONE TOTALE SAGRA (TUTTI I GIORNI)</h2>
                    </div>""", unsafe_allow_html=True)
        
        # Sommiamo il massimo raggiunto ogni giorno per ogni prodotto
        df_max_giornalieri = df_q.groupby(["Giorno", "Prodotto"])["Quantita"].max().reset_index()
        df_sagra_completa = df_max_giornalieri.groupby("Prodotto")["Quantita"].sum().reindex(PRODOTTI).fillna(0).reset_index()
        
        st.plotly_chart(px.bar(df_sagra_completa, x="Prodotto", y="Quantita", color="Prodotto", text_auto=True,
                           color_discrete_map=COLORI_CARNE, height=400), use_container_width=True)
        
        st.divider()

        # 2. DETTAGLIO SINGOLE GIORNATE
        st.subheader("🔍 Analisi per Turno")
        # Mostriamo solo i giorni che hanno effettivamente dei dati
        giorni_con_dati = [d for d in DATE_UFFICIALI if d in df_q["Giorno"].unique()]
        
        for g in giorni_con_dati:
            df_g = df_q[df_q["Giorno"] == g].sort_values("Ora")
            
            # Calcolo Ritmo (Variazione tra una riga e l'altra)
            df_g["Variazione"] = df_g.groupby("Prodotto")["Quantita"].diff().fillna(df_g["Quantita"])
            df_g.loc[df_g["Variazione"] < 0, "Variazione"] = 0 # Evitiamo ritmi negativi se si corregge un dato

            with st.expander(f"📅 Dettaglio: {g}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    # Barre del totale raggiunto nel turno
                    df_b = df_g.groupby("Prodotto")["Quantita"].max().reindex(PRODOTTI).fillna(0).reset_index()
                    st.plotly_chart(px.bar(df_b, x="Prodotto", y="Quantita", color="Prodotto", text_auto=True,
                                         color_discrete_map=COLORI_CARNE, title="Pezzi Totali Turno", height=300), use_container_width=True, key=f"b_{g}")
                with c2:
                    # Linee del ritmo di grigliata
                    st.plotly_chart(px.line(df_g, x="Ora", y="Variazione", color="Prodotto", markers=True,
                                          color_discrete_map=COLORI_CARNE, title="Ritmo (Pezzi aggiunti per ora)", height=300), use_container_width=True, key=f"l_{g}")
    else:
        st.info("Nessun dato inserito. Vai nel tab 'Inserimento' per aggiungere i primi pezzi.")

# --- TAB 2: INSERIMENTO E MODIFICA ---
with tab_gestione:
    col_ins, col_list = st.columns([1, 1])
    
    with col_ins:
        st.subheader("➕ Nuova Rilevazione")
        ora_attuale = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
        with st.form("inserimento_carne", clear_on_submit=True):
            f_data = st.selectbox("Seleziona Turno", DATE_UFFICIALI)
            f_prod = st.selectbox("Prodotto", PRODOTTI)
            f_qta = st.number_input("Pezzi totali letti sul monitor", min_value=0, step=1)
            f_ora = st.text_input("Ora rilevazione", value=ora_attuale)
            
            if st.form_submit_button("REGISTRA DATO"):
                if save_data("Quantità Grigliate", [f_data, f_prod, f_qta, f_ora]):
                    st.success("Dato salvato correttamente!")
                    time.sleep(1)
                    st.rerun()

    with col_list:
        st.subheader("🗑️ Storico Inserimenti")
        if not df_q.empty:
            # Mostriamo gli ultimi 10 inserimenti per poterli cancellare
            for idx, row in df_q.sort_index(ascending=False).head(15).iterrows():
                c_t, c_b = st.columns([4, 1])
                c_t.write(f"**{row['Giorno']}** - {row['Prodotto']}: {int(row['Quantita'])} pz ({row['Ora']})")
                if c_b.button("Elimina", key=f"del_{idx}"):
                    if delete_row("Quantità Grigliate", idx):
                        st.rerun()

    # DEBUG SECTION
    with st.expander("🛠️ Controllo Sincronizzazione Excel"):
        if not df_q.empty:
            date_errate = [d for d in df_q["Giorno"].unique() if d not in DATE_UFFICIALI and d != ""]
            if date_errate:
                st.error(f"ATTENZIONE: Nel foglio Excel ci sono date scritte male: {date_errate}")
                st.info("Questi dati non appariranno nei grafici finché non correggi il nome nel foglio Google.")
            else:
                st.success("Tutte le date nel foglio Carne sono sincronizzate con l'app!")
