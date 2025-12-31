import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. CONFIGURATION & STYLE (NÉON)
# ==========================================
st.set_page_config(layout="wide", page_title="Culture Dashboard", page_icon="🧬")

# CSS FORCE POUR ÉCRASER LE STYLE PAR DÉFAUT DE STREAMLIT
st.markdown("""
<style>
    /* FOND & TEXTE */
    [data-testid="stAppViewContainer"] { background-color: #050505; color: white; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    
    /* TEXTES */
    h1, h2, h3, p, div, span, label { color: white !important; font-family: 'Helvetica', sans-serif; }
    h1 { text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 10px #F58AFF; color: #F58AFF !important; }
    
    /* BOUTONS NAVIGATION (Sidebar) */
    section[data-testid="stSidebar"] button {
        width: 100%; border: 1px solid #333; background: #000; color: #aaa; text-align: left;
    }
    section[data-testid="stSidebar"] button:hover {
        border-color: #F58AFF; color: #F58AFF;
    }

    /* CARTES TIMELINE */
    div[data-testid="stExpander"] {
        background-color: #111; border: 1px solid #333; border-left: 5px solid #F58AFF;
        border-radius: 10px; margin-bottom: 10px;
    }
    .streamlit-expanderHeader p { font-size: 1.1rem; font-weight: bold; color: #F9FCBB !important; }

    /* TAGS */
    .badge {
        display: inline-block; padding: 4px 10px; border-radius: 15px;
        background: #222; border: 1px solid #444; color: #ccc; font-size: 0.75rem; margin: 2px;
    }

    /* METRICS (HUB) */
    [data-testid="stMetricValue"] {
        font-size: 4rem !important; color: #F58AFF !important; text-shadow: 0 0 20px rgba(245, 138, 255, 0.5);
    }
    [data-testid="stMetricLabel"] {
        font-size: 1rem !important; color: #F9FCBB !important; letter-spacing: 2px; text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CHARGEMENT & NETTOYAGE
# ==========================================
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1-CXmo-ghJwOdFtXsBV-lUBcSQN60itiaMEaYUYfWnl8"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns]
        
        # 1. Supprimer les lignes vides (CRITIQUE)
        df = df.dropna(subset=['Nom']) 
        df = df[df['Nom'].str.strip() != '']
        
        # 2. Remplir les manques
        cols_fill = {'Média global': 'Autre', 'Média': 'Autre', 'Rank': 'Sans Rank', 'Genres': '', 'Tags': ''}
        df = df.fillna(cols_fill)
        
        # 3. Dates
        df['Début'] = pd.to_datetime(df['Début'], dayfirst=True, errors='coerce')
        df['Fin'] = pd.to_datetime(df['Fin'], dayfirst=True, errors='coerce')
        df['Mois'] = df['Fin'].dt.strftime('%Y-%m') # Pour le tri graphiques
        
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.error("Erreur : Données vides ou inaccessibles.")
    st.stop()

# ==========================================
# 3. NAVIGATION (SIDEBAR)
# ==========================================
if 'nav' not in st.session_state: st.session_state.nav = 'Hub'

with st.sidebar:
    st.title("MENU ☰")
    if st.button("🏠 HUB / ACCUEIL"): st.session_state.nav = 'Hub'
    if st.button("📅 DATABASE & CHRONO"): st.session_state.nav = 'Timeline'
    if st.button("📂 MÉDIAS WALL"): st.session_state.nav = 'Media'
    if st.button("🏆 CLASSEMENT"): st.session_state.nav = 'Rank'
    if st.button("🎭 MOODS (GENRES)"): st.session_state.nav = 'Moods'
    
    st.divider()
    
    # FILTRES GLOBAUX (Actifs partout sauf Hub)
    if st.session_state.nav != 'Hub':
        st.header("FILTRES 🧬")
        search = st.text_input("Rechercher...", placeholder="Zelda, Matrix...")
        
        all_medias = sorted(df['Média global'].unique())
        f_media = st.multiselect("Média", all_medias)
        
        all_ranks = ["Parfait", "Coup de cœur", "Cool +", "Cool", "Sympa +", "Sympa", "Sans Rank"]
        f_rank = st.multiselect("Rank", all_ranks)
        
        # Extraction Tags/Genres pour listes
        all_tags = sorted(list(set([x.strip() for sub in df['Tags'].str.split(',') for x in sub if x.strip()])))
        f_tags = st.multiselect("Tags", all_tags)

        # Application filtres
        df_filtered = df.copy()
        if f_media: df_filtered = df_filtered[df_filtered['Média global'].isin(f_media)]
        if f_rank: df_filtered = df_filtered[df_filtered['Rank'].isin(f_rank)]
        if f_tags: df_filtered = df_filtered[df_filtered['Tags'].apply(lambda x: any(t in x for t in f_tags))]
        if search: df_filtered = df_filtered[df_filtered['Nom'].str.contains(search, case=False)]
    else:
        df_filtered = df.copy()

# ==========================================
# 4. PAGES
# ==========================================

# --- PAGE ACCUEIL ---
if st.session_state.nav == 'Hub':
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h3 style='text-align:center; color:#F9FCBB !important; letter-spacing:5px;'>RÉTROSPECTIVE</h3>", unsafe_allow_html=True)
        st.metric(label="ŒUVRES TERMINÉES", value=len(df))
    
    st.divider()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("JEUX VIDÉO", len(df[df['Média global'].str.contains('Jeu', case=False)]))
    c2.metric("LIVRES", len(df[df['Média global'].str.contains('Livre', case=False)]))
    c3.metric("FILMS/SÉRIES", len(df[df['Média global'].isin(['Film', 'Série'])]))

# --- PAGE TIMELINE (DATABASE) ---
elif st.session_state.nav == 'Timeline':
    st.title("CHRONOLOGIE & ANALYSE")
    
    # 1. GRAPHIQUE HISTORIQUE (Horizontal & Dark)
    if not df_filtered.empty:
        # Préparation données graphiques
        df_chart = df_filtered.copy()
        df_chart = df_chart.sort_values('Fin')
        
        fig = px.histogram(
            df_chart, y="Mois", x="Nom", color="Média global",
            orientation='h', # Horizontal
            color_discrete_sequence=['#F58AFF', '#29B6F6', '#F9FCBB', '#FF5555'],
            template="plotly_dark", # Thème sombre natif
            title="VOLUME D'ACTIVITÉ"
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Nombre d'œuvres",
            yaxis_title="Mois"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 2. LISTE DÉTAILLÉE
    st.subheader(f"LISTE ({len(df_filtered)})")
    
    for idx, row in df_filtered.sort_values('Fin', ascending=False).iterrows():
        # Construction Titre Carte
        date_str = row['Fin'].strftime('%d/%m') if pd.notnull(row['Fin']) else "?"
        titre_carte = f"{row['Média']} | {row['Nom']}  —  ⭐ {row['Rank']}"
        
        with st.expander(titre_carte):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"_{row['Review']}_" if str(row['Review']) != 'nan' else "Pas de review.")
                
                # Badges Tags/Genres
                tags = [t.strip() for t in str(row['Genres']).split(',') + str(row['Tags']).split(',') if t.strip()]
                badges_html = "".join([f'<span class="badge">{t}</span>' for t in tags])
                st.markdown(badges_html, unsafe_allow_html=True)
                
            with c2:
                st.caption(f"Terminé le : {row['Fin'].strftime('%d/%m/%Y')}")
                st.caption(f"Média Global : {row['Média global']}")

# --- PAGE MÉDIA WALL ---
elif st.session_state.nav == 'Media':
    st.title("MÉDIAS WALL")
    
    # Agrégation
    stats = df_filtered['Média global'].value_counts()
    
    # Affichage en grille
    cols = st.columns(4)
    for i, (media, count) in enumerate(stats.items()):
        with cols[i % 4]:
            st.markdown(f"""
            <div style="background:#111; border:1px solid #333; border-radius:10px; padding:20px; text-align:center; margin-bottom:10px;">
                <div style="font-size:3rem; color:#29B6F6; font-weight:bold;">{count}</div>
                <div style="color:#fff; text-transform:uppercase; letter-spacing:1px;">{media}</div>
            </div>
            """, unsafe_allow_html=True)
            
    # Graphique Camembert
    fig = px.pie(df_filtered, names='Média global', color_discrete_sequence=px.colors.qualitative.Pastel, template="plotly_dark")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

# --- PAGE RANKING ---
elif st.session_state.nav == 'Rank':
    st.title("CLASSEMENT")
    
    # Ordre spécifique
    rank_order = ["Parfait", "Coup de cœur", "Cool +", "Cool", "Sympa +", "Sympa", "Sans Rank"]
    stats = df_filtered['Rank'].value_counts().reindex(rank_order).fillna(0)
    
    cols = st.columns(4)
    for i, (rank, count) in enumerate(stats.items()):
        if count > 0: # On n'affiche pas les vides
            color = "#FDD835" if "Parfait" in rank else "#F58AFF" if "Coup" in rank else "#fff"
            with cols[i % 4]:
                st.markdown(f"""
                <div style="background:#111; border-left:4px solid {color}; border-radius:10px; padding:20px; text-align:center; margin-bottom:10px;">
                    <div style="font-size:3rem; color:{color}; font-weight:bold;">{int(count)}</div>
                    <div style="color:#fff;">{rank}</div>
                </div>
                """, unsafe_allow_html=True)

# --- PAGE MOODS ---
elif st.session_state.nav == 'Moods':
    st.title("GENRES & TAGS")
    
    # Calculs Genres
    all_genres = [g.strip() for sub in df_filtered['Genres'].str.split(',') for g in sub if g.strip()]
    genre_counts = pd.Series(all_genres).value_counts().head(20)
    
    st.subheader("TOP GENRES")
    fig_g = px.bar(x=genre_counts.values, y=genre_counts.index, orientation='h', template="plotly_dark", color_discrete_sequence=['#F58AFF'])
    fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)", yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_g, use_container_width=True)
