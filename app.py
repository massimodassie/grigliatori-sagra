import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import urllib.parse
import requests

# 1. --- CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

LAT, LON = 45.8, 12.2 # Coordinate zona Sagra

GRIGLIATORI = sorted([
    "Seleziona il tuo nome...",
    "Botteon Marco", "Da Ronch Loris", "Denis Boscaratto", "Flavio",
    "Francesco Perencin", "Francesco Vicenza", "Giacomo",
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

DATA_FILE = "presenze_sagra.csv"
CONTATTI_FILE = "contatti_grigliatori.csv"

# --- FUNZIONI ---
def load_data(file):
    if os.path.exists(file):
        try: return pd.read_csv(file)
        except: return pd.DataFrame()
    return pd.DataFrame()

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

def update_presence(nome, turno, chiave):
    stato = st.session_state[chiave]
    df = load_data(DATA_FILE)
    if df.empty: df = pd.DataFrame(columns=["Nome", "Turno"])
    df = df[~((df["Nome"] == nome) & (df["Turno"] == turno))]
    if stato:
        df = pd.concat([df, pd.DataFrame({"Nome": [nome], "Turno": [turno]})], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

# --- INTERFACCIA ---
st.title("🔥 Coordinamento Grigliatori 2026")

tab_user, tab_admin = st.tabs(["📝 I Miei Turni", "📢 Promemoria WA"])

with tab_user:
    nome_sel = st.selectbox("Chi sei?", GRIGLIATORI, key="user_select")

    if nome_sel != "Seleziona il tuo nome...":
        # Parte contatti
        df_c = load_data(CONTATTI_FILE)
        tel_att = df_c[df_c["Nome"] == nome_sel]["Telefono"].iloc[0] if not df_c.empty and nome_sel in df_c["Nome"].values else ""
        
        c_t, c_b = st.columns([3, 1])
        new_tel = c_t.text_input("Il tuo numero:", value=str(tel_att))
        if c_b.button("Salva Tel", use_container_width=True):
            df_c = load_data(CONTATTI_FILE)
            if df_c.empty: df_c = pd.DataFrame(columns=["Nome", "Telefono"])
            df_c = df_c[df_c["Nome"] != nome_sel]
            df_c = pd.concat([df_c, pd.DataFrame({"Nome":[nome_sel], "Telefono":[new_tel]})], ignore_index=True)
            df_c.to_csv(CONTATTI_FILE, index=False)
            st.toast("Salvato!")

        st.divider()
        df_p = load_data(DATA_FILE)
        attivi = df_p[df_p["Nome"] == nome_sel]["Turno"].tolist() if not df_p.empty else []
        
        # Qui c'era l'errore: ora siamo dentro l'IF, quindi nome_sel esiste!
        cols = st.columns(3)
        for i, turno in enumerate(TURNI):
            with cols[i % 3]:
                d_chiave = " ".join(turno.split(" ")[:3])
                meteo = get_weather(DATE_SOGLIA.get(d_chiave, ""))
                st.caption(f"Previsione: {meteo}")
                
                k = f"tgl_{nome_sel.replace(' ', '_')}_{i}" # Chiave pulita
                st.toggle(turno, value=(turno in attivi), key=k, 
                          on_change=update_presence, args=(nome_sel, turno, k))

with tab_admin:
    st.subheader("Admin - Lista per Turno")
    df_p, df_c = load_data(DATA_FILE), load_data(CONTATTI_FILE)
    t_adm = st.selectbox("Seleziona turno:", TURNI)
    if not df_p.empty and t_adm in df_p["Turno"].values:
        pres = df_p[df_p["Turno"] == t_adm]["Nome"].tolist()
        for p in pres:
            c_n, c_w = st.columns([2, 1])
            num = df_c[df_c["Nome"] == p]["Telefono"].iloc[0] if not df_c.empty and p in df_c["Nome"].values else ""
            c_n.write(f"• {p}")
            if num:
                m = urllib.parse.quote(f"Ciao {p}! Turno: {t_adm}. 🔥")
                c_w.markdown(f"[📲 WA](https://wa.me/39{num}?text={m})")
    else: st.info("Nessuno segnato.")

# 3. --- GRAFICI ---
st.divider()
df_v = load_data(DATA_FILE)
cols_g = st.columns(3)
for i, t in enumerate(TURNI):
    with cols_g[i % 3]:
        count = len(df_v[df_v["Turno"] == t]) if not df_v.empty else 0
        target = 5 if "Pranzo" in t else 6
        fig = go.Figure(data=[go.Pie(values=[count, max(0, target-count)], hole=.6, 
                                    marker_colors=["green" if count>=target else "red", "#eee"], showlegend=False)])
        fig.update_layout(title=f"<b>{t}</b>", margin=dict(t=30, b=0, l=0, r=0), height=180, 
                          annotations=[dict(text=str(count), x=0.5, y=0.5, font_size=18, showarrow=False)])
        st.plotly_chart(fig, key=f"g_{i}", use_container_width=True)
