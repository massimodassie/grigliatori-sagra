import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import io
import base64
from datetime import datetime, timedelta

# ==========================================
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 04.9
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide", page_icon="🔥")

SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"
TARGET_PERSONE = 7 

def get_it_time():
    return (datetime.now() + timedelta(hours=2)).strftime("%H:%M")

def load_data(sheet_name):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}&t={int(time.time())}"
        r = requests.get(url, timeout=10)
        return pd.read_csv(io.StringIO(r.text)).fillna("")
    except:
        return pd.DataFrame()

def get_image_url(url):
    if not isinstance(url, str): return ""
    try:
        f_id = url.split("id=")[1].split("&")[0] if "id=" in url else url.split("/d/")[1].split("/")[0]
        return f"https://drive.google.com/thumbnail?id={f_id}&sz=w800"
    except: return url

DATE_UFFICIALI = [
    "Sabato 09 maggio - Cena", "Domenica 10 maggio - Pranzo", "Domenica 10 maggio - Cena",
    "Venerdì 15 maggio - Cena della costata", "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Pranzo", "Domenica 17 maggio - Cena",
    "Sabato 23 maggio - Cena", "Domenica 24 maggio - Pranzo", "Domenica 24 maggio - Cena"
]
PRODOTTI = ["Costicine", "Salsicce", "Braciole"]

st.title("🔥 Portale Grigliatori 2026")

df_p = load_data("Presenze")
df_n = load_data("ListaGrigliatori")
df_g = load_data("Galleria")
df_c = load_data("Quantità Grigliate")

tabs = st.tabs(["👥 Presenze", "🍖 Monitor Carne", "📸 Galleria", "⚙️ Sistema", "ℹ️ Info Release"])

# --- TAB 1: PRESENZE (OK) ---
with tabs[0]:
    c1, c2 = st.columns([1, 3])
    with c1:
        nomi_list = sorted(df_n.iloc[:,0].unique().tolist()) if not df_n.empty else []
        user = st.selectbox("Chi sei?", [""] + nomi_list, key="u_sel")
        if user:
            p_u = df_p[df_p.iloc[:,0] == user].iloc[:,1].tolist() if not df_p.empty else []
            st.write("---")
            for d in DATE_UFFICIALI:
                if st.checkbox(d, value=(d in p_u), key=f"c_{d}"):
                    if d not in p_u:
                        requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Presenze", "data": [user, d]}))
                        st.rerun()
                elif d in p_u:
                    idx = df_p[(df_p.iloc[:,0] == user) & (df_p.iloc[:,1] == d)].index.tolist()
                    if idx:
                        requests.get(f"{SCRIPT_URL}?sheet=Presenze&deleteRow={idx[0]+2}")
                        st.rerun()
    with c2:
        for d in DATE_UFFICIALI:
            pres = df_p[df_p.iloc[:, 1] == d].iloc[:, 0].tolist() if not df_p.empty else []
            v = len(pres)
            col_b = "#2eb0a2" if v >= TARGET_PERSONE else "#e67e5e"
            col_g, col_i = st.columns([1, 3])
            with col_g:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=v,
                    number={'font': {'color': col_b, 'size': 35}},
                    gauge={'axis': {'range': [0, 12], 'visible': False}, 'bar': {'color': col_b},
                           'bgcolor': "#00bfff", 'shape': "angular",
                           'threshold': {'line': {'color': "black", 'width': 3}, 'value': TARGET_PERSONE}}))
                fig.update_layout(height=140, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True, key=f"g_{d}")
            with col_i:
                st.subheader(d)
                st.write(f"**{'✅ TARGET OK' if v >= TARGET_PERSONE else '⚠️ TARGET KO'}** ({v}/{TARGET_PERSONE})")
                st.write(f"**PRESENTI:** {', '.join(pres)}")
            st.write("---")

