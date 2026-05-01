import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import urllib.parse
import requests
import json

# 1. --- CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxlzO8HR87qEHeM5L6kDLWwctu_AehDK8yZZhhCh_bNLiLmPk3GTTJXKRHGeM0XBtxA/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_CONTATTI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Contatti"
# Aggiornato con il tuo nuovo nome foglio
URL_MAGAZZINO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Quantità%20Grigliate"

LAT, LON = 45.8, 12.2 

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
        return pd.read_csv(f"{url}&nocache={os.urandom(4).hex()}")
    except:
        return pd.DataFrame()

def save_to_gsheet(sheet_name, data_list):
    try:
        requests.post(f"{SCRIPT_URL}?sheet={sheet_name}", data=json.dumps(data_list), timeout=10)
    except Exception as e:
        st.error(f"Errore: {e}")

def get_weather(date_iso):
    if not date_iso: return "⏳ -"
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=weathercode,temperature_2m_max&timezone=Europe%2FRome&start_date={date_iso}&end_date={date_iso}"
        res = requests.get(url, timeout=5).json()
        if 'daily' in res:
            c, t = res['daily']['weathercode'][0], res['daily']['temperature_2m_max'][0]
            icons = {0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 61: "🌧️", 95: "⛈️"}
            return f"{icons.get(c, '🌤️')} {t}°C"
        return "⏳ -"
    except: return "🌡️ -"

# --- INTERFACCIA ---
st.title("🔥 Portale Sagra 2026")

tab_user, tab_food, tab_admin = st.tabs(["📝 I Miei Turni", "📦 Cucina & Quantità", "📢 Admin"])

# --- SCHEDA TURNI ---
with tab_user:
    nome_sel = st.selectbox("Chi sei?", GRIGLIATORI)
    if nome_sel != "Seleziona il tuo nome...":
        df_c = load_gsheet(URL_CONTATTI)
        tel_att = df_c[df_c["Nome"] == nome_sel]["Telefono"].iloc[-1] if not df_c.empty and nome_sel in df_c["Nome"].values else ""
        c_t, c_b = st.columns([3, 1])
        new_tel = c_t.text_input("Il tuo numero:", value=str(tel_att))
        if c_b.button("Salva Tel"):
            save_to_gsheet("Contatti", [nome_sel, new_tel])
            st.success("Salvato!")
            st.rerun()

        st.divider()
        df_p = load_gsheet(URL_PRESENZE)
        attivi = df_p[df_p["Nome"] == nome_sel]["Turno"].tolist() if not df_p.empty else []
        cols = st.columns(3)
        for i, turno in enumerate(TURNI):
            with cols[i % 3]:
                d_chiave = " ".join(turno.split(" ")[:3])
                st.caption(f"Meteo: {get_weather(DATE_SOGLIA.get(d_chiave, ''))}")
                if st.toggle(turno, value=(turno in attivi), key=f"tgl_{i}"):
                    if turno not in attivi:
                        save_to_gsheet("Presenze", [nome_sel, turno])
                        st.rerun()

# --- SCHEDA CUCINA ---
with tab_food:
    st.subheader("Registrazione Quantità Preparate")
    with st.form("food_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        f_data = col1.selectbox("Giorno", list(DATE_SOGLIA.keys()))
        f_prod = col2.text_input("Prodotto (es: Costine, Salsicce)")
        f_qty = col3.text_input("Quantità (es: 30kg, 100pz)")
        submit = st.form_submit_button("Invia in cucina 📝")
        
        if submit and f_prod and f_qty:
            # Salvataggio nel foglio corretto
            save_to_gsheet("Quantità Grigliate", [f_data, f_prod, f_qty])
            st.success(f"Registrato: {f_prod} per {f_data}")

    st.divider()
    st.subheader("Riepilogo Preparazioni")
    df_m = load_gsheet(URL_MAGAZZINO)
    if not df_m.empty:
        st.dataframe(df_m.iloc[::-1], use_container_width=True)
    else:
        st.info("Ancora nessuna quantità registrata nel foglio 'Quantità Grigliate'.")

# --- SCHEDA ADMIN ---
with tab_admin:
    st.subheader("Gestione")
    st.link_button("📊 Apri Foglio Google", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
    df_p = load_gsheet(URL_PRESENZE)
    df_c = load_gsheet(URL_CONTATTI)
    t_adm = st.selectbox("Seleziona turno:", TURNI)
    if not df_p.empty and t_adm in df_p["Turno"].values:
        df_clean = df_p.drop_duplicates(subset=['Nome', 'Turno'], keep='last')
        pres = df_clean[df_clean["Turno"] == t_adm]["Nome"].tolist()
        for p in pres:
            c_n, c_w = st.columns([2, 1])
            num = df_c[df_c["Nome"] == p]["Telefono"].iloc[-1] if not df_c.empty and p in df_c["Nome"].values else ""
            c_n.write(f"• {p}")
            if num:
                m = urllib.parse.quote(f"Ciao {p}! Turno: {t_adm}. 🔥")
                c_w.markdown(f"[📲 WA](https://wa.me/39{num}?text={m})")

# 3. --- GRAFICI ---
st.divider()
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
            fig.update_layout(title=f"<b>{t}</b>", margin=dict(t=30, b=0, l=0, r=0), height=180, 
                              annotations=[dict(text=str(count), x=0.5, y=0.5, font_size=18, showarrow=False)])
            st.plotly_chart(fig, key=f"g_{i}", use_container_width=True)
