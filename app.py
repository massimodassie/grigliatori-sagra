import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.express as px
import urllib.parse
import requests
import json
import re
import time

# 1. --- CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxlzO8HR87qEHeM5L6kDLWwctu_AehDK8yZZhhCh_bNLiLmPk3GTTJXKRHGeM0XBtxA/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_CONTATTI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Contatti"
URL_MAGAZZINO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Quantità%20Grigliate"

GRIGLIATORI = sorted([
    "Seleziona il tuo nome...", "Botteon Marco", "Da Ronch Loris", "Denis Boscaratto", 
    "Flavio", "Francesco Perencin", "Francesco Vicenza", "Giacomo",
    "Gianluca Sossai", "Massimo Dassie", "Mauro Micieli",
    "Mirko Modolo Zanchetta", "Radu Apostol", "Riccardo Rossi"
])

DATE_SOGLIA = {
    "Venerdì 09 maggio": "2026-05-09", "Domenica 10 maggio": "2026-05-10",
    "Venerdì 15 maggio": "2026-05-15", "Sabato 16 maggio": "2026-05-16",
    "Domenica 17 maggio": "2026-05-17", "Sabato 23 maggio": "2026-05-23",
    "Domenica 24 maggio": "2026-05-24"
}

TURNI = [
    "Venerdì 09 maggio - Cena", "Domenica 10 maggio - Pranzo", 
    "Domenica 10 maggio - Cena", "Venerdì 15 maggio - Cena della costata", 
    "Sabato 16 maggio - Cena", "Domenica 17 maggio - Cena", 
    "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", 
    "Domenica 24 maggio - Cena"
]

# --- FUNZIONI ---
def load_gsheet(url):
    try:
        # Usiamo il timestamp per distruggere la cache di Google e Streamlit
        return pd.read_csv(f"{url}&cachebuster={int(time.time())}")
    except:
        return pd.DataFrame()

def save_to_gsheet(sheet_name, data_list):
    try:
        requests.post(f"{SCRIPT_URL}?sheet={sheet_name}", data=json.dumps(data_list), timeout=10)
    except:
        st.error("Errore di invio dati")

def extract_number(text):
    if pd.isna(text): return 0
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else 0

# --- INTERFACCIA ---
st.title("🔥 Portale Sagra 2026")

tab_user, tab_food, tab_admin = st.tabs(["📝 Turni", "📊 Quantità Cibo", "📢 Admin"])

# --- SCHEDA TURNI ---
with tab_user:
    nome_sel = st.selectbox("Chi sei?", GRIGLIATORI)
    if nome_sel != "Seleziona il tuo nome...":
        df_p = load_gsheet(URL_PRESENZE)
        attivi = df_p[df_p["Nome"] == nome_sel]["Turno"].tolist() if not df_p.empty else []
        
        st.write("### I tuoi turni:")
        cols = st.columns(3)
        for i, turno in enumerate(TURNI):
            with cols[i % 3]:
                if st.toggle(turno, value=(turno in attivi), key=f"tgl_{i}"):
                    if turno not in attivi:
                        save_to_gsheet("Presenze", [nome_sel, turno])
                        st.rerun()

# --- SCHEDA CUCINA (FIX GRAFICO) ---
with tab_food:
    st.header("📦 Gestione Cucina")
    
    with st.form("food_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_data = c1.selectbox("Giorno", list(DATE_SOGLIA.keys()))
        f_prod = c2.selectbox("Cibo", ["Costicine", "Salsicce", "Braciole"])
        f_qty = c3.number_input("Quantità (kg o pezzi)", min_value=0, step=1)
        if st.form_submit_button("Registra Quantità 📝"):
            save_to_gsheet("Quantità Grigliate", [f_data, f_prod, f_qty])
            st.success("Dato inviato! Aggiorno...")
            time.sleep(1) # Diamo tempo a Google di digerire il dato
            st.rerun()

    st.divider()
    
    # Carichiamo i dati del magazzino
    df_m = load_gsheet(URL_MAGAZZINO)
    
    if not df_m.empty:
        # Pulizia e calcolo
        df_m['Valore'] = df_m['Quantita'].apply(extract_number)
        df_plot = df_m.groupby('Prodotto')['Valore'].sum().reset_index()
        
        # GRAFICO A BARRE (Solo nella tab Cucina)
        fig_bar = px.bar(df_plot, x='Prodotto', y='Valore', 
                         title="TOTALE GRIGLIATO (Intera Sagra)",
                         color='Prodotto',
                         text_auto=True,
                         color_discrete_map={"Costicine": "#EF553B", "Salsicce": "#FFA15A", "Braciole": "#636EFA"})
        st.plotly_chart(fig_bar, use_container_width=True)
        
        with st.expander("Vedi log preparazioni (ultime inserite)"):
            st.dataframe(df_m.iloc[::-1], use_container_width=True)
    else:
        st.info("Inserisci i primi dati per vedere il grafico delle quantità.")

# --- SCHEDA ADMIN ---
with tab_admin:
    st.link_button("📊 Apri Foglio Google", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
    # ... (resto della logica admin invariata)

# --- GRAFICI TURNI (Sempre in fondo alla pagina principale) ---
st.divider()
st.subheader("Stato Copertura Turni (Obiettivo: 5-6 persone)")
df_v = load_gsheet(URL_PRESENZE)
if not df_v.empty:
    df_v = df_v.drop_duplicates(subset=['Nome', 'Turno'], keep='last')
    cols_g = st.columns(3)
    for i, t in enumerate(TURNI):
        with cols_g[i % 3]:
            count = len(df_v[df_v["Turno"] == t])
            target = 5 if "Pranzo" in t else 6
            fig = go.Figure(data=[go.Pie(values=[count, max(0, target-count)], hole=.6, 
                                        marker_colors=["green" if count>=target else "red", "#eee"], showlegend=False)])
            fig.update_layout(title=f"<b>{t}</b>", height=200, margin=dict(t=30, b=0, l=0, r=0),
                              annotations=[dict(text=str(count), x=0.5, y=0.5, font_size=20, showarrow=False)])
            st.plotly_chart(fig, key=f"pie_{i}", use_container_width=True)
