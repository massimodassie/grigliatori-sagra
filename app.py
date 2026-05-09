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
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 03.2
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide", page_icon="🔥")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
TARGET_PERSONE = 8 

def convert_drive_url(url):
    if not isinstance(url, str): return url
    if "drive.google.com" in url:
        # Estrae l'ID del file dal link di Drive
        if "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
        elif "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
        else: return url
        # Ritorna il link diretto per la visualizzazione immediata
        return f"https://drive.google.com/uc?export=view&id={file_id}"
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

# --- TAB 1: PRESENZE (RIPRISTINO NOMI E TARGET) ---
with tabs[0]:
    df_n = load_data("ListaGrigliatori")
    nomi_lista = sorted([n for n in df_n.iloc[:,0].unique() if n and n != "nan"]) if not df_n.empty else []
    col1, col2 = st.columns([1, 3])
    with col1:
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
    with col2:
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
                    # RIPRISTINO TAB INFO NOMI
                    if presenti_turno:
                        st.info(f"👥 **Presenti ({v}):** {', '.join(presenti_turno)}")
                    else:
                        st.caption("Nessuno segnato")
                    st.write("---")

# --- TAB 3: GALLERIA ---
with tabs[2]:
    st.header("📸 Galleria Foto")
    with st.expander("➕ CARICA NUOVA FOTO"):
        u_d = st.selectbox("Turno Foto", DATE_UFFICIALI)
        u_c = st.text_input("Commento")
        u_f = st.file_uploader("Scegli Immagine", type=['png', 'jpg', 'jpeg'])
        if st.button("PUBBLICA"):
            if u_f:
                b64 = base64.b64encode(u_f.read()).decode()
                requests.post(SCRIPT_URL, data=json.dumps({"action": "upload_photo", "date": u_d, "description": u_c, "file_data": b64, "file_name": u_f.name}))
                st.success("Foto inviata!"); time.sleep(1); st.rerun()

    df_g = load_data("Galleria")
    if not df_g.empty:
        df_g.columns = ["Data", "Link", "Desc"][:len(df_g.columns)]
        cols = st.columns(3)
        for i, row in df_g.iterrows():
            with cols[i % 3]:
                # TRASFORMAZIONE LINK DRIVE PER VISUALIZZAZIONE
                img_url = convert_drive_url(row["Link"])
                st.image(img_url, caption=f"{row['Data']}: {row['Desc']}", use_container_width=True)

# (Le altre tab Carne e Nomi rimangono uguali alle precedenti versioni funzionanti)
with tabs[1]:
    # Carne Code... (omesso per brevità ma da mantenere)
    pass
with tabs[3]:
    # Nomi Code... (omesso per brevità ma da mantenere)
    pass
