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
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 02.1
# ==========================================
# Configurazione URL e ID
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide", page_icon="🔥")

# Il tuo URL aggiornato e autorizzato
SCRIPT_URL = "https://script.google.com/macros/s/AKfycby6v6PsVlSigakKuhZY2yrA799MEH5LmD8NZR-eVfj-nIZ1PkAqqurjg9wK67dzGaEn/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

# Endpoint per la lettura dei dati
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
COLORI_CARNE = {"Costicine": "#FF4B4B", "Salsicce": "#1C83E1", "Braciole": "#31333F"}

# --- FUNZIONI DI SERVIZIO ---
def load_data(url):
    try:
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        return df.apply(lambda x: x.str.strip())
    except:
        return pd.DataFrame()

def convert_google_drive_url(url):
    """Trasforma il link Drive in un formato visualizzabile dall'app"""
    if "drive.google.com" in url:
        if "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=view&id={file_id}"
        elif "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
            return f"https://drive.google.com/uc?export=view&id={file_id}"
    return url

# --- INTERFACCIA PRINCIPALE ---
st.title("🔥 Portale Grigliatori Sagra 2026")
tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Gestione Nomi", "ℹ️ Info"])

# --- TAB 1: GESTIONE PRESENZE ---
with tabs[0]:
    st.header("Gestione Turni Team")
    df_nomi = load_data(URL_NOMI)
    lista_nomi = sorted([n for n in df_nomi.iloc[:,0].unique() if n and n != "nan"]) if not df_nomi.empty else []
    
    col1, col2 = st.columns([1, 2])
    with col1:
        user = st.selectbox("Seleziona il tuo nome", [""] + lista_nomi)
        if user:
            df_p = load_data(URL_PRESENZE)
            presenze_user = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist() if not df_p.empty else []
            
            st.subheader(f"Turni di {user}")
            for d in DATE_UFFICIALI:
                presente = d in presenze_user
                if st.checkbox(d, value=presente, key=f"p_{d}"):
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
            st.subheader("Copertura Turni")
            c_g = st.columns(2)
            for i, d in enumerate(DATE_UFFICIALI):
                val = int(count_p.get(d, 0))
                with c_g[i % 2]:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number", value=val, title={'text': d, 'font': {'size': 14}},
                        gauge={'axis': {'range': [0, 10]}, 'bar': {'color': "seagreen"}}
                    ))
                    fig.update_layout(height=160, margin=dict(l=20, r=20, t=40, b=10))
                    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: MONITORAGGIO CARNE ---
with tabs[1]:
    st.header("🍖 Monitoraggio Carne Grigliata")
    with st.form("carne_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_data = c1.selectbox("Turno", DATE_UFFICIALI)
        f_prod = c2.selectbox("Prodotto", PRODOTTI)
        f_qta = c3.number_input("Quantità (kg)", min_value=0.0, step=0.5)
        if st.form_submit_button("Registra Grigliata"):
            payload = {"sheet": "Quantità Grigliate", "data": [f_data, f_prod, f_qta, datetime.now().strftime("%H:%M")]}
            requests.post(SCRIPT_URL, data=json.dumps(payload))
            st.success(f"Registrati {f_qta}kg di {f_prod}")
            time.sleep(1)
            st.rerun()

    df_c = load_data(URL_CARNE)
    if not df_c.empty:
        df_c.columns = ["Data", "Prodotto", "Quantita", "Ora"]
        df_c["Quantita"] = pd.to_numeric(df_c["Quantita"])
        fig_carne = px.line(df_c, x="Ora", y="Quantita", color="Prodotto", facet_col="Data", 
                            line_shape="spline", color_discrete_map=COLORI_CARNE, markers=True)
        st.plotly_chart(fig_carne, use_container_width=True)

# --- TAB 3: GALLERIA FOTOGRAFICA ---
with tabs[2]:
    st.header("📸 Galleria Live della Sagra")
    
    with st.expander("➕ CARICA UNA NUOVA FOTO"):
        u_data = st.selectbox("A quale turno si riferisce?", DATE_UFFICIALI, key="gal_date")
        u_desc = st.text_input("Commento (es. Team Griglia al completo!)", key="gal_desc")
        u_file = st.file_uploader("Scatta una foto o scegline una", type=['png', 'jpg', 'jpeg'])
        
        if st.button("PUBBLICA FOTO"):
            if u_file:
                img_64 = base64.b64encode(u_file.read()).decode()
                payload = {
                    "action": "upload_photo", 
                    "date": u_data, 
                    "description": u_desc, 
                    "file_data": img_64, 
                    "file_name": u_file.name
                }
                with st.spinner("Invio a Google Drive in corso..."):
                    res = requests.post(SCRIPT_URL, data=json.dumps(payload))
                    if "Success" in res.text:
                        st.success("Foto pubblicata con successo!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"Errore: {res.text}")
            else:
                st.warning("Seleziona prima un file!")

    st.divider()
    
    df_g = load_data(URL_GALLERIA)
    if not df_g.empty:
        # Assicuriamoci di avere le colonne giuste
        df_g.columns = ["Data", "Link", "Descrizione"][:len(df_g.columns)]
        
        filtro_data = st.selectbox("Filtra per data", ["Tutte le foto"] + DATE_UFFICIALI)
        view_df = df_g if filtro_data == "Tutte le foto" else df_g[df_g["Data"] == filtro_data]
        
        cols = st.columns(3)
        for i, row in view_df.iterrows():
            with cols[i % 3]:
                img_display = convert_google_drive_url(row["Link"])
                st.image(img_display, caption=f"{row['Data']}: {row['Descrizione']}", use_container_width=True)
    else:
        st.info("Nessuna foto ancora presente. Carica la prima!")

# --- TAB 4: GESTIONE NOMI ---
with tabs[3]:
    st.header("⚙️ Gestione Anagrafica")
    col_a, col_b = st.columns(2)
    with col_a:
        new_n = st.text_input("Aggiungi nuovo grigliatore")
        if st.button("Salva nel Database"):
            if new_n:
                requests.post(SCRIPT_URL, data=json.dumps({"sheet": "ListaGrigliatori", "data": [new_n]}))
                st.success(f"{new_n} aggiunto!")
                st.rerun()
    with col_b:
        st.write("Lista attuale:")
        st.write(lista_nomi)

# --- TAB 5: INFO ---
with tabs[4]:
    st.header("ℹ️ Informazioni Sistema")
    st.markdown("""
    **Stato del Sistema:** Operativo ✅
    **Versione:** 02.1 (Maggio 2026)
    
    **Funzionalità attive:**
    *   Gestione presenze dinamica
    *   Grafici in tempo reale (Spline & Gauge)
    *   Upload diretto immagini su Google Drive
    *   Database sincronizzato su Google Sheets
    """)
