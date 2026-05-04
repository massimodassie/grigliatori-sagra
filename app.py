import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import urllib.parse
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

# URL Aggiornato con il tuo nuovo deployment
SCRIPT_URL = "https://script.google.com/macros/s/AKfycby7yJ-jjJYworKTL9w20Er0w_Av3U1xqUvLQi0oGlrYy70Sg1xK6BJysNGZIZlJ0DtM/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_MAGAZZINO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")
URL_LISTA_NOMI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=ListaGrigliatori"

DATE_SOGLIA = ["Sabato 09 maggio", "Sabato 10 maggio", "Domenica 10 maggio", "Venerdì 15 maggio", "Sabato 16 maggio", "Domenica 17 maggio", "Sabato 23 maggio", "Domenica 24 maggio"]
PRODOTTI_ORDINE = ["Costicine", "Salsicce", "Braciole"]
COLOR_MAP = {"Costicine": "#FF0000", "Salsicce": "#00BFFF", "Braciole": "#000000"}

# --- 2. FUNZIONI TECNICHE ---
def load_data(url):
    try:
        response = requests.get(f"{url}&nocache={time.time()}")
        if response.status_code == 200:
            import io
            df = pd.read_csv(io.StringIO(response.text))
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            df.columns = [str(c).strip() for c in df.columns]
            df = df.map(lambda x: str(x).strip() if pd.notnull(x) else x)
            return df
    except: pass
    return pd.DataFrame()

def save_data(sheet, data):
    try:
        requests.post(f"{SCRIPT_URL}?sheet={sheet}", data=json.dumps(data), timeout=10)
        return True
    except: return False

def delete_row(sheet, row_index):
    try:
        google_row = int(row_index) + 2
        url = f"{SCRIPT_URL}?sheet={urllib.parse.quote(sheet)}&deleteRow={google_row}"
        response = requests.get(url, timeout=15)
        return response.status_code == 200
    except: return False

def rename_grigliatore(vecchio_nome, nuovo_nome):
    try:
        url = f"{SCRIPT_URL}?renameOld={urllib.parse.quote(vecchio_nome)}&renameNew={urllib.parse.quote(nuovo_nome)}"
        response = requests.get(url, timeout=15)
        return response.status_code == 200
    except: return False

