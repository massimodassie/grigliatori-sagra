import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import urllib.parse
from datetime import datetime, timedelta

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby7yJ-jjJYworKTL9w20Er0w_Av3U1xqUvLQi0oGlrYy70Sg1xK6BJysNGZIZlJ0DtM/exec"
SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"

URL_PRESENZE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presenze"
URL_MAGAZZINO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote("Quantità Grigliate")
URL_LISTA_NOMI = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=ListaGrigliatori"

# Date corrette e separate per le domeniche
DATE_SOGLIA = [
    "Sabato 09 maggio", 
    "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio", 
    "Sabato 16 maggio", 
    "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio", 
    "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
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
        "Sabato 09 maggio": "20260509", "Domenica 10 maggio": "20260510",
        "Venerdì 15 maggio": "20260515", "Sabato 16 maggio": "20260516", "Domenica 17 maggio": "20260517",
        "Sabato 23 maggio": "20260523", "Domenica 24 maggio": "20260524",
    }
    # Prende la data pulita (senza pranzo/cena) per l'ICS
    giorno_testo = turno_nome.split(" - ")[0]
    data_iso = date_map.get(giorno_testo, "20260501")
    ics_content = f"""BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Grigliatori Sagra//IT\nBEGIN:VEVENT\nSUMMARY:🔥 Turno Griglia: {turno_nome}\nDTSTART;TZID=Europe/Rome:{data_iso}T090000\nDTEND;TZID=Europe/Rome:{data_iso}T100000\nDESCRIPTION:Promemoria sagra: {turno_nome}\nBEGIN:VALARM\nTRIGGER:PT0M\nACTION:DISPLAY\nDESCRIPTION:Sveglia Turno Griglia\nEND:VALARM\nEND:VEVENT\nEND:VCALENDAR"""
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
    
    # Lista turni per la selezione (corrisponde alle nuove DATE_SOGLIA)
    turni_lista = [
        "Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena", 
        "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", "Domenica 17 maggio - Cena", 
        "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
    ]
    
    st.subheader("Segna i tuoi turni")
    cols = st.columns(3)
    for i, t in enumerate(turni_lista):
        with cols[i%3]:
            is_on = (t in miei_turni)
            state = st.toggle(t, value=is_on, key=f"t_{user}_{i}")
            if state != is_on:
                if state:
                    if save_data("Presenze", [user, t]): st.rerun()
                else:
                    # Funzione di cancellazione semplificata
                    match = df_p[(df_p['Nome'] == user) & (df_p['Turno'] == t)]
                    if not match.empty:
                        if delete_row("Presenze", match.index[0]): st.rerun()

    if miei_turni:
        st.divider()
        st.subheader("📅 Calendario")
        c_cal = st.columns(2)
        for idx, turno in enumerate(miei_turni):
            with c_cal[idx % 2]:
                ics_data = create_ics(turno, user)
                st.download_button(label=f"⏰ Sveglia {turno}", data=ics_data, file_name=f"turno_{idx}.ics", mime="text/calendar", key=f"btn_ics_{idx}")

