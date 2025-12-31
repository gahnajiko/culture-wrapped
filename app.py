import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(layout="wide", page_title="Rétrospective")

# ==========================================
# 2. MOTEUR DE DONNÉES (BLINDÉ)
# ==========================================
@st.cache_data(ttl=60)
def load_data():
    # Votre ID de Sheet
    sheet_id = "1-CXmo-ghJwOdFtXsBV-lUBcSQN60itiaMEaYUYfWnl8"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        # 1. Lecture
        df = pd.read_csv(url)
        
        # 2. Nettoyage agressif des noms de colonnes (supprime les espaces invisibles)
        df.columns = [c.strip() for c in df.columns]
        
        # 3. Mapping manuel des colonnes (Pour être sûr à 100%)
        # On cherche la colonne qui contient "Nom", "Média", etc. peu importe la casse
        def get_col(candidates):
            for col in df.columns:
                if col.lower() in [c.lower() for c in candidates]:
                    return col
            return None

        c_nom = get_col(['Nom', 'Name', 'Titre'])
        c_glob = get_col(['Média global', 'Media global', 'Global', 'Type'])
        c_det = get_col(['Média', 'Media', 'Support'])
        c_rank = get_col(['Rank', 'Note', 'Classement'])
        c_debut = get_col(['Début', 'Debut', 'Start'])
        c_fin = get_col(['Fin', 'End', 'Date'])
        c_rev = get_col(['Review', 'Avis'])
        c_genre = get_col(['Genres', 'Genre'])
        c_tag = get_col(['Tags', 'Tag'])

        # Si pas de nom, on arrête tout
        if not c_nom: return [], {}, {}

        # 4. Nettoyage des données vides
        df = df.dropna(subset=[c_nom])
        
        # 5. Préparation des variables de sortie
        db_export = []
        stats = {"media": {}, "rank": {}, "genre": {}, "tag": {}}
        histo_data = {}
        unique_medias = []
        
        MOIS_FR = {1:'JANVIER', 2:'FÉVRIER', 3:'MARS', 4:'AVRIL', 5:'MAI', 6:'JUIN', 7:'JUILLET', 8:'AOÛT', 9:'SEPTEMBRE', 10:'OCTOBRE', 11:'NOVEMBRE', 12:'DÉCEMBRE'}
        # Liste exacte des mois à exclure (Vérifiez l'orthographe dans votre Sheet)
        EXCLUS = ["SEPTEMBRE 2025", "OCTOBRE 2025"] 

        for row in df.itertuples():
            # Récupération sécurisée via le mapping
            nom = str(getattr(row, c_nom, ''))
            if not nom or nom.lower() == 'nan': continue
            
            # Gestion des Médias (Si vide => Autre)
            val_glob = str(getattr(row, c_glob, 'Autre')) if c_glob else 'Autre'
            if val_glob.lower() == 'nan' or val_glob.strip() == '': val_glob = 'Autre'
            
            val_det = str(getattr(row, c_det, val_glob)) if c_det else val_glob
            if val_det.lower() == 'nan' or val_det.strip() == '': val_det = val_glob

            # Gestion Rank
            val_rank = str(getattr(row, c_rank, 'Sans Rank')) if c_rank else 'Sans Rank'
            if val_rank.lower() in ['nan', '']: val_rank = 'Sans Rank'

            # Gestion Dates
            d_start = pd.to_datetime(getattr(row, c_debut, None), dayfirst=True, errors='coerce')
            d_end = pd.to_datetime(getattr(row, c_fin, None), dayfirst=True, errors='coerce')
            ref_date = d_end if pd.notnull(d_end) else d_start
            
            # Si pas de date, on met une date par défaut pour éviter le bug d'affichage
            date_aff = "?"
            m_nom = "INCONNU"
            m_sort = 0
            
            if pd.notnull(ref_date):
                date_aff = ref_date.strftime("%d/%m")
                m_nom = f"{MOIS_FR.get(ref_date.month, '')} {ref_date.year}"
                m_sort = int(ref_date.strftime("%Y%m"))

            # Exclusion
            if m_nom in EXCLUS: continue

            # Remplissage Stats
            stats["media"][val_glob] = stats["media"].get(val_glob, 0) + 1
            stats["rank"][val_rank] = stats["rank"].get(val_rank, 0) + 1
            
            # Genres & Tags
            gs = []
            if c_genre: gs = [g.strip() for g in str(getattr(row, c_genre, '')).split(',') if g.strip() and g.lower() != 'nan']
            for g in gs: stats["genre"][g] = stats["genre"].get(g, 0) + 1
            
            ts = []
            if c_tag: ts = [t.strip() for t in str(getattr(row, c_tag, '')).split(',') if t.strip() and t.lower() != 'nan']
            for t in ts: stats["tag"][t] = stats["tag"].get(t, 0) + 1

            # Mapping Media/Global pour le filtre
            if not any(x['media'] == val_det for x in unique_medias):
                unique_medias.append({'media': val_det, 'global': val_glob})

            # Remplissage Histo
            if m_sort > 0:
                if m_sort not in histo_data: histo_data[m_sort] = {"label": m_nom, "total": 0, "sort": m_sort, "breakdown": {}}
                histo_data[m_sort]["total"] += 1
                histo_data[m_sort]["breakdown"][val_glob] = histo_data[m_sort]["breakdown"].get(val_glob, 0) + 1

            # Export
            db_export.append({
                "id": str(row.Index),
                "nom": nom,
                "unique_key": nom.lower(),
                "global": val_glob,
                "media": val_det,
                "rank": val_rank,
                "genres": gs,
                "tags": ts,
                "mois_display": m_nom,
                "sort_key": m_sort, # CRUCIAL POUR LE TRI
                "date_aff": date_aff,
                "date_full": ref_date.strftime("%d/%m/%Y") if pd.notnull(ref_date) else "?",
                "review": str(getattr(row, c_rev, '')).replace('\n', '<br>') if c_rev else ""
            })

        # TRI ABSOLU PAR DATE (Pour éviter que Novembre apparaisse 2 fois)
        db_export = sorted(db_export, key=lambda x: (x['sort_key'], x['date_aff']), reverse=True)
        
        return db_export, stats, histo_data, unique_medias

    except Exception as e:
        print(f"Erreur Python: {e}")
        return [], {}, {}, []

