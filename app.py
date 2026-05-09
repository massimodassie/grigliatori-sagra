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

# Endpoint CSV diretti
URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_CARNE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")
URL_NOMI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=ListaGrigliatori"

# Liste di riferimento
DATE_SOGLIA = [
    "Sabato 09 maggio", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio", "Sabato 16 maggio", "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI = ["Costicine", "Salsicce", "Braciole"]
COLORI = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

# --- 2. FUNZIONI TECNICHE (SUPER ROBUSTE) ---
def get_df(url):
    try:
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        if r.status_code == 200:
            # dtype=str e na_filter=False impediscono i "nan"
            df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
            # Rimuove righe e colonne "Unnamed" o vuote
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            df = df.apply(lambda x: x.str.strip())
            return df
    except: pass
    return pd.DataFrame()

def send_to_sheet(sheet, data):
    try:
        r = requests.post(f"{SCRIPT_URL}?sheet={sheet}", data=json.dumps(data), timeout=15)
        return r.status_code == 200
    except: return False

def kill_row(sheet, row_idx):
    try:
        # row_idx + 2 perché Sheets parte da 1 e c'è l'header
        u = f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}&deleteRow={int(row_idx) + 2}"
        requests.get(u, timeout=10)
        return True
    except: return False

# --- 3. INTERFACCIA ---
st.title("🔥 Portale Grigliatori 2026")
t1, t2, t3 = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "⚙️ Sistema"])

# --- TAB 1: PRESENZE ---
with t1:
    df_n = get_df(URL_NOMI)
    nomi = sorted([n for n in df_n.iloc[:,0].unique() if n]) if not df_n.empty else []
    user = st.selectbox("Seleziona Nome", [""] + nomi)
    
    df_p = get_df(URL_PRESENZE)
    
    if user:
        st.subheader(f"Turni di {user}")
        # Normalizzazione dati presenze per il controllo
        miei_turni = []
        if not df_p.empty:
            miei_turni = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist()
        
        c = st.columns(3)
        for i, data_t in enumerate(DATE_SOGLIA):
            with c[i%3]:
                presente = data_t in miei_turni
                if st.toggle(data_t, value=presente, key=f"p_{i}") != presente:
                    if not presente: send_to_sheet("Presenze", [user, data_t])
                    else:
                        match = df_p[(df_p.iloc[:,0] == user) & (df_p.iloc[:,1] == data_t)]
                        if not match.empty: kill_row("Presenze", match.index[0])
                    st.rerun()

    st.divider()
    st.subheader("📊 Copertura Team")
    if not df_p.empty:
        for data_t in DATE_SOGLIA:
            iscritti = [p for p in df_p[df_p.iloc[:,1] == data_t].iloc[:,0].unique() if p]
            count = len(iscritti)
            target = 5 if "Pranzo" in data_t else 6
            col1, col2 = st.columns([1, 3])
            with col1:
                fig = go.Figure(go.Pie(values=[count, max(0, target-count)], hole=0.7, 
                                      marker_colors=["#2a9d8f", "#eeeeee"], showlegend=False, textinfo='none'))
                fig.update_layout(height=100, margin=dict(t=0, b=0, l=0, r=0), 
                                 annotations=[dict(text=f"{count}/{target}", x=0.5, y=0.5, font_size=14, showarrow=False)])
                st.plotly_chart(fig, use_container_width=True, key=f"pie_{data_t}")
            with col2:
                st.markdown(f"**{data_t}**")
                st.caption(", ".join(iscritti) if iscritti else "Vuoto")

