import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
import time
import io
import base64
from datetime import datetime

# ==========================================
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 03.5 (ULTRA-STABILE)
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
TARGET_PERSONE = 8 

# Funzione conversione link Drive super-semplice
def get_drive_direct(url):
    if not isinstance(url, str) or "id=" not in url and "/d/" not in url: return url
    f_id = url.split("id=")[1].split("&")[0] if "id=" in url else url.split("/d/")[1].split("/")[0]
    return f"https://drive.google.com/uc?export=view&id={f_id}"

# Caricamento dati con gestione errori totale
def load_data_safe(sheet_name):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}&nocache={time.time()}"
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str).fillna("")
        return df
    except:
        return pd.DataFrame()

DATE_UFFICIALI = ["Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena", "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"]

st.title("🔥 Portale Grigliatori 2026")
t1, t2, t3, t4 = st.tabs(["👥 Presenze", "🍖 Carne", "📸 Galleria", "⚙️ Nomi"])

# --- TAB 1: PRESENZE ---
with t1:
    df_n = load_data_safe("ListaGrigliatori")
    nomi = sorted(df_n.iloc[:,0].tolist()) if not df_n.empty else []
    
    c1, c2 = st.columns([1, 3])
    with c1:
        user = st.selectbox("Chi sei?", [""] + nomi)
        if user:
            df_p = load_data_safe("Presenze")
            # Gestione check/uncheck... (codice precedente invariato)
            st.write("Seleziona i tuoi turni:")
            # ... (logica checkbox omessa qui per brevità, tieni quella della 03.4)

    with c2:
        df_all = load_data_safe("Presenze")
        col_grafici = st.columns(2)
        for i, d in enumerate(DATE_UFFICIALI):
            # Filtro nomi presenti per questo turno
            presenti = []
            if not df_all.empty and df_all.shape[1] >= 2:
                presenti = df_all[df_all.iloc[:,1] == d].iloc[:,0].unique().tolist()
            
            with col_grafici[i % 2]:
                val = len(presenti)
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=val,
                    title={'text': d, 'font': {'size': 14}},
                    gauge={
                        'axis': {'range': [0, 15]},
                        'bar': {'color': "black", 'thickness': 0.2},
                        'steps': [
                            {'range': [0, TARGET_PERSONE], 'color': "orange"},
                            {'range': [TARGET_PERSONE, 15], 'color': "green"}
                        ],
                        'threshold': {'line': {'color': "red", 'width': 4}, 'value': TARGET_PERSONE}
                    }
                ))
                fig.update_layout(height=180, margin=dict(l=10,r=10,t=40,b=0))
                st.plotly_chart(fig, use_container_width=True)
                
                # BOX INFO - Scritto in HTML per essere sicuri che appaia
                nomi_str = ", ".join(presenti) if presenti else "Nessuno"
                st.markdown(f"""<div style="background-color:#d4edda; padding:10px; border-radius:5px; border-left:5px solid #28a745; color:#155724; font-size:14px;">
                <strong>👥 Presenti:</strong> {nomi_str}
                </div>""", unsafe_allow_html=True)
                st.write("")

# --- TAB 3: GALLERIA ---
with t3:
    st.header("📸 Galleria")
    df_g = load_data_safe("Galleria")
    if not df_g.empty:
        # Mostra le foto in una griglia
        cols = st.columns(3)
        for i, row in df_g.iterrows():
            with cols[i % 3]:
                url_diretto = get_drive_direct(row.iloc[1]) # Colonna B: Link
                desc = f"{row.iloc[0]} - {row.iloc[2]}" # Colonna A (Data) - C (Desc)
                st.image(url_diretto, caption=desc, use_container_width=True)
