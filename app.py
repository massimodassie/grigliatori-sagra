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
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 03.3
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide", page_icon="🔥")

# --- CONFIGURAZIONE ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
TARGET_PERSONE = 8 

def convert_drive_url(url):
    """Trasforma link Drive in link diretto compatibile con Streamlit"""
    if not isinstance(url, str) or "drive.google.com" not in url:
        return url
    try:
        if "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
        else:
            file_id = url.split("/file/d/")[1].split("/")[0]
        # Il parametro &t serve a bypassare la cache se carichi foto con lo stesso nome
        return f"https://drive.google.com/uc?export=view&id={file_id}&t={int(time.time())}"
    except:
        return url

def load_data(sheet_name):
    """Carica dati dal foglio Google"""
    try:
        encoded_name = urllib.parse.quote(sheet_name)
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_name}"
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        return df.apply(lambda x: x.str.strip())
    except:
        return pd.DataFrame()

DATE_UFFICIALI = [
    "Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI = ["Costicine", "Salsicce", "Braciole"]

st.title("🔥 Portale Grigliatori Sagra 2026")
tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Nomi"])

# --- 1. TAB PRESENZE (GRAFICI, TARGET E INFO NOMI) ---
with tabs[0]:
    df_n = load_data("ListaGrigliatori")
    nomi_lista = sorted([n for n in df_n.iloc[:,0].unique() if n and n != "nan"]) if not df_n.empty else []
    
    col_dx, col_sx = st.columns([1, 3])
    
    with col_dx:
        user = st.selectbox("Chi sei?", [""] + nomi_lista)
        if user:
            df_p = load_data("Presenze")
            p_u = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist() if not df_p.empty else []
            st.write("---")
            for d in DATE_UFFICIALI:
                if st.checkbox(d, value=(d in p_u), key=f"p_{d}"):
                    if d not in p_u:
                        requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Presenze", "data": [user, d]}))
                        st.rerun()
                elif d in p_u:
                    idx_list = df_p[(df_p.iloc[:,0] == user) & (df_p.iloc[:,1] == d)].index.tolist()
                    if idx_list:
                        requests.get(f"{SCRIPT_URL}?sheet=Presenze&deleteRow={idx_list[0]+2}")
                        st.rerun()

    with col_sx:
        df_all = load_data("Presenze")
        if not df_all.empty:
            cg = st.columns(2)
            for i, d in enumerate(DATE_UFFICIALI):
                presenti_turno = df_all[df_all.iloc[:,1] == d].iloc[:,0].tolist()
                v = len(presenti_turno)
                
                with cg[i % 2]:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number", value=v,
                        title={'text': f"<b>{d}</b>", 'font': {'size': 16, 'color': 'black'}},
                        gauge={
                            'axis': {'range': [0, 15]},
                            'bar': {'color': "black", 'thickness': 0.25},
                            'bgcolor': "#eeeeee",
                            'steps': [
                                {'range': [0, TARGET_PERSONE], 'color': "#FF8C00"}, # Arancio
                                {'range': [TARGET_PERSONE, 15], 'color': "#228B22"} # Verde
                            ],
                            'threshold': {'line': {'color': "red", 'width': 5}, 'thickness': 0.8, 'value': TARGET_PERSONE}
                        }
                    ))
                    fig.update_layout(height=230, margin=dict(l=30, r=30, t=60, b=10), paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # BOX INFO NOMI (RIPRISTINATO)
                    if presenti_turno:
                        st.info(f"👥 **Presenti ({v}):** {', '.join(presenti_turno)}")
                    else:
                        st.caption("Nessun grigliatore segnato")
                    st.write("---")

# --- 2. TAB MONITOR CARNE ---
with tabs[1]:
    with st.form("carne_form"):
        c1, c2, c3 = st.columns(3)
        f_d = c1.selectbox("Turno", DATE_UFFICIALI)
        f_p = c2.selectbox("Carne", PRODOTTI)
        f_q = c3.number_input("KG", min_value=0.0, step=0.5)
        if st.form_submit_button("Registra"):
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Quantità Grigliate", "data": [f_d, f_p, f_q, datetime.now().strftime("%H:%M")]}))
            st.success("Dato salvato!")
            st.rerun()
    
    df_c = load_data("Quantità Grigliate")
    if not df_c.empty:
        df_c.columns = ["Data", "Prodotto", "Qta", "Ora"]
        df_c["Qta"] = pd.to_numeric(df_c["Qta"])
        st.plotly_chart(px.line(df_c, x="Ora", y="Qta", color="Prodotto", facet_col="Data", markers=True), use_container_width=True)

# --- 3. TAB GALLERIA (FIXED IMAGE DISPLAY) ---
with tabs[2]:
    st.header("📸 Galleria Live")
    with st.expander("➕ CARICA NUOVA FOTO"):
        u_d = st.selectbox("Turno Foto", DATE_UFFICIALI, key="sel_foto")
        u_c = st.text_input("Commento Foto", key="txt_foto")
        u_f = st.file_uploader("Scegli Immagine", type=['png', 'jpg', 'jpeg'], key="up_foto")
        if st.button("PUBBLICA FOTO"):
            if u_f:
                b64 = base64.b64encode(u_f.read()).decode()
                with st.spinner("Invio a Google Drive..."):
                    requests.post(SCRIPT_URL, data=json.dumps({"action": "upload_photo", "date": u_d, "description": u_c, "file_data": b64, "file_name": u_f.name}))
                st.success("Foto caricata con successo!")
                time.sleep(1)
                st.rerun()

    df_g = load_data("Galleria")
    if not df_g.empty:
        df_g.columns = ["Data", "Link", "Desc"][:len(df_g.columns)]
        st.write("---")
        cols = st.columns(3)
        for i, row in df_g.iterrows():
            with cols[i % 3]:
                # Conversione URL Drive
                img_url = convert_drive_url(row["Link"])
                st.image(img_url, caption=f"{row['Data']}: {row['Desc']}", use_container_width=True)

# --- 4. TAB GESTIONE NOMI ---
with tabs[3]:
    st.header("⚙️ Nomi Grigliatori")
    new_n = st.text_input("Aggiungi Nome")
    if st.button("Salva Nome"):
        if new_n:
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "ListaGrigliatori", "data": [new_n]}))
            st.success(f"{new_n} aggiunto!")
            st.rerun()
