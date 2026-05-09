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

def delete_row(sheet, row_idx):
    try:
        url = f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}&deleteRow={int(row_idx) + 2}"
        requests.get(url, timeout=10)
        return True
    except: return False

# --- CARICAMENTO ---
df_q = load_data(URL_CARNE)
if not df_q.empty:
    while len(df_q.columns) < 4: df_q[f"Col_{len(df_q.columns)}"] = ""
    df_q.columns = ["Giorno", "Prodotto", "Quantita", "Ora"][:len(df_q.columns)]
    df_q["Quantita"] = pd.to_numeric(df_q["Quantita"], errors='coerce').fillna(0)

# --- INTERFACCIA ---
st.title("🍖 Monitoraggio Carne Sagra")

# 1. SEZIONE INSERIMENTO (Sempre visibile)
with st.container():
    st.subheader("➕ Inserimento Dati")
    with st.form("form_carne", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        f_d = c1.selectbox("Turno", DATE_UFFICIALI)
        f_p = c2.selectbox("Prodotto", PRODOTTI)
        f_q = c3.number_input("Pezzi Monitor", min_value=0, step=1)
        f_h = c4.text_input("Ora", value=(datetime.now() + timedelta(hours=2)).strftime("%H:%M"))
        if st.form_submit_button("REGISTRA"):
            if save_data("Quantità Grigliate", [f_d, f_p, f_q, f_h]):
                st.success("Dato Salvato!")
                time.sleep(1)
                st.rerun()

st.divider()

if not df_q.empty:
    # 2. GRAFICO TOTALE
    st.subheader("🏆 Produzione Totale Sagra")
    df_max_giorni = df_q.groupby(["Giorno", "Prodotto"])["Quantita"].max().reset_index()
    df_totale = df_max_giorni.groupby("Prodotto")["Quantita"].sum().reindex(PRODOTTI).fillna(0).reset_index()
    st.plotly_chart(px.bar(df_totale, x="Prodotto", y="Quantita", color="Prodotto", text_auto=True, color_discrete_map=COLORI_CARNE), use_container_width=True)

    # 3. DETTAGLIO TURNI (Appaiono solo se il nome coincide con DATE_UFFICIALI)
    st.subheader("🔍 Dettaglio per Singolo Turno")
    for g_uff in DATE_UFFICIALI:
        df_g = df_q[df_q["Giorno"] == g_uff].sort_values("Ora")
        if not df_g.empty:
            st.markdown(f"#### 📅 {g_uff}")
            df_g["Ritmo"] = df_g.groupby("Prodotto")["Quantita"].diff().fillna(df_g["Quantita"])
            df_g.loc[df_g["Ritmo"] < 0, "Ritmo"] = 0
            
            ca, cb = st.columns(2)
            with ca:
                res = df_g.groupby("Prodotto")["Quantita"].max().reindex(PRODOTTI).fillna(0).reset_index()
                st.plotly_chart(px.bar(res, x="Prodotto", y="Quantita", color="Prodotto", text_auto=True, color_discrete_map=COLORI_CARNE, height=250), use_container_width=True, key=f"b_{g_uff}")
            with cb:
                st.plotly_chart(px.line(df_g, x="Ora", y="Ritmo", color="Prodotto", markers=True, color_discrete_map=COLORI_CARNE, height=250), use_container_width=True, key=f"l_{g_uff}")
    
    st.divider()
    
    # 4. SEZIONE MODIFICA/ELIMINA (Sempre visibile in fondo)
    with st.expander("⚙️ Storico Dati e Cancellazione"):
        st.write("Qui puoi vedere gli ultimi inserimenti e cancellare quelli sbagliati:")
        # Mostriamo gli ultimi 20 inserimenti (dal più recente)
        for idx, row in df_q.iloc[::-1].head(20).iterrows():
            col1, col2 = st.columns([8, 2])
            col1.write(f"**{row['Giorno']}** | {row['Prodotto']} | {int(row['Quantita'])} pz | ore {row['Ora']}")
            if col2.button("Elimina", key=f"del_{idx}"):
                if delete_row("Quantità Grigliate", idx):
                    st.success("Eliminato!")
                    time.sleep(1)
                    st.rerun()

else:
    st.warning("Nessun dato presente nel foglio 'Quantità Grigliate'.")
