import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import io
import urllib.parse
from datetime import datetime, timedelta

# --- 1. CONFIGURAZIONE GENERALE ---
st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby7yJ-jjJYworKTL9w20Er0w_Av3U1xqUvLQi0oGlrYy70Sg1xK6BJysNGZIZlJ0DtM/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_CARNE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")
URL_NOMI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=ListaGrigliatori"

DATE_UFFICIALI = [
    "Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI = ["Costicine", "Salsicce", "Braciole"]
COLORI_CARNE = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

# --- 2. FUNZIONI DI COMUNICAZIONE ---
def load_data(url):
    try:
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        df = df.apply(lambda x: x.str.strip())
        return df
    except: return pd.DataFrame()

def save_data(sheet, data):
    try:
        res = requests.post(f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}", data=json.dumps(data), timeout=15)
        return res.status_code == 200
    except: return False

def delete_row(sheet, row_idx):
    try:
        url = f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}&deleteRow={int(row_idx) + 2}"
        requests.get(url, timeout=10)
        return True
    except: return False

# --- 3. INTERFACCIA ---
st.title("🔥 Portale Grigliatori Sagra 2026")
tab_presenze, tab_carne, tab_impostazioni = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "⚙️ Gestione Nomi"])

# --- TAB 1: PRESENZE ---
with tab_presenze:
    st.header("Gestione Turni Team")
    df_n = load_data(URL_NOMI)
    lista_nomi = sorted([n for n in df_n.iloc[:,0].unique() if n and n != "nan"]) if not df_n.empty else []
    
    user = st.selectbox("Seleziona il tuo nome", [""] + lista_nomi, key="user_p")
    df_p = load_data(URL_PRESENZE)
    if not df_p.empty: df_p.columns = ["Nome", "Turno"][:len(df_p.columns)]

    if user:
        st.subheader(f"I tuoi turni: {user}")
        miei_turni = df_p[df_p["Nome"].str.lower() == user.lower()]["Turno"].tolist() if not df_p.empty else []
        cols = st.columns(2)
        for i, dt in enumerate(DATE_UFFICIALI):
            with cols[i%2]:
                is_checked = any(dt.lower() == str(mt).lower() for mt in miei_turni)
                if st.toggle(dt, value=is_checked, key=f"p_{i}") != is_checked:
                    if not is_checked: save_data("Presenze", [user, dt])
                    else:
                        match = df_p[(df_p["Nome"].str.lower() == user.lower()) & (df_p["Turno"].str.lower() == dt.lower())]
                        if not match.empty: delete_row("Presenze", match.index[0])
                    st.rerun()

    st.divider()
    st.subheader("📊 Stato Copertura Team")
    if not df_p.empty:
        for dt in DATE_UFFICIALI:
            presenti = [p for p in df_p[df_p["Turno"].str.lower() == dt.lower()]["Nome"].unique().tolist() if p and p != "nan"]
            count = len(presenti)
            target = 5 if "Pranzo" in dt else 7
            
            # Definizione colore e testo
            if count < target:
                color_c = "#e76f51" # Arancio
                status_m = f"⚠️ TARGET KO: -{target-count}"
            elif count == target:
                color_c = "#2a9d8f" # Verde
                status_m = "✅ TARGET OK"
            else:
                color_c = "#1d3557" # Blu Scuro
                status_m = f"✅ TARGET OK (+{count-target})"

            c1, c2 = st.columns([1, 4])
            with c1:
                # TRUCCO: Il range del gauge deve essere SEMPRE uguale al count se count > target
                # Questo impedisce a Plotly di disegnare l'arco grigio di "sfondo"
                max_gauge = max(target, count)
                
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = count,
                    number = {'font': {'color': color_c, 'size': 26}},
                    gauge = {
                        'axis': {'range': [0, max_gauge], 'visible': False},
                        'bar': {'color': color_c},
                        'bgcolor': "#eeeeee",
                        'borderwidth': 0
                    }
                ))
                fig.update_layout(height=140, margin=dict(t=20, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True, key=f"g_{dt}", config={'displayModeBar': False})
            
            with c2:
                st.markdown(f"### {dt}")
                st.markdown(f"**{status_m}** ({count}/{target})")
                st.markdown(f"PRESENTI: {', '.join(presenti) if presenti else '*Nessuno*'}")
            st.divider()

# --- TAB 2: MONITOR CARNE (Invariato) ---
with tab_carne:
    df_q = load_data(URL_CARNE)
    if not df_q.empty:
        while len(df_q.columns) < 4: df_q[f"Col_{len(df_q.columns)}"] = ""
        df_q.columns = ["Giorno", "Prodotto", "Quantita", "Ora"][:len(df_q.columns)]
        df_q["Quantita"] = pd.to_numeric(df_q["Quantita"], errors='coerce').fillna(0)

    st.markdown("### ➕ 1. Inserimento Nuova Rilevazione")
    with st.form("form_carne", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        f_d = c1.selectbox("Turno", DATE_UFFICIALI)
        f_p = c2.selectbox("Prodotto", PRODOTTI)
        f_qta = c3.number_input("Pezzi Totali Monitor", min_value=0, step=1)
        f_ora = c4.text_input("Ora (HH:MM)", value=(datetime.now() + timedelta(hours=2)).strftime("%H:%M"))
        if st.form_submit_button("REGISTRA DATO"):
            if save_data("Quantità Grigliate", [f_d, f_p, f_qta, f_ora]):
                st.success("Dato Salvato!")
                time.sleep(1)
                st.rerun()

    st.divider()
    st.markdown("### 🔍 3. Dettaglio Turni")
    if not df_q.empty:
        for g_uff in DATE_UFFICIALI:
            df_g = df_q[df_q["Giorno"] == g_uff].sort_values("Ora")
            if not df_g.empty:
                st.markdown(f"#### 📅 {g_uff}")
                df_g["Ritmo"] = df_g.groupby("Prodotto")["Quantita"].diff().fillna(df_g["Quantita"])
                df_g.loc[df_g["Ritmo"] < 0, "Ritmo"] = 0
                ca, cb = st.columns(2)
                with ca:
                    res = df_g.groupby("Prodotto")["Quantita"].max().reindex(PRODOTTI).fillna(0).reset_index()
                    st.plotly_chart(px.bar(res, x="Prodotto", y="Quantita", color="Prodotto", text_auto=True, 
                                         color_discrete_map=COLORI_CARNE, height=300, title="Totale Giornaliero"), use_container_width=True, key=f"b_{g_uff}")
                with cb:
                    st.plotly_chart(px.line(df_g, x="Ora", y="Ritmo", color="Prodotto", markers=True, 
                                          color_discrete_map=COLORI_CARNE, height=300, title="Andamento Orario", line_shape="spline"), use_container_width=True, key=f"l_{g_uff}")

# --- TAB 3: GESTIONE NOMI (Invariato) ---
with tab_impostazioni:
    st.header("Gestione Anagrafica Grigliatori")
    df_n = load_data(URL_NOMI)
    if not df_n.empty:
        for i, row in df_n.iterrows():
            if row.iloc[0]:
                cx, cy = st.columns([8,2])
                cx.write(row.iloc[0])
                if cy.button("Rimuovi", key=f"rm_n_{i}"):
                    if delete_row("ListaGrigliatori", i): st.rerun()
    
    nuovo = st.text_input("Aggiungi nuovo nome")
    if st.button("Aggiungi"):
        if nuovo and save_data("ListaGrigliatori", [nuovo]): st.rerun()
