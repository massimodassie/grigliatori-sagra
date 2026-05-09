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
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 03.4
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide", page_icon="🔥")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
TARGET_PERSONE = 8 

def convert_drive_url(url):
    """Estrae l'ID in modo pulito per bypassare i blocchi di Google"""
    if not isinstance(url, str) or "drive.google.com" not in url:
        return url
    try:
        # Estrazione ID universale
        if "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
        else:
            file_id = url.split("/file/d/")[1].split("/")[0]
        # Formato 'uc' (User Content) che è il più compatibile
        return f"https://drive.google.com/uc?id={file_id}"
    except:
        return url

def load_data(sheet_name):
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

st.title("🔥 Portale Grigliatori Sagra 2026")
tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Nomi"])

# --- 1. TAB PRESENZE ---
with tabs[0]:
    df_n = load_data("ListaGrigliatori")
    nomi_lista = sorted([n for n in df_n.iloc[:,0].unique() if n and n != "nan"]) if not df_n.empty else []
    
    col_dx, col_sx = st.columns([1, 3])
    with col_dx:
        user = st.selectbox("Chi sei?", [""] + nomi_lista)
        if user:
            df_p = load_data("Presenze")
            p_u = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist() if not df_p.empty else []
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
        cg = st.columns(2)
        for i, d in enumerate(DATE_UFFICIALI):
            # Logica nomi presenti super-sicura
            presenti = []
            if not df_all.empty:
                presenti = df_all[df_all.iloc[:,1] == d].iloc[:,0].tolist()
            
            v = len(presenti)
            with cg[i % 2]:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=v,
                    title={'text': f"<b>{d}</b>", 'font': {'size': 16}},
                    gauge={
                        'axis': {'range': [0, 15]},
                        'bar': {'color': "black", 'thickness': 0.25},
                        'steps': [
                            {'range': [0, TARGET_PERSONE], 'color': "#FF8C00"},
                            {'range': [TARGET_PERSONE, 15], 'color': "#228B22"}
                        ],
                        'threshold': {'line': {'color': "red", 'width': 4}, 'value': TARGET_PERSONE}
                    }
                ))
                fig.update_layout(height=220, margin=dict(l=20,r=20,t=50,b=0))
                st.plotly_chart(fig, use_container_width=True)
                
                # BOX NOMI - Ora fuori da ogni IF bloccante
                if v > 0:
                    st.info(f"👥 {', '.join(presenti)}")
                else:
                    st.caption("Vuoto")
                st.write("---")

# --- 3. TAB GALLERIA ---
with tabs[2]:
    st.header("📸 Galleria")
    with st.expander("➕ CARICA FOTO"):
        u_f = st.file_uploader("Scegli", type=['jpg', 'jpeg', 'png'])
        u_d = st.selectbox("Turno", DATE_UFFICIALI, key="gal_d")
        u_c = st.text_input("Commento", key="gal_c")
        if st.button("CARICA ORA") and u_f:
            b64 = base64.b64encode(u_f.read()).decode()
            requests.post(SCRIPT_URL, data=json.dumps({"action": "upload_photo", "date": u_d, "description": u_c, "file_data": b64, "file_name": u_f.name}))
            st.success("Fatto!"); time.sleep(1); st.rerun()

    df_g = load_data("Galleria")
    if not df_g.empty:
        df_g.columns = ["Data", "Link", "Desc"][:len(df_g.columns)]
        it = st.columns(3)
        for i, row in df_g.iterrows():
            with it[i % 3]:
                link_pulito = convert_drive_url(row["Link"])
                # Se l'immagine fallisce ancora, mostriamo il link per debug
                try:
                    st.image(link_pulito, use_container_width=True, caption=row["Desc"])
                except:
                    st.error("Errore immagine")
                    st.write(f"[Link Diretto]({link_pulito})")

# Mantenere Tab Carne e Nomi come prima
