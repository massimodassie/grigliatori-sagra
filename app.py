import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import urllib.parse
import requests
from datetime import datetime

# 1. --- CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

# Coordinate per il meteo (Esempio: zona Treviso/Venezia)
LAT = 45.8
LON = 12.2

GRIGLIATORI = sorted([
    "Seleziona il tuo nome...",
    "Botteon Marco", "Da Ronch Loris", "Denis Boscaratto", "Flavio",
    "Francesco Perencin", "Francesco Vicenza", "Giacomo",
    "Gianluca Sossai", "Massimo Dassie", "Mauro Micieli",
    "Mirko Modolo Zanchetta", "Radu Apostol", "Riccardo Rossi"
])

# Mappa delle date per il meteo (YYYY-MM-DD)
DATE_SOGLIA = {
    "Venerdì 09 maggio": "2026-05-09",
    "Domenica 10 maggio": "2026-05-10",
    "Venerdì 15 maggio": "2026-05-15",
    "Sabato 16 maggio": "2026-05-16",
    "Domenica 17 maggio": "2026-05-17",
    "Sabato 23 maggio": "2026-05-23",
    "Domenica 24 maggio": "2026-05-24"
}

TURNI = [
    "Venerdì 09 maggio - Cena", 
    "Domenica 10 maggio - Pranzo", 
    "Domenica 10 maggio - Cena", 
    "Venerdì 15 maggio - Cena della costata", 
    "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Cena", 
    "Sabato 23 maggio - Cena", 
    "Domenica 24 maggio - Pranzo", 
    "Domenica 24 maggio - Cena"
]

DATA_FILE = "presenze_sagra.csv"
CONTATTI_FILE = "contatti_grigliatori.csv"

# --- FUNZIONI METEO ---
def get_weather(date_str):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=weathercode,temperature_2m_max&timezone=Europe%2遴Rome&start_date={date_str}&end_date={date_str}"
        response = requests.get(url).json()
        code = response['daily']['weathercode'][0]
        temp = response['daily']['temperature_2m_max'][0]
        
        # Icone semplici basate sui codici WMO
        icons = {0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 51: "🌦️", 61: "🌧️", 71: "❄️", 95: "⛈️"}
        icon = icons.get(code, "🌡️")
        return f"{icon} {temp}°C"
    except:
        return "N/D"

# --- ALTRE FUNZIONI (DB) ---
def load_data(file):
    if os.path.exists(file):
        try: return pd.read_csv(file)
        except: return pd.DataFrame()
    return pd.DataFrame()

def update_presence(nome, turno, chiave_toggle):
    stato = st.session_state[chiave_toggle]
    df = load_data(DATA_FILE)
    if df.empty: df = pd.DataFrame(columns=["Nome", "Turno"])
    df = df[~((df["Nome"] == nome) & (df["Turno"] == turno))]
    if stato:
        nuova_riga = pd.DataFrame({"Nome": [nome], "Turno": [turno]})
        df = pd.concat([df, nuova_riga], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

# --- INTERFACCIA ---
st.title("🔥 Coordinamento Grigliatori 2026")

tab_user, tab_admin = st.tabs(["📝 I Miei Turni", "📢 Promemoria WA"])

with tab_user:
    nome_sel = st.selectbox("Chi sei?", GRIGLIATORI, key="user_select")
    if nome_sel != "Seleziona il tuo nome...":
        # (Codice contatti invariato...)
        df_c = load_data(CONTATTI_FILE)
        tel_attuale = df_c[df_c["Nome"] == nome_sel]["Telefono"].iloc[0] if not df_c.empty and nome_sel in df_c["Nome"].values else ""
        col_tel, col_btn = st.columns([3, 1])
        with col_tel: nuovo_tel = st.text_input("Numero per WA:", value=str(tel_attuale))
        with col_btn: 
            st.write(" ")
            if st.button("Salva"):
                df_c = load_data(CONTATTI_FILE)
                if df_c.empty: df_c = pd.DataFrame(columns=["Nome", "Telefono"])
                df_c = df_c[df_c["Nome"] != nome_sel]
                df_c = pd.concat([df_c, pd.DataFrame({"Nome": [nome_sel], "Telefono": [nuovo_tel]})], ignore_index=True)
                df_c.to_csv(CONTATTI_FILE, index=False)
                st.toast("Salvato!")

        st.divider()
        st.info("Tocca i turni per confermare:")
        df_p = load_data(DATA_FILE)
        turni_attivi = df_p[df_p["Nome"] == nome_sel]["Turno"].tolist() if not df_p.empty else []
        
        col1, col2, col3 = st.columns(3)
        for i, turno in enumerate(TURNI):
            target_col = [col1, col2, col3][i % 3]
            with target_col:
                # ESTRAZIONE METEO
                data_chiave = " ".join(turno.split(" ")[:3])
                info_meteo = get_weather(DATE_SOGLIA.get(data_chiave, ""))
                
                st.write(f"**{info_meteo}**") # Mostra meteo sopra il toggle
                chiave = f"tgl_{nome_sel}_{turno}"
                st.toggle(turno, value=(turno in turni_attivi), key=chiave,
                          on_change=update_presence, args=(nome_sel, turno, chiave))

# (Resto del codice Admin e Grafici invariato...)
with tab_admin:
    st.subheader("Lista Grigliatori per Turno")
    df_p = load_data(DATA_FILE)
    df_c = load_data(CONTATTI_FILE)
    turno_admin = st.selectbox("Turno:", TURNI)
    if not df_p.empty and turno_admin in df_p["Turno"].values:
        presenti = df_p[df_p["Turno"] == turno_admin]["Nome"].tolist()
        for p in presenti:
            c_n, c_l = st.columns([2, 1])
            num = df_c[df_c["Nome"] == p]["Telefono"].iloc[0] if not df_c.empty and p in df_c["Nome"].values else ""
            c_n.write(f"• {p}")
            if num:
                msg = urllib.parse.quote(f"Ciao {p}! Turno: {turno_admin}. 🔥")
                c_l.markdown(f"[📲 WA](https://wa.me/39{num}?text={msg})")
    else: st.warning("Nessuno segnato.")

st.divider()
st.subheader("📊 Stato Copertura")
df_vis = load_data(DATA_FILE)
cols = st.columns(3)
for i, turno in enumerate(TURNI):
    with cols[i % 3]:
        count = len(df_vis[df_vis["Turno"] == turno]) if not df_vis.empty else 0
        target = 5 if "Pranzo" in turno else 6
        fig = go.Figure(data=[go.Pie(values=[count, max(0, target-count)], hole=.5, marker_colors=["green" if count>=target else "red", "#eee"], showlegend=False)])
        fig.update_layout(title=f"<b>{turno}</b>", margin=dict(t=30, b=0, l=0, r=0), height=180)
        st.plotly_chart(fig, key=f"ch_{i}")
