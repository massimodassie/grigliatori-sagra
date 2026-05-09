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

# Liste di riferimento
DATE_SOGLIA = [
    "Sabato 09 maggio", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio", "Sabato 16 maggio", "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI_ORDINE = ["Costicine", "Salsicce", "Braciole"]
COLOR_MAP = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

# --- 2. FUNZIONI ROBUSTE ---
def load_data(url):
    try:
        response = requests.get(f"{url}&nocache={time.time()}", timeout=15)
        if response.status_code == 200:
            import io
            df = pd.read_csv(io.StringIO(response.text))
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            # Pulizia radicale: rimuove righe completamente vuote e converte in stringhe pulite
            df = df.dropna(how='all').fillna("")
            df = df.astype(str).map(lambda x: x.strip())
            return df
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
    return pd.DataFrame()

def save_data(sheet, data):
    try:
        res = requests.post(f"{SCRIPT_URL}?sheet={sheet}", data=json.dumps(data), timeout=20)
        if res.status_code == 200:
            return True
        else:
            st.error(f"Errore Server: {res.status_code}")
    except Exception as e:
        st.error(f"Errore invio: {e}")
    return False

def delete_row(sheet, row_index):
    try:
        url = f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}&deleteRow={int(row_index) + 2}"
        requests.get(url, timeout=15)
        return True
    except: return False

# --- 3. INTERFACCIA ---
st.title("🔥 Portale Grigliatori 2026")
tab1, tab2, tab3 = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "⚙️ Gestione"])

# --- TAB 1: PRESENZE ---
with tab1:
    df_nomi = load_data(URL_LISTA_NOMI)
    lista_grig = sorted(df_nomi.iloc[:,0].unique().tolist()) if not df_nomi.empty else []
    lista_grig = [n for n in lista_grig if n and n != "nan"]
    
    user = st.selectbox("Chi sei?", [""] + lista_grig)
    
    if user:
        df_p = load_data(URL_PRESENZE)
        miei_turni = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist() if not df_p.empty else []
        
        st.subheader("I tuoi turni")
        cols = st.columns(3)
        for i, t in enumerate(DATE_SOGLIA): # Usiamo la stessa lista per coerenza
            with cols[i%3]:
                is_on = (t in miei_turni)
                if st.toggle(t, value=is_on, key=f"p_{i}") != is_on:
                    if not is_on: save_data("Presenze", [user, t])
                    else:
                        idx = df_p[(df_p.iloc[:,0] == user) & (df_p.iloc[:,1] == t)].index[0]
                        delete_row("Presenze", idx)
                    st.rerun()

# --- TAB 2: CARNE (FIX GRAFICI) ---
with tab2:
    st.header("🍖 Monitoraggio Produzione")
    
    col_in, col_de = st.columns(2)
    with col_in:
        with st.expander("➕ Inserimento Pezzi Monitor"):
            ora_it = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
            with st.form("form_carne", clear_on_submit=True):
                f_data = st.selectbox("Giorno/Turno", DATE_SOGLIA)
                f_tipo = st.selectbox("Prodotto", PRODOTTI_ORDINE)
                f_qta = st.number_input("Pezzi Totali Monitor", min_value=0, step=1)
                f_ora = st.text_input("Ora", value=ora_it)
                submit = st.form_submit_button("REGISTRA DATO")
                if submit:
                    if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]):
                        st.success("Dato registrato!")
                        time.sleep(1)
                        st.rerun()

    df_q = load_data(URL_MAGAZZINO)
    
    if not df_q.empty:
        # Forziamo i nomi colonne e i tipi
        df_q.columns = ['Giorno', 'Prodotto', 'Quantita', 'Ora'][:len(df_q.columns)]
        df_q = df_q[df_q['Giorno'] != "nan"] # Filtro anti-bug
        df_q['Quantita'] = pd.to_numeric(df_q['Quantita'], errors='coerce').fillna(0)
        
        # Calcolo ritmo
        df_linee = df_q.sort_values(['Giorno', 'Prodotto', 'Ora'])
        df_linee['Variazione'] = df_linee.groupby(['Giorno', 'Prodotto'])['Quantita'].diff().fillna(df_linee['Quantita'])
        df_linee.loc[df_linee['Variazione'] < 0, 'Variazione'] = 0

        # --- 1. GRAFICI DELLE SINGOLE GIORNATE (PRIMA) ---
        st.subheader("🔍 Dettaglio per Turno")
        
        # Prendiamo i giorni unici effettivamente presenti nel file, ordinati
        giorni_presenti = [d for d in DATE_SOGLIA if d in df_q['Giorno'].unique()]
        # Se ci sono giorni extra non in lista, li aggiungiamo
        extra_days = [g for g in df_q['Giorno'].unique() if g not in DATE_SOGLIA and g != ""]
        
        for g in (giorni_presenti + extra_days):
            df_g = df_q[df_q['Giorno'] == g]
            if not df_g.empty:
                st.markdown(f"#### 📅 {g}")
                c1, c2 = st.columns(2)
                with c1:
                    df_b = df_g.groupby('Prodotto')['Quantita'].max().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
                    fig_b = px.bar(df_b, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True,
                                 color_discrete_map=COLOR_MAP, title="Pezzi Totali", height=300)
                    st.plotly_chart(fig_b, use_container_width=True, key=f"bar_{g}_{time.time()}")
                with c2:
                    df_l = df_linee[df_linee['Giorno'] == g]
                    fig_l = px.line(df_l, x='Ora', y='Variazione', color='Prodotto', markers=True,
                                  color_discrete_map=COLOR_MAP, title="Ritmo", height=300)
                    st.plotly_chart(fig_l, use_container_width=True, key=f"line_{g}_{time.time()}")
                st.divider()

        # --- 2. TOTALE GENERALE (ALLA FINE) ---
        st.markdown("""<div style="background-color:#ff4b4b; padding:15px; border-radius:10px; margin-top:40px;">
                    <h2 style="color:white; text-align:center; margin:0;">🏆 TOTALE GENERALE SAGRA</h2>
                    </div>""", unsafe_allow_html=True)
        
        df_max_day = df_q.groupby(['Giorno', 'Prodotto'])['Quantita'].max().reset_index()
        df_tot_sagra = df_max_day.groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
        st.plotly_chart(px.bar(df_tot_sagra, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True, color_discrete_map=COLOR_MAP, height=400), use_container_width=True)

    with col_de:
        with st.expander("🗑️ Modifica / Elimina"):
            if not df_q.empty:
                for idx, row in df_q.iterrows():
                    c_txt, c_btn = st.columns([7,3])
                    c_txt.write(f"**{row['Giorno']}** - {row['Prodotto']} ({int(row['Quantita'])} pz)")
                    if c_btn.button("Elimina", key=f"del_{idx}"):
                        if delete_row("Quantità Grigliate", idx): st.rerun()

# --- TAB 3: GESTIONE ---
with tab3:
    st.header("⚙️ Gestione Team")
    df_n = load_data(URL_LISTA_NOMI)
    if not df_n.empty:
        for i, row in df_n.iterrows():
            if row.iloc[0] and row.iloc[0] != "nan":
                cx, cy = st.columns([8,2])
                cx.write(row.iloc[0])
                if cy.button("Rimuovi", key=f"rm_{i}"):
                    if delete_row("ListaGrigliatori", i): st.rerun()
    
    nuovo = st.text_input("Aggiungi nuovo nome")
    if st.button("Aggiungi"):
        if nuovo and save_data("ListaGrigliatori", [nuovo]): st.rerun()
