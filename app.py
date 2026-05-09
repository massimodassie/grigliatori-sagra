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
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 02.9 (FULL DASHBOARD)
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide", page_icon="🔥")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
TARGET_PERSONE = 8  # Obiettivo minimo di grigliatori per turno

def get_csv_url(sheet_name):
    encoded_name = urllib.parse.quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_name}"

DATE_UFFICIALI = [
    "Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI = ["Costicine", "Salsicce", "Braciole"]

def load_data(sheet_name):
    try:
        url = get_csv_url(sheet_name)
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        return df.apply(lambda x: x.str.strip())
    except:
        return pd.DataFrame()

st.title("🔥 Portale Grigliatori Sagra 2026")
tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Nomi"])

# --- 1. TAB PRESENZE (CON TARGET E NOMI) ---
with tabs[0]:
    df_n = load_data("ListaGrigliatori")
    nomi_lista = sorted([n for n in df_n.iloc[:,0].unique() if n and n != "nan"]) if not df_n.empty else []
    
    col1, col2 = st.columns([1, 3])
    with col1:
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

    with col2:
        df_all = load_data("Presenze")
        if not df_all.empty:
            cg = st.columns(2)
            for i, d in enumerate(DATE_UFFICIALI):
                # Filtra i nomi dei presenti per questo turno
                presenti_turno = df_all[df_all.iloc[:,1] == d].iloc[:,0].tolist()
                v = len(presenti_turno)
                
                with cg[i % 2]:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=v,
                        title={'text': f"<b>{d}</b>", 'font': {'size': 16, 'color': 'black'}},
                        gauge={
                            'axis': {'range': [0, 15], 'tickwidth': 1, 'tickcolor': "black"},
                            'bar': {'color': "darkgreen" if v >= TARGET_PERSONE else "orange"},
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': TARGET_PERSONE
                            }
                        }
                    ))
                    fig.update_layout(height=220, margin=dict(l=30, r=30, t=50, b=10), paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # MOSTRA I NOMI SOTTO IL GRAFICO
                    if presenti_turno:
                        st.caption(f"👥 **Presenti:** {', '.join(presenti_turno)}")
                    else:
                        st.caption("¯\\_(ツ)_/¯ Nessuno ancora segnato")
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

# --- 3. TAB GALLERIA ---
with tabs[2]:
    with st.expander("➕ CARICA FOTO"):
        u_d = st.selectbox("Data", DATE_UFFICIALI, key="g_d")
        u_c = st.text_input("Commento", key="g_c")
        u_f = st.file_uploader("Scatta/Scegli", type=['png', 'jpg', 'jpeg'])
        if st.button("CARICA"):
            if u_f:
                b64 = base64.b64encode(u_f.read()).decode()
                with st.spinner("Invio su Drive..."):
                    res = requests.post(SCRIPT_URL, data=json.dumps({
                        "action": "upload_photo", "date": u_d, "description": u_c, 
                        "file_data": b64, "file_name": u_f.name
                    }))
                    if "Success" in res.text:
                        st.success("Foto caricata!"); time.sleep(1); st.rerun()
                    else: st.error(res.text)

    df_g = load_data("Galleria")
    if not df_g.empty:
        df_g.columns = ["Data", "Link", "Desc"][:len(df_g.columns)]
        cols = st.columns(3)
        for i, row in df_g.iterrows():
            with cols[i % 3]:
                st.image(row["Link"], caption=f"{row['Data']}: {row['Desc']}", use_container_width=True)

# --- 4. TAB GESTIONE NOMI ---
with tabs[3]:
    new_n = st.text_input("Aggiungi Nome Grigliatore")
    if st.button("Salva Nome"):
        if new_n:
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "ListaGrigliatori", "data": [new_n]}))
            st.success(f"{new_n} aggiunto!")
            st.rerun()