# --- TAB 2: CARNE (CORREZIONE ORA E DATE) ---
with tab2:
    st.header("🍖 Monitoraggio Produzione")
    
    col_inserimento, col_eliminazione = st.columns(2)
    
    with col_inserimento:
        with st.expander("➕ Inserisci Quantità (da Monitor)"):
            # CORREZIONE ORA: Aggiungiamo 2 ore all'orario del server (UTC+2)
            ora_italiana = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
            
            with st.form("carne_form"):
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                f_data = c1.selectbox("Giorno / Turno", DATE_SOGLIA)
                f_tipo = c2.selectbox("Cibo", PRODOTTI_ORDINE)
                f_qta = c3.number_input("Totale Pezzi", min_value=0, step=1)
                f_ora = c4.text_input("Ora (HH:MM)", value=ora_italiana)
                if st.form_submit_button("Salva 📝"):
                    if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]): 
                        st.success("Dato salvato!"); time.sleep(1); st.rerun()

    df_q = load_data(URL_MAGAZZINO)
    
    with col_eliminazione:
        with st.expander("✏️ Gestisci / Elimina"):
            if not df_q.empty:
                nomi_colonne_standard = ['Giorno', 'Prodotto', 'Quantita', 'Ora']
                mappa_colonne = {df_q.columns[i]: nomi_colonne_standard[i] for i in range(min(len(df_q.columns), 4))}
                df_temp = df_q.rename(columns=mappa_colonne)
                
                for idx, row in df_temp.iterrows():
                    testo_riga = f"🗑️ {row['Giorno']} - {row['Prodotto']}: {int(float(row['Quantita']))} Pz ({row['Ora']})"
                    col_testo, col_cancella = st.columns([8, 2])
                    col_testo.write(testo_riga)
                    if col_cancella.button("Elimina", key=f"del_carne_{idx}"):
                        if delete_row("Quantità Grigliate", idx): st.rerun()

    if not df_q.empty:
        nomi_colonne_standard = ['Giorno', 'Prodotto', 'Quantita', 'Ora']
        mappa_colonne = {df_q.columns[i]: nomi_colonne_standard[i] for i in range(min(len(df_q.columns), 4))}
        df_q = df_q.rename(columns=mappa_colonne)
        df_q['Quantita'] = pd.to_numeric(df_q['Quantita'], errors='coerce').fillna(0)
        
        # Logica incrementale
        df_diff = df_q.copy().sort_values(['Giorno', 'Prodotto', 'Ora'])
        df_diff['Produzione_Effettiva'] = df_diff.groupby(['Giorno', 'Prodotto'])['Quantita'].diff().fillna(df_diff['Quantita'])
        df_diff.loc[df_diff['Produzione_Effettiva'] < 0, 'Produzione_Effettiva'] = 0

        # --- Riepilogo Generale ---
        st.markdown("""<div style="background-color: #ff4b4b; padding: 12px; border-radius: 5px; margin: 25px 0 15px 0;">
                        <h2 style="margin:0; color:#FFFFFF; text-align:center;">🏆 Totale Sagra (Somma di ogni turno)</h2>
                     </div>""", unsafe_allow_html=True)
        
        df_max_per_giorno = df_q.groupby(['Giorno', 'Prodotto'])['Quantita'].max().reset_index()
        df_sagra_totale = df_max_per_giorno.groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
        
        fig_tot = px.bar(df_sagra_totale, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True, 
                         color_discrete_map=COLOR_MAP)
        fig_tot.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_tot, use_container_width=True)

        st.divider()

        # --- Dettaglio Giornate ---
        for data_target in DATE_SOGLIA:
            df_giorno_monitor = df_q[df_q['Giorno'] == data_target]
            df_giorno_diff = df_diff[df_diff['Giorno'] == data_target]
            
            if not df_giorno_monitor.empty:
                st.markdown(f"### 📊 {data_target}")
                c1, c2 = st.columns(2)
                
                with c1:
                    df_bar = df_giorno_monitor.groupby('Prodotto')['Quantita'].max().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
                    fig_b = px.bar(df_bar, x='Prodotto', y='Quantita', color='Prodotto', text_auto=True, 
                                   title="Totale Pezzi raggiunti", color_discrete_map=COLOR_MAP)
                    st.plotly_chart(fig_b, use_container_width=True, key=f"b_{data_target}")
                
                with c2:
                    fig_l = px.line(df_giorno_diff.sort_values('Ora'), x='Ora', y='Produzione_Effettiva', color='Prodotto', markers=True, 
                                   title="Ritmo di produzione (incrementale)", color_discrete_map=COLOR_MAP)
                    st.plotly_chart(fig_l, use_container_width=True, key=f"l_{data_target}")

# --- TAB 3: GESTIONE TEAM ---
with tab3:
    st.header("⚙️ Gestione Team")
    with st.expander("➕ Aggiungi un nuovo grigliatore"):
        nuovo_nome = st.text_input("Nome e Cognome per inserimento")
        if st.button("Salva Nuovo"):
            if nuovo_nome and save_data("ListaGrigliatori", [nuovo_nome]):
                st.success("Aggiunto!"); time.sleep(1); st.rerun()
    with st.expander("📝 Modifica nome esistente"):
        if not df_nomi.empty:
            vecchio = st.selectbox("Seleziona chi vuoi rinominare", lista_grigliatori)
            nuovo = st.text_input("Inserisci il nuovo nome corretto")
            if st.button("Aggiorna Nome Ovunque"):
                if vecchio and nuovo:
                    if rename_grigliatore(vecchio, nuovo):
                        st.success("Aggiornato!"); time.sleep(1.5); st.rerun()
    with st.expander("🗑️ Rimuovi definitivamente"):
        if not df_nomi.empty:
            for idx, row in df_nomi.iterrows():
                col1, col2 = st.columns([8, 2])
                col1.write(row['Nome'])
                if col2.button("Elimina", key=f"del_grig_{idx}"):
                    if delete_row("ListaGrigliatori", idx): st.rerun()