def create_ics(turno_nome, utente):
    date_map = {
        "Sabato 09 maggio": "20260509", "Sabato 10 maggio": "20260510", "Domenica 10 maggio": "20260510",
        "Venerdì 15 maggio": "20260515", "Sabato 16 maggio": "20260516", "Domenica 17 maggio": "20260517",
        "Sabato 23 maggio": "20260523", "Domenica 24 maggio": "20260524",
    }
    giorno_testo = turno_nome.split(" - ")[0]
    data_iso = date_map.get(giorno_testo, "20260501")
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Grigliatori Sagra//IT
BEGIN:VEVENT
SUMMARY:🔥 Turno Griglia: {turno_nome}
DTSTART;TZID=Europe/Rome:{data_iso}T090000
DTEND;TZID=Europe/Rome:{data_iso}T100000
DESCRIPTION:Promemoria per il tuo turno alla sagra: {turno_nome}
BEGIN:VALARM
TRIGGER:PT0M
ACTION:DISPLAY
DESCRIPTION:Sveglia Turno Griglia
END:VALARM
END:VEVENT
END:VCALENDAR"""
    return ics_content

# --- 3. CARICAMENTO NOMI ---
df_nomi = load_data(URL_LISTA_NOMI)
lista_grigliatori = sorted(df_nomi['Nome'].unique().tolist()) if not df_nomi.empty else ["Caricamento..."]

# --- 4. INTERFACCIA ---
st.title("🔥 Portale Grigliatori 2026")
tab1, tab2, tab3 = st.tabs(["👥 Presenze & Calendario", "🍖 Monitor Carne", "⚙️ Gestione Team"])

# --- TAB 1: PRESENZE ---
with tab1:
    user = st.selectbox("Chi sei?", lista_grigliatori)
    df_p = load_data(URL_PRESENZE)
    miei_turni = []
    if not df_p.empty and len(df_p.columns) >= 2:
        df_p.columns = ['Nome', 'Turno'] + list(df_p.columns[2:])
        miei_turni = df_p[df_p['Nome'] == user]['Turno'].tolist()
    
    turni_lista = ["Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Cena", "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"]
    
    st.subheader("Segna i tuoi turni")
    cols = st.columns(3)
    for i, t in enumerate(turni_lista):
        with cols[i%3]:
            is_on = (t in miei_turni)
            if st.toggle(t, value=is_on, key=f"t_{user}_{i}"):
                if not is_on:
                    if save_data("Presenze", [user, t]): st.rerun()

    if miei_turni:
        st.divider()
        st.subheader("📅 Calendario")
        c_cal = st.columns(2)
        for idx, turno in enumerate(miei_turni):
            with c_cal[idx % 2]:
                ics_data = create_ics(turno, user)
                st.download_button(label=f"⏰ Sveglia {turno}", data=ics_data, file_name=f"turno_{idx}.ics", mime="text/calendar", key=f"btn_ics_{idx}")

    st.divider()
    if not df_p.empty:
        st.subheader("📊 Stato Copertura & Team")
        df_count = df_p.drop_duplicates().copy()
        cp = st.columns(3)
        for i, t in enumerate(turni_lista):
            with cp[i%3]:
                presenti = df_count[df_count['Turno'] == t]['Nome'].unique()
                count = len(presenti)
                target = 5 if "Pranzo" in t else 6
                if count < target:
                    values, colors = [count, target - count], ["#FF0000", "#eeeeee"]
                elif count == target:
                    values, colors = [count], ["#2a9d8f"]
                else:
                    values, colors = [target, count - target], ["#2a9d8f", "#0000FF"]
                
                perc = int((count / target) * 100)
                fig = go.Figure(go.Pie(values=values, hole=0.6, marker_colors=colors, showlegend=False, textinfo='none'))
                fig.update_layout(title=f"<b>{t}</b>", height=220, margin=dict(t=40,b=0,l=0,r=0),
                                  annotations=[dict(text=f"{perc}%<br><span style='font-size:12px'>{count}/{target}</span>", x=0.5, y=0.5, font_size=18, showarrow=False)])
                st.plotly_chart(fig, use_container_width=True)
                if count > 0:
                    for nome in sorted(presenti): st.write(f"• {nome}")

# --- TAB 2: CARNE ---
with tab2:
    st.header("🍖 Monitoraggio Produzione")
    with st.expander("➕ Inserisci Nuova Quantità"):
        with st.form("carne_form"):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            f_data = c1.selectbox("Giorno", DATE_SOGLIA)
            f_tipo = c2.selectbox("Cibo", PRODOTTI_ORDINE)
            f_qta = c3.number_input("Kg", min_value=1)
            f_ora = c4.text_input("Ora", value=datetime.now().strftime("%H:%M"))
            if st.form_submit_button("Salva 📝"):
                if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]): 
                    st.success("Dato salvato!"); time.sleep(1); st.rerun()

    df_q = load_data(URL_MAGAZZINO)
    if not df_q.empty:
        df_q.columns = ['Giorno', 'Prodotto', 'Quantita', 'Ora'][:len(df_q.columns)]
        df_q['Quantita'] = pd.to_numeric(df_q['Quantita'], errors='coerce').fillna(0)
        for data_target in DATE_SOGLIA:
            df_giorno = df_q[df_q['Giorno'].str.contains(data_target, na=False, case=False)]
            if not df_giorno.empty:
                df_plot = df_giorno.groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
                if df_plot['Quantita'].sum() > 0:
                    fig = px.bar(df_plot, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True, title=f"Produzione: {data_target}", color_discrete_map=COLOR_MAP)
                    st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: GESTIONE TEAM ---
with tab3:
    st.header("⚙️ Gestione Elenco Grigliatori")
    
    with st.expander("➕ Aggiungi un nuovo grigliatore"):
        nuovo_nome = st.text_input("Nome e Cognome per inserimento")
        if st.button("Salva Nuovo"):
            if nuovo_nome and save_data("ListaGrigliatori", [nuovo_nome]):
                st.success("Aggiunto!"); time.sleep(1); st.rerun()
    
    with st.expander("📝 Modifica nome esistente (Senza perdere i turni)"):
        if not df_nomi.empty:
            vecchio = st.selectbox("Seleziona chi vuoi rinominare", lista_grigliatori)
            nuovo = st.text_input("Inserisci il nuovo nome corretto")
            if st.button("Aggiorna Nome Ovunque"):
                if vecchio and nuovo:
                    with st.spinner("Aggiornamento in corso..."):
                        if rename_grigliatore(vecchio, nuovo):
                            st.success(f"Perfetto! {vecchio} è ora {nuovo} in tutti i turni.")
                            time.sleep(1.5); st.rerun()
                else:
                    st.warning("Inserisci il nuovo nome!")

    with st.expander("🗑️ Rimuovi definitivamente un grigliatore"):
        if not df_nomi.empty:
            for idx, row in df_nomi.iterrows():
                col1, col2 = st.columns([8, 2])
                col1.write(row['Nome'])
                if col2.button("Elimina", key=f"del_grig_{idx}"):
                    if delete_row("ListaGrigliatori", idx): st.rerun()
