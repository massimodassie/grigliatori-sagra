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
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 03.9.1
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide")

# --- VERSIONING ---
VERSION = "03.9.1"
LAST_UPDATE = "2026-05-09"
STATUS = "Stabile - Foto Fixate"

SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"

def load_data(sheet_name):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}&t={int(time.time())}"
        r = requests.get(url, timeout=10)
        return pd.read_csv(io.StringIO(r.text)).fillna("")
    except:
        return pd.DataFrame()

def get_image_url(url):
    if not isinstance(url, str): return ""
    try:
        f_id = ""
        if "id=" in url: f_id = url.split("id=")[1].split("&")[0]
        elif "/d/" in url: f_id = url.split("/d/")[1].split("/")[0]
        return f"https://drive.google.com/thumbnail?id={f_id}&sz=w800" if f_id else url
    except: return url

DATE_UFFICIALI = ["Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena", "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"]
PRODOTTI = ["Costicine", "Salsicce", "Braciole"]

# Sidebar o Header per Info Software
st.sidebar.info(f"**Versione:** {VERSION}\n\n**Data:** {LAST_UPDATE}\n\n**Status:** {STATUS}")

st.title("🔥 Portale Grigliatori 2026")

# Caricamento Dati
df_p = load_data("Presenze")
df_n = load_data("ListaGrigliatori")
df_g = load_data("Galleria")
df_c = load_data("Quantità Grigliate")

tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Sistema"])

# --- TAB 1: PRESENZE ---
with tabs[0]:
    c1, c2 = st.columns([1, 3])
    with c1:
        if not df_n.empty:
            nomi = sorted(df_n.iloc[:,0].unique().tolist())
            user = st.selectbox("Chi sei?", [""] + nomi)
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
        cg = st.columns(2)
        for i, d in enumerate(DATE_UFFICIALI):
            presenti = df_p[df_p.iloc[:, 1] == d].iloc[:, 0].tolist() if not df_p.empty else []
            with cg[i % 2]:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=len(presenti),
                    title={'text': d, 'font': {'size': 14}},
                    gauge={'axis': {'range': [0, 12]}, 'bar': {'color': "black"},
                           'steps': [{'range': [0, 8], 'color': "orange"}, {'range': [8, 12], 'color': "green"}]}
                ))
                fig.update_layout(height=160, margin=dict(l=10, r=10, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)
                
                if presenti:
                    st.success(f"Presenti: {', '.join(presenti)}")
                else:
                    st.info("Nessuno segnato")

# --- TAB 2: MONITOR CARNE ---
with tabs[1]:
    st.subheader("🍖 Registra KG Grigliati")
    with st.form("carne_form"):
        f_d = st.selectbox("Turno", DATE_UFFICIALI)
        f_p = st.selectbox("Carne", PRODOTTI)
        f_q = st.number_input("KG", min_value=0.0, step=0.5)
        if st.form_submit_button("Salva Dato"):
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Quantità Grigliate", "data": [f_d, f_p, f_q, datetime.now().strftime("%H:%M")]}))
            st.success("Dato inviato!"); time.sleep(1); st.rerun()
    
    if not df_c.empty:
        df_c.columns = ["Data", "Prodotto", "Qta", "Ora"]
        df_c["Qta"] = pd.to_numeric(df_c["Qta"])
        st.plotly_chart(px.line(df_c, x="Ora", y="Qta", color="Prodotto", facet_col="Data", markers=True))

# --- TAB 3: GALLERIA ---
with tabs[2]:
    st.subheader("📸 Galleria e Caricamento")
    with st.expander("➕ CARICA NUOVA FOTO"):
        u_f = st.file_uploader("Scegli file", type=['png', 'jpg', 'jpeg'])
        u_d = st.selectbox("Turno Foto", DATE_UFFICIALI)
        u_c = st.text_input("Commento")
        if st.button("Carica") and u_f:
            b64 = base64.b64encode(u_f.read()).decode()
            requests.post(SCRIPT_URL, data=json.dumps({"action": "upload_photo", "date": u_d, "description": u_c, "file_data": b64, "file_name": u_f.name}))
            st.success("Foto caricata!"); st.rerun()

    if not df_g.empty:
        st.write("---")
        gcols = st.columns(3)
        for idx, row in df_g.iterrows():
            with gcols[idx % 3]:
                st.image(get_image_url(row.iloc[1]), use_container_width=True)
                st.caption(f"{row.iloc[0]} - {row.iloc[2]}")

# --- TAB 4: SISTEMA ---
with tabs[3]:
    st.subheader("⚙️ Gestione e Info")
    st.info(f"""
    **Release Software:** {VERSION}
    **Ultimo Aggiornamento:** {LAST_UPDATE}
    **Database:** Google Sheets
    **Stato Immagini:** Drive Thumbnail API (Attivo)
    """)
    
    st.write("---")
    st.write("### Aggiungi Nuovo Grigliatore")
    new_n = st.text_input("Nome e Cognome")
    if st.button("Aggiungi"):
        if new_n:
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "ListaGrigliatori", "data": [new_n]}))
            st.success("Fatto!"); st.rerun()
