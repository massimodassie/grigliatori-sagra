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
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 03.7
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide")

SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"

def load_data(sheet_name):
    try:
        # Forzo il refresh dei dati aggiungendo un timestamp all'URL
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}&t={int(time.time())}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return pd.DataFrame()
        df = pd.read_csv(io.StringIO(r.text)).fillna("")
        return df
    except Exception as e:
        st.error(f"Errore caricamento {sheet_name}: {e}")
        return pd.DataFrame()

def get_image_url(url):
    """Trasforma il link di Drive in un link che Streamlit DEVE leggere"""
    if "id=" in url:
        f_id = url.split("id=")[1].split("&")[0]
    elif "/d/" in url:
        f_id = url.split("/d/")[1].split("/")[0]
    else:
        return url
    return f"https://drive.google.com/thumbnail?id={f_id}&sz=w1000"

DATE_UFFICIALI = ["Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena", "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"]

st.title("🔥 Monitor Grigliatori 2026")

# CARICAMENTO DATI ALL'INIZIO
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
                # Logica salvataggio presenze (invariata)
                st.info(f"Ciao {user}, seleziona i tuoi turni.")
        else:
            st.warning("Lista nomi non caricata. Verifica il foglio 'ListaGrigliatori'")

    with col_sx:
        c_griglia = st.columns(2)
        for i, d in enumerate(DATE_UFFICIALI):
            # RECUPERO NOMI PER QUESTO TURNO
            presenti_oggi = []
            if not df_p.empty:
                # Cerchiamo i nomi nella colonna 0 dove la colonna 1 corrisponde alla data
                presenti_oggi = df_p[df_p.iloc[:, 1] == d].iloc[:, 0].tolist()
            
            with c_griglia[i % 2]:
                # Grafico
                v = len(presenti_oggi)
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=v,
                    title={'text': d},
                    gauge={'axis': {'range': [0, 15]}, 'bar': {'color': "black"},
                           'steps': [{'range': [0, 8], 'color': "orange"}, {'range': [8, 15], 'color': "green"}]}
                ))
                fig.update_layout(height=200, margin=dict(l=10, r=10, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)
                
                # --- IL TAB NOMI (RIFATTO DA ZERO) ---
                if presenti_oggi:
                    st.success(f"✅ **Presenti:** {', '.join(presenti_oggi)}")
                else:
                    st.code("Nessun grigliatore segnato", icon="⚠️")
                st.write("---")

with t2:
    st.header("📸 Galleria Live")
    if not df_g.empty:
        g_cols = st.columns(3)
        for idx, row in df_g.iterrows():
            with g_cols[idx % 3]:
                link_foto = get_image_url(row.iloc[1]) # Colonna B
                st.image(link_foto, caption=f"{row.iloc[0]}: {row.iloc[2]}", use_container_width=True)
    else:
        st.info("Nessuna foto in galleria. Caricane una dal foglio Google!")

with t3:
    st.write("Gestione nomi...")
    # (codice aggiunta nomi semplice)