DB_DATA, STATS_DATA, HISTO_DATA, MEDIAS_LIST = load_data()

# Liste globale unique triée
GLOBALS_LIST = sorted(list(stats_data["media"].keys())) if "media" in STATS_DATA else []

# ==========================================
# 3. INTERFACE (HTML/CSS/JS)
# ==========================================
html_code = f"""
<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;700;900&display=swap" rel="stylesheet">
<style>
    :root {{ --bg: #050505; --card: #111; --rose: #F58AFF; --jaune: #F9FCBB; --font: 'Outfit', sans-serif; }}
    body {{ background: var(--bg); color: white; font-family: var(--font); margin: 0; padding: 0; overflow-x: hidden; }}
    * {{ box-sizing: border-box; }}

    /* NAV */
    .nav {{ display: flex; justify-content: center; gap: 30px; padding: 25px; background: rgba(5,5,5,0.95); position: sticky; top: 0; z-index: 200; backdrop-filter: blur(10px); }}
    .nav-btn {{ background: transparent; border: none; color: #888; font-weight: 900; text-transform: uppercase; cursor: pointer; font-size: 0.9rem; letter-spacing: 2px; transition: 0.2s; }}
    .nav-btn:hover, .nav-btn.active {{ color: white; text-shadow: 0 0 10px var(--rose); transform: scale(1.05); }}

    /* PAGES */
    .page {{ display: none; min-height: 100vh; flex-direction: column; align-items: center; padding-bottom: 60px; width: 100%; }}
    .active-page {{ display: flex; }}

    /* HUB */
    .h-stat {{ font-size: 11rem; font-weight: 900; color: var(--rose); line-height: 1; text-shadow: 0 0 40px rgba(245, 138, 255, 0.25); margin: 20px 0; }}
    
    /* BOUTON EXPLORER (CORRIGÉ) */
    .btn-explore {{
        margin-top: 30px;
        padding: 15px 50px;
        background: transparent;
        border: 2px solid var(--rose);
        color: var(--rose);
        border-radius: 50px;
        font-weight: 900;
        font-size: 1.2rem;
        cursor: pointer;
        transition: 0.2s;
        text-transform: uppercase;
        letter-spacing: 2px;
    }}
    .btn-explore:hover {{ background: var(--rose); color: #000; box-shadow: 0 0 25px var(--rose); }}

    /* FILTERS */
    .filter-area {{ width: 100%; max-width: 900px; display: flex; flex-direction: column; align-items: center; gap: 12px; margin: 30px 0; }}
    .search-wrap {{ position: relative; width: 350px; margin-bottom: 10px; }}
    .search-in {{ width: 100%; background: #111; border: 1px solid #333; color: white; padding: 12px 40px; border-radius: 30px; text-align: center; font-weight: bold; outline: none; text-transform: uppercase; }}
    .search-in:focus {{ border-color: var(--rose); }}
    .search-x {{ position: absolute; right: 15px; top: 50%; transform: translateY(-50%); color: #ff5555; cursor: pointer; display: none; font-weight: 900; font-size: 1.2rem; }}
    
    .f-row {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; width: 100%; }}
    .btn-f {{ background: #151515; border: 1px solid #333; color: #777; padding: 6px 14px; border-radius: 20px; cursor: pointer; font-size: 0.75rem; font-weight: 700; transition: 0.2s; text-transform: uppercase; }}
    .btn-f:hover {{ color: white; border-color: #666; }}
    .btn-f.active {{ border-color: var(--rose); color: white; background: rgba(245, 138, 255, 0.15); }}

    /* TIMELINE (MOIS CLAIRS) */
    .tl-cont {{ width: 100%; max-width: 800px; }}
    .month-lbl {{ font-size: 3.5rem; font-weight: 900; color: transparent; -webkit-text-stroke: 1px var(--jaune); text-align: center; margin: 60px 0 30px 0; clear: both; width: 100%; }}
    
    .card {{ background: var(--card); border-left: 5px solid var(--rose); padding: 20px 25px; margin-bottom: 15px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; transition: 0.2s; box-shadow: 0 5px 15px rgba(0,0,0,0.3); }}
    .card:hover {{ transform: translateX(5px); background: #181818; box-shadow: 0 5px 25px rgba(245, 138, 255, 0.1); }}
    .c-tit {{ font-size: 1.3rem; font-weight: 700; color: white; margin-bottom: 5px; }}
    .c-rnk {{ border: 1px solid var(--rose); color: var(--rose); padding: 5px 10px; border-radius: 8px; font-size: 0.8rem; font-weight: 900; text-transform: uppercase; }}

    /* HISTOGRAMMES */
    .histo-sec {{ width: 100%; max-width: 850px; margin-top: 80px; border-top: 1px dashed #333; padding-top: 40px; }}
    .chart-box {{ height: 220px; display: flex; align-items: flex-end; justify-content: center; gap: 10px; margin-bottom: 50px; }}
    .c-col {{ flex: 1; background: rgba(255,255,255,0.05); border-radius: 4px; position: relative; display: flex; flex-direction: column-reverse; cursor: pointer; transition: 0.2s; }}
    .c-col:hover {{ filter: brightness(1.3); transform: scaleY(1.02); }}
    .c-seg {{ width: 100%; transition: 0.2s; border-bottom: 1px solid rgba(0,0,0,0.1); }}
    .c-val {{ position: absolute; top: -25px; left: 50%; transform: translateX(-50%); font-size: 0.75rem; color: var(--rose); font-weight: 900; }}
    .c-lbl {{ position: absolute; bottom: -35px; left: 50%; transform: translateX(-50%) rotate(-45deg); font-size: 0.7rem; color: #888; white-space: nowrap; font-weight: 700; }}

    /* WORK PAGE */
    .w-rev {{ background: #fff; color: #000; padding: 30px; border-radius: 15px; margin: 30px 0; line-height: 1.6; font-size: 1.1rem; font-weight: 500; display: block; }}
    .w-rev.hidden {{ display: none; }}
</style>
</head>
<body>

    <div class="nav">
        <button class="nav-btn active" onclick="nav('hub')">HOME</button>
        <button class="nav-btn" onclick="nav('timeline')">DATABASE</button>
        <button class="nav-btn" onclick="nav('media')">MÉDIAS</button>
        <button class="nav-btn" onclick="nav('rank')">CLASSEMENT</button>
        <button class="nav-btn" onclick="nav('mood')">MOODS</button>
    </div>

    <div id="hub" class="page active-page" style="justify-content:center;">
        <div style="letter-spacing:12px; color:var(--jaune); font-weight:900;">RÉTROSPECTIVE</div>
        <div class="h-stat" id="hub-count">0</div>
        <div style="letter-spacing:6px; color:#555; font-weight:900; margin-bottom:50px;">ŒUVRES TERMINÉES</div>
        <button class="btn-explore" onclick="nav('timeline')">EXPLORER LA DATABASE</button>
    </div>

    <div id="timeline" class="page">
        <div class="filter-area">
            <div class="search-wrap">
                <input type="text" id="search" class="search-in" placeholder="RECHERCHER..." oninput="handleSearch()">
                <span id="search-x" class="search-x" onclick="clearSearch()">✕</span>
            </div>
            <div id="row-glob" class="f-row"></div>
            <div id="row-med" class="f-row" style="display:none;"></div>
            <div id="row-rnk" class="f-row"></div>
        </div>

        <div id="tl-cont" class="tl-cont"></div>

        <div class="histo-sec">
            <div style="color:var(--jaune); font-weight:900; margin-bottom:20px; border-left:4px solid var(--rose); padding-left:10px;">VOLUME MENSUEL</div>
            <div id="chart-vol" class="chart-box"></div>
        </div>
    </div>

    <div id="media" class="page"><h1 style="color:var(--rose)">MÉDIAS WALL</h1><div id="wall-media" style="margin-top:20px;"></div></div>
    <div id="rank" class="page"><h1 style="color:var(--rose)">CLASSEMENT</h1><div id="wall-rank" style="margin-top:20px;"></div></div>
    <div id="mood" class="page"><h1 style="color:var(--rose)">MOODS</h1><div id="wall-mood" style="margin-top:20px;"></div></div>
    
    <div id="work" class="page"></div>

    <script>
        const DATA = {json.dumps(DB_DATA)};
        const STATS = {json.dumps(STATS_DATA)};
        const HISTO = {json.dumps(HISTO_DATA)};
        const GLOBALS = {json.dumps(GLOBALS_LIST)};
        const MEDIAS = {json.dumps(MEDIAS_LIST)};
        const COLORS = {{"Jeu vidéo": "#29B6F6", "Livre": "#66BB6A", "Film": "#EF5350", "Série": "#AB47BC", "Manga": "#FDD835"}};
        const RANKS = ["Parfait", "Coup de cœur", "Cool +", "Cool", "Sympa +", "Sympa", "Sans Rank"];

        let activeGlobal = "All", activeMedia = "All", activeRank = "All", activeSearch = "";

        // INIT
        document.getElementById('hub-count').innerText = DATA.length;

        function nav(id) {{
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active-page'));
            document.getElementById(id).classList.add('active-page');
            window.scrollTo(0,0);
            
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            [...document.querySelectorAll('.nav-btn')].forEach(b => {{
                if(b.innerText.toLowerCase().includes(id)) b.classList.add('active');
            }});

            if(id === 'timeline') updateFilters();
        }}

        function updateFilters() {{
            renderRow('row-glob', ['All', ...GLOBALS], activeGlobal, 'global');
            
            // Sous-médias dynamiques
            if(activeGlobal !== 'All') {{
                const subs = MEDIAS.filter(m => m.global === activeGlobal && m.media !== activeGlobal).map(m => m.media);
                if(subs.length > 0) {{
                    document.getElementById('row-med').style.display = 'flex';
                    renderRow('row-med', ['All', ...subs], activeMedia, 'media');
                }} else document.getElementById('row-med').style.display = 'none';
            }} else document.getElementById('row-med').style.display = 'none';

            renderRow('row-rnk', ['All', ...RANKS], activeRank, 'rank');
            renderTimeline();
            renderHisto();
        }}

        function renderRow(id, items, activeVal, type) {{
            const el = document.getElementById(id);
            el.innerHTML = items.map(i => {{
                let c = getCount(type, i);
                if (c === 0 && i !== 'All') return ''; // Cache si 0
                return `<button class="btn-f ${{i===activeVal?'active':''}}" onclick="setF('${{type}}', '${{i.replace(/'/g, "\\\\'") }}')">${{i}} (${{c}})</button>`;
            }}).join('');
        }}

        function getCount(type, val) {{
            return DATA.filter(d => {{
                if (val === 'All') return true;
                if (type === 'global') return d.global === val;
                if (type === 'media') return d.media === val;
                if (type === 'rank') return d.rank === val;
                return true;
            }}).length;
        }}

        function setF(type, val) {{
            if(type === 'global') {{ activeGlobal = val; activeMedia = 'All'; }}
            if(type === 'media') activeMedia = val;
            if(type === 'rank') activeRank = val;
            updateFilters();
        }}

        function renderTimeline() {{
            const cont = document.getElementById('tl-cont');
            cont.innerHTML = "";
            
            const list = DATA.filter(d => {{
                if(activeGlobal !== 'All' && d.global !== activeGlobal) return false;
                if(activeMedia !== 'All' && d.media !== activeMedia) return false;
                if(activeRank !== 'All' && d.rank !== activeRank) return false;
                if(activeSearch && !d.nom.toLowerCase().includes(activeSearch)) return false;
                return true;
            }});

            if(list.length === 0) {{ cont.innerHTML = "<div style='color:#666; text-align:center; margin-top:50px;'>Aucun résultat</div>"; return; }}

            let lastM = "";
            list.forEach(d => {{
                if(d.mois_display !== lastM) {{
                    cont.innerHTML += `<div class="month-lbl">${{d.mois_display}}</div>`;
                    lastM = d.mois_display;
                }}
                cont.innerHTML += `
                    <div class="card" onclick="goToWork('${{d.unique_key}}')">
                        <div>
                            <div class="c-tit">${{d.nom}}</div>
                            <div style="color:#888; font-size:0.8rem; font-weight:700;">${{d.date_aff}}</div>
                        </div>
                        <div class="c-rnk">${{d.rank}}</div>
                    </div>`;
            }});
        }}

        function renderHisto() {{
            const box = document.getElementById('chart-vol');
            box.innerHTML = "";
            const hData = Object.values(HISTO).sort((a,b) => a.sort - b.sort);
            const max = Math.max(...hData.map(h => h.total));
            
            hData.forEach(h => {{
                let segs = Object.entries(h.breakdown).map(([m, c]) => {{
                    let col = COLORS[m] || '#555';
                    return `<div class="c-seg" style="height:${{(c/h.total)*100}}%; background:${{col}};"></div>`;
                }}).join('');
                
                box.innerHTML += `
                    <div class="c-col" style="height:${{(h.total/max)*100}}%">
                        ${{segs}}
                        <div class="c-val">${{h.total}}</div>
                        <div class="c-lbl">${{h.label}}</div>
                    </div>`;
            }});
        }}

        // SEARCH
        function handleSearch() {{
            activeSearch = document.getElementById('search').value.toLowerCase();
            document.getElementById('search-x').style.display = activeSearch ? 'block' : 'none';
            renderTimeline();
        }}
        function clearSearch() {{
            document.getElementById('search').value = ""; activeSearch = "";
            document.getElementById('search-x').style.display = 'none';
            renderTimeline();
        }}

        // WORK PAGE
        function goToWork(key) {{
            const d = DATA.find(x => x.unique_key === key);
            if(!d) return;
            
            let hasRev = (d.review && d.review !== 'nan' && d.review.trim() !== "");
            
            document.getElementById('work').innerHTML = `
                <div style="width:100%; max-width:800px;">
                    <button class="nav-btn" onclick="nav('timeline')" style="margin-bottom:30px;">RETOUR</button>
                    <h1 style="color:var(--jaune); font-size:3rem; margin-bottom:10px;">${{d.nom}}</h1>
                    <div style="color:var(--rose); font-weight:900; margin-bottom:30px;">${{d.date_full}} • ${{d.rank}}</div>
                    
                    <div class="w-rev ${{hasRev ? '' : 'hidden'}}">${{d.review}}</div>
                    
                    <div style="margin-top:30px;">
                        ${{d.genres.map(g => `<span style="border:1px solid #333; padding:5px 15px; border-radius:20px; margin:5px; display:inline-block; color:#aaa;">${{g}}</span>`).join('')}}
                    </div>
                </div>`;
            nav('work');
        }}
    </script>
</body>
</html>
"""

components.html(html_code, height=2000, scrolling=True)
