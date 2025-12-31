import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURATION INITIALE ---
st.set_page_config(layout="wide", page_title="Dashboard Culturel")

# CONFIGURATION DES TITRES (Modifiables ici)
TITRE_HISTO_MOIS = "Progression Mensuelle par Média"
TITRE_HISTO_RANK = "Distribution par Rank"
TITRE_HISTO_GENRE = "Répartition par Genres/Tags"
TITRE_HISTO_RANK_MOIS = "Évolution du Rank par Mois"

# URL DE TON SHEET (Conversion automatique en CSV)
SHEET_ID = "1-CXmo-ghJwOdFtXsBV-lUBcSQN60itiaMEaYUYfWnl8"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

@st.cache_data(ttl=60) # Rafraîchissement toutes les minutes
def load_data():
    df = pd.read_csv(URL)
    # Nettoyage des colonnes
    df.columns = [c.strip().lower() for c in df.columns]
    df['date_dt'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
    return df.sort_values(by='date_dt', ascending=False)

try:
    df = load_data()
except Exception as e:
    st.error(f"Erreur de connexion au Sheet : {e}")
    st.stop()

# --- CSS PERSONNALISÉ (Le Rose, les Croix, le Zebra) ---
st.markdown("""
<style>
    /* Zebra Striping très contrasté */
    [data-testid="stDataTable"] tr:nth-child(even) { background-color: #262626 !important; }
    [data-testid="stDataTable"] tr:nth-child(odd) { background-color: #0e0e0e !important; }

    /* Titre Œuvre Centré */
    .title-container { text-align: center; margin: 30px 0; }
    .title-main { color: #ff69b4; font-size: 2.8rem; font-weight: 900; text-transform: uppercase; }
    
    /* Rank à droite, même ligne que média */
    .meta-line { display: flex; justify-content: space-between; align-items: center; padding: 0 20px; }
    .rank-text { font-size: 130%; font-weight: bold; color: #ffcd56; }

    /* Bloc Review avec Margins */
    .review-box { 
        background-color: #4b0082; 
        padding: 25px; 
        border-radius: 15px; 
        margin: 20px; 
        color: #ffffff;
        font-size: 1.1rem;
        line-height: 1.6;
    }

    /* Croix Rouge Reset Filtre */
    .reset-btn { color: #ff0000; font-weight: 900; cursor: pointer; border: 1px solid #ff0000; padding: 2px 8px; border-radius: 5px; }

    /* Suppression de la croix parasite GitHub/Streamlit */
    button[title="View fullscreen"] { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- NAVIGATION ---
menu = ["Accueil", "Database", "Statistiques", "Médailles"]
page = st.sidebar.radio("Navigation", menu)

# --- FONCTION TOOLTIP INTELLIGENT ---
def smart_fig(fig):
    # Cache le tooltip si un seul segment (simple barre)
    fig.update_layout(hovermode="x unified" if len(fig.data) > 1 else False)
    fig.update_traces(hoverlabel=dict(bgcolor="rgba(255,255,255,0.9)", font_size=14))
    return fig

# --- PAGE : DATABASE ---
if page == "Database":
    st.title("🗂️ Database")
    
    col_g, col_t = st.columns(2)
    with col_g:
        all_genres = sorted(list(set([g.strip() for sub in df['genre'].dropna() for g in str(sub).split(',')])))
        sel_genres = st.multiselect("🏷️ Filtrer par Genres", all_genres)
        if sel_genres: st.markdown('<span class="reset-btn">✖ Reset</span>', unsafe_allow_html=True)
        
    with col_t:
        all_tags = sorted(list(set([t.strip() for sub in df['tag'].dropna() for t in str(sub).split(',')])))
        sel_tags = st.multiselect("🔖 Filtrer par Tags", all_tags)
        if sel_tags: st.markdown('<span class="reset-btn">✖ Reset</span>', unsafe_allow_html=True)

    # Filtrage logique
    dff = df.copy()
    if sel_genres: dff = dff[dff['genre'].apply(lambda x: any(g in str(x) for g in sel_genres))]
    if sel_tags: dff = dff[dff['tag'].apply(lambda x: any(t in str(x) for t in sel_tags))]

    st.dataframe(dff.drop(columns=['date_dt']), use_container_width=True)

    # Ajout du 3ème histogramme (Mois x Rank) ici aussi
    st.write(f"### {TITRE_HISTO_RANK_MOIS}")
    fig_db = px.bar(dff, x=dff['date_dt'].dt.strftime('%b %Y'), y="rank", color="media", barmode="group")
    st.plotly_chart(smart_fig(fig_db), use_container_width=True)

# --- PAGE : STATISTIQUES ---
elif page == "Statistiques":
    st.title("📊 Centre de Statistiques")
    
    # 1. Mois x Médias
    st.write(f"### {TITRE_HISTO_MOIS}")
    toggle_m = st.toggle("Empiler les médias (Mois)", value=False)
    fig1 = px.histogram(df, x=df['date_dt'].dt.strftime('%Y-%m'), color="media", barmode="group" if not toggle_m else "relative")
    st.plotly_chart(smart_fig(fig1), use_container_width=True)

    # 2. Rank x Médias
    st.write(f"### {TITRE_HISTO_RANK}")
    toggle_r = st.toggle("Empiler les médias (Rank)", value=True)
    fig2 = px.histogram(df, x="rank", color="media", barmode="stack" if toggle_r else "group")
    st.plotly_chart(smart_fig(fig2), use_container_width=True)

    # 3. Mois x Rank
    st.write(f"### {TITRE_HISTO_RANK_MOIS}")
    fig3 = px.scatter(df, x=df['date_dt'].dt.strftime('%Y-%m'), y="rank", color="media", size="rank")
    st.plotly_chart(smart_fig(fig3), use_container_width=True)

    # 4. Genres/Tags X Total
    st.write(f"### {TITRE_HISTO_GENRE}")
    is_tag = st.toggle("Switch Genres / Tags", value=False)
    col_target = 'tag' if is_tag else 'genre'
    flat_list = [item.strip() for sub in df[col_target].dropna() for item in str(sub).split(',')]
    count_df = pd.Series(flat_list).value_counts().reset_index()
    fig4 = px.bar(count_df, x='count', y='index', orientation='h', color_discrete_sequence=['#ff69b4'])
    st.plotly_chart(fig4, use_container_width=True)

# --- PAGE : MÉDAILLES ---
elif page == "Médailles":
    st.title("🏅 Système de Médailles")
    
    m_col1, m_col2, m_col3 = st.columns(3)
    
    badges = [
        {"nom": "Petit Joueur", "seuil": 10, "icon": "🥉"},
        {"nom": "Collectionneur", "seuil": 20, "icon": "🥈"},
        {"nom": "Maître Culturel", "seuil": 50, "icon": "🥇"}
    ]
    
    for i, b in enumerate(badges):
        with [m_col1, m_col2, m_col3][i]:
            progress = min(len(df) / b['seuil'], 1.0)
            unlocked = len(df) >= b['seuil']
            st.markdown(f"""
                <div style="background:{'#ff69b4' if unlocked else '#222'}; padding:30px; border-radius:20px; text-align:center; border: 2px solid #ff69b4;">
                    <h1 style="margin:0; font-size:4rem;">{b['icon'] if unlocked else '🔒'}</h1>
                    <h2 style="color:white;">{b['nom']}</h2>
                    <p style="color:white;">Palier : {b['seuil']} œuvres</p>
                    <p style="font-weight:bold;">{len(df)} / {b['seuil']}</p>
                </div>
            """, unsafe_allow_html=True)

# --- PAGE ACCUEIL / DÉTAIL ---
else:
    # On affiche la dernière oeuvre par défaut
    if not df.empty:
        item = df.iloc[0]
        
        # Titre centré
        st.markdown(f'<div class="title-container"><div class="title-main">{item["titre"]}</div></div>', unsafe_allow_html=True)
        
        # Ligne Média et Rank
        st.markdown(f"""
            <div class="meta-line">
                <span style="font-size:1.2rem;">🎬 MÉDIA : <b>{item['media']}</b></span>
                <span class="rank-text">⭐ RANK : {item['rank']}</span>
            </div>
        """, unsafe_allow_html=True)
        
        # Bloc Review avec Marges
        st.markdown(f'<div class="review-box">{item.get("review", "Pas de review.")}</div>', unsafe_allow_html=True)
        
        # Dates, Sessions et Tags en dehors
        sess = f", {item['sessions']} sessions" if pd.notna(item.get('sessions')) else ""
        st.write(f"📅 *Dates : {item['date']}{sess}*")
        st.write(f"🏷️ **Genres :** {item['genre']}  |  🔖 **Tags :** {item['tag']}")

        # Saisie de Review
        st.write("---")
        with st.expander("✍️ Modifier ou ajouter une review"):
            review_input = st.text_area("Ta review ici...", value=item.get('review', ''))
            if st.button("Enregistrer dans le Sheet"):
                st.info("Pour l'enregistrement, connecte un Google Apps Script à l'URL de ton Sheet.")
