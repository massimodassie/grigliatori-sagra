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

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby7yJ-jjJYworKTL9w20Er0w_Av3U1xqUvLQi0oGlrYy70Sg1xK6BJysNGZIZlJ0DtM/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_CARNE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")
URL_NOMI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=ListaGrigliatori"

# LISTA TURNI BLINDATA (Identica per Presenze e Carne)
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
PRODOTTI = ["Costicine", "Salsicce", "Braciole"]
COLORI_CARNE = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

# --- 2. FUNZIONI DI CARICAMENTO ---
def load_data(url):
    try:
        r = requests.get(f"{url}&nocache={time.time()}", timeout=10)
        df = pd.read_csv(io.StringIO(r.text), dtype=str, na_filter=False)
        df = df.apply(lambda x: x.str.strip())
        return df
    except: return pd.DataFrame()

def save_data(sheet, data):
    try:
        requests.post(f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}", data=json.dumps(data), timeout=15)
        return True
    except: return False

def delete_row(sheet, row_idx):
    try:
        url = f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}&deleteRow={int(row_idx) + 2}"
        requests.get(url, timeout=10)
        return True
    except: return False

# --- 3. INTERFACCIA ---
st.title("🔥 Portale Grigliatori 2026")
tab1, tab2, tab3 = st.tabs(["👥 Presenze & Turni", "🍖 Monitor Carne", "⚙️ Gestione"])

# --- TAB 1: PRESENZE (VERSIONE BLINDATA) ---
with tab1:
    df_n = load_data(URL_NOMI)
    lista_nomi = sorted([n for n in df_n.iloc[:,0].unique() if n and n != "nan"]) if not df_n.empty else []
    user = st.selectbox("Seleziona il tuo nome", [""] + lista_nomi)
    
    df_p = load_data(URL_PRESENZE)
    if not df_p.empty: df_p.columns = ["Nome", "Turno"][:len(df_p.columns)]

    if user:
        st.subheader(f"I tuoi turni: {user}")
        miei_turni = df_p[df_p["Nome"].str.lower() == user.lower()]["Turno"].tolist() if not df_p.empty else []
        cols = st.columns(2)
        for i, data_t in enumerate(DATE_UFFICIALI):
            with cols[i%2]:
                is_checked = any(data_t.lower() == str(mt).lower() for mt in miei_turni)
                if st.toggle(data_t, value=is_checked, key=f"t_{i}") != is_checked:
                    if not is_checked: save_data("Presenze", [user, data_t])
                    else:
                        match = df_p[(df_p["Nome"].str.lower() == user.lower()) & (df_p["Turno"].str.lower() == data_t.lower())]
                        if not match.empty: delete_row("Presenze", match.index[0])
                    st.rerun()

    st.divider()
    st.subheader("📊 Stato Copertura Team")
    if not df_p.empty:
        for data_t in DATE_UFFICIALI:
            presenti = df_p[df_p["Turno"].str.lower() == data_t.lower()]["Nome"].unique().tolist()
            presenti = [p for p in presenti if p and p != "nan"]
            count, target = len(presenti), (5 if "Pranzo" in data_t else 6)
            color_pie = "#2a9d8f" if count >= target else "#e76f51"
            
            c1, c2 = st.columns([1, 4])
            with c1:
                fig = go.Figure(go.Pie(values=[count, max(0, target-count)], hole=0.7, marker_colors=[color_pie, "#eeeeee"], showlegend=False, textinfo='none', sort=False))
                fig.update_layout(height=70, margin=dict(t=0, b=0, l=0, r=0), annotations=[dict(text=f"{count}/{target}", x=0.5, y=0.5, font_size=12, showarrow=False, font_color=color_pie)])
                st.plotly_chart(fig, use_container_width=True, key=f"pie_{data_t}")
            with c2:
                st.markdown(f"**{data_t}**")
                st.caption(f"{'✅' if count>=target else '⚠️'} {', '.join(presenti) if presenti else 'Nessuno'}")

