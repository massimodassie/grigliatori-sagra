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

# --- 1. CONFIGURAZIONE GENERALE ---
st.set_page_config(page_title="Portale Grigliatori 2026 - R2.1", layout="wide")

# IL TUO NUOVO URL DEPLOYMENT
SCRIPT_URL = "https://script.google.com/macros/s/AKfycby6v6PsVlSigakKuhZY2yrA799MEH5LmD8NZR-eVfj-nIZ1PkAqqurjg9wK67dzGaEn/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

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
COLORI_CARNE = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

# --- 2. FUNZIONI DI SERVIZIO ---
def load_data(url):
    try:
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        return df.apply(lambda x: x.str.strip())
    except: return pd.DataFrame()

def convert_google_drive_url(url):
    if "drive.google.com" in url:
        if "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=view&id={file_id}"
    return url

# --- 3. INTERFACCIA ---
st.title("🔥 Portale Grigliatori Sagra 2026")
tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Gestione Nomi", "ℹ️ Info"])

# --- TAB 1: PRESENZE ---
with tabs[0]:
    st.header("Gestione Turni Team")
    df_nomi = load_data(URL_NOMI)
    lista_nomi = sorted([n for n in df_nomi.iloc[:,0].unique() if n and n != "nan"]) if not df_nomi.empty else []
    
    col1, col2 = st.columns([1, 2])
    with col1:
        user = st.selectbox("Chi sei?", [""] + lista_nomi)
        if user:
            df_p = load_data(URL_PRESENZE)
            presenze_user = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist() if not df_p.empty else []
            for d in DATE_UFFICIALI:
                if st.checkbox(d, value=(d in presenze_user), key=f"p_{d}"):
                    if d not in presenze_user:
                        requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Presenze", "data": [user, d]}))
                        st.rerun()
                else:
                    if d in presenze_user:
                        idx = df_p[(df_p.iloc[:,0] == user) & (df_p.iloc[:,1] == d)].index[0]
                        requests.get(f"{SCRIPT_URL}?sheet=Presenze&deleteRow={idx+2}")
                        st.rerun()

    with col2:
        df_p_all = load_data(URL_PRESENZE)
        if not df_p_all.empty:
            count_p = df_p_all.iloc[:,1].value_counts()
            cols_g = st.columns(2)
            for i, d in enumerate(DATE_UFFICIALI):
                val = int(count_p.get(d, 0))
                with cols_g[i % 2]:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number", value=val, title={'text': d, 'font': {'size': 14}},
                        gauge={'axis': {'range': [0, 10]}, 'bar': {'color': "seagreen"}}
                    ))
                    fig.update_layout(height=180, margin=dict(l=20, r=20, t=40, b=10))
                    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: CARNE ---
with tabs[1]:
    st.header("🍖 Monitoraggio Carne")
    with st.form("carne_form"):
        c1, c2, c3 = st.columns(3)
        f_data = c1.selectbox("Turno", DATE_UFFICIALI)
        f_prod = c2.selectbox("Cosa hai messo in griglia?", PRODOTTI)
        f_qta = c3.number_input("Quantità (kg)", min_value=0.0, step=0.5)
        if st.form_submit_button("Registra"):
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Quantità Grigliate", "data": [f_data, f_prod, f_qta, datetime.now().strftime("%H:%M")]}))
            st.success("Registrato!")
            time.sleep(1)
            st.rerun()

    df_c = load_data(URL_CARNE)
    if not df_c.empty:
        df_c.columns = ["Data", "Prodotto", "Quantita", "Ora"]
        df_c["Quantita"] = pd.to_numeric(df_c["Quantita"])
        fig_carne = px.line(df_c, x="Ora", y="Quantita", color="Prodotto", facet_col="Data", 
                            line_shape="spline", color_discrete_map=COLORI_CARNE)
        st.plotly_chart(fig_carne, use_container_width=True)

# --- TAB 3: GALLERIA ---
with tabs[2]:
    st.header("📸 Galleria & Upload")
    with st.expander("➕ AGGIUNGI FOTO"):
        u_data = st.selectbox("Data foto", DATE_UFFICIALI)
        u_desc = st.text_input("Commento")
        u_file = st.file_uploader("Scegli o scatta", type=['png', 'jpg', 'jpeg'])
        if st.button("CARICA"):
            if u_file:
                img_64 = base64.b64encode(u_file.read()).decode()
                payload = {"action": "upload_photo", "date": u_data, "description": u_desc, "file_data": img_64, "file_name": u_file.name}
                with st.spinner("Invio in corso..."):
                    res = requests.post(SCRIPT_URL, data=json.dumps(payload))
                    if "Success" in res.text:
                        st.success("Foto caricata!")
                        st.rerun()
                    else: st.error(f"Errore: {res.text}")

    df_g = load_data(URL_GALLERIA)
    if not df_g.empty:
        df_g.columns = ["Data", "Link", "Descrizione"][:len(df_g.columns)]
        cols = st.columns(3)
        for i, row in df_g.iterrows():
            with cols[i % 3]:
                st.image(convert_google_drive_url(row["Link"]), caption=f"{row['Data']}: {row['Descrizione']}")

# --- TAB 4 & 5: GESTIONE & INFO ---
with tabs[3]:
    st.header("⚙️ Gestione Nomi")
    new_n = st.text_input("Aggiungi un Grigliatore")
    if st.button("Salva Nome"):
        requests.post(SCRIPT_URL, data=json.dumps({"sheet": "ListaGrigliatori", "data": [new_n]}))
        st.rerun()

with tabs[4]:
    st.header("ℹ️ Info")
    st.markdown("### RELEASE 02.1\n* Upload Foto Funzionante\n* Grafici Presenze Verdi\n* Monitor Spline Carne")
