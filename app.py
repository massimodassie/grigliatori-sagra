import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import urllib.parse

# 1. --- CONFIGURAZIONE ---
st.set_page_config(page_title="Grigliatori Sagra", page_icon="🔥", layout="wide")

GRIGLIATORI = sorted([
    "Seleziona il tuo nome...",
    "Botteon Marco", "Da Ronch Loris", "Denis Boscaratto", "Flavio",
    "Francesco Perencin", "Francesco Disconzi", "Giacomo",
    "Gianluca Sossai", "Massimo Dassie", "Mauro Micieli",
    "Mirko Modolo Zanchetta", "Radu Apostol", "Riccardo Rossi"
])

TURNI = [
    "Venerdì 09 maggio - Cena", 
    "Domenica 10 maggio - Pranzo", 
    "Domenica 10 maggio - Cena", 
    "Venerdì 15 maggio - Cena della costata", 
    "Sabato 16 maggio - Cena", 
    "Domenica 17 maggio - Cena", 
    "Sabato 23 maggio - Cena", 
    "Domenica 24 maggio - Pranzo", 
    "Domenica 24 maggio - Cena"
]

DATA_FILE = "presenze_sagra.csv"
CONTATTI_FILE = "contatti_grigliatori.csv"

def load_data(file):
    if os.path.exists(file):
        try: return pd.read_csv(file)
        except: return pd.DataFrame()
    return pd.DataFrame()

def update_presence(nome, turno, chiave_toggle):
    stato = st.session_state[chiave_toggle]
    df = load_data(DATA_FILE)
    if df.empty: df = pd.DataFrame(columns=["Nome", "Turno"])
    df = df[~((df["Nome"] == nome) & (df["Turno"] == turno))]
    if stato:
        nuova_riga = pd.DataFrame({"Nome": [nome], "Turno": [turno]})
        df = pd.concat([df, nuova_riga], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

def save_phone(nome, numero):
    df_c = load_data(CONTATTI_FILE)
    if df_c.empty: df_c = pd.DataFrame(columns=["Nome", "Telefono"])
    df_c = df_c[df_c["Nome"] != nome]
    if numero:
        nuovo_contatto = pd.DataFrame({"Nome": [nome], "Telefono": [numero]})
        df_c = pd.concat([df_c, nuovo_contatto], ignore_index=True)
    df_c.to_csv(CONTATTI_FILE, index=False)
    st.toast(f"Numero di {nome} salvato!", icon="✅")

# 2. --- INTERFACCIA ---
st.title("🔥 Coordinamento Grigliatori")

tab_user, tab_admin = st.tabs(["📝 I Miei Turni", "📢 Promemoria WA"])

with tab_user:
    nome_sel = st.selectbox("Chi sei?", GRIGLIATORI, key="user_select")

    if nome_sel != "Seleziona il tuo nome...":
        df_c = load_data(CONTATTI_FILE)
        tel_attuale = ""
        if not df_c.empty and nome_sel in df_c["Nome"].values:
            tel_attuale = df_c[df_c["Nome"] == nome_sel]["Telefono"].iloc[0]
        
        col_tel, col_btn = st.columns([3, 1])
        with col_tel:
            nuovo_tel = st.text_input("Il tuo numero (per i promemoria):", value=str(tel_attuale), placeholder="3401234567")
        with col_btn:
            st.write(" ") # Spazio estetico
            if st.button("Salva Tel"):
                save_phone(nome_sel, nuovo_tel)

        df_presenze = load_data(DATA_FILE)
        turni_attivi = []
        if not df_presenze.empty:
            turni_attivi = df_presenze[df_presenze["Nome"] == nome_sel]["Turno"].tolist()
        
        st.divider()
        st.info("Tocca i turni per accenderli o spegnerli:")
        col1, col2, col3 = st.columns(3)
        for i, turno in enumerate(TURNI):
            target_col = [col1, col2, col3][i % 3]
            with target_col:
                chiave = f"tgl_{nome_sel}_{turno}"
                st.toggle(turno, value=(turno in turni_attivi), key=chiave,
                          on_change=update_presence, args=(nome_sel, turno, chiave))

with tab_admin:
    st.subheader("Lista Grigliatori per Turno")
    df_p = load_data(DATA_FILE)
    df_c = load_data(CONTATTI_FILE)
    
    turno_admin = st.selectbox("Seleziona turno da controllare:", TURNI)
    
    if not df_p.empty and turno_admin in df_p["Turno"].values:
        presenti = df_p[df_p["Turno"] == turno_admin]["Nome"].tolist()
        st.write(f"Ci sono **{len(presenti)}** grigliatori segnati:")
        for p in presenti:
            c_nome, c_link = st.columns([2, 1])
            num = ""
            if not df_c.empty and p in df_c["Nome"].values:
                num = df_c[df_c["Nome"] == p]["Telefono"].iloc[0]
            
            c_nome.write(f"• {p}")
            if num:
                msg = urllib.parse.quote(f"Ciao {p}! Ti ricordo il tuo turno in griglia per: {turno_admin}. A dopo! 🔥")
                c_link.markdown(f"[📲 Invia WA](https://wa.me/39{num}?text={msg})")
            else:
                c_link.caption("Senza numero")
    else:
        st.warning("Ancora nessuno segnato per questo turno.")

# 3. --- GRAFICI ---
st.divider()
st.subheader("📊 Stato Copertura")
df_vis = load_data(DATA_FILE)
cols = st.columns(3)
for i, turno in enumerate(TURNI):
    with cols[i % 3]:
        target = 5 if "Pranzo" in turno else 6
        count = len(df_vis[df_vis["Turno"] == turno]) if not df_vis.empty else 0
        colore = "green" if count >= target else "red"
        
        fig = go.Figure(data=[go.Pie(labels=['Presenti', 'Mancanti'], values=[count, max(0, target-count)],
                                    hole=.5, marker_colors=[colore, "#eeeeee"], textinfo='none', showlegend=False)])
        fig.update_layout(title=dict(text=f"<b>{turno}</b>", font=dict(size=13)),
                          margin=dict(t=30, b=0, l=0, r=0), height=180,
                          annotations=[dict(text=str(count), x=0.5, y=0.5, font_size=18, showarrow=False)])
        st.plotly_chart(fig, key=f"ch_{i}", use_container_width=True)