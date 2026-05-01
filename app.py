import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import urllib.parse
import requests

# 1. --- CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

# URL del tuo foglio Google (formato export CSV)
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_CONTATTI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Contatti"

# Link per scrivere (Apps Script o Form sarebbe meglio, ma usiamo un trucco con Google Form o istruzioni semplici)
# Per ora, l'app userà i file locali e tu potrai fare l'export, 
# ma per SCRIVERE direttamente su Sheets senza API serve un piccolo "ponte".

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

# --- FUNZIONI DI LETTURA (Da Google Sheets) ---
def load_gsheet(url):
    try:
        return pd.read_csv(url)
    except:
        return pd.DataFrame()

# NOTA: Per scrivere su Google Sheets in modo sicuro da Streamlit Cloud 
# senza database complessi, continuiamo a usare i file locali per la SCRITTURA
# ma li caricheremo nel foglio. 
DATA_FILE = "presenze_sagra.csv"
CONTATTI_FILE = "contatti_grigliatori.csv"

def save_data(df, file):
    df.to_csv(file, index=False)

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
st.title("🔥 Coordinamento Grigliatori 2026")

tab_user, tab_admin = st.tabs(["📝 I Miei Turni", "📢 Promemoria WA"])

with tab_user:
    nome_sel = st.selectbox("Chi sei?", GRIGLIATORI)

    if nome_sel != "Seleziona il tuo nome...":
        df_c = load_gsheet(URL_CONTATTI) if 'URL_CONTATTI' in locals() else pd.DataFrame()
        # Se il foglio online è vuoto, cerca in locale
        if df_c.empty: df_c = pd.read_csv(CONTATTI_FILE) if os.path.exists(CONTATTI_FILE) else pd.DataFrame(columns=["Nome", "Telefono"])
        
        tel_att = df_c[df_c["Nome"] == nome_sel]["Telefono"].iloc[0] if nome_sel in df_c["Nome"].values else ""
        
        c_t, c_b = st.columns([3, 1])
        new_tel = c_t.text_input("Il tuo numero:", value=str(tel_att))
        if c_b.button("Salva Tel"):
            df_c = df_c[df_c["Nome"] != nome_sel]
            df_c = pd.concat([df_c, pd.DataFrame({"Nome":[nome_sel], "Telefono":[new_tel]})], ignore_index=True)
            save_data(df_c, CONTATTI_FILE)
            st.toast("Salvato in locale (Sincronizza con Admin)")

        st.divider()
        df_p = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame(columns=["Nome", "Turno"])
        attivi = df_p[df_p["Nome"] == nome_sel]["Turno"].tolist()
        
        cols = st.columns(3)
        for i, turno in enumerate(TURNI):
            with cols[i % 3]:
                d_chiave = " ".join(turno.split(" ")[:3])
                meteo = get_weather(DATE_SOGLIA.get(d_chiave, ""))
                st.caption(f"Meteo: {meteo}")
                
                k = f"tgl_{nome_sel.replace(' ', '_')}_{i}"
                if st.toggle(turno, value=(turno in attivi), key=k):
                    if turno not in attivi:
                        df_p = pd.concat([df_p, pd.DataFrame({"Nome": [nome_sel], "Turno": [turno]})], ignore_index=True)
                        save_data(df_p, DATA_FILE)
                else:
                    if turno in attivi:
                        df_p = df_p[~((df_p["Nome"] == nome_sel) & (df_p["Turno"] == turno))]
                        save_data(df_p, DATA_FILE)

with tab_admin:
    st.subheader("Pannello di Controllo")
    # Tasto per scaricare i dati attuali (per caricarli su Sheets se necessario)
    col_a, col_b = st.columns(2)
    with col_a:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "rb") as file:
                st.download_button("📥 Scarica CSV Presenze", file, "presenze.csv", "text/csv")
    with col_b:
        if os.path.exists(CONTATTI_FILE):
            with open(CONTATTI_FILE, "rb") as file:
                st.download_button("📥 Scarica CSV Contatti", file, "contatti.csv", "text/csv")
    
    st.divider()
    df_p = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame()
    df_c = pd.read_csv(CONTATTI_FILE) if os.path.exists(CONTATTI_FILE) else pd.DataFrame()
    
    t_adm = st.selectbox("Seleziona turno per inviare WA:", TURNI)
    if not df_p.empty and t_adm in df_p["Turno"].values:
        pres = df_p[df_p["Turno"] == t_adm]["Nome"].tolist()
        for p in pres:
            c_n, c_w = st.columns([2, 1])
            num = df_c[df_c["Nome"] == p]["Telefono"].iloc[0] if p in df_c["Nome"].values else ""
            c_n.write(f"• {p}")
            if num:
                m = urllib.parse.quote(f"Ciao {p}! Turno: {t_adm}. 🔥")
                c_w.markdown(f"[📲 WA](https://wa.me/39{num}?text={m})")
