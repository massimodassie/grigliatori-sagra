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
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 04.1
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide")

SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"
TARGET_PERSONE = 7 # Come da tua immagine (7/7)

def load_data(sheet_name):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}&t={int(time.time())}"
        r = requests.get(url, timeout=10)
        return pd.read_csv(io.StringIO(r.text)).fillna("")
    except:
        return pd.DataFrame()

DATE_UFFICIALI = ["Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena", "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"]

st.title("🔥 Monitor Grigliatori 2026")

df_p = load_data("Presenze")
df_n = load_data("ListaGrigliatori")

tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Sistema", "ℹ️ Release"])

with tabs[0]:
    c1, c2 = st.columns([1, 3])
    
    with c1:
        nomi = sorted(df_n.iloc[:,0].unique().tolist()) if not df_n.empty else []
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
        for d in DATE_UFFICIALI:
            presenti = df_p[df_p.iloc[:, 1] == d].iloc[:, 0].tolist() if not df_p.empty else []
            v = len(presenti)
            diff = v - TARGET_PERSONE
            
            # Logica colori e icone come da tua immagine
            color_barra = "#2eb0a2" if v >= TARGET_PERSONE else "#e67e5e"
            icona = "✅ TARGET OK" if v >= TARGET_PERSONE else "⚠️ TARGET KO"
            segno = f"(+{diff})" if diff > 0 else f"({diff})" if diff < 0 else ""
            
            # Layout riga per riga
            col_gauge, col_info = st.columns([1, 3])
            
            with col_gauge:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=v,
                    number={'font': {'color': color_barra, 'size': 30}},
                    gauge={
                        'axis': {'range': [0, 12], 'visible': False},
                        'bar': {'color': color_barra, 'thickness': 1},
                        'bgcolor': "#00bfff", # Azzurro sfondo
                        'shape': "angular",
                        'threshold': {'line': {'color': "black", 'width': 3}, 'thickness': 0.8, 'value': TARGET_PERSONE}
                    }
                ))
                fig.update_layout(height=150, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            
            with col_info:
                st.subheader(d)
                st.markdown(f"**{icona}** {segno} ({v}/{TARGET_PERSONE})")
                st.markdown(f"PRESENTI: {', '.join(presenti)}")
            st.write("---")

# Tab Info Release con storico
with tabs[4]:
    st.markdown("""
    ### ℹ️ Storico Versioni
    - **v04.1**: Ripristinato layout grafico originale (Barra Rossa/Smeraldo, Sfondo Azzurro).
    - **v04.0**: Aggiunto tab Release e sistemata scala Target.
    - **v03.9**: Fix definitivo caricamento foto da Drive (Thumbnail mode).
    """)
