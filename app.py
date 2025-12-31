import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURATION ET STYLE
st.set_page_config(layout="wide", page_title="Rétrospective", page_icon="🧬")

st.markdown("""
<style>
    .stApp { background-color: #050505; color: white; }
    div[data-testid="stMetricValue"] {
        font-size: 3.5rem; color: #F58AFF; text-shadow: 0 0 15px rgba(245, 138, 255, 0.4);
    }
    .stButton > button {
        border-radius: 20px; font-weight: bold; border: 1px solid #F58AFF;
        background-color: #111; color: #fff; transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #F58AFF; color: #000; border-color: #fff;
    }
    .streamlit-expanderHeader {
        background-color: #111; border-left: 4px solid #F58AFF; color: #F9FCBB;
    }
</style>
""", unsafe_allow_html=True)

# 2. GESTION DE L'ÉTAT
if 'page' not in st.session_state: st.session_state.page = 'hub'
if 'selected_work' not in st.session_state: st.session_state.selected_work = None
if 'filters' not in st.session_state: st.session_state.filters = {}

def navigate_to(page, work_id=None):
    st.session_state.page = page
    if work_id is not None: st.session_state.selected_work = work_id
    st.rerun()

def set_filter(key, value):
    st.session_state.filters = {key: [value]}
    navigate_to('timeline')

# 3. CHARGEMENT SÉCURISÉ
@st.cache_data(ttl=600)
def get_data():
    sheet_id = "1-CXmo-ghJwOdFtXsBV-lUBcSQN60itiaMEaYUYfWnl8"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url)
        # Nettoyage des noms de colonnes (retire les espaces avant/après)
        df.columns = [c.strip() for c in df.columns]
        
        # Remplissage des vides pour éviter les plantages
        cols_txt = ['Nom', 'Média global', 'Média', 'Rank', 'Genres', 'Tags', 'Review']
        for c in cols_txt:
            if c in df.columns:
                df[c] = df[c].fillna("").astype(str)

        # Conversion Dates (Robuste)
        df['Début'] = pd.to_datetime(df['Début'], dayfirst=True, errors='coerce')
        df['Fin'] = pd.to_datetime(df['Fin'], dayfirst=True, errors='coerce')
        
        # Création colonne Mois pour le tri (YYYY-MM)
        df['Mois_Sort'] = df['Fin'].dt.to_period('M').astype(str)
        
        return df
    except Exception as e:
        st.error(f"Erreur technique : {e}")
        return pd.DataFrame()

df = get_data()

if df.empty:
    st.warning("En attente des données... Vérifiez l'ID du Sheet.")
    st.stop()

# ==========================================
# PAGE 1 : HUB
# ==========================================
if st.session_state.page == 'hub':
    st.title("RÉTROSPECTIVE CULTURELLE")
    st.markdown("---")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("ŒUVRES", len(df))
    # Mode() peut planter si vide, on sécurise
    top_media = df['Média global'].mode()[0] if not df.empty else "N/A"
    c2.metric("TEMPS FORT", top_media)
    c3.metric("COUPS DE ❤️", len(df[df['Rank'] == 'Coup de cœur']))
    
    st.markdown("###")
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if st.button("EXPLORER LA DATABASE 🚀", use_container_width=True):
            navigate_to('timeline')

# ==========================================
# PAGE 2 : TIMELINE
# ==========================================
elif st.session_state.page == 'timeline':
    with st.sidebar:
        st.header("FILTRES 🧬")
        if st.button("🏠 Retour Accueil"): navigate_to('hub')
        st.markdown("---")
        
        # Récupération des valeurs uniques propres
        all_medias = sorted([x for x in df['Média global'].unique() if x != ""])
        all_ranks = sorted([x for x in df['Rank'].unique() if x != ""])
        
        # Extraction complexe des genres uniques
        raw_genres = df['Genres'].dropna().str.split(',')
        all_genres = sorted(list(set([g.strip() for sub in raw_genres for g in sub if g.strip()])))

        media_f = st.multiselect("Média", all_medias, default=st.session_state.filters.get('media', []))
        rank_f = st.multiselect("Rank", all_ranks, default=st.session_state.filters.get('rank', []))
        genre_f = st.multiselect("Genres", all_genres, default=st.session_state.filters.get('genre', []))

    # Filtrage
    df_s = df.copy()
    if media_f: df_s = df_s[df_s['Média global'].isin(media_f)]
    if rank_f: df_s = df_s[df_s['Rank'].isin(rank_f)]
    if genre_f: df_s = df_s[df_s['Genres'].apply(lambda x: any(g in x for g in genre_f))]

    st.markdown("### STATISTIQUES")
    view = st.radio("Vue :", ["Global", "Détail"], horizontal=True)
    col_c = 'Média global' if view == "Global" else 'Média'
    
    # Graphique
    if not df_s.empty:
        fig = px.histogram(
            df_s.sort_values('Fin'), y="Mois_Sort", color=col_c, 
            orientation='h', text_auto=True, title="Volume Mensuel",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(paper_bgcolor="#050505", plot_bgcolor="#111", font_color="#fff")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée avec ces filtres.")

    st.markdown("### CHRONOLOGIE")
    # Tri par date décroissante
    for idx, row in df_s.sort_values('Fin', ascending=False).iterrows():
        label = f"{row['Média']} | {row['Nom']}  ({row['Rank']})"
        with st.expander(label):
            cols = st.columns([4, 1])
            with cols[0]:
                rev = row['Review']
                st.write(f"_{rev}_" if len(rev) > 3 else "Pas de review.")
            with cols[1]:
                if st.button("VOIR ➜", key=f"btn_{idx}"):
                    navigate_to('work', idx)

# ==========================================
# PAGE 3 : FICHE ŒUVRE
# ==========================================
elif st.session_state.page == 'work':
    if st.session_state.selected_work not in df.index:
        st.error("Œuvre introuvable.")
        if st.button("Retour"): navigate_to('timeline')
    else:
        item = df.loc[st.session_state.selected_work]
        
        if st.button("⬅ RETOUR LISTE"): navigate_to('timeline')
        
        st.title(item['Nom'])
        
        # Gestion date propre
        date_aff = item['Fin'].strftime('%d/%m/%Y') if pd.notnull(item['Fin']) else "?"
        st.markdown(f"### {item['Média']}  •  {item['Rank']}")
        st.caption(f"Terminé le : {date_aff}")
        
        st.markdown("---")
        st.info(item['Review'] if len(item['Review']) > 3 else "Aucune review.")
        
        st.markdown("### MÉTADONNÉES CLIQUABLES")
        c1, c2, c3 = st.columns(3)
        with c1: 
            if st.button(f"📂 {item['Média global']}", key="b_m"): set_filter('media', item['Média global'])
        with c2: 
            if st.button(f"⭐ {item['Rank']}", key="b_r"): set_filter('rank', item['Rank'])
        with c3:
            # Premier genre cliquable
            genres = [g.strip() for g in item['Genres'].split(',') if g.strip()]
            if genres:
                if st.button(f"🏷️ {genres[0]}", key="b_g"): set_filter('genre', genres[0])
