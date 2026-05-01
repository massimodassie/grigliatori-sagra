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
TURNI = ["Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Cena", "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"]

# Mappa Colori e Ordine Custom
COLOR_MAP = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}
PRODOTTI_ORDINE = ["Costicine", "Salsicce", "Braciole"]

# --- 2. FUNZIONI ---
def load_data(url):
    try:
        df = pd.read_csv(f"{url}&nocache={time.time()}")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return pd.DataFrame()

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

# --- 3. INTERFACCIA ---
st.title("🔥 Portale Grigliatori 2026")
tab1, tab2, tab3 = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "⚙️ Admin"])

# --- TAB 1: PRESENZE ---
with tab1:
    grigliatori = ["Boscaratto Denis", "Botteon Marco", "Da Ronch Loris", "Dassie Massimo", "Disconzi Francesco", "Flavio", "Giacomo", "Micieli Mauro", "Modolo Zanchetta Mirko", "Perencin Davide", "Perencin Francesco", "Rossi Riccardo", "Sossai Gianluca"]
    user = st.selectbox("Chi sei?", grigliatori)
    df_p = load_data(URL_PRESENZE)
    
    if not df_p.empty:
        if len(df_p.columns) >= 2:
            df_p.columns = ['Nome', 'Turno'] + list(df_p.columns[2:])
        miei_turni = df_p[df_p['Nome'] == user]['Turno'].tolist()
    else: miei_turni = []

    cols = st.columns(3)
    for i, t in enumerate(TURNI):
        with cols[i%3]:
            if st.toggle(t, value=(t in miei_turni), key=f"t_{user}_{i}"):
                if t not in miei_turni:
                    if save_data("Presenze", [user, t]): st.rerun()

    st.divider()
    st.subheader("📊 Stato Copertura")
    if not df_p.empty:
        df_count = df_p.drop_duplicates(subset=['Nome', 'Turno'])
        cols_pie = st.columns(3)
        for i, t in enumerate(TURNI):
            with cols_pie[i%3]:
                count = len(df_count[df_count['Turno'] == t])
                target = 5 if "Pranzo" in t else 6
                color = "#2a9d8f" if count >= target else "#e63946"
                fig = go.Figure(go.Pie(values=[count, max(0, target-count)], hole=0.6, 
                                        marker_colors=[color, "#eeeeee"], showlegend=False, sort=False))
                fig.update_layout(title=f"<b>{t}</b>", height=200, margin=dict(t=40,b=10,l=10,r=10),
                                  annotations=[dict(text=str(count), x=0.5, y=0.5, font_size=20, showarrow=False)])
                st.plotly_chart(fig, use_container_width=True, key=f"pie_{i}")

# --- TAB 2: CARNE (GRAFICI SEPARATI E COLORI NUOVI) ---
with tab2:
    st.header("🍖 Produzione Carne")
    
    with st.expander("➕ Inserisci Quantità"):
        with st.form("carne_form"):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            f_data = c1.selectbox("Giorno", DATE_SOGLIA)
            f_tipo = c2.selectbox("Cibo", PRODOTTI_ORDINE)
            f_qta = c3.number_input("Kg", min_value=1)
            f_ora = c4.text_input("Ora", value=datetime.now().strftime("%H:%M"))
            if st.form_submit_button("Salva 📝"):
                if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]): st.rerun()

    df_q = load_data(URL_MAGAZZINO)
    
    if not df_q.empty:
        if len(df_q.columns) >= 3:
            cols_names = ['Giorno', 'Prodotto', 'Quantita']
            if len(df_q.columns) >= 4: cols_names.append('Ora')
            df_q.columns = cols_names + list(df_q.columns[len(cols_names):])
        
        df_q['Quantita'] = pd.to_numeric(df_q['Quantita'], errors='coerce').fillna(0)

        # 1. GRAFICO TOTALE SAGRA
        st.subheader("📊 Totale Complessivo Sagra (Kg)")
        df_sum = df_q.groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).reset_index().fillna(0)
        fig_bar = px.bar(df_sum, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True,
                         color_discrete_map=COLOR_MAP, category_orders={"Prodotto": PRODOTTI_ORDINE})
        st.plotly_chart(fig_bar, use_container_width=True)

        # 2. GRAFICI SEPARATI PER GIORNO
        st.divider()
        st.subheader("📅 Dettaglio Produzione Giornaliera")
        
        # Filtriamo solo i giorni che hanno effettivamente dei dati
        giorni_con_dati = [d for d in DATE_SOGLIA if d in df_q['Giorno'].unique()]
        
        for giorno in giorni_con_dati:
            with st.expander(f"Dettaglio {giorno}", expanded=True):
                df_giorno = df_q[df_q['Giorno'] == giorno].groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).reset_index().fillna(0)
                
                fig_giorno = px.bar(
                    df_giorno, x='Prodotto', y='Quantita', color='Prodotto', 
                    text_auto=True, title=f"Produzione del {giorno}",
                    color_discrete_map=COLOR_MAP,
                    category_orders={"Prodotto": PRODOTTI_ORDINE}
                )
                fig_giorno.update_layout(showlegend=False, height=350)
                st.plotly_chart(fig_giorno, use_container_width=True, key=f"graph_{giorno}")

        # 3. GESTIONE ELIMINA
        st.divider()
        st.subheader("🗑️ Correzione Errori")
        last_entries = df_q.tail(10).iloc[::-1]
        for i, row in last_entries.iterrows():
            c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
            c1.write(row['Giorno'])
            c2.write(row['Prodotto'])
            c3.write(f"{int(row['Quantita'])}kg")
            c4.write(row.get('Ora', '-'))
            if c5.button("Elimina", key=f"del_{i}"):
                if delete_row("Quantità Grigliate", i + 1): st.rerun()
    else:
        st.info("Nessun dato carne presente.")

# --- TAB 3: ADMIN ---
with tab3:
    st.link_button("📂 Apri Foglio Google", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