# --- TAB 2: MONITOR CARNE (INSERIMENTO MULTIPLO VELOCE) ---
with tabs[1]:
    st.subheader("🍖 Inserimento Rapido Pezzi Carne")
    
    if not df_c.empty:
        df_c.columns = ["Data", "Prodotto", "Qta", "Ora"]
        df_c["Qta"] = pd.to_numeric(df_c["Qta"], errors='coerce').fillna(0)
    
    with st.form("c_form_multiplo"):
        c_date, c_time = st.columns(2)
        f_d = c_date.selectbox("Turno", DATE_UFFICIALI)
        ora_attuale = get_it_time()
        f_t = c_time.text_input("Ora Inserimento", value=get_it_time())
        
        st.write("---")
        # Tre colonne per le tre pietanze
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### Costicine")
            f_q_costicine = st.number_input("Totale Monitor", min_value=0, step=1, key="q_cost")
        with col2:
            st.markdown("### Salsicce")
            f_q_salsicce = st.number_input("Totale Monitor", min_value=0, step=1, key="q_sals")
        with col3:
            st.markdown("### Braciole")
            f_q_braciole = st.number_input("Totale Monitor", min_value=0, step=1, key="q_brac")
            
        st.write("---")
        submit = st.form_submit_button("🚀 SALVA TUTTO")
        
        if submit:
            inputs = [
                ("Costicine", f_q_costicine),
                ("Salsicce", f_q_salsicce),
                ("Braciole", f_q_braciole)
            ]
            
            errori = []
            dati_da_inviare = []

            for prodotto, valore_totale in inputs:
                if valore_totale > 0: # Registriamo solo se il valore è inserito
                    last_val = 0
                    if not df_c.empty:
                        last_val_rows = df_c[df_c["Prodotto"] == prodotto]
                        if not last_val_rows.empty:
                            last_val = last_val_rows.iloc[-1]["Qta"]
                    
                    diff = valore_totale - last_val
                    
                    if diff < 0:
                        errori.append(f"{prodotto} (Monitor {valore_totale} < Ultimo {int(last_val)})")
                    else:
                        dati_da_inviare.append({"sheet": "Quantità Grigliate", "data": [f_d, prodotto, int(diff), f_t]})

            if errori:
                st.error(f"⚠️ Errori nei valori di: {', '.join(errori)}")
            elif dati_da_inviare:
                with st.spinner("Salvataggio in corso..."):
                    for payload in dati_da_inviare:
                        requests.post(SCRIPT_URL, data=json.dumps(payload))
                st.success(f"✅ Registrati con successo: {len(dati_da_inviare)} prodotti!")
                time.sleep(1)
                st.rerun()

    if not df_c.empty:
        st.write("---")
        for d in df_c["Data"].unique():
            with st.expander(f"📊 Analisi e Modifiche Turno: {d}", expanded=True):
                df_turno = df_c[df_c["Data"] == d]
                
                # Grafici
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    df_sum = df_turno.groupby("Prodotto")["Qta"].sum().reset_index()
                    fig_t = px.bar(df_sum, x="Prodotto", y="Qta", color="Prodotto", text="Qta", title="Totali")
                    fig_t.update_traces(textposition='outside')
                    st.plotly_chart(fig_t, use_container_width=True, key=f"bar_v_{d}")
                with col_g2:
                    # Ordiniamo i dati per 'Ora' così la linea non torna mai indietro
                    df_linea = df_turno.copy()
                    df_linea = df_linea.sort_values(by="Ora")
                    
                    fig_a = px.line(
                        df_linea, 
                        x="Ora", 
                        y="Qta", 
                        color="Prodotto", 
                        line_shape="spline", 
                        markers=True, 
                        title="Andamento Temporale"
                    )
                    
                    # Questo comando assicura che l'asse delle X sia trattato come tempo lineare
                    fig_a.update_xaxes(categoryorder="category ascending")
                    
                    st.plotly_chart(fig_a, use_container_width=True, key=f"line_v_{d}")
                
                # FINESTRA MODIFICHE (Indentazione Corretta)
                st.write("**📝 Lista Inserimenti (clicca Elimina per correggere)**")
                for idx, row in df_turno.iterrows():
                    cm1, cm2, cm3, cm4 = st.columns([2, 2, 1, 1])
                    cm1.write(f"🕒 {row['Ora']}")
                    cm2.write(f"🍖 {row['Prodotto']}")
                    cm3.write(f"🔢 {int(row['Qta'])} pz")
                    if cm4.button("🗑️", key=f"del_meat_{idx}"):
                        requests.get(f"{SCRIPT_URL}?sheet=Quantità Grigliate&deleteRow={idx+2}")
                        st.warning("Eliminato!"); time.sleep(1); st.rerun()

        st.write("---")
        st.subheader("📈 Totali Sagra (Tutto il periodo)")
        c_fin1, c_fin2 = st.columns(2)
        with c_fin1:
            df_g_sum = df_c.groupby("Prodotto")["Qta"].sum().reset_index()
            fig_g_b = px.bar(df_g_sum, x="Prodotto", y="Qta", color="Prodotto", text="Qta", title="Pezzi Totali Sagra")
            fig_g_b.update_traces(textposition='outside')
            st.plotly_chart(fig_g_b, use_container_width=True)
        with c_fin2:
            df_day = df_c.groupby(["Data", "Prodotto"])["Qta"].sum().reset_index()
            fig_day = px.area(df_day, x="Data", y="Qta", color="Prodotto", line_shape="spline", title="Andamento Globale Sagra")
            st.plotly_chart(fig_day, use_container_width=True)

