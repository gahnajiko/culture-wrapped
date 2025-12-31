import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Mon Dashboard Culturel")

# --- STYLE CSS (Le retour du Rose et des Croix Rouges) ---
st.markdown("""
    <style>
    /* Global */
    .main { background-color: #121212; color: white; }
    
    /* Bouton Explorer */
    .stButton>button {
        background-color: #ff69b4 !important;
        color: white !important;
        border-radius: 20px !important;
        border: none !important;
        padding: 10px 25px !important;
    }

    /* Fiches d'œuvres */
    .fiche-container {
        background-color: #1e1e1e;
        border-left: 6px solid #ff69b4;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        position: relative;
    }

    .fiche-title {
        color: #ff69b4 !important;
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        margin-bottom: 0px;
    }

    .fiche-date {
        color: #b0b0b0;
        font-size: 0.9rem;
        font-style: italic;
    }

    /* Croix Rouge et Épaisse */
    .close-cross {
        color: #ff0000;
        font-size: 30px;
        font-weight: 900;
        position: absolute;
        top: 10px;
        right: 20px;
        cursor: pointer;
    }

    /* Séparateurs */
    .tag-label { color: #ff69b4; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES ---
# Remplace par l'URL de ton Google Sheet (format CSV pour pandas)
SHEET_URL = "TON_URL_GOOGLE_SHEET_EXPORT_CSV"

@st.cache_data
def load_data():
    df = pd.read_csv(SHEET_URL)
    # Conversion de la date pour un tri propre
    df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
    # Tri chronologique inverse (Plus récent en haut)
    df = df.sort_values(by='date_dt', ascending=False)
    return df

try:
    df = load_data()

    # --- ENTÊTE ---
    col1, col2 = st.columns([1, 4])
    with col1:
        st.button("EXPLORER")
    with col2:
        st.write(f"### {len(df)} œuvres terminées")

    # --- FILTRES (Médias : Manga, Série, etc.) ---
    # Ici on s'assure que toutes les catégories s'affichent
    categories = ["All"] + sorted(df['media'].unique().tolist())
    selected_media = st.selectbox("Filtrer par média", categories)

    filtered_df = df if selected_media == "All" else df[df['media'] == selected_media]

    # --- GRAPHIQUES (Histogramme Rose & Mood) ---
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.write("### Progression")
        # Histogramme Rose et Fin
        stats_mois = filtered_df.groupby(filtered_df['date_dt'].dt.strftime('%Y-%m')).size()
        st.bar_chart(stats_mois, color="#ff69b4")

    with col_chart2:
        st.write("### Répartition Mood")
        # Répartition Mood (Données propres)
        mood_counts = filtered_df['mood'].value_counts()
        st.pie_chart(mood_counts)

    # --- AFFICHAGE DES FICHES ---
    st.write("---")
    for _, row in filtered_df.iterrows():
        # Séparation propre Genres et Tags
        genres = row['genre'] if pd.notna(row['genre']) else "Aucun"
        tags = row['tag'] if pd.notna(row['tag']) else "Aucun"
        
        st.markdown(f"""
            <div class="fiche-container">
                <div class="close-cross">×</div>
                <div class="fiche-title">{row['titre']}</div>
                <div class="fiche-date">Terminé le : {row['date']}</div>
                <div style="margin-top:10px;">
                    <span class="tag-label">Genres :</span> {genres} | 
                    <span class="tag-label">Tags :</span> {tags}
                </div>
            </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Erreur lors du chargement des données : {e}")

# --- LOGIQUE DE NAVIGATION (Classements) ---
st.sidebar.title("Navigation")
if st.sidebar.button("Top Cool"):
    st.query_params["filter"] = "Cool"
    # Ici, Streamlit va recharger avec le paramètre
