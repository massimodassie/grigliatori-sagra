import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import urllib.parse
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxlzO8HR87qEHeM5L6kDLWwctu_AehDK8yZZhhCh_bNLiLmPk3GTTJXKRHGeM0XBtxA/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_MAGAZZINO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")

DATE_SOGLIA = ["Sabato 09 maggio", "Sabato 10 maggio", "Domenica 10 maggio", "Venerdì 15 maggio", "Sabato 16 maggio", "Domenica 17 maggio", "Sabato 23 maggio", "Domenica 24 maggio"]
PRODOTTI_ORDINE = ["Costicine", "Salsicce", "Braciole"]
COLOR_MAP = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

def load_data(url):
    try:
        # Forziamo il refresh scaricando il CSV puro
        response = requests.get(f"{url}&nocache={time.time()}")
        if response.status_code == 200:
            import io
            df = pd.read_csv(io.StringIO(response.text))
            # Pulizia universale: togliamo spazi dai nomi colonne e dai dati testo
            df.columns = [str(c).strip() for c in df.columns]
            df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
            return df
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
    return pd.DataFrame()

def save_data(sheet, data):
    try:
        requests.post(f"{SCRIPT_URL}?sheet={sheet}", data=json.dumps(data), timeout=10)
        return True
    except: return False

def delete_row(sheet, row_index):
    try:
        requests.get(f"{SCRIPT_URL}?sheet={sheet}&deleteRow={row_index}", timeout=10)
        return True
    except: return False

# --- INTERFACCIA ---
st.title("🔥 Portale Grigliatori 2026")
tab1, tab2, tab3 = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "⚙️ Admin"])

# --- TAB 1: PRESENZE (RIFATTO) ---
with tab1:
    grigliatori = ["Boscaratto Denis", "Botteon Marco", "Da Ronch Loris", "Dassie Massimo", "Disconzi Francesco", "Flavio", "Giacomo", "Micieli Mauro", "Modolo Zanchetta Mirko", "Perencin Davide", "Perencin Francesco", "Rossi Riccardo", "Sossai Gianluca"]
    user = st.selectbox("Chi sei?", grigliatori)
    df_p = load_data(URL_PRESENZE)
    
    # Se il foglio ha dati, mappiamo per posizione (Colonna 0: Nome, Colonna 1: Turno)
    if not df_p.empty and len(df_p.columns) >= 2:
        miei_turni = df_p[df_p.iloc[:, 0] == user].iloc[:, 1].tolist()
    else:
        miei_turni = []

    turni_lista = ["Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Cena", "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"]
    
    cols = st.columns(3)
    for i, t in enumerate(turni_lista):
        with cols[i%3]:
            if st.toggle(t, value=(t in miei_turni), key=f"t_{user}_{i}"):
                if t not in miei_turni:
                    if save_data("Presenze", [user, t]): st.rerun()

    st.divider()
    st.subheader("📊 Stato Copertura")
    if not df_p.empty and len(df_p.columns) >= 2:
        df_count = df_p.drop_duplicates()
        c_pie = st.columns(3)
        for i, t in enumerate(turni_lista):
            with c_pie[i%3]:
                # Contiamo quante persone ci sono per quel turno (colonna 1)
                count = len(df_count[df_count.iloc[:, 1] == t])
                target = 5 if "Pranzo" in t else 6
                fig = go.Figure(go.Pie(values=[count, max(0, target-count)], hole=0.6, 
                                        marker_colors=["#2a9d8f" if count >= target else "#FF0000", "#eeeeee"], 
                                        showlegend=False))
                fig.update_layout(title=f"<b>{t}</b>", height=180, margin=dict(t=30,b=0,l=0,r=0),
                                  annotations=[dict(text=str(count), x=0.5, y=0.5, font_size=18, showarrow=False)])
                st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: CARNE (FIX TOTALE) ---
with tab2:
    st.header("🍖 Monitoraggio Produzione")
    
    with st.expander("➕ Inserisci Nuova Quantità"):
        with st.form("carne_form"):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            f_data = c1.selectbox("Giorno", DATE_SOGLIA)
            f_tipo = c2.selectbox("Cibo", PRODOTTI_ORDINE)
            f_qta = c3.number_input("Kg", min_value=1)
            f_ora = c4.text_input("Ora", value=datetime.now().strftime("%H:%M"))
            if st.form_submit_button("Salva 📝"):
                if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]): st.rerun()

    df_q = load_data(URL_MAGAZZINO)
    
    if not df_q.empty and len(df_q.columns) >= 3:
        # Col 0: Giorno, Col 1: Prodotto, Col 2: Quantità
        df_q['Quantita'] = pd.to_numeric(df_q.iloc[:, 2], errors='coerce').fillna(0)
        df_q.columns = ['Giorno', 'Prodotto', 'Quantita'] + list(df_q.columns[3:])

        # 1. GRAFICI GIORNALIERI
        st.subheader("📅 Produzione per Giorno")
        giorni_presenti = df_q['Giorno'].unique()
        
        for g in DATE_SOGLIA:
            if g in giorni_presenti:
                df_g = df_q[df_q['Giorno'] == g].groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
                if df_g['Quantita'].sum() > 0:
                    fig = px.bar(df_g, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True,
                                 title=f"Produzione: {g}", color_discrete_map=COLOR_MAP, 
                                 category_orders={"Prodotto": PRODOTTI_ORDINE})
                    fig.update_layout(showlegend=False, height=250)
                    st.plotly_chart(fig, use_container_width=True)

        # 2. TOTALE
        st.divider()
        st.subheader("📊 Totale Sagra (Kg)")
        df_tot = df_q.groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
        fig_tot = px.bar(df_tot, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True,
                         color_discrete_map=COLOR_MAP, category_orders={"Prodotto": PRODOTTI_ORDINE})
        st.plotly_chart(fig_tot, use_container_width=True)

        # 3. ELIMINA
        st.divider()
        with st.expander("🗑️ Correzione Errori"):
            for i, row in df_q.tail(10).iloc[::-1].iterrows():
                c1, c2, c3 = st.columns([4, 4, 2])
                c1.write(f"{row['Giorno']} - {row['Prodotto']}")
                c2.write(f"{int(row['Quantita'])}kg")
                if c3.button("Elimina", key=f"del_{i}"):
                    if delete_row("Quantità Grigliate", i + 1): st.rerun()
    else:
        st.info("Nessun dato carne rilevato.")

with tab3:
    st.link_button("📂 Foglio Google", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
