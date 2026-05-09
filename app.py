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

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Monitor Carne 2026", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby7yJ-jjJYworKTL9w20Er0w_Av3U1xqUvLQi0oGlrYy70Sg1xK6BJysNGZIZlJ0DtM/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
URL_CARNE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")

DATE_UFFICIALI = [
    "Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI = ["Costicine", "Salsicce", "Braciole"]
COLORI_CARNE = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

# --- 2. FUNZIONI ---
def load_data(url):
    try:
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        df = df.apply(lambda x: x.str.strip())
        return df
    except: return pd.DataFrame()

def save_data(sheet, data):
    try:
        res = requests.post(f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}", data=json.dumps(data), timeout=15)
        return res.status_code == 200
    except: return False

# --- 3. LOGICA CARICAMENTO ---
df_q = load_data(URL_CARNE)

# Pulizia e preparazione colonne
if not df_q.empty:
    # Se il foglio ha meno di 4 colonne, aggiungiamo quelle mancanti
    while len(df_q.columns) < 4:
        df_q[f"Col_{len(df_q.columns)}"] = ""
    df_q.columns = ["Giorno", "Prodotto", "Quantita", "Ora"][:len(df_q.columns)]
    df_q["Quantita"] = pd.to_numeric(df_q["Quantita"], errors='coerce').fillna(0)

# --- 4. INTERFACCIA ---
st.title("🍖 Monitoraggio Carne")

# --- SEMPRE VISIBILE: FINESTRA INSERIMENTO ---
with st.expander("➕ CLICCA QUI PER INSERIRE NUOVI DATI", expanded=True):
    ora_it = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
    with st.form("form_nuovo_dato", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        f_d = c1.selectbox("Giorno", DATE_UFFICIALI)
        f_p = c2.selectbox("Prodotto", PRODOTTI)
        f_q = c3.number_input("Pezzi Monitor", min_value=0, step=1)
        f_h = c4.text_input("Ora", value=ora_it)
        if st.form_submit_button("REGISTRA"):
            if save_data("Quantità Grigliate", [f_d, f_p, f_q, f_h]):
                st.success("Registrato!")
                time.sleep(1)
                st.rerun()

st.divider()

if not df_q.empty:
    # 5. TOTALE GENERALE (Somma dei massimi di ogni giorno)
    st.subheader("🏆 Totale Generale Sagra")
    # Logica per raggruppare anche se le date sono scritte leggermente diverse
    df_max = df_q.groupby(["Giorno", "Prodotto"])["Quantita"].max().reset_index()
    df_tot = df_max.groupby("Prodotto")["Quantita"].sum().reindex(PRODOTTI).fillna(0).reset_index()
    st.plotly_chart(px.bar(df_tot, x="Prodotto", y="Quantita", color="Prodotto", text_auto=True,
                           color_discrete_map=COLORI_CARNE), use_container_width=True)

    # 6. GRAFICI SINGOLI TURNI
    st.subheader("🔍 Dettaglio Turni")
    
    # Cerchiamo quali giorni della lista DATE_UFFICIALI sono presenti nel foglio
    # Usiamo una ricerca flessibile: basta che la data ufficiale contenga il testo del foglio
    giorni_presenti = df_q["Giorno"].unique()
    
    for g_uff in DATE_UFFICIALI:
        # Filtriamo i dati che corrispondono a questo turno
        df_g = df_q[df_q["Giorno"] == g_uff]
        
        if not df_g.empty:
            st.markdown(f"### 📅 {g_uff}")
            df_g = df_g.sort_values("Ora")
            # Calcolo Ritmo
            df_g["Variazione"] = df_g.groupby("Prodotto")["Quantita"].diff().fillna(df_g["Quantita"])
            df_g.loc[df_g["Variazione"] < 0, "Variazione"] = 0
            
            col_a, col_b = st.columns(2)
            with col_a:
                res = df_g.groupby("Prodotto")["Quantita"].max().reindex(PRODOTTI).fillna(0).reset_index()
                st.plotly_chart(px.bar(res, x="Prodotto", y="Quantita", color="Prodotto", text_auto=True,
                                     color_discrete_map=COLORI_CARNE, title="Pezzi Totali", height=250), use_container_width=True, key=f"b_{g_uff}")
            with col_b:
                st.plotly_chart(px.line(df_g, x="Ora", y="Variazione", color="Prodotto", markers=True,
                                      color_discrete_map=COLORI_CARNE, title="Ritmo", height=250), use_container_width=True, key=f"l_{g_uff}")
else:
    st.warning("⚠️ Nessun dato trovato nel foglio 'Quantità Grigliate'. Inserisci il primo dato qui sopra.")

# --- DEBUG IN FONDO ---
with st.expander("⚙️ Debug Dati (Se non vedi i grafici, controlla qui)"):
    st.write("Cosa legge l'app dal foglio Google:")
    st.dataframe(df_q)
