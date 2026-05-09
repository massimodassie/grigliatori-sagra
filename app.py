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

DATE_SOGLIA = [
    "Sabato 09 maggio", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio", "Sabato 16 maggio", "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI_ORDINE = ["Costicine", "Salsicce", "Braciole"]
COLOR_MAP = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

# --- 2. FUNZIONI ---
def load_data(url):
    try:
        response = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        if response.status_code == 200:
            import io
            df = pd.read_csv(io.StringIO(response.text))
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
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
        url = f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}&deleteRow={int(row_index) + 2}"
        requests.get(url, timeout=10)
        return True
    except: return False

# --- 3. LOGICA APP ---
st.title("🔥 Portale Grigliatori 2026")
tab1, tab2, tab3 = st.tabs(["👥 Presenze & Team", "🍖 Monitor Carne", "⚙️ Gestione Nomi"])

# --- TAB 1: PRESENZE ---
with tab1:
    df_nomi = load_data(URL_LISTA_NOMI)
    lista_grigliatori = sorted(df_nomi.iloc[:,0].dropna().tolist()) if not df_nomi.empty else ["Caricamento..."]
    user = st.selectbox("Seleziona il tuo nome", lista_grigliatori)
    
    df_p = load_data(URL_PRESENZE)
    miei_turni = []
    if not df_p.empty and user:
        df_p.columns = ['Nome', 'Turno'] + list(df_p.columns[2:])
        miei_turni = df_p[df_p['Nome'] == user]['Turno'].tolist()

    turni_fissi = [
        "Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", 
        "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Cena", 
        "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
    ]
    
    st.subheader("I tuoi turni")
    cols = st.columns(3)
    for i, t in enumerate(turni_fissi):
        with cols[i%3]:
            presenza = (t in miei_turni)
            if st.toggle(t, value=presenza, key=f"p_{i}") != presenza:
                if not presenza: save_data("Presenze", [user, t])
                else: 
                    idx = df_p[(df_p['Nome'] == user) & (df_p['Turno'] == t)].index[0]
                    delete_row("Presenze", idx)
                st.rerun()

    st.divider()
    st.subheader("📊 Stato Copertura Team")
    if not df_p.empty:
        for t in turni_fissi:
            presenti = df_p[df_p['Turno'] == t]['Nome'].unique()
            count = len(presenti)
            target = 5 if "Pranzo" in t else 6
            
            c_graf, c_nomi = st.columns([1, 2])
            with c_graf:
                fig = go.Figure(go.Pie(values=[count, max(0, target-count)], hole=0.6, 
                                      marker_colors=["#2a9d8f", "#eeeeee"], showlegend=False, textinfo='none'))
                fig.update_layout(height=150, margin=dict(t=0, b=0, l=0, r=0), 
                                 annotations=[dict(text=f"{count}/{target}", x=0.5, y=0.5, font_size=20, showarrow=False)])
                st.plotly_chart(fig, use_container_width=True, key=f"pie_{t}")
            with c_nomi:
                st.markdown(f"**{t}**")
                st.write(", ".join(presenti) if count > 0 else " nessuno ancora")
            st.markdown("---")

# --- TAB 2: CARNE ---
with tab2:
    st.header("🍖 Monitoraggio Carne")
    
    col_in, col_de = st.columns(2)
    with col_in:
        with st.expander("➕ Inserimento Pezzi Monitor"):
            ora_it = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
            with st.form("form_carne"):
                f_data = st.selectbox("Giorno/Turno", DATE_SOGLIA)
                f_tipo = st.selectbox("Prodotto", PRODOTTI_ORDINE)
                f_qta = st.number_input("Pezzi Totali Monitor", min_value=0, step=1)
                f_ora = st.text_input("Ora", value=ora_it)
                if st.form_submit_button("Registra"):
                    if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]): st.rerun()

    df_q = load_data(URL_MAGAZZINO)
    
    if not df_q.empty:
        df_q.columns = ['Giorno', 'Prodotto', 'Quantita', 'Ora'][:len(df_q.columns)]
        df_q['Quantita'] = pd.to_numeric(df_q['Quantita'], errors='coerce').fillna(0)
        
        # Calcolo variazioni
        df_linee = df_q.sort_values(['Giorno', 'Prodotto', 'Ora'])
        df_linee['Variazione'] = df_linee.groupby(['Giorno', 'Prodotto'])['Quantita'].diff().fillna(df_linee['Quantita'])
        df_linee.loc[df_linee['Variazione'] < 0, 'Variazione'] = 0

        # --- PRIMA I GRAFICI DELLE SINGOLE GIORNATE ---
        st.subheader("🔍 Dettaglio Produzione per Turno")
        giorni_presenti = df_q['Giorno'].unique()
        
        # Usiamo DATE_SOGLIA per mantenere l'ordine cronologico se possibile
        for g in [d for d in DATE_SOGLIA if d in giorni_presenti]:
            df_g = df_q[df_q['Giorno'] == g]
            st.markdown(f"#### 📅 {g}")
            c1, c2 = st.columns(2)
            with c1:
                df_b = df_g.groupby('Prodotto')['Quantita'].max().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
                st.plotly_chart(px.bar(df_b, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True,
                                     color_discrete_map=COLOR_MAP, title="Pezzi Totali Turno", height=300), 
                                use_container_width=True, key=f"bar_{g}")
            with c2:
                df_l = df_linee[df_linee['Giorno'] == g]
                st.plotly_chart(px.line(df_l, x='Ora', y='Variazione', color='Prodotto', markers=True,
                                      color_discrete_map=COLOR_MAP, title="Ritmo Produzione", height=300), 
                                use_container_width=True, key=f"line_{g}")
            st.divider()

        # --- INFINE IL TOTALE SAGRA ---
        st.markdown("""<div style="background-color:#ff4b4b; padding:15px; border-radius:10px; margin:40px 0 20px 0;">
                    <h2 style="color:white; text-align:center; margin:0;">🏆 TOTALE GENERALE SAGRA (Somma dei Turni)</h2>
                    </div>""", unsafe_allow_html=True)
        
        df_max_day = df_q.groupby(['Giorno', 'Prodotto'])['Quantita'].max().reset_index()
        df_tot_sagra = df_max_day.groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
        
        fig_global = px.bar(df_tot_sagra, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True,
                           color_discrete_map=COLOR_MAP)
        fig_global.update_layout(yaxis_title="Pezzi Totali", showlegend=False, height=450)
        st.plotly_chart(fig_global, use_container_width=True)

    with col_de:
        with st.expander("🗑️ Gestisci Inserimenti"):
            if not df_q.empty:
                for idx, row in df_q.iterrows():
                    c_txt, c_btn = st.columns([7,3])
                    c_txt.write(f"**{row['Giorno']}** - {row['Prodotto']} ({int(row['Quantita'])} pz)")
                    if c_btn.button("Elimina", key=f"del_q_{idx}"):
                        if delete_row("Quantità Grigliate", idx): st.rerun()

# --- TAB 3: GESTIONE ---
with tab3:
    st.header("⚙️ Gestione Team")
    df_n = load_data(URL_LISTA_NOMI)
    if not df_n.empty:
        for i, row in df_n.iterrows():
            cx, cy = st.columns([8,2])
            cx.write(row.iloc[0])
            if cy.button("X", key=f"rm_n_{i}"):
                if delete_row("ListaGrigliatori", i): st.rerun()
    
    nome_n = st.text_input("Aggiungi nuovo nome")
    if st.button("Aggiungi"):
        if nome_n and save_data("ListaGrigliatori", [nome_n]): st.rerun()
