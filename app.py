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
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 02.5
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide", page_icon="🔥")

# --- CONFIGURAZIONE URL ---
# Questo è il tuo ultimo URL funzionante
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyoaMP9w99bDPAXNITEwS7nN02hPZsPBf7S2Ie5UElW1mpjgXMr20HNNRDf_OfylZJZ/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

# URL per la lettura dei dati (CSV)
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

# --- FUNZIONI DI SUPPORTO ---
def load_data(url):
    try:
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        return df.apply(lambda x: x.str.strip())
    except:
        return pd.DataFrame()

def convert_drive_url(url):
    if "drive.google.com" in url:
        if "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=view&id={file_id}"
        elif "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
            return f"https://drive.google.com/uc?export=view&id={file_id}"
    return url

# --- INTERFACCIA PRINCIPALE ---
st.title("🔥 Portale Grigliatori Sagra 2026")
tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Nomi"])

# --- TAB 1: PRESENZE ---
with tabs[0]:
    st.header("Gestione Turni")
    df_n = load_data(URL_NOMI)
    nomi = sorted([n for n in df_n.iloc[:,0].unique() if n and n != "nan"]) if not df_n.empty else []
    
    col1, col2 = st.columns([1, 2])
    with col1:
        user = st.selectbox("Seleziona il tuo nome", [""] + nomi)
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
        df_all = load_data(URL_PRESENZE)
        if not df_all.empty:
            counts = df_all.iloc[:,1].value_counts()
            cg = st.columns(2)
            for i, d in enumerate(DATE_UFFICIALI):
                with cg[i % 2]:
                    v = int(counts.get(d, 0))
                    fig = go.Figure(go.Indicator(mode="gauge+number", value=v, title={'text': d, 'font':{'size':14}},
                                   gauge={'axis':{'range':[0,10]}, 'bar':{'color':"orange"}}))
                    fig.update_layout(height=150, margin=dict(l=15, r=15, t=40, b=10))
                    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: CARNE ---
with tabs[1]:
    st.header("🍖 Registro Carne")
    with st.form("carne_form"):
        c1, c2, c3 = st.columns(3)
        f_d = c1.selectbox("Turno", DATE_UFFICIALI)
        f_p = c2.selectbox("Tipo", PRODOTTI)
        f_q = c3.number_input("KG", min_value=0.0, step=0.5)
        if st.form_submit_button("Registra"):
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Quantità Grigliate", "data": [f_d, f_p, f_q, datetime.now().strftime("%H:%M")]}))
            st.success("Registrato!")
            time.sleep(1)
            st.rerun()
    
    df_c = load_data(URL_CARNE)
    if not df_c.empty:
        df_c.columns = ["Data", "Prodotto", "Qta", "Ora"]
        df_c["Qta"] = pd.to_numeric(df_c["Qta"])
        st.plotly_chart(px.line(df_c, x="Ora", y="Qta", color="Prodotto", facet_col="Data", markers=True), use_container_width=True)

# --- TAB 3: GALLERIA ---
with tabs[2]:
    st.header("📸 Galleria Live")
    with st.expander("➕ CARICA NUOVA FOTO"):
        u_d = st.selectbox("Data", DATE_UFFICIALI, key="g_d")
        u_c = st.text_input("Commento", key="g_c")
        u_f = st.file_uploader("Scegli Immagine", type=['png', 'jpg', 'jpeg'])
        if st.button("PUBBLICA"):
            if u_f:
                b64 = base64.b64encode(u_f.read()).decode()
                with st.spinner("Invio a Google Drive..."):
                    res = requests.post(SCRIPT_URL, data=json.dumps({"action": "upload_photo", "date": u_d, "description": u_c, "file_data": b64, "file_name": u_f.name}))
                    if "Success" in res.text:
                        st.success("Foto caricata!")
                        time.sleep(1)
                        st.rerun()
                    else: st.error(res.text)

    df_g = load_data(URL_GALLERIA)
    if not df_g.empty:
        df_g.columns = ["Data", "Link", "Desc"][:len(df_g.columns)]
        cols = st.columns(3)
        for i, row in df_g.iterrows():
            with cols[i % 3]:
                st.image(convert_drive_url(row["Link"]), caption=f"{row['Data']}: {row['Desc']}", use_container_width=True)

# --- TAB 4: GESTIONE NOMI ---
with tabs[3]:
    st.header("⚙️ Nomi Grigliatori")
    new_n = st.text_input("Nome nuovo")
    if st.button("Aggiungi"):
        requests.post(SCRIPT_URL, data=json.dumps({"sheet": "ListaGrigliatori", "data": [new_n]}))
        st.rerun()
