import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
import time
import io
import urllib.parse

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori - Presenze", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby7yJ-jjJYworKTL9w20Er0w_Av3U1xqUvLQi0oGlrYy70Sg1xK6BJysNGZIZlJ0DtM/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_NOMI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=ListaGrigliatori"

# LISTA AGGIORNATA CON I TUOI TURNI ESATTI
DATE_UFFICIALI = [
    "Sabato 09 maggio - Cena", 
    "Domenica 10 maggio - Pranzo", 
    "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio - Cena della costata", 
    "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Pranzo", 
    "Domenica 17 maggio - Cena",
    "Sabato 23 maggio - Cena", 
    "Domenica 24 maggio - Pranzo", 
    "Domenica 24 maggio - Cena"
]

def load_data(url):
    try:
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        df = df.apply(lambda x: x.str.strip())
        return df
    except: return pd.DataFrame()

def save_presence(nome, turno):
    requests.post(f"{SCRIPT_URL}?sheet=Presenze", data=json.dumps([nome, turno]))

def delete_presence(sheet, row_idx):
    url = f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}&deleteRow={int(row_idx) + 2}"
    requests.get(url)

# --- INTERFACCIA ---
st.title("👥 Gestione Presenze")

df_n = load_data(URL_NOMI)
lista_nomi = sorted([n for n in df_n.iloc[:,0].unique() if n and n != "nan"]) if not df_n.empty else []
user = st.selectbox("Seleziona il tuo nome", [""] + lista_nomi)

df_p = load_data(URL_PRESENZE)

if user:
    st.subheader(f"Turni di: {user}")
    
    # Pulizia nomi colonne se presenti
    if not df_p.empty:
        df_p.columns = ["Nome", "Turno"][:len(df_p.columns)]
        miei_turni = df_p[df_p["Nome"].str.lower() == user.lower()]["Turno"].tolist()
    else:
        miei_turni = []

    cols = st.columns(2) # Due colonne per leggere meglio i nomi lunghi
    for i, data_t in enumerate(DATE_UFFICIALI):
        with cols[i%2]:
            # Controllo presenza (case-insensitive)
            is_checked = any(data_t.lower() == str(mt).lower() for mt in miei_turni)
            
            if st.toggle(data_t, value=is_checked, key=f"t_{i}") != is_checked:
                if not is_checked:
                    save_presence(user, data_t)
                else:
                    # Trova l'indice per cancellare
                    match = df_p[(df_p["Nome"].str.lower() == user.lower()) & (df_p["Turno"].str.lower() == data_t.lower())]
                    if not match.empty:
                        delete_presence("Presenze", match.index[0])
                st.rerun()

st.divider()
st.subheader("📊 Stato Copertura Team")

if not df_p.empty:
    for data_t in DATE_UFFICIALI:
        # Filtro presenti per il turno specifico
        presenti_turno = df_p[df_p["Turno"].str.lower() == data_t.lower()]["Nome"].unique().tolist()
        presenti_turno = [p for p in presenti_turno if p and p != "nan"]
        
        count = len(presenti_turno)
        target = 5 if "Pranzo" in data_t else 6
        
        col1, col2 = st.columns([1, 4])
        with col1:
            # Grafico a torta mini
            fig = go.Figure(go.Pie(values=[count, max(0, target-count)], hole=0.7, 
                                  marker_colors=["#2a9d8f", "#eeeeee"], showlegend=False, textinfo='none'))
            fig.update_layout(height=70, margin=dict(t=0, b=0, l=0, r=0), 
                             annotations=[dict(text=f"{count}/{target}", x=0.5, y=0.5, font_size=12, showarrow=False)])
            st.plotly_chart(fig, use_container_width=True, key=f"pie_{data_t}")
        with col2:
            st.markdown(f"**{data_t}**")
            st.caption(", ".join(presenti_turno) if presenti_turno else "Nessuno")

    # SEZIONE DEBUG PER SISTEMARE L'EXCEL
    with st.expander("🛠️ Analisi dati Excel (Controlla se ci sono errori)"):
        date_nel_foglio = df_p["Turno"].unique().tolist()
        errori = [d for d in date_nel_foglio if d not in DATE_UFFICIALI and d != ""]
        if errori:
            st.warning(f"Nell'Excel ci sono turni con nomi non riconosciuti: {errori}")
            st.info("Suggerimento: Correggi questi nomi nel foglio 'Presenze' usando quelli esatti (es. aggiungi '- Cena' dove manca)")
        else:
            st.success("Tutte le date nel foglio Excel sono sincronizzate correttamente!")
