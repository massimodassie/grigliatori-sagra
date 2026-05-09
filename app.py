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
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby7yJ-jjJYworKTL9w20Er0w_Av3U1xqUvLQi0oGlrYy70Sg1xK6BJysNGZIZlJ0DtM/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_MAGAZZINO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")
URL_LISTA_NOMI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=ListaGrigliatori"

# Liste fisse allineate (DEVONO ESSERE IDENTICHE OVUNQUE)
DATE_SOGLIA = [
    "Sabato 09 maggio", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio", "Sabato 16 maggio", "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI_ORDINE = ["Costicine", "Salsicce", "Braciole"]
COLOR_MAP = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

# --- 2. FUNZIONI DI CARICAMENTO (VERSIONE ROBUSTA) ---
def load_data(url):
    try:
        # na_filter=False evita i vari "nan"
        response = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text), na_filter=False)
            # Pulizia nomi colonne e spazi
            df.columns = [str(c).strip() for c in df.columns]
            df = df.apply(lambda x: x.astype(str).str.strip())
            return df
    except:
        return pd.DataFrame()

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

# --- 3. LOGICA APP ---
st.title("🔥 Portale Grigliatori 2026")
tab1, tab2, tab3 = st.tabs(["👥 Presenze & Turni", "🍖 Monitor Carne", "⚙️ Gestione Team"])

# --- TAB 1: PRESENZE ---
with tab1:
    df_nomi = load_data(URL_LISTA_NOMI)
    lista_grigliatori = sorted([n for n in df_nomi.iloc[:,0].tolist() if n]) if not df_nomi.empty else []
    
    user = st.selectbox("Seleziona il tuo nome", [""] + lista_grigliatori)
    
    df_p = load_data(URL_PRESENZE)
    
    if user and not df_p.empty:
        # Troviamo i turni dell'utente (usiamo le prime due colonne per sicurezza)
        miei_turni = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist()
        
        st.subheader("I tuoi turni")
        cols = st.columns(3)
        for i, t in enumerate(DATE_SOGLIA):
            with cols[i%3]:
                is_checked = t in miei_turni
                if st.toggle(t, value=is_checked, key=f"t_{i}") != is_checked:
                    if not is_checked: save_data("Presenze", [user, t])
                    else:
                        idx = df_p[(df_p.iloc[:,0] == user) & (df_p.iloc[:,1] == t)].index[0]
                        delete_row("Presenze", idx)
                    st.rerun()

    st.divider()
    st.subheader("📊 Stato Copertura Team")
    if not df_p.empty:
        for t in DATE_SOGLIA:
            # Filtriamo i presenti per ogni turno
            presenti = df_p[df_p.iloc[:,1] == t].iloc[:,0].unique().tolist()
            presenti = [p for p in presenti if p]
            count = len(presenti)
            target = 5 if "Pranzo" in t else 6
            
            c_graf, c_nomi = st.columns([1, 2])
            with c_graf:
                fig = go.Figure(go.Pie(values=[count, max(0, target-count)], hole=0.7, 
                                      marker_colors=["#2a9d8f", "#eeeeee"], showlegend=False, textinfo='none'))
                fig.update_layout(height=100, margin=dict(t=0, b=0, l=0, r=0), 
                                 annotations=[dict(text=f"{count}/{target}", x=0.5, y=0.5, font_size=16, showarrow=False)])
                st.plotly_chart(fig, use_container_width=True, key=f"pie_{t}")
            with c_nomi:
                st.markdown(f"**{t}**")
                st.caption(", ".join(presenti) if count > 0 else "Nessun iscritto")
            st.markdown("---")