# --- TAB 2: CARNE (MODALITÀ MONITOR) ---
with tab2:
    st.header("🍖 Monitoraggio Quantità")
    
    # Inserimento dati
    col_in, col_de = st.columns(2)
    with col_in:
        with st.expander("➕ Inserisci Pezzi Monitor"):
            ora_it = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
            with st.form("form_carne", clear_on_submit=True):
                f_data = st.selectbox("Giorno/Turno", DATE_UFFICIALI)
                f_tipo = st.selectbox("Prodotto", PRODOTTI)
                f_qta = st.number_input("Pezzi Totali Visualizzati", min_value=0, step=1)
                f_ora = st.text_input("Ora rilevazione", value=ora_it)
                if st.form_submit_button("REGISTRA DATO"):
                    if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]):
                        st.success("Dato registrato!")
                        time.sleep(1)
                        st.rerun()

    df_q = load_data(URL_CARNE)
    if not df_q.empty:
        df_q.columns = ["Giorno", "Prodotto", "Quantita", "Ora"][:len(df_q.columns)]
        df_q["Quantita"] = pd.to_numeric(df_q["Quantita"], errors='coerce').fillna(0)
        
        # Calcolo variazioni (Ritmo)
        df_q = df_q.sort_values(["Giorno", "Prodotto", "Ora"])
        df_q["Variazione"] = df_q.groupby(["Giorno", "Prodotto"])["Quantita"].diff().fillna(df_q["Quantita"])
        df_q.loc[df_q["Variazione"] < 0, "Variazione"] = 0

        # --- GRAFICI DELLE GIORNATE ---
        st.subheader("🔍 Dettaglio Produzione Turni")
        giorni_attivi = [d for d in DATE_UFFICIALI if d in df_q["Giorno"].unique()]
        
        for g in giorni_attivi:
            df_g = df_q[df_q["Giorno"] == g]
            st.markdown(f"#### 📅 {g}")
            c1, c2 = st.columns(2)
            with c1:
                # Barre Totali del turno
                res = df_g.groupby("Prodotto")["Quantita"].max().reindex(PRODOTTI).fillna(0).reset_index()
                st.plotly_chart(px.bar(res, x="Prodotto", y="Quantita", color="Prodotto", text_auto=True,
                                     color_discrete_map=COLORI_CARNE, title="Pezzi Totali Turno", height=300), use_container_width=True, key=f"bar_{g}")
            with c2:
                # Linea del ritmo
                st.plotly_chart(px.line(df_g, x="Ora", y="Variazione", color="Prodotto", markers=True,
                                      color_discrete_map=COLORI_CARNE, title="Ritmo (Aggiunte)", height=300), use_container_width=True, key=f"line_{g}")
            st.divider()

        # --- TOTALE GENERALE SAGRA ---
        st.markdown("""<div style="background-color:#ff4b4b; padding:15px; border-radius:10px; margin:40px 0 20px 0;">
                    <h2 style="color:white; text-align:center; margin:0;">🏆 TOTALE GENERALE SAGRA</h2>
                    </div>""", unsafe_allow_html=True)
        
        df_max_day = df_q.groupby(["Giorno", "Prodotto"])["Quantita"].max().reset_index()
        df_tot_sagra = df_max_day.groupby("Prodotto")["Quantita"].sum().reindex(PRODOTTI).fillna(0).reset_index()
        st.plotly_chart(px.bar(df_tot_sagra, x="Prodotto", y="Quantita", color="Prodotto", text_auto=True,
                           color_discrete_map=COLORI_CARNE, height=450), use_container_width=True, key="totale_sagra")

    with col_de:
        with st.expander("🗑️ Gestione/Elimina Dati"):
            if not df_q.empty:
                for idx, row in df_q.sort_index(ascending=False).iterrows():
                    c_txt, c_btn = st.columns([7,3])
                    c_txt.caption(f"{row['Giorno']} - {row['Prodotto']}: {int(row['Quantita'])}pz")
                    if c_btn.button("Elimina", key=f"del_q_{idx}"):
                        if delete_row("Quantità Grigliate", idx): st.rerun()

# --- TAB 3: GESTIONE NOMI ---
with tab3:
    st.header("⚙️ Gestione Grigliatori")
    if not df_n.empty:
        for i, row in df_n.iterrows():
            if row.iloc[0]:
                cx, cy = st.columns([8,2])
                cx.write(row.iloc[0])
                if cy.button("Rimuovi", key=f"rm_n_{i}"):
                    if delete_row("ListaGrigliatori", i): st.rerun()
    
    nuovo = st.text_input("Aggiungi nuovo grigliatore")
    if st.button("Aggiungi"):
        if nuovo and save_data("ListaGrigliatori", [nuovo]): st.rerun()
