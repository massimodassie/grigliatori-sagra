import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
import io
import base64
from datetime import datetime

# ==========================================
# 🚀 PORTALE GRIGLIATORI 2026 - RELEASE 04.5
# ==========================================

st.set_page_config(page_title="Portale Grigliatori 2026", layout="wide", page_icon="🔥")

SHEET_ID = "1mNyNxsXuGODr9AVicYlH-cmGVjrrnlD3pJk2rajs-U8"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzMy80_9pusPTyIWhyCb7Vp-nm4aBkBr8MU259VV0HJvAUy_Y-dxnhqDhbUyaePEOzy/exec"
TARGET_PERSONE = 7 

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

# --- TAB 1: PRESENZE (BLINDATO) ---
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

# --- TAB 2: MONITOR CARNE (FULL R01 LOGIC) ---
with tabs[1]:
    st.subheader("🍖 Inserimento Pezzi Carne")
    with st.form("c_form_v2"):
        c_date, c_prod, c_qta, c_time = st.columns(4)
        f_d = c_date.selectbox("Turno", DATE_UFFICIALI)
        f_p = c_prod.selectbox("Tipo", PRODOTTI)
        f_q = c_qta.number_input("Pezzi", min_value=0, step=1)
        f_t = c_time.text_input("Ora (HH:MM)", value=datetime.now().strftime("%H:%M"))
        if st.form_submit_button("REGISTRA"):
            requests.post(SCRIPT_URL, data=json.dumps({"sheet": "Quantità Grigliate", "data": [f_d, f_p, f_q, f_t]}))
            st.success("Dato inserito!"); time.sleep(1); st.rerun()
    
    if not df_c.empty:
        df_c.columns = ["Data", "Prodotto", "Qta", "Ora"]
        df_c["Qta"] = pd.to_numeric(df_c["Qta"])
        
        st.write("---")
        st.subheader("📊 Analisi per Turno")
        for d in df_c["Data"].unique():
            with st.expander(f"Dettaglio: {d}", expanded=True):
                df_turno = df_c[df_c["Data"] == d]
                col_left, col_right = st.columns(2)
                
                with col_left:
                    # Grafico Totali Turno
                    fig_t = px.bar(df_turno.groupby("Prodotto")["Qta"].sum().reset_index(), 
                                   x="Prodotto", y="Qta", color="Prodotto", title="Totali Pezzi")
                    st.plotly_chart(fig_t, use_container_width=True, key=f"bar_{d}")
                
                with col_right:
                    # Grafico Andamento Turno (Spline)
                    fig_a = px.line(df_turno.sort_values("Ora"), x="Ora", y="Qta", color="Prodotto", 
                                    line_shape="spline", markers=True, title="Andamento Temporale")
                    st.plotly_chart(fig_a, use_container_width=True, key=f"line_{d}")

        st.write("---")
        st.subheader("📈 Riepilogo Generale Sagra")
        c_tot1, c_tot2 = st.columns(2)
        with c_tot1:
            st.write("**Pezzi Totali per Prodotto**")
            fig_glob = px.pie(df_c, values="Qta", names="Prodotto", hole=0.4)
            st.plotly_chart(fig_glob, use_container_width=True)
        with c_tot2:
            st.write("**Andamento Giornate**")
            fig_day = px.area(df_c.groupby(["Data", "Prodotto"])["Qta"].sum().reset_index(), 
                             x="Data", y="Qta", color="Prodotto", line_shape="spline", title="Volume Totale per Giorno")
            st.plotly_chart(fig_day, use_container_width=True)

# --- TAB 3, 4, 5 (INVARIATI E FUNZIONANTI) ---
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
            if cb.button("Elimina", key=f"del_{idx}"):
                requests.get(f"{SCRIPT_URL}?sheet=ListaGrigliatori&deleteRow={idx[0]+2}")
                st.rerun()

with tabs[4]:
    st.subheader("📜 Release Note")
    st.info("Release: **04.5**")
    st.markdown("- Inserimento Carne con **Ora manuale**.\n- Doppi grafici per turno (**Totale + Spline**).\n- Riepiloghi **Totali Sagra** a fondo pagina.")