# --- TAB 2: CARNE ---
with tab2:
    st.header("🍖 Monitoraggio Quantità")
    
    col_in, col_de = st.columns(2)
    with col_in:
        with st.expander("➕ Inserisci Pezzi Monitor"):
            ora_it = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
            with st.form("form_carne"):
                f_data = st.selectbox("Giorno", DATE_SOGLIA)
                f_tipo = st.selectbox("Prodotto", PRODOTTI_ORDINE)
                f_qta = st.number_input("Pezzi Totali", min_value=0, step=1)
                f_ora = st.text_input("Ora", value=ora_it)
                if st.form_submit_button("REGISTRA"):
                    if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]): st.rerun()

    df_q = load_data(URL_MAGAZZINO)
    
    if not df_q.empty:
        # Pulizia colonne
        df_q.columns = ['Giorno', 'Prodotto', 'Quantita', 'Ora'][:len(df_q.columns)]
        df_q['Quantita'] = pd.to_numeric(df_q['Quantita'], errors='coerce').fillna(0)
        
        # Calcolo ritmo
        df_linee = df_q.copy()
        df_linee = df_linee.sort_values(['Giorno', 'Prodotto', 'Ora'])
        df_linee['Variazione'] = df_linee.groupby(['Giorno', 'Prodotto'])['Quantita'].diff().fillna(df_linee['Quantita'])
        df_linee.loc[df_linee['Variazione'] < 0, 'Variazione'] = 0

        # --- PRIMA: GRAFICI GIORNALIERI ---
        st.subheader("🔍 Dettaglio Produzione Turni")
        giorni_nel_foglio = df_q['Giorno'].unique()
        
        for g in [d for d in DATE_SOGLIA if d in giorni_nel_foglio]:
            df_g = df_q[df_q['Giorno'] == g]
            st.markdown(f"#### 📅 {g}")
            c1, c2 = st.columns(2)
            with c1:
                # Barre totali
                df_b = df_g.groupby('Prodotto')['Quantita'].max().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
                st.plotly_chart(px.bar(df_b, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True,
                                     color_discrete_map=COLOR_MAP, title="Pezzi Totali", height=300), 
                                use_container_width=True, key=f"bar_{g}")
            with c2:
                # Linea ritmo
                df_l = df_linee[df_linee['Giorno'] == g]
                st.plotly_chart(px.line(df_l, x='Ora', y='Variazione', color='Prodotto', markers=True,
                                      color_discrete_map=COLOR_MAP, title="Ritmo (Pezzi aggiunti)", height=300), 
                                use_container_width=True, key=f"line_{g}")
            st.divider()

        # --- DOPO: TOTALE SAGRA ---
        st.markdown("""<div style="background-color:#ff4b4b; padding:15px; border-radius:10px; margin:40px 0 20px 0;">
                    <h2 style="color:white; text-align:center; margin:0;">🏆 TOTALE GENERALE SAGRA</h2>
                    </div>""", unsafe_allow_html=True)
        
        df_max_day = df_q.groupby(['Giorno', 'Prodotto'])['Quantita'].max().reset_index()
        df_tot_sagra = df_max_day.groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
        st.plotly_chart(px.bar(df_tot_sagra, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True,
                           color_discrete_map=COLOR_MAP, height=450), use_container_width=True)

    with col_de:
        with st.expander("🗑️ Gestione Inserimenti"):
            if not df_q.empty:
                for idx, row in df_q.iterrows():
                    c_txt, c_btn = st.columns([7,3])
                    c_txt.write(f"**{row['Giorno']}** - {row['Prodotto']} ({int(row['Quantita'])} pz)")
                    if c_btn.button("Elimina", key=f"del_q_{idx}"):
                        if delete_row("Quantità Grigliate", idx): st.rerun()

# --- TAB 3: GESTIONE ---
with tab3:
    st.header("⚙️ Nomi Team")
    df_n = load_data(URL_LISTA_NOMI)
    if not df_n.empty:
        for i, row in df_n.iterrows():
            if row.iloc[0]:
                cx, cy = st.columns([8,2])
                cx.write(row.iloc[0])
                if cy.button("X", key=f"rm_n_{i}"):
                    if delete_row("ListaGrigliatori", i): st.rerun()
    
    n_nome = st.text_input("Nuovo Grigliatore")
    if st.button("Aggiungi"):
        if n_nome and save_data("ListaGrigliatori", [n_nome]): st.rerun()
