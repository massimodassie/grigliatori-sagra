import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
import time
import io
import base64
import urllib.parse

# ==========================================
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 03.8
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide")

SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"

def load_data(sheet_name):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}&t={int(time.time())}"
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.text)).fillna("")
        return df
    except Exception as e:
        return pd.DataFrame()

def get_image_url(url):
    """Metodo thumbnail: il più leggero e compatibile per Drive"""
    if not isinstance(url, str): return url
    try:
        if "id=" in url:
            f_id = url.split("id=")[1].split("&")[0]
        elif "/d/" in url:
            f_id = url.split("/d/")[1].split("/")[0]
        else: return url
        return f"https://drive.google.com/thumbnail?id={f_id}&sz=w800"
    except:
        return url

DATE_UFFICIALI = ["Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena", "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"]

st.title("🔥 Monitor Grigliatori 2026")

# Caricamento centralizzato
df_p = load_data("Presenze")
df_n = load_data("ListaGrigliatori")
df_g = load_data("Galleria")

t1, t2, t3 = st.tabs(["👥 Presenze", "📸 Galleria", "⚙️ Nomi"])

with t1:
    col_dx, col_sx = st.columns([1, 3])
    
    with col_dx:
        if not df_n.empty:
            nomi = sorted(df_n.iloc[:,0].unique().tolist())
            user = st.selectbox("Seleziona il tuo nome", [""] + nomi)
            if user:
                p_u = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist() if not df_p.empty else []
                for d in DATE_UFFICIALI:
                    if st.checkbox(d, value=(d in p_u), key=f"chk_{d}"):
                        if d not in p_u:
                            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Presenze", "data": [user, d]}))
                            st.rerun()
                    elif d in p_u:
                        # Cancellazione riga se deselezionato
                        idx = df_p[(df_p.iloc[:,0] == user) & (df_p.iloc[:,1] == d)].index.tolist()
                        if idx:
                            requests.get(f"{SCRIPT_URL}?sheet=Presenze&deleteRow={idx[0]+2}")
                            st.rerun()
        else:
            st.error("Errore: Foglio 'ListaGrigliatori' non trovato o vuoto.")

    with col_sx:
        c_griglia = st.columns(2)
        for i, d in enumerate(DATE_UFFICIALI):
            presenti_oggi = []
            if not df_p.empty and df_p.shape[1] >= 2:
                # Filtro: colonna 1 (Data) == d, prendi colonna 0 (Nome)
                presenti_oggi = df_p[df_p.iloc[:, 1] == d].iloc[:, 0].tolist()
            
            with c_griglia[i % 2]:
                v = len(presenti_oggi)
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=v,
                    title={'text': d, 'font': {'size': 14}},
                    gauge={'axis': {'range': [0, 12]}, 'bar': {'color': "black"},
                           'steps': [{'range': [0, 8], 'color': "orange"}, {'range': [8, 12], 'color': "green"}]}
                ))
                fig.update_layout(height=180, margin=dict(l=10, r=10, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)
                
                # BOX NOMI - Semplificato al massimo per evitare TypeError
                if presenti_oggi:
                    testo_nomi = ", ".join(presenti_oggi)
                    st.success(f"Presenti: {testo_nomi}")
                else:
                    st.warning("Nessun grigliatore segnato")
                st.write("---")

with t2:
    st.header("📸 Galleria")
    if not df_g.empty:
        g_cols = st.columns(3)
        for idx, row in df_g.iterrows():
            if len(row) >= 2:
                with g_cols[idx % 3]:
                    url_f = get_image_url(row.iloc[1])
                    st.image(url_f, use_container_width=True)
                    st.caption(f"{row.iloc[0]} - {row.iloc[2]}")
    else:
        st.info("Galleria vuota.")

with t3:
    st.subheader("Aggiungi Grigliatore")
    nuovo = st.text_input("Nome e Cognome")
    if st.button("Salva"):
        if nuovo:
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "ListaGrigliatori", "data": [nuovo]}))
            st.success("Aggiunto!"); time.sleep(1); st.rerun()
