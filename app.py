import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
import time
import io
import urllib.parse

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby7yJ-jjJYworKTL9w20Er0w_Av3U1xqUvLQi0oGlrYy70Sg1xK6BJysNGZIZlJ0DtM/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_NOMI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=ListaGrigliatori"

# LISTA UFFICIALE (Deve corrispondere a quella dell'Excel)
DATE_UFFICIALI = [
    "Sabato 09 maggio", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio", "Sabato 16 maggio", "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]

def load_data(url):
    try:
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        # Pulizia: tutto in stringa, togli spazi bianchi all'inizio e alla fine
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
lista_nomi = sorted([n for n in df_n.iloc[:,0].unique() if n]) if not df_n.empty else []
user = st.selectbox("Chi sei?", [""] + lista_nomi)

df_p = load_data(URL_PRESENZE)

if user:
    st.subheader(f"I tuoi turni ({user})")
    # Filtriamo i turni dell'utente ignorando maiuscole/minuscole e spazi
    miei_turni = []
    if not df_p.empty:
        # Colonna 0 = Nome, Colonna 1 = Turno
        miei_turni = df_p[df_p.iloc[:,0].str.lower() == user.lower()].iloc[:,1].tolist()

    cols = st.columns(3)
    for i, data_t in enumerate(DATE_UFFICIALI):
        with cols[i%3]:
            # Controllo "blindato": verifica se il turno dell'utente è nella lista ufficiale
            is_checked = any(data_t.lower() == mt.lower() for mt in miei_turni)
            
            if st.toggle(data_t, value=is_checked, key=f"t_{i}") != is_checked:
                if not is_checked:
                    save_presence(user, data_t)
                else:
                    # Troviamo l'indice esatto per cancellare
                    match = df_p[(df_p.iloc[:,0].str.lower() == user.lower()) & (df_p.iloc[:,1].str.lower() == data_t.lower())]
                    if not match.empty:
                        delete_presence("Presenze", match.index[0])
                st.rerun()

st.divider()
st.subheader("📊 Copertura Team")

if not df_p.empty:
    for data_t in DATE_UFFICIALI:
        # Contiamo i presenti per questo turno in modo "insensibile" a errori di battitura
        presenti = df_p[df_p.iloc[:,1].str.lower() == data_t.lower()].iloc[:,0].unique().tolist()
        count = len([p for p in presenti if p])
        target = 5 if "Pranzo" in data_t else 6
        
        c1, c2 = st.columns([1, 4])
        with c1:
            fig = go.Figure(go.Pie(values=[count, max(0, target-count)], hole=0.7, 
                                  marker_colors=["#2a9d8f", "#eeeeee"], showlegend=False, textinfo='none'))
            fig.update_layout(height=80, margin=dict(t=0, b=0, l=0, r=0), 
                             annotations=[dict(text=f"{count}/{target}", x=0.5, y=0.5, font_size=14, showarrow=False)])
            st.plotly_chart(fig, use_container_width=True, key=f"pie_{data_t}")
        with c2:
            st.markdown(f"**{data_t}**")
            st.caption(", ".join(presenti) if presenti else "Nessun grigliatore")

    # DEBUG: Mostra se ci sono dati "orfani" nel foglio Excel
    with st.expander("⚠️ Verifica errori nel foglio Excel"):
        st.write("Se vedi date qui sotto, significa che nell'Excel sono scritte male e devi correggerle:")
        date_nel_foglio = df_p.iloc[:,1].unique()
        errori = [d for d in date_nel_foglio if d not in DATE_UFFICIALI and d != ""]
        if errori:
            st.error(f"Date errate trovate nell'Excel: {errori}")
        else:
            st.success("Tutte le date nel foglio Excel sono scritte correttamente!")
