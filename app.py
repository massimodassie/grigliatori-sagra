import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import urllib.parse
from datetime import datetime, timedelta

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby7yJ-jjJYworKTL9w20Er0w_Av3U1xqUvLQi0oGlrYy70Sg1xK6BJysNGZIZlJ0DtM/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_MAGAZZINO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")
URL_LISTA_NOMI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=ListaGrigliatori"

# Lista completa delle date/turni
DATE_SOGLIA = [
    "Sabato 09 maggio", 
    "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio", 
    "Sabato 16 maggio", 
    "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio", 
    "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI_ORDINE = ["Costicine", "Salsicce", "Braciole"]
COLOR_MAP = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

# --- 2. FUNZIONI TECNICHE ---
def load_data(url):
    try:
        response = requests.get(f"{url}&nocache={time.time()}")
        if response.status_code == 200:
            import io
            df = pd.read_csv(io.StringIO(response.text))
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            df.columns = [str(c).strip() for c in df.columns]
            df = df.map(lambda x: str(x).strip() if pd.notnull(x) else x)
            return df
    except: pass
    return pd.DataFrame()

def save_data(sheet, data):
    try:
        requests.post(f"{SCRIPT_URL}?sheet={sheet}", data=json.dumps(data), timeout=10)
        return True
    except: return False

def delete_row(sheet, row_index):
    try:
        google_row = int(row_index) + 2
        url = f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}&deleteRow={google_row}"
        response = requests.get(url, timeout=15)
        return response.status_code == 200
    except: return False

# --- 4. INTERFACCIA ---
st.title("🔥 Portale Grigliatori 2026")
tab1, tab2, tab3 = st.tabs(["👥 Presenze & Calendario", "🍖 Monitor Carne", "⚙️ Gestione Team"])

# --- TAB 1: PRESENZE ---
with tab1:
    user = st.selectbox("Chi sei?", lista_grigliatori if 'lista_grigliatori' in locals() else ["Caricamento..."])
    df_p = load_data(URL_PRESENZE)
    miei_turni = []
    if not df_p.empty and len(df_p.columns) >= 2:
        df_p.columns = ['Nome', 'Turno'] + list(df_p.columns[2:])
        miei_turni = df_p[df_p['Nome'] == user]['Turno'].tolist()
    
    turni_lista = [
        "Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", 
        "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Cena", 
        "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
    ]
    
    st.subheader("Segna i tuoi turni")
    cols = st.columns(3)
    for i, t in enumerate(turni_lista):
        with cols[i%3]:
            is_on = (t in miei_turni)
            if st.toggle(t, value=is_on, key=f"t_{user}_{i}") != is_on:
                if not is_on: save_data("Presenze", [user, t])
                else: 
                    idx = df_p[(df_p['Nome'] == user) & (df_p['Turno'] == t)].index[0]
                    delete_row("Presenze", idx)
                st.rerun()

# --- TAB 2: CARNE (RIPRISTINO GRAFICI GIORNALIERI) ---
with tab2:
    st.header("🍖 Monitoraggio Produzione")
    
    col_ins, col_del = st.columns(2)
    with col_ins:
        with st.expander("➕ Inserisci Quantità"):
            ora_it = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
            with st.form("carne_form"):
                f_data = st.selectbox("Giorno / Turno", DATE_SOGLIA)
                f_tipo = st.selectbox("Cibo", PRODOTTI_ORDINE)
                f_qta = st.number_input("Totale Pezzi Monitor", min_value=0, step=1)
                f_ora = st.text_input("Ora", value=ora_it)
                if st.form_submit_button("Salva"):
                    if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]): st.rerun()

    df_q = load_data(URL_MAGAZZINO)
    
    if not df_q.empty:
        # Pulizia colonne
        nomi_std = ['Giorno', 'Prodotto', 'Quantita', 'Ora']
        df_q.columns = nomi_std[:len(df_q.columns)]
        df_q['Quantita'] = pd.to_numeric(df_q['Quantita'], errors='coerce').fillna(0)
        
        # Calcolo incrementale
        df_diff = df_q.copy().sort_values(['Giorno', 'Prodotto', 'Ora'])
        df_diff['Produzione_Effettiva'] = df_diff.groupby(['Giorno', 'Prodotto'])['Quantita'].diff().fillna(df_diff['Quantita'])
        df_diff.loc[df_diff['Produzione_Effettiva'] < 0, 'Produzione_Effettiva'] = 0

        # GRAFICO TOTALE SAGRA
        st.markdown("""<div style="background-color: #ff4b4b; padding: 10px; border-radius: 5px; margin: 20px 0;">
                        <h2 style="margin:0; color:white; text-align:center;">🏆 Totale Sagra (Tutti i turni)</h2>
                     </div>""", unsafe_allow_html=True)
        
        df_max_giorni = df_q.groupby(['Giorno', 'Prodotto'])['Quantita'].max().reset_index()
        df_sagra = df_max_giorni.groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
        st.plotly_chart(px.bar(df_sagra, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True, color_discrete_map=COLOR_MAP), use_container_width=True)

        st.divider()

        # GRAFICI GIORNALIERI (RIPRISTINATI)
        st.subheader("🔍 Dettaglio per Turno")
        
        # Cerchiamo tutte le date uniche presenti nel file per non perdere nulla
        giorni_nel_file = df_q['Giorno'].unique()
        
        for data_target in DATE_SOGLIA:
            # Mostra la giornata solo se ci sono dati
            df_g_mon = df_q[df_q['Giorno'] == data_target]
            df_g_diff = df_diff[df_diff['Giorno'] == data_target]
            
            if not df_g_mon.empty:
                st.markdown(f"#### 📊 {data_target}")
                c1, c2 = st.columns(2)
                with c1:
                    df_b = df_g_mon.groupby('Prodotto')['Quantita'].max().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
                    st.plotly_chart(px.bar(df_b, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True, title="Pezzi raggiunti", color_discrete_map=COLOR_MAP, height=300), use_container_width=True, key=f"b_{data_target}")
                with c2:
                    st.plotly_chart(px.line(df_g_diff.sort_values('Ora'), x='Ora', y='Produzione_Effettiva', color='Prodotto', markers=True, title="Andamento", color_discrete_map=COLOR_MAP, height=300), use_container_width=True, key=f"l_{data_target}")

    with col_del:
        with st.expander("🗑️ Gestisci / Elimina"):
            if not df_q.empty:
                for idx, row in df_q.iterrows():
                    col_t, col_b = st.columns([8, 2])
                    col_t.write(f"{row['Giorno']} - {row['Prodotto']}: {int(row['Quantita'])} Pz")
                    if col_b.button("Elimina", key=f"del_{idx}"):
                        if delete_row("Quantità Grigliate", idx): st.rerun()

# --- TAB 3: GESTIONE TEAM ---
with tab3:
    st.header("⚙️ Gestione Team")
    df_n = load_data(URL_LISTA_NOMI)
    lista_grigliatori = sorted(df_n.iloc[:,0].unique().tolist()) if not df_n.empty else []
    
    with st.expander("➕ Aggiungi Grigliatore"):
        nuovo = st.text_input("Nome")
        if st.button("Salva"):
            if nuovo and save_data("ListaGrigliatori", [nuovo]): st.rerun()
            
    with st.expander("🗑️ Rimuovi"):
        for i, nome in enumerate(lista_grigliatori):
            c1, c2 = st.columns([8,2])
            c1.write(nome)
            if c2.button("X", key=f"rm_{i}"):
                if delete_row("ListaGrigliatori", i): st.rerun()
