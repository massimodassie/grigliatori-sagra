import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import io
import base64
import urllib.parse
from datetime import datetime

# ==========================================
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE FINALE 02.4
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide", page_icon="🔥")

# IL TUO NUOVO URL DEPLOYMENT
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzuYGJOpkFvaQBtQJhEZoK-wuis7IxTk13hamR4yAKYrrMBUr2o6GgfqEI2YRERzv7j/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

# Endpoint per la lettura (CSV)
URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_CARNE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")
URL_NOMI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=ListaGrigliatori"
URL_GALLERIA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Galleria"

DATE_UFFICIALI = [
    "Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI = ["Costicine", "Salsicce", "Braciole"]

# --- FUNZIONI DI SERVIZIO ---
def load_data(url):
    try:
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        return df.apply(lambda x: x.str.strip())
    except:
        return pd.DataFrame()

def convert_drive_url(url):
    """Converte i link di Google Drive in formati visualizzabili da Streamlit"""
    if "drive.google.com" in url:
        if "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=view&id={file_id}"
        elif "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
            return f"https://drive.google.com/uc?export=view&id={file_id}"
    return url

# --- INTERFACCIA ---
st.title("🔥 Portale Grigliatori Sagra 2026")
tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Gestione Nomi"])

# --- TAB 1: PRESENZE ---
with tabs[0]:
    st.header("Gestione Turni Team")
    df_n = load_data(URL_NOMI)
    nomi = sorted([n for n in df_n.iloc[:,0].unique() if n and n != "nan"]) if not df_n.empty else []
    
    col1, col2 = st.columns([1, 2])
    with col1:
        user = st.selectbox("Chi sei?", [""] + nomi)
        if user:
            df_p = load_data(URL_PRESENZE)
            p_u = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist() if not df_p.empty else []
            for d in DATE_UFFICIALI:
                if st.checkbox(d, value=(d in p_u), key=f"p_{d}"):
                    if d not in p_u:
                        requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Presenze", "data": [user, d]}))
                        st.rerun()
                elif d in p_u:
                    idx = df_p[(df_p.iloc[:,0] == user) & (df_p.iloc[:,1] == d)].index[0]
                    requests.get(f"{SCRIPT_URL}?sheet=Presenze&deleteRow={idx+2}")
                    st.rerun()

    with col2:
        df_p_all = load_data(URL_PRESENZE)
        if not df_p_all.empty:
            counts = df_p_all.iloc[:,1].value_counts()
            cg = st.columns(2)
            for i, d in enumerate(DATE_UFFICIALI):
                with cg[i % 2]:
                    val = int(counts.get(d, 0))
                    fig = go.Figure(go.Indicator(mode="gauge+number", value=val, title={'text': d, 'font':{'size':14}},
                                                 gauge={'axis':{'range':[0,10]}, 'bar':{'color':"seagreen"}}))
                    fig.update_layout(height=160, margin=dict(l=20, r=20, t=40, b=10))
                    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: CARNE ---
with tabs[1]:
    st.header("🍖 Monitoraggio Grigliata")
    with st.form("carne_form"):
        c1, c2, c3 = st.columns(3)
        f_d = c1.selectbox("Turno", DATE_UFFICIALI)
        f_p = c2.selectbox("Prodotto", PRODOTTI)
        f_q = c3.number_input("kg messi in griglia", min_value=0.0, step=0.5)
        if st.form_submit_button("Invia Dati"):
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Quantità Grigliate", "data": [f_d, f_p, f_q, datetime.now().strftime("%H:%M")]}))
            st.success("Registrato!")
            time.sleep(1)
            st.rerun()
    
    df_c = load_data(URL_CARNE)
    if not df_c.empty:
        df_c.columns = ["Data", "Prodotto", "Qta", "Ora"]
        df_c["Qta"] = pd.to_numeric(df_c["Qta"])
        st.plotly_chart(px.line(df_c, x="Ora", y="Qta", color="Prodotto", facet_col="Data", line_shape="spline", markers=True), use_container_width=True)

# --- TAB 3: GALLERIA ---
with tabs[2]:
    st.header("📸 Galleria & Foto Live")
    with st.expander("➕ AGGIUNGI FOTO"):
        u_d = st.selectbox("Turno della foto", DATE_UFFICIALI, key="gal_u_d")
        u_c = st.text_input("Commento", key="gal_u_c")
        u_f = st.file_uploader("Scatta o seleziona foto", type=['png', 'jpg', 'jpeg'])
        if st.button("CARICA SU DRIVE"):
            if u_f:
                b64_data = base64.b64encode(u_f.read()).decode()
                with st.spinner("Invio in corso..."):
                    res = requests.post(SCRIPT_URL, data=json.dumps({
                        "action": "upload_photo", 
                        "date": u_d, 
                        "description": u_c, 
                        "file_data": b64_data, 
                        "file_name": u_f.name
                    }))
                    if "Success" in res.text:
                        st.success("Foto caricata con successo!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Errore: {res.text}")

    df_g = load_data(URL_GALLERIA)
    if not df_g.empty:
        df_g.columns = ["Data", "Link", "Desc"][:len(df_g.columns)]
        cols = st.columns(3)
        for i, row in df_g.iterrows():
            with cols[i % 3]:
                img_url = convert_drive_url(row["Link"])
                st.image(img_url, caption=f"{row['Data']}: {row['Desc']}", use_container_width=True)

# --- TAB 4: NOMI ---
with tabs[3]:
    st.header("⚙️ Gestione Team")
    new_n = st.text_input("Nome nuovo grigliatore")
    if st.button("Aggiungi alla lista"):
        if new_n:
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "ListaGrigliatori", "data": [new_n]}))
            st.success("Aggiunto!")
            st.rerun()
