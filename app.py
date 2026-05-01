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

# --- FUNZIONI DI SUPPORTO ---
def load_data_from_gs(url):
    try:
        # Aggiungiamo un timestamp per forzare Google a darci i dati nuovi
        return pd.read_csv(f"{url}&ts={int(time.time())}")
    except:
        return pd.DataFrame()

def send_to_google(sheet_name, row_data):
    try:
        requests.post(f"{SCRIPT_URL}?sheet={sheet_name}", data=json.dumps(row_data), timeout=10)
    except:
        st.error("Errore di connessione")

def clean_qty(val):
    if pd.isna(val): return 0
    # Estrae solo i numeri (es. "20 kg" -> 20)
    n = re.findall(r'\d+', str(val))
    return int(n[0]) if n else 0

# --- INTERFACCIA PRINCIPALE ---
st.title("🔥 Portale Coordinamento Sagra")

# Creiamo le schede
t1, t2, t3 = st.tabs(["📝 Turni Personali", "📊 Quantità Carne", "📢 Pannello Admin"])

# --- TAB 1: TURNI ---
with t1:
    user = st.selectbox("Seleziona il tuo nome:", GRIGLIATORI)
    if user != "Seleziona il tuo nome...":
        df_p = load_data_from_gs(URL_PRESENZE)
        mie_presenze = df_p[df_p["Nome"] == user]["Turno"].tolist() if not df_p.empty else []
        
        st.info(f"Ciao {user}, seleziona i turni in cui sarai presente alla griglia:")
        c = st.columns(3)
        for idx, trn in enumerate(TURNI):
            with c[idx % 3]:
                is_on = st.toggle(trn, value=(trn in mie_presenze), key=f"trn_{idx}")
                if is_on and trn not in mie_presenze:
                    send_to_google("Presenze", [user, trn])
                    st.rerun()

# --- TAB 2: QUANTITÀ CARNE (BAR CHART) ---
with t2:
    st.header("🥩 Carne Preparata")
    
    # Form di inserimento
    with st.container(border=True):
        st.write("**Inserisci nuova produzione:**")
        f_c1, f_c2, f_c3 = st.columns(3)
        giorno = f_c1.selectbox("Giorno", list(DATE_SOGLIA.keys()), key="f_giorno")
        cibo = f_c2.selectbox("Tipo Carne", ["Costicine", "Salsicce", "Braciole"], key="f_cibo")
        quant = f_c3.number_input("Quantità (kg)", min_value=0, step=1, key="f_quant")
        
        if st.button("Registra in foglio 📝"):
            send_to_google("Quantità Grigliate", [giorno, cibo, quant])
            st.success(f"Registrati {quant}kg di {cibo}")
            time.sleep(1)
            st.rerun()

    st.divider()

    # Visualizzazione Grafico a Barre
    df_m = load_data_from_gs(URL_MAGAZZINO)
    if not df_m.empty:
        # Puliamo i dati per sicurezza
        df_m['Valore'] = df_m['Quantita'].apply(clean_qty)
        # Raggruppiamo per tipo carne
        df_bar = df_m.groupby('Prodotto')['Valore'].sum().reset_index()
        
        fig_carne = px.bar(
            df_bar, 
            x='Prodotto', 
            y='Valore',
            color='Prodotto',
            title="Quantità Totali Prodotte (kg)",
            text_auto=True,
            color_discrete_map={"Costicine": "#d32f2f", "Salsicce": "#ef6c00", "Braciole": "#1976d2"}
        )
        st.plotly_chart(fig_carne, use_container_width=True)
        
        with st.expander("Vedi storico inserimenti"):
            st.table(df_m.iloc[::-1].head(10)) # Ultime 10 righe
    else:
        st.warning("Nessun dato trovato nel foglio 'Quantità Grigliate'.")

# --- TAB 3: ADMIN E TORTE ---
with t3:
    st.subheader("Copertura Turni e Contatti")
    st.link_button("📂 Apri Excel Originale", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
    
    df_p = load_data_from_gs(URL_PRESENZE)
    
    # Grafici a Torta
    if not df_p.empty:
        df_p_clean = df_p.drop_duplicates(subset=['Nome', 'Turno'], keep='last')
        st.write("### Stato Turni")
        cols_pie = st.columns(3)
        for idx, t_name in enumerate(TURNI):
            with cols_pie[idx % 3]:
                count = len(df_p_clean[df_p_clean["Turno"] == t_name])
                target = 5 if "Pranzo" in t_name else 6
                
                fig = go.Figure(go.Pie(
                    values=[count, max(0, target-count)],
                    hole=0.6,
                    marker_colors=["#2e7d32", "#eeeeee"],
                    showlegend=False
                ))
                fig.update_layout(title=f"{t_name}", height=180, margin=dict(t=30, b=0, l=0, r=0),
                                  annotations=[dict(text=str(count), x=0.5, y=0.5, font_size=20, showarrow=False)])
                st.plotly_chart(fig, use_container_width=True, key=f"pie_chart_{idx}")

    st.divider()
    
    # WhatsApp Admin
    st.write("### WhatsApp Rapido")
    df_c = load_data_from_gs(URL_CONTATTI)
    t_wa = st.selectbox("Invia promemoria per:", TURNI)
    if not df_p.empty:
        nomi = df_p_clean[df_p_clean["Turno"] == t_wa]["Nome"].tolist()
        for n in nomi:
            tel = df_c[df_c["Nome"] == n]["Telefono"].iloc[-1] if not df_c.empty and n in df_c["Nome"].values else ""
            c_a, c_b = st.columns([2, 1])
            c_a.write(f"🏃 {n}")
            if tel:
                msg = urllib.parse.quote(f"Ciao {n}! Ricordati il turno in griglia: {t_wa} 🔥")
                c_b.markdown(f"[Invia WA](https://wa.me/39{tel}?text={msg})")
