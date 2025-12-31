import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURATION ET STYLE
st.set_page_config(layout="wide", page_title="Rétrospective", page_icon="🧬")

# CSS Néon pour forcer le look Dark
st.markdown("""
<style>
    .stApp { background-color: #050505; color: white; }
    
    /* Gros chiffres du Hub */
    div[data-testid="stMetricValue"] {
        font-size: 3.5rem; color: #F58AFF; text-shadow: 0 0 15px rgba(245, 138, 255, 0.4);
    }
    
    /* Boutons personnalisés */
    .stButton > button {
        border-radius: 20px; font-weight: bold; border: 1px solid #F58AFF;
        background-color: #111; color: #fff; transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #F58AFF; color: #000; border-color: #fff;
    }
    
    /* Expander (Cartes) */
    .streamlit-expanderHeader {
        background-color: #111; border-left: 4px solid #F58AFF; color: #F9FCBB;
    }
</style>
""", unsafe_allow_html=True)

# 2. GESTION DE L'ÉTAT (NAVIGATION)
if 'page' not in st.session_state: st.session_state.page = 'hub'
if 'selected_work' not in st.session_state: st.session_state.selected_work = None
if 'filters' not in st.session_state: st.session_state.filters = {}

def navigate_to(page, work_id=None):
    st.session_state.page = page
    if work_id: st.session_state.selected_work = work_id
    st.rerun()

def set_filter(key, value):
    # Réinitialise et applique un filtre spécifique (ex: clic sur un genre)
    st.session_state.filters = {key: [value]}
    navigate_to('timeline')

# 3. CHARGEMENT DES DONNÉES
@st.cache_data
def get_data():
    # ID public du Sheet (Lecture seule)
    sheet_id = "1-CXmo-ghJwOdFtXsBV-lUBcSQN60itiaMEaYUYfWnl8"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns] # Nettoyage noms colonnes
        # Conversion Dates
        df['Début'] = pd.to_datetime(df['Début'], dayfirst=True, errors='coerce')
        df['Fin'] = pd.to_datetime(df['Fin'], dayfirst=True, errors='coerce')
        # Colonne Mois pour les graphiques (YYYY-MM pour tri)
        df['Mois_Sort'] = df['Fin'].dt.to_period('M').astype(str)
        return df
    except:
        return pd.DataFrame()

df = get_data()

if df.empty:
    st.error("Impossible de charger les données. Vérifiez que le Sheet est public.")
    st.stop()

# ==========================================
# PAGE 1 : LE HUB (ACCUEIL)
# ==========================================
if st.session_state.page == 'hub':
    st.title("RÉTROSPECTIVE CULTURELLE")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("ŒUVRES", len(df))
    col2.metric("TEMPS FORT", df['Média global'].mode()[0])
    col3.metric("COUPS DE ❤️", len(df[df['Rank'] == 'Coup de cœur']))
    
    st.markdown("###")
    
    # Gros boutons de navigation
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("EXPLORER LA DATABASE 🚀", use_container_width=True):
            navigate_to('timeline')

# ==========================================
# PAGE 2 : TIMELINE (LISTE + GRAPHIQUES)
# ==========================================
elif st.session_state.page == 'timeline':
    with st.sidebar:
        st.header("FILTRES 🧬")
        if st.button("🏠 Retour Accueil"): navigate_to('hub')
        st.markdown("---")
        
        # Filtres dynamiques (connectés au session_state)
        default_media = st.session_state.filters.get('media', [])
        media_filter = st.multiselect("Média", df['Média global'].unique(), default=default_media)
        
        rank_filter = st.multiselect("Rank", df['Rank'].unique(), default=st.session_state.filters.get('rank', []))
        
        genre_options = sorted(list(set([x.strip() for sublist in df['Genres'].dropna().str.split(',') for x in sublist])))
        genre_filter = st.multiselect("Genres", genre_options, default=st.session_state.filters.get('genre', []))

    # Application des filtres
    df_show = df.copy()
    if media_filter: df_show = df_show[df_show['Média global'].isin(media_filter)]
    if rank_filter: df_show = df_show[df_show['Rank'].isin(rank_filter)]
    if genre_filter: df_show = df_show[df_show['Genres'].apply(lambda x: any(g in str(x) for g in genre_filter))]

    # --- SECTION GRAPHIQUES (Toggle) ---
    st.markdown("### STATISTIQUES")
    
    # Toggle pour changer la vue (Global vs Détail)
    view_mode = st.radio("Vue Histogramme :", ["Global", "Détail Média"], horizontal=True)
    color_col = 'Média global' if view_mode == "Global" else 'Média'
    
    # Graphique Horizontal Empilé (Plotly)
    fig = px.histogram(
        df_show.sort_values('Fin'), 
        y="Mois_Sort", # Y pour horizontal
        color=color_col, 
        orientation='h', # Horizontal
        text_auto=True, # Affiche les chiffres dans les barres
        color_discrete_sequence=px.colors.qualitative.Pastel,
        title="Volume Mensuel"
    )
    fig.update_layout(
        paper_bgcolor="#050505", plot_bgcolor="#111", font_color="#fff",
        bargap=0.2, xaxis_title="Nombre d'œuvres", yaxis_title="Mois"
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- LISTE DES ŒUVRES ---
    st.markdown("### CHRONOLOGIE")
    
    for idx, row in df_show.sort_values('Fin', ascending=False).iterrows():
        # Carte cliquable (simulation avec bouton dans l'expander)
        with st.expander(f"{row['Média']} | {row['Nom']}  ({row['Rank']})"):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.write(f"_{row['Review']}_" if pd.notnull(row['Review']) else "Pas de review.")
            with c2:
                # BOUTON POUR ALLER À LA PAGE DÉTAIL
                if st.button("VOIR LA FICHE ➜", key=f"btn_{idx}"):
                    navigate_to('work', idx)

# ==========================================
# PAGE 3 : FICHE ŒUVRE (DÉTAIL)
# ==========================================
elif st.session_state.page == 'work':
    # Récupération de l'œuvre
    idx = st.session_state.selected_work
    item = df.loc[idx]
    
    # Header navigation
    if st.button("⬅ RETOUR LISTE"): navigate_to('timeline')
    
    # Contenu Fiche
    st.title(item['Nom'])
    st.markdown(f"### {item['Média']}  •  {item['Rank']}")
    st.caption(f"Terminé le : {item['Fin'].strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    
    # Review
    st.info(item['Review'] if pd.notnull(item['Review']) else "Aucune review pour le moment.")
    
    st.markdown("### MÉTADONNÉES CLIQUABLES")
    
    # Boutons de "Cross-Filtering"
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("**Média**")
        if st.button(f"📂 {item['Média global']}", key="btn_media"):
            set_filter('media', item['Média global'])
            
    with c2:
        st.markdown("**Classement**")
        if st.button(f"⭐ {item['Rank']}", key="btn_rank"):
            set_filter('rank', item['Rank'])
            
    with c3:
        st.markdown("**Genres (Premier)**")
        # On prend le premier genre pour l'exemple de clic
        first_genre = str(item['Genres']).split(',')[0].strip()
        if st.button(f"🏷️ {first_genre}", key="btn_genre"):
            set_filter('genre', first_genre)
