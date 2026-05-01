import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import urllib.parse
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxlzO8HR87qEHeM5L6kDLWwctu_AehDK8yZZhhCh_bNLiLmPk3GTTJXKRHGeM0XBtxA/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_MAGAZZINO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")
URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"

DATE_SOGLIA = ["Sabato 09 maggio", "Sabato 10 maggio", "Domenica 10 maggio", "Venerdì 15 maggio", "Sabato 16 maggio", "Domenica 17 maggio", "Sabato 23 maggio", "Domenica 24 maggio"]
TURNI = ["Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Cena", "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"]

# --- FUNZIONI ---
def load_data(url):
    try:
        df = pd.read_csv(f"{url}&nocache={time.time()}")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return pd.DataFrame()

def save_data(sheet, data):
    try: requests.post(f"{SCRIPT_URL}?sheet={sheet}", data=json.dumps(data), timeout=10); return True
    except: return False

def delete_row(sheet, row_index):
    try: requests.get(f"{SCRIPT_URL}?sheet={sheet}&deleteRow={row_index}", timeout=10); return True
    except: return False

# --- INTERFACCIA ---
st.title("🔥 Portale Grigliatori 2026")
tab1, tab2, tab3 = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "⚙️ Admin"])

# --- TAB 1: PRESENZE (Invariata) ---
with tab1:
    grigliatori = ["Boscaratto Denis", "Botteon Marco", "Da Ronch Loris", "Dassie Massimo", "Disconzi Francesco", "Flavio", "Giacomo", "Micieli Mauro", "Modolo Zanchetta Mirko", "Perencin Davide", "Perencin Francesco", "Rossi Riccardo", "Sossai Gianluca"]
    user = st.selectbox("Chi sei?", grigliatori)
    df_p = load_data(URL_PRESENZE)
    miei_turni = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist() if not df_p.empty else []
    
    cols = st.columns(3)
    for i, t in enumerate(TURNI):
        with cols[i%3]:
            if st.toggle(t, value=(t in miei_turni), key=f"t_{user}_{i}"):
                if t not in miei_turni:
                    if save_data("Presenze", [user, t]): st.rerun()

# --- TAB 2: CARNE SMART CON CANCELLAZIONE ---
with tab2:
    st.header("🍖 Registrazione e Correzione")
    
    # Inserimento
    with st.expander("➕ Inserisci Nuova Grigliata", expanded=True):
        with st.form("carne_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            f_data = c1.selectbox("Giorno", DATE_SOGLIA)
            f_tipo = c2.selectbox("Cibo", ["Costicine", "Salsicce", "Braciole"])
            f_qta = c3.number_input("Kg", min_value=1, step=1)
            f_ora = c4.text_input("Ora", value=datetime.now().strftime("%H:%M"))
            if st.form_submit_button("Registra 📝"):
                if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]):
                    st.success("Dato salvato!"); time.sleep(1); st.rerun()

    # Sezione Correzione Errori
    df_q = load_data(URL_MAGAZZINO)
    if not df_q.empty:
        if len(df_q.columns) >= 4:
            df_q.columns = ['Giorno', 'Prodotto', 'Quantita', 'Ora'] + list(df_q.columns[4:])
        
        st.subheader("⚠️ Ultimi inserimenti (per correggere errori)")
        # Mostriamo gli ultimi 5 inserimenti
        last_entries = df_q.tail(5).copy()
        for i, row in last_entries.iterrows():
            c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
            c1.write(row['Giorno'])
            c2.write(row['Prodotto'])
            c3.write(f"{row['Quantita']}kg")
            c4.write(row['Ora'])
            if c5.button("Elimina 🗑️", key=f"del_{i}"):
                if delete_row("Quantità Grigliate", i + 1): # +1 per saltare intestazione
                    st.warning("Dato eliminato..."); time.sleep(1); st.rerun()

        # Grafico Andamento
        st.divider()
        st.subheader("📈 Andamento Giornaliero")
        f_data_view = st.selectbox("Giorno da analizzare:", DATE_SOGLIA)
        df_filtered = df_q[df_q['Giorno'] == f_data_view].sort_values(by='Ora')
        if not df_filtered.empty:
            fig = px.line(df_filtered, x='Ora', y='Quantita', color='Prodotto', markers=True,
                          color_discrete_map={"Costicine": "#e63946", "Salsicce": "#f4a261", "Braciole": "#457b9d"})
            st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: ADMIN ---
with tab3:
    st.link_button("📂 Apri Foglio Google", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