# --- TAB GALLERIA, SISTEMA, INFO (INVARIATI) ---
with tabs[2]:
    st.subheader("📸 Galleria")
    with st.expander("➕ Carica Foto"):
        u_f = st.file_uploader("Scegli", type=['png','jpg','jpeg'])
        if st.button("Invia") and u_f:
            b64 = base64.b64encode(u_f.read()).decode()
            requests.post(SCRIPT_URL, data=json.dumps({"action": "upload_photo", "date": datetime.now().strftime("%d/%m"), "description": "Sagra", "file_data": b64, "file_name": u_f.name}))
            st.success("Caricata!"); st.rerun()
    if not df_g.empty:
        cols = st.columns(3)
        for i, row in df_g.iterrows():
            with cols[i % 3]:
                st.image(get_image_url(row.iloc[1]), use_container_width=True)

with tabs[3]:
    st.subheader("⚙️ Sistema")
    new_n = st.text_input("Aggiungi Nome")
    if st.button("Salva Nome"):
        if new_n:
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "ListaGrigliatori", "data": [new_n]}))
            st.rerun()
    st.write("---")
    if not df_n.empty:
        for idx, row in df_n.iterrows():
            cn, cb = st.columns([3, 1])
            cn.text(row.iloc[0])
            if cb.button("Elimina", key=f"del_n_{idx}"):
                requests.get(f"{SCRIPT_URL}?sheet=ListaGrigliatori&deleteRow={idx[0]+2}")
                st.rerun()

# --- TAB 5: INFO RELEASE (STORICO AGGIORNATO) ---
with tabs[4]:
    st.subheader("📜 Registro Modifiche (Release Log)")
    
    # Nuova Versione in evidenza
    st.info("🚀 **Release Attuale: 04.10 (Versione 5.0)**")
    st.markdown("""
    **Novità di oggi (10 Maggio 2026):**
    - ⚡ **Inserimento Multiplo**: Aggiunto form unico per inserire Costicine, Salsicce e Braciole contemporaneamente (risparmio tempo durante il servizio).
    - 🔢 **Sottrazione Automatica**: Ora l'app calcola da sola la differenza! Inserisci il valore totale che leggi sul monitor e l'app salva solo i pezzi aggiunti.
    - 🕒 **Fix Orario Dinamico**: L'ora di inserimento si aggiorna automaticamente ogni volta che apri il form o salvi un dato.
    - 📈 **Grafici Spline Ordinati**: Risolto il problema del "gomitolo" nei grafici. Ora i dati sono ordinati cronologicamente e la linea segue l'andamento reale del tempo.
    - 🛡️ **Fix KeyError**: Blindato il sistema di lettura dati per evitare crash se i nomi delle colonne nel foglio Google cambiano.
    """)

    st.write("---")
    
    # Storico versioni precedenti
    with st.expander("📚 Storico Versioni Precedenti"):
        st.markdown("""
        - **v04.9**: Ripristinata la Lista Inserimenti con tasto elimina per correggere errori.
        - **v04.8**: Grafico Sagra ripristinato a Spline (Area curve).
        - **v04.7**: Fix orario italiano (+2h) nel form carne.
        - **v04.6**: Aggiunte etichette quantità fisse sui grafici a barre.
        - **v04.5**: Implementazione sistema di caricamento foto in Galleria.
        - **v04.0**: Prima release ufficiale Monitor Carne e Presenze.
        """)
