import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import io
import base64
from datetime import datetime

# ==========================================
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 04.2
# ==========================================

# 1. Configurazione Pagina
st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide", page_icon="🔥")

SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"
TARGET_PERSONE = 7 

# 2. Funzioni di Caricamento
def load_data(sheet_name):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}&t={int(time.time())}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return pd.read_csv(io.StringIO(r.text)).fillna("")
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def get_image_url(url):
    if not isinstance(url, str): return ""
    try:
        f_id = url.split("id=")[1].split("&")[0] if "id=" in url else url.split("/d/")[1].split("/")[0]
        return f"https://drive.google.com/thumbnail?id={f_id}&sz=w800"
    except: return url

# 3. Date e Prodotti
DATE_UFFICIALI = [
    "Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI = ["Costicine", "Salsicce", "Braciole"]

# 4. Header
st.title("🔥 Portale Grigliatori 2026")

# Caricamento dati
df_p = load_data("Presenze")
df_n = load_data("ListaGrigliatori")
df_g = load_data("Galleria")
df_c = load_data("Quantità Grigliate")

# 5. Struttura Tab
tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Sistema", "ℹ️ Info Release"])

# --- TAB 1: PRESENZE ---
with tabs[0]:
    c1, c2 = st.columns([1, 3])
    
    with c1:
        nomi = sorted(df_n.iloc[:,0].unique().tolist()) if not df_n.empty else []
        user = st.selectbox("Chi sei?", [""] + nomi, key="user_select")
        if user:
            p_u = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist() if not df_p.empty else []
            st.write("---")
            for d in DATE_UFFICIALI:
                if st.checkbox(d, value=(d in p_u), key=f"chk_{d}"):
                    if d not in p_u:
                        requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Presenze", "data": [user, d]}))
                        st.rerun()
                elif d in p_u:
                    idx = df_p[(df_p.iloc[:,0] == user) & (df_p.iloc[:,1] == d)].index.tolist()
                    if idx:
                        requests.get(f"{SCRIPT_URL}?sheet=Presenze&deleteRow={idx[0]+2}")
                        st.rerun()

    with c2:
        for d in DATE_UFFICIALI:
            presenti = df_p[df_p.iloc[:, 1] == d].iloc[:, 0].tolist() if not df_p.empty else []
            v = len(presenti)
            diff = v - TARGET_PERSONE
            
            color_barra = "#2eb0a2" if v >= TARGET_PERSONE else "#e67e5e"
            icona = "✅ TARGET OK" if v >= TARGET_PERSONE else "⚠️ TARGET KO"
            segno = f"(+{diff})" if diff > 0 else f"({diff})" if diff < 0 else ""
            
            col_gauge, col_info = st.columns([1, 3])
            
            with col_gauge:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=v,
                    number={'font': {'color': color_barra, 'size': 35}},
                    gauge={
                        'axis': {'range': [0, 12], 'visible': False},
                        'bar': {'color': color_barra, 'thickness': 1},
                        'bgcolor': "#00bfff", 
                        'shape': "angular",
                        'threshold': {'line': {'color': "black", 'width': 3}, 'thickness': 0.8, 'value': TARGET_PERSONE}
                    }
                ))
                fig.update_layout(height=140, margin=dict(l=10, r=10, t=10, b=10))
                # Aggiunta KEY univoca per evitare StreamlitDuplicateElementId
                st.plotly_chart(fig, use_container_width=True, key=f"gauge_{d}")
            
            with col_info:
                st.subheader(d)
                st.markdown(f"**{icona}** {segno} ({v}/{TARGET_PERSONE})")
                st.markdown(f"**PRESENTI:** {', '.join(presenti)}")
            st.write("---")

# --- TAB 2: MONITOR CARNE ---
with tabs[1]:
    st.subheader("🍖 Registrazione KG Carne")
    with st.form("carne_form"):
        f_d = st.selectbox("Turno", DATE_UFFICIALI)
        f_p = st.selectbox("Tipo Carne", PRODOTTI)
        f_q = st.number_input("Chili (KG)", min_value=0.0, step=0.5)
        if st.form_submit_button("Salva nel Database"):
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Quantità Grigliate", "data": [f_d, f_p, f_q, datetime.now().strftime("%H:%M")]}))
            st.success("Dato salvato!"); time.sleep(1); st.rerun()
    
    if not df_c.empty:
        try:
            df_plot = df_c.copy()
            df_plot.columns = ["Data", "Prodotto", "Qta", "Ora"]
            df_plot["Qta"] = pd.to_numeric(df_plot["Qta"])
            st.plotly_chart(px.line(df_plot, x="Ora", y="Qta", color="Prodotto", facet_col="Data", markers=True), use_container_width=True)
        except:
            st.warning("Dati carne non ancora pronti per il grafico.")

# --- TAB 3: GALLERIA ---
with tabs[2]:
    st.subheader("📸 Galleria Foto Sagra")
    with st.expander("➕ CARICA NUOVA FOTO"):
        u_f = st.file_uploader("Scegli file", type=['png', 'jpg', 'jpeg'])
        u_c = st.text_input("Breve descrizione")
        if st.button("Invia Foto") and u_f:
            b64 = base64.b64encode(u_f.read()).decode()
            requests.post(SCRIPT_URL, data=json.dumps({"action": "upload_photo", "date": datetime.now().strftime("%d/%m"), "description": u_c, "file_data": b64, "file_name": u_f.name}))
            st.success("Caricamento completato!"); time.sleep(1); st.rerun()
    
    if not df_g.empty:
        st.write("---")
        g_cols = st.columns(3)
        for i, row in df_g.iterrows():
            with g_cols[i % 3]:
                st.image(get_image_url(row.iloc[1]), use_container_width=True)
                st.caption(f"{row.iloc[0]} - {row.iloc[2]}")

# --- TAB 4: SISTEMA ---
with tabs[3]:
    st.subheader("⚙️ Gestione Anagrafica")
    nuovo_membro = st.text_input("Inserisci Nome e Cognome nuovo grigliatore")
    if st.button("Aggiungi alla lista"):
        if nuovo_membro:
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "ListaGrigliatori", "data": [nuovo_membro]}))
            st.success(f"{nuovo_membro} aggiunto con successo!"); time.sleep(1); st.rerun()

# --- TAB 5: INFO RELEASE ---
with tabs[4]:
    st.subheader("📜 Storico Release Software")
    st.info("Release Attuale: **04.2**")
    st.markdown("""
    - **v04.2**: Risolto errore `DuplicateElementId` nei grafici (ID univoci).
    - **v04.1**: Fix grafico: sfondo azzurro, barra bicolore (Smeraldo/Rosso) e layout riga per riga.
    - **v03.9**: Fix immagini: implementato sistema thumbnail per bypassare i blocchi Google Drive.
    - **v03.0**: Aggiunta gestione Monitor Carne con grafici temporali.
    - **v01.0**: Creazione portale e sincronizzazione con Google Sheets.
    """)
