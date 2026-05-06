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

def delete_presenza(nome, turno):
    try:
        df_p = load_data(URL_PRESENZE)
        if not df_p.empty:
            df_p.columns = ['Nome', 'Turno'] + list(df_p.columns[2:])
            match = df_p[(df_p['Nome'] == nome) & (df_p['Turno'] == turno)]
            if not match.empty:
                idx = match.index[0]
                return delete_row("Presenze", idx)
    except: pass
    return False

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
                    if delete_presenza(user, t): st.rerun()

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
        st.subheader("📊 Stato Copertura Team")
        df_count = df_p.drop_duplicates().copy()
        
        last_date = ""
        for i, t in enumerate(turni_lista):
            current_date = t.split(" - ")[0]
            
            if current_date != last_date:
                st.markdown(f"""<div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 20px 0 10px 0; border-left: 5px solid #ff4b4b;">
                                <h3 style="margin:0; color:#31333F;">📅 {current_date}</h3>
                             </div>""", unsafe_allow_html=True)
                last_date = current_date

            col_graf, col_txt = st.columns([1, 1])
            
            presenti = df_count[df_count['Turno'] == t]['Nome'].unique()
            count = len(presenti)
            target = 5 if "Pranzo" in t else 6
            
            if count < target: values, colors = [count, target - count], ["#FF0000", "#eeeeee"]
            elif count == target: values, colors = [count], ["#2a9d8f"]
            else: values, colors = [target, count - target], ["#2a9d8f", "#0000FF"]
            
            perc = int((count / target) * 100)
            
            with col_graf:
                fig = go.Figure(go.Pie(values=values, hole=0.6, marker_colors=colors, showlegend=False, textinfo='none'))
                fig.update_layout(
                    title=f"<b>{t.split(' - ')[1]}</b>", 
                    height=180, 
                    margin=dict(t=30, b=10, l=10, r=10),
                    annotations=[dict(text=f"{perc}%<br><span style='font-size:11px'>{count}/{target}</span>", x=0.5, y=0.5, font_size=16, showarrow=False)]
                )
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{t.replace(' ', '_')}")
            
            with col_txt:
                st.markdown("<br>", unsafe_allow_html=True)
                if count > 0:
                    for nome in sorted(presenti): st.write(f"• {nome}")
                else: st.write("⚠️ *Nessuno ancora*")
            
            st.markdown("---")

# --- TAB 2: CARNE (AGGIORNATA CON DOPPIO GRAFICO) ---
with tab2:
    st.header("🍖 Monitoraggio Produzione")
    with st.expander("➕ Inserisci Nuova Quantità"):
        with st.form("carne_form"):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            f_data = c1.selectbox("Giorno", DATE_SOGLIA)
            f_tipo = c2.selectbox("Cibo", PRODOTTI_ORDINE)
            f_qta = c3.number_input("Kg", min_value=1)
            f_ora = c4.text_input("Ora (HH:MM)", value=datetime.now().strftime("%H:%M"))
            if st.form_submit_button("Salva 📝"):
                if save_data("Quantità Grigliate", [f_data, f_tipo, f_qta, f_ora]): 
                    st.success("Dato salvato!"); time.sleep(1); st.rerun()
    
    df_q = load_data(URL_MAGAZZINO)
    if not df_q.empty:
        df_q.columns = ['Giorno', 'Prodotto', 'Quantita', 'Ora'][:len(df_q.columns)]
        df_q['Quantita'] = pd.to_numeric(df_q['Quantita'], errors='coerce').fillna(0)
        
        # Puliamo le ore per assicurarci che siano ordinate temporalmente
        df_q['Ora'] = df_q['Ora'].astype(str).str.strip()
        
        for data_target in DATE_SOGLIA:
            df_giorno = df_q[df_q['Giorno'].str.contains(data_target, na=False, case=False)]
            
            if not df_giorno.empty:
                # Verifichiamo se c'è effettivamente della carne grigliata per questo giorno
                if df_giorno['Quantita'].sum() > 0:
                    st.markdown(f"""<div style="background-color: #31333F; padding: 10px; border-radius: 5px; margin: 30px 0 15px 0;">
                                    <h3 style="margin:0; color:#FFFFFF; text-align:center;">📊 Analisi Produzione: {data_target}</h3>
                                 </div>""", unsafe_allow_html=True)
                    
                    # Usiamo un layout a due colonne per mettere i grafici affiancati (se lo schermo è grande)
                    c_graf1, c_graf2 = st.columns(2)
                    
                    # GRAFICO 1: Quantità Totale (A Barre)
                    with c_graf1:
                        df_plot_tot = df_giorno.groupby('Prodotto')['Quantita'].sum().reindex(PRODOTTI_ORDINE).fillna(0).reset_index()
                        fig_tot = px.bar(
                            df_plot_tot, 
                            x='Prodotto', 
                            y='Quantita', 
                            color='Prodotto', 
                            text_auto=True, 
                            title="📦 Kg Totali Grigliati (Sera)", 
                            color_discrete_map=COLOR_MAP
                        )
                        fig_tot.update_layout(showlegend=False, height=350)
                        st.plotly_chart(fig_tot, use_container_width=True, key=f"carne_tot_{data_target.replace(' ', '_')}")
                    
                    # GRAFICO 2: Picchi di Lavoro (Linea Temporale)
                    with c_graf2:
                        # Ordiniamo per orario per avere un grafico sequenziale corretto
                        df_time = df_giorno.sort_values(by='Ora')
                        
                        # Creiamo un grafico a linee con pallini (markers) sui punti di inserimento
                        fig_line = px.line(
                            df_time, 
                            x='Ora', 
                            y='Quantita', 
                            color='Prodotto', 
                            markers=True, 
                            title="📈 Picchi di Lavoro (Produzione nel tempo)",
                            color_discrete_map=COLOR_MAP
                        )
                        fig_line.update_layout(
                            xaxis_title="Fascia Oraria", 
                            yaxis_title="Quantità (Kg)", 
                            height=350,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig_line, use_container_width=True, key=f"carne_time_{data_target.replace(' ', '_')}")

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
                    with st.spinner("Aggiornamento..."):
                        if rename_grigliatore(vecchio, nuovo):
                            st.success("Aggiornato!"); time.sleep(1.5); st.rerun()
    with st.expander("🗑️ Rimuovi definitivamente"):
        if not df_nomi.empty:
            for idx, row in df_nomi.iterrows():
                col1, col2 = st.columns([8, 2])
                col1.write(row['Nome'])
                if col2.button("Elimina", key=f"del_grig_{idx}"):
                    if delete_row("ListaGrigliatori", idx): st.rerun()
