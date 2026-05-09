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
            # Pulizia: rimuove righe nulle e converte tutto in stringa pulita
            df = df.dropna(how='all').fillna("")
            df = df.astype(str).apply(lambda x: x.str.strip())
            return df
    except: return pd.DataFrame()

def save_data(sheet, data):
    try:
        requests.post(f"{SCRIPT_URL}?sheet={sheet}", data=json.dumps(data), timeout=15)
        return True
    except: return False

def delete_row(sheet, row_index):
    try:
        url = f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}&deleteRow={int(row_index) + 2}"
        requests.get(url, timeout=10)
        return True
    except: return False

# --- 3. APP ---
st.title("🔥 Portale Grigliatori 2026")
tab1, tab2, tab3 = st.tabs(["👥 Presenze", "🍖 Carne", "⚙️ Gestione"])

# --- TAB 1: PRESENZE (FIX GRAFICI) ---
with tab1:
    df_nomi = load_data(URL_LISTA_NOMI)
    lista_grigliatori = sorted([n for n in df_nomi.iloc[:,0].unique() if n and n != "***"]) if not df_nomi.empty else []
    user = st.selectbox("Seleziona il tuo nome", [""] + lista_grigliatori)
    
    df_p = load_data(URL_PRESENZE)
    
    if user:
        # Troviamo i turni dell'utente (normalizzando per sicurezza)
        miei_turni = []
        if not df_p.empty:
            df_p.columns = ['Nome', 'Turno'][:len(df_p.columns)]
            miei_turni = df_p[df_p['Nome'] == user]['Turno'].tolist()

        st.subheader("I tuoi turni")
        cols = st.columns(3)
        for i, t in enumerate(DATE_SOGLIA):
            with cols[i%3]:
                presenza = t in miei_turni
                if st.toggle(t, value=presenza, key=f"tog_{i}") != presenza:
                    if not presenza: save_data("Presenze", [user, t])
                    else:
                        match_idx = df_p[(df_p['Nome'] == user) & (df_p['Turno'] == t)].index
                        if not match_idx.empty: delete_row("Presenze", match_idx[0])
                    st.rerun()

    st.divider()
    st.subheader("📊 Stato Copertura Team")
    if not df_p.empty:
        for t in DATE_SOGLIA:
            presenti = df_p[df_p.iloc[:,1] == t].iloc[:,0].unique()
            presenti = [p for p in presenti if p and p != "***"]
            count = len(presenti)
            target = 5 if "Pranzo" in t else 6
            
            c1, c2 = st.columns([1, 3])
            with c1:
                fig = go.Figure(go.Pie(values=[count, max(0, target-count)], hole=0.7, 
                                      marker_colors=["#2a9d8f", "#eeeeee"], showlegend=False, textinfo='none'))
                fig.update_layout(height=100, margin=dict(t=0, b=0, l=0, r=0), 
                                 annotations=[dict(text=f"{count}/{target}", x=0.5, y=0.5, font_size=16, showarrow=False)])
                st.plotly_chart(fig, use_container_width=True, key=f"pie_{t}")
            with c2:
                st.markdown(f"**{t}**")
                st.caption(", ".join(presenti) if count > 0 else "Nessuno ancora")

# --- TAB 2: CARNE (FIX DOMENICA) ---
with tab2:
    st.header("🍖 Monitoraggio Carne")
    
    c_in, c_de = st.columns(2)
    with c_in:
        with st.expander("➕ Inserisci Dati"):
            ora_it = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
            with st.form("carne_form"):
                f_data = st.selectbox("Giorno", DATE_SOGLIA)
                f_tipo = st.selectbox("Prodotto", PRODOTTI_ORDINE)
                f_qta = st.number_input("Pezzi Totali", min_value=0, step=1)
                f_ora = st.text_input("Ora", value=ora_it)
                if st.form_submit_button("REGISTRA"):
                    if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]): st.rerun()

    df_q = load_data(URL_MAGAZZINO)
    if not df_q.empty:
        df_q.columns = ['Giorno', 'Prodotto', 'Quantita', 'Ora'][:len(df_q.columns)]
        # Pulizia forzata: rimuoviamo righe con asterischi o vuote
        df_q = df_q[~df_q['Giorno'].str.contains("\*", na=False)]
        df_q = df_q[df_q['Giorno'] != ""]
        df_q['Quantita'] = pd.to_numeric(df_q['Quantita'], errors='coerce').fillna(0)
        
        # Calcolo variazioni
        df_q = df_q.sort_values(['Giorno', 'Prodotto', 'Ora'])
        df_q['Variazione'] = df_q.groupby(['Giorno', 'Prodotto'])['Quantita'].diff().fillna(df_q['Quantita'])
        df_q.loc[df_q['Variazione'] < 0, 'Variazione'] = 0

        st.subheader("🔍 Dettaglio Giornaliero")
        # Visualizziamo i grafici per ogni giorno che ha almeno un dato
        giorni_con_dati = df_q['Giorno'].unique()
        
        # Ordiniamo i giorni secondo la nostra lista DATE_SOGLIA
        for g in [d for d in DATE_SOGLIA if d in giorni_con_dati]:
            df_g = df_q[df_q['Giorno'] == g]
            st.markdown(f"#### 📅 {g}")
            col_a, col_b = st.columns(2)
            with col_a:
                df_b = df_g.groupby('Prodotto')['Quantita'].max().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
                st.plotly_chart(px.bar(df_b, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True,
                                     color_discrete_map=COLOR_MAP, title="Totale Pezzi", height=300), 
                                use_container_width=True, key=f"b_{g}")
            with col_b:
                st.plotly_chart(px.line(df_g, x='Ora', y='Variazione', color='Prodotto', markers=True,
                                      color_discrete_map=COLOR_MAP, title="Ritmo Produzione", height=300), 
                                use_container_width=True, key=f"l_{g}")
            st.divider()

        # TOTALE GENERALE ALLA FINE
        st.markdown("""<div style="background-color:#ff4b4b; padding:15px; border-radius:10px; margin-top:30px;">
                    <h2 style="color:white; text-align:center; margin:0;">🏆 TOTALE GENERALE SAGRA</h2>
                    </div>""", unsafe_allow_html=True)
        df_max = df_q.groupby(['Giorno', 'Prodotto'])['Quantita'].max().reset_index()
        df_tot = df_max.groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
        st.plotly_chart(px.bar(df_tot, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True, color_discrete_map=COLOR_MAP), use_container_width=True)

    with c_de:
        with st.expander("🗑️ Cancella Inserimenti"):
            if not df_q.empty:
                for idx, row in df_q.iterrows():
                    c_t, c_b = st.columns([4,1])
                    c_t.write(f"{row['Giorno']} - {row['Prodotto']} ({int(row['Quantita'])})")
                    if c_b.button("Elimina", key=f"del_{idx}"):
                        if delete_row("Quantità Grigliate", idx): st.rerun()

# --- TAB 3: GESTIONE ---
with tab3:
    st.header("⚙️ Team")
    df_n = load_data(URL_LISTA_NOMI)
    if not df_n.empty:
        for i, row in df_n.iterrows():
            if row.iloc[0] and row.iloc[0] != "***":
                cx, cy = st.columns([4,1])
                cx.write(row.iloc[0])
                if cy.button("X", key=f"rn_{i}"):
                    if delete_row("ListaGrigliatori", i): st.rerun()
    
    n_nome = st.text_input("Aggiungi Nome")
    if st.button("Salva"):
        if n_nome and save_data("ListaGrigliatori", [n_nome]): st.rerun()
