import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import urllib.parse

# 1. --- CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxlzO8HR87qEHeM5L6kDLWwctu_AehDK8yZZhhCh_bNLiLmPk3GTTJXKRHGeM0XBtxA/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

# Encoding per i nomi dei fogli
foglio_q = urllib.parse.quote("Quantità Grigliate")
URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_MAGAZZINO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={foglio_q}"

DATE_SOGLIA = [
    "Venerdì 09 maggio", "Sabato 10 maggio", "Domenica 10 maggio",
    "Venerdì 15 maggio", "Sabato 16 maggio", "Domenica 17 maggio",
    "Sabato 23 maggio", "Domenica 24 maggio"
]

TURNI = [
    "Venerdì 09 maggio - Cena", "Domenica 10 maggio - Pranzo", 
    "Domenica 10 maggio - Cena", "Venerdì 15 maggio - Cena della costata", 
    "Sabato 16 maggio - Cena", "Domenica 17 maggio - Cena", 
    "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", 
    "Domenica 24 maggio - Cena"
]

# --- FUNZIONI ---
def load_data(url):
    try:
        # Timestamp per evitare cache vecchia
        return pd.read_csv(f"{url}&nocache={time.time()}")
    except:
        return pd.DataFrame()

def save_data(sheet, data):
    try:
        requests.post(f"{SCRIPT_URL}?sheet={sheet}", data=json.dumps(data), timeout=10)
        return True
    except:
        return False

# --- INTERFACCIA ---
st.title("🔥 Portale Grigliatori 2026")

tab1, tab2, tab3 = st.tabs(["👥 I Miei Turni", "🍖 Quantità Carne", "⚙️ Admin"])

# --- TAB 1: TURNI PERSONALI + GRAFICI COPERTURA ---
with tab1:
    user = st.selectbox("Chi sei?", sorted(["Botteon Marco", "Da Ronch Loris", "Denis Boscaratto", "Flavio", "Francesco Perencin", "Francesco Vicenza", "Giacomo", "Gianluca Sossai", "Massimo Dassie", "Mauro Micieli", "Mirko Modolo Zanchetta", "Radu Apostol", "Riccardo Rossi"]), index=0)
    
    st.subheader("Segna la tua presenza")
    df_p = load_data(URL_PRESENZE)
    miei_turni = df_p[df_p['Nome'] == user]['Turno'].tolist() if not df_p.empty else []
    
    cols = st.columns(3)
    for i, t in enumerate(TURNI):
        with cols[i%3]:
            if st.toggle(t, value=(t in miei_turni), key=f"t_{i}"):
                if t not in miei_turni:
                    if save_data("Presenze", [user, t]):
                        st.rerun()

    st.divider()
    
    # AGGIUNTO: Grafici a torta visibili a tutti qui sotto
    st.subheader("Stato attuale copertura (Obiettivo 5-6 persone)")
    if not df_p.empty:
        df_clean = df_p.drop_duplicates(subset=['Nome', 'Turno'], keep='last')
        cols_pie = st.columns(3)
        for i, t in enumerate(TURNI):
            with cols_pie[i%3]:
                count = len(df_clean[df_clean['Turno'] == t])
                target = 5 if "Pranzo" in t else 6
                fig = go.Figure(go.Pie(values=[count, max(0, target-count)], hole=0.6, 
                                        marker_colors=["#2a9d8f", "#eeeeee"], showlegend=False))
                fig.update_layout(title=f"<b>{t}</b>", height=200, margin=dict(t=40,b=0,l=0,r=0),
                                  annotations=[dict(text=str(count), x=0.5, y=0.5, font_size=20, showarrow=False)])
                st.plotly_chart(fig, use_container_width=True, key=f"p_chart_{i}")

# --- TAB 2: CARNE (RIPRISTINATA DATA) ---
with tab2:
    st.header("🍖 Registrazione Produzione")
    
    with st.form("carne_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_data = c1.selectbox("Giorno", DATE_SOGLIA) # RIPRISTINATO
        f_tipo = c2.selectbox("Cibo", ["Costicine", "Salsicce", "Braciole"])
        f_qta = c3.number_input("Quantità (kg)", min_value=1, step=1)
        
        if st.form_submit_button("Invia Dati 📝"):
            if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta]):
                st.success(f"Registrati {f_qta}kg di {f_tipo} per {f_data}")
                time.sleep(1)
                st.rerun()

    st.divider()
    
    # Grafico Quantità
    df_q = load_data(URL_MAGAZZINO)
    if not df_q.empty:
        # Correzione automatica nome colonna Quantità
        df_q.columns = [c.replace('Quantità', 'Quantita') for c in df_q.columns]
        
        if 'Quantita' in df_q.columns:
            df_q['Quantita'] = pd.to_numeric(df_q['Quantita'], errors='coerce').fillna(0)
            df_sum = df_q.groupby('Prodotto')['Quantita'].sum().reset_index()
            
            fig_bar = px.bar(df_sum, x='Prodotto', y='Quantita', 
                             title="TOTALE KG GRIGLIATI (Sagra Completa)", 
                             color='Prodotto', text_auto=True,
                             color_discrete_map={"Costicine": "#e63946", "Salsicce": "#f4a261", "Braciole": "#457b9d"})
            st.plotly_chart(fig_bar, use_container_width=True)
            
            with st.expander("Vedi log inserimenti"):
                st.dataframe(df_q.iloc[::-1], use_container_width=True)

# --- TAB 3: ADMIN ---
with tab3:
    st.subheader("Gestione Avanzata")
    st.link_button("📂 Vai al Foglio Google Completo", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
    st.write("Usa il foglio per cancellare errori o modificare i nomi dei grigliatori.")