# --- TAB 2: CARNE ---
with t2:
    st.header("🍖 Monitoraggio Carne")
    
    # Inserimento
    with st.expander("➕ Inserisci Nuova Rilevazione"):
        with st.form("add_carne"):
            f_d = st.selectbox("Giorno", DATE_SOGLIA)
            f_p = st.selectbox("Cosa", PRODOTTI)
            f_q = st.number_input("Pezzi sul Monitor", min_value=0, step=1)
            f_h = st.text_input("Ora", value=(datetime.now() + timedelta(hours=2)).strftime("%H:%M"))
            if st.form_submit_button("REGISTRA"):
                if send_to_sheet("Quantità Grigliate", [f_d, f_p, f_q, f_h]): st.rerun()

    df_c = get_df(URL_CARNE)
    if not df_c.empty:
        # Forziamo i nomi colonne per la logica interna
        df_c.columns = ["G", "P", "Q", "H"][:len(df_c.columns)]
        df_c["Q"] = pd.to_numeric(df_c["Q"], errors='coerce').fillna(0)
        
        # Calcolo ritmo
        df_c = df_c.sort_values(["G", "P", "H"])
        df_c["Diff"] = df_c.groupby(["G", "P"])["Q"].diff().fillna(df_c["Q"])
        df_c.loc[df_c["Diff"] < 0, "Diff"] = 0

        # GRAFICI GIORNALIERI
        st.subheader("🔍 Dettaglio Giornate")
        for d in DATE_SOGLIA:
            df_g = df_c[df_c["G"] == d]
            if not df_g.empty:
                st.markdown(f"### 📅 {d}")
                c1, c2 = st.columns(2)
                with c1:
                    # Barre Totali
                    res = df_g.groupby("P")["Q"].max().reindex(PRODOTTI).fillna(0).reset_index()
                    st.plotly_chart(px.bar(res, x="P", y="Q", color="P", text_auto=True, 
                                         color_discrete_map=COLORI, title="Pezzi Raggiunti", height=300), use_container_width=True)
                with c2:
                    # Linea Ritmo
                    st.plotly_chart(px.line(df_g, x="H", y="Diff", color="P", markers=True,
                                          color_discrete_map=COLORI, title="Pezzi Prodotti x Ora", height=300), use_container_width=True)
                st.divider()

        # TOTALE GENERALE
        st.markdown("""<div style="background-color:#ff4b4b; padding:15px; border-radius:10px; margin:30px 0;">
                    <h2 style="color:white; text-align:center; margin:0;">🏆 TOTALE GENERALE SAGRA</h2>
                    </div>""", unsafe_allow_html=True)
        tot = df_c.groupby(["G", "P"])["Q"].max().reset_index()
        tot_final = tot.groupby("P")["Q"].sum().reindex(PRODOTTI).fillna(0).reset_index()
        st.plotly_chart(px.bar(tot_final, x="P", y="Q", color="P", text_auto=True, color_discrete_map=COLORI), use_container_width=True)

# --- TAB 3: GESTIONE ---
with t3:
    st.subheader("🛠️ Debug e Gestione")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Lista Nomi Team**")
        df_nomi_raw = get_df(URL_NOMI)
        if not df_nomi_raw.empty:
            for i, r in df_nomi_raw.iterrows():
                if r.iloc[0]:
                    cx, cy = st.columns([4,1])
                    cx.write(r.iloc[0])
                    if cy.button("Elimina", key=f"rn_{i}"):
                        if kill_row("ListaGrigliatori", i): st.rerun()
        
        nuovo = st.text_input("Aggiungi Nome")
        if st.button("Salva Nome"):
            if nuovo and send_to_sheet("ListaGrigliatori", [nuovo]): st.rerun()

    with col_b:
        st.write("**Dati Carne Registrati**")
        if not df_c.empty:
            for i, r in df_c.iterrows():
                ctx, cbt = st.columns([4,1])
                ctx.caption(f"{r['G']} | {r['P']} | {int(r['Q'])}pz")
                if cbt.button("Elimina", key=f"rc_{i}"):
                    if kill_row("Quantità Grigliate", i): st.rerun()

    st.divider()
    with st.expander("👀 VISUALIZZA DATI GREZZI (Se i grafici non appaiono, controlla qui)"):
        st.write("Dati Carne ricevuti dal foglio:")
        st.dataframe(get_df(URL_CARNE))
        st.write("Dati Presenze ricevuti dal foglio:")
        st.dataframe(get_df(URL_PRESENZE))
