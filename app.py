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
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 04.0
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide", page_icon="🔥")

SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"
TARGET_PERSONE = 8

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
        f_id = url.split("id=")[1].split("&")[0] if "id=" in url else url.split("/d/")[1].split("/")[0]
        return f"https://drive.google.com/thumbnail?id={f_id}&sz=w800"
    except: return url

DATE_UFFICIALI = [
    "Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]

st.title("🔥 Portale Grigliatori 2026")

df_p = load_data("Presenze")
df_n = load_data("ListaGrigliatori")
df_g = load_data("Galleria")
df_c = load_data("Quantità Grigliate")

tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Sistema", "ℹ️ Info Release"])

# --- TAB 1: PRESENZE ---
with tabs[0]:
    c1, c2 = st.columns([1, 3])
    with c1:
        if not df_n.empty:
            nomi = sorted(df_n.iloc[:,0].unique().tolist())
            user = st.selectbox("Chi sei?", [""] + nomi)
            if user:
                p_u = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist() if not df_p.empty else []
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
            v = len(presenti)
            with cg[i % 2]:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=v,
                    title={'text': f"<b>{d}</b>", 'font': {'size': 16, 'color': 'darkblue'}},
                    gauge={
                        'axis': {'range': [0, 15], 'tickwidth': 1},
                        'bar': {'color': "green", 'thickness': 0.3}, # BARRA VERDE
                        'bgcolor': "white",
                        'steps': [
                            {'range': [0, TARGET_PERSONE], 'color': "#FF8C00"}, # ARANCIONE
                            {'range': [TARGET_PERSONE, 15], 'color': "#228B22"}  # VERDE
                        ],
                        'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': TARGET_PERSONE}
                    }
                ))
                fig.update_layout(height=200, margin=dict(l=20, r=20, t=50, b=20))
                st.plotly_chart(fig, use_container_width=True)
                
                if presenti:
                    st.success(f"👥 **Presenti:** {', '.join(presenti)}")
                else:
                    st.info("Nessuno segnato")
                st.write("---")

# --- TAB 2, 3, 4 (INVARIATI MA PULITI) ---
with tabs[1]:
    # ... (Codice Carne)
    st.subheader("🍖 Registra KG")
    with st.form("carne_f"):
        c_d, c_p, c_q = st.columns(3)
        f_d = c_d.selectbox("Turno", DATE_UFFICIALI)
        f_p = c_p.selectbox("Tipo", ["Costicine", "Salsicce", "Braciole"])
        f_q = c_q.number_input("KG", min_value=0.0)
        if st.form_submit_button("Invia"):
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Quantità Grigliate", "data": [f_d, f_p, f_q, datetime.now().strftime("%H:%M")]}))
            st.rerun()

with tabs[2]:
    st.subheader("📸 Galleria")
    with st.expander("➕ Carica Foto"):
        u_f = st.file_uploader("Immagine", type=['png','jpg','jpeg'])
        if st.button("Carica") and u_f:
            b64 = base64.b64encode(u_f.read()).decode()
            requests.post(SCRIPT_URL, data=json.dumps({"action": "upload_photo", "date": "Live", "description": "Galleria", "file_data": b64, "file_name": u_f.name}))
            st.rerun()
    if not df_g.empty:
        g_c = st.columns(3)
        for idx, row in df_g.iterrows():
            with g_c[idx % 3]:
                st.image(get_image_url(row.iloc[1]), use_container_width=True)

with tabs[3]:
    st.subheader("⚙️ Aggiungi Grigliatore")
    nn = st.text_input("Nuovo Nome")
    if st.button("Salva"):
        requests.post(SCRIPT_URL, data=json.dumps({"sheet": "ListaGrigliatori", "data": [nn]}))
        st.rerun()

# --- TAB 5: INFO RELEASE (LO STORICO) ---
with tabs[4]:
    st.title("📜 Storico Versioni")
    st.markdown("""
    ### Release 04.0 (Oggi)
    - **Fix Grafici**: Ripristinata barra verde e zone Arancione/Verde.
    - **Fix Layout**: Reinserito il tab Info dedicato.
    - **Fix Scala**: Gauge settata su max 15.
    
    ### Release 03.9
    - **Fix Foto**: Implementato sistema Thumbnail per bypassare i blocchi di Google Drive.
    
    ### Release 03.5
    - **Stabilità**: Migliorato il caricamento dati con bypass della cache.
    """)
