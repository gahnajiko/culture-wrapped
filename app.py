import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(layout="wide", page_title="Rétrospective")

# ==========================================
# 2. MOTEUR DE DONNÉES (MODE "RIGIDE")
# ==========================================
@st.cache_data(ttl=60)
def load_data():
    sheet_id = "1-CXmo-ghJwOdFtXsBV-lUBcSQN60itiaMEaYUYfWnl8"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        # 1. Lecture
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns] # Nettoyage espaces
        
        # 2. Nettoyage des lignes vides
        df = df.dropna(subset=['Nom'])
        
        # 3. Préparation Export
        db_export = []
        stats = {
            "media": {}, 
            "rank": {"Parfait":0, "Coup de cœur":0, "Cool +":0, "Cool":0, "Sympa +":0, "Sympa":0, "Sans Rank":0}, 
            "genre": {}, 
            "tag": {}
        }
        histo_data = {}
        unique_medias = []
        
        # Mois
        MOIS_FR = {1:'JANVIER', 2:'FÉVRIER', 3:'MARS', 4:'AVRIL', 5:'MAI', 6:'JUIN', 7:'JUILLET', 8:'AOÛT', 9:'SEPTEMBRE', 10:'OCTOBRE', 11:'NOVEMBRE', 12:'DÉCEMBRE'}
        EXCLUS = ["SEPTEMBRE 2025", "OCTOBRE 2025"] # A adapter selon tes besoins

        for row in df.itertuples():
            # Mapping STRICT basé sur tes screenshots
            nom = str(getattr(row, 'Nom', ''))
            # Si le nom est vide ou bizarre, on saute
            if not nom or nom.lower() == 'nan': continue

            # Récupération Valeurs
            m_glob = str(getattr(row, 'Média_global', 'Autre')).strip()
            # Fallback si Média global est vide dans le sheet (cf tes screenshots #N/A)
            if m_glob == 'nan' or m_glob == '#N/A' or m_glob == '': m_glob = 'Autre'

            m_det = str(getattr(row, 'Média', m_glob)).strip()
            rank = str(getattr(row, 'Rank', 'Sans Rank')).strip()
            if rank == 'nan' or rank == '': rank = 'Sans Rank'

            # Dates
            d_debut = pd.to_datetime(getattr(row, 'Début', None), dayfirst=True, errors='coerce')
            d_fin = pd.to_datetime(getattr(row, 'Fin', None), dayfirst=True, errors='coerce')
            # Date de référence pour le tri
            ref_date = d_fin if pd.notnull(d_fin) else d_debut
            
            if pd.isnull(ref_date):
                m_lbl = "INCONNU"
                m_sort = 0
                d_aff = "?"
            else:
                m_lbl = f"{MOIS_FR.get(ref_date.month, '')} {ref_date.year}"
                m_sort = int(ref_date.strftime("%Y%m"))
                d_aff = ref_date.strftime("%d/%m")

            # Exclusion
            if m_lbl in EXCLUS: continue

            # Remplissage Stats
            stats["media"][m_glob] = stats["media"].get(m_glob, 0) + 1
            if m_det != m_glob: stats["media"][m_det] = stats["media"].get(m_det, 0) + 1
            
            stats["rank"][rank] = stats["rank"].get(rank, 0) + 1

            # Genres / Tags
            gs = [g.strip() for g in str(getattr(row, 'Genres', '')).split(',') if g.strip() and g.lower() != 'nan']
            for g in gs: stats["genre"][g] = stats["genre"].get(g, 0) + 1
            
            ts = [t.strip() for t in str(getattr(row, 'Tags', '')).split(',') if t.strip() and t.lower() != 'nan']
            for t in ts: stats["tag"][t] = stats["tag"].get(t, 0) + 1

            # Liste unique pour le menu filtre (pour lier sous-media a global)
            if not any(x['media'] == m_det for x in unique_medias):
                unique_medias.append({'media': m_det, 'global': m_glob})

            # Histo Data (Structure stricte pour JS)
            if m_sort > 0:
                if m_sort not in histo_data: 
                    histo_data[m_sort] = {"label": m_lbl, "total": 0, "sort": m_sort, "breakdown": {}}
                
                histo_data[m_sort]["total"] += 1
                histo_data[m_sort]["breakdown"][m_glob] = histo_data[m_sort]["breakdown"].get(m_glob, 0) + 1

            # Objet Final
            db_export.append({
                "id": str(row.Index),
                "nom": nom,
                "unique_key": nom.lower(),
                "global": m_glob,
                "media": m_det,
                "rank": rank,
                "genres": gs,
                "tags": ts,
                "mois_display": m_lbl,
                "sort_key": m_sort,
                "date_aff": d_aff,
                "date_full": ref_date.strftime("%d/%m/%Y") if pd.notnull(ref_date) else "?",
                "review": str(getattr(row, 'Review', '')).replace('\n', '<br>')
            })

        # Tri Final (Date décroissante)
        db_export = sorted(db_export, key=lambda x: (x['sort_key'], x['date_aff']), reverse=True)
        
        # Nettoyage des Ranks vides pour l'affichage
        stats["rank"] = {k:v for k,v in stats["rank"].items() if v > 0}

        return db_export, stats, histo_data, unique_medias

    except Exception as e:
        # En cas de crash total, on renvoie du vide pour pas que Streamlit explose
        print(f"CRITICAL ERROR: {e}")
        return [], {"media":{}, "rank":{}, "genre":{}, "tag":{}}, {}, []

DB_DATA, STATS_DATA, HISTO_DATA, MEDIAS_LIST = load_data()
GLOBALS_LIST = sorted(list(set(d['global'] for d in DB_DATA)))

# ==========================================
# 3. INTERFACE HTML/JS (CORRIGÉE)
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

    /* NAVIGATION */
    .nav {{ display: flex; justify-content: center; gap: 30px; padding: 25px; background: rgba(5,5,5,0.95); position: sticky; top: 0; z-index: 200; backdrop-filter: blur(10px); }}
    .nav-btn {{ background: transparent; border: none; color: #888; font-weight: 900; text-transform: uppercase; cursor: pointer; font-size: 0.9rem; letter-spacing: 2px; transition: 0.2s; }}
    .nav-btn:hover, .nav-btn.active {{ color: white; text-shadow: 0 0 10px var(--rose); transform: scale(1.05); }}

    /* PAGES */
    .page {{ display: none; min-height: 100vh; flex-direction: column; align-items: center; padding-bottom: 60px; width: 100%; }}
    .active-page {{ display: flex; }}

    /* HUB */
    .h-stat {{ font-size: 11rem; font-weight: 900; color: var(--rose); line-height: 1; text-shadow: 0 0 40px rgba(245, 138, 255, 0.25); margin: 20px 0; }}
    .btn-explore {{ margin-top: 30px; padding: 15px 50px; background: transparent; border: 2px solid var(--rose); color: var(--rose); border-radius: 50px; font-weight: 900; font-size: 1.2rem; cursor: pointer; transition: 0.2s; text-transform: uppercase; letter-spacing: 2px; }}
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

    /* DROPDOWNS */
    .dd-wrap {{ position: relative; display: inline-block; }}
    .dd-menu {{ display: none; position: absolute; background: #111; border: 1px solid var(--rose); border-radius: 10px; width: 220px; max-height: 300px; overflow-y: auto; z-index: 1000; top: 110%; left: 50%; transform: translateX(-50%); box-shadow: 0 10px 40px rgba(0,0,0,0.8); }}
    .dd-menu.show {{ display: block; }}
    .dd-item {{ padding: 10px; color: #aaa; font-size: 0.8rem; border-bottom: 1px solid #222; cursor: pointer; text-align: left; }}
    .dd-item:hover {{ background: #222; color: white; }}
    .dd-item.sel {{ color: var(--rose); font-weight: 900; }}
    .reset-x {{ color: #ff5555; font-weight: 900; cursor: pointer; margin-left: 8px; vertical-align: middle; }}

    /* TIMELINE */
    .tl-cont {{ width: 100%; max-width: 800px; }}
    .month-lbl {{ font-size: 3.5rem; font-weight: 900; color: transparent; -webkit-text-stroke: 1px var(--jaune); text-align: center; margin: 60px 0 30px 0; clear: both; width: 100%; }}
    .card {{ background: var(--card); border-left: 5px solid var(--rose); padding: 20px 25px; margin-bottom: 15px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; transition: 0.2s; box-shadow: 0 5px 15px rgba(0,0,0,0.3); }}
    .card:hover {{ transform: translateX(5px); background: #181818; box-shadow: 0 5px 25px rgba(245, 138, 255, 0.1); }}
    .c-tit {{ font-size: 1.3rem; font-weight: 700; color: white; margin-bottom: 5px; }}
    .c-rnk {{ border: 1px solid var(--rose); color: var(--rose); padding: 5px 10px; border-radius: 8px; font-size: 0.8rem; font-weight: 900; text-transform: uppercase; }}

    /* HISTOGRAMMES */
    .histo-sec {{ width: 100%; max-width: 850px; margin-top: 80px; border-top: 1px dashed #333; padding-top: 40px; }}
    .chart-box {{ height: 250px; display: flex; align-items: flex-end; justify-content: center; gap: 12px; margin-bottom: 50px; }}
    .c-col {{ flex: 1; background: rgba(255,255,255,0.05); border-radius: 4px; position: relative; display: flex; flex-direction: column-reverse; cursor: pointer; transition: 0.2s; }}
    .c-col:hover {{ filter: brightness(1.3); transform: scaleY(1.02); }}
    .c-seg {{ width: 100%; transition: 0.2s; border-bottom: 1px solid rgba(0,0,0,0.2); }}
    .c-val {{ position: absolute; top: -25px; left: 50%; transform: translateX(-50%); font-size: 0.75rem; color: var(--rose); font-weight: 900; }}
    .c-lbl {{ position: absolute; bottom: -35px; left: 50%; transform: translateX(-50%) rotate(-45deg); font-size: 0.7rem; color: #888; white-space: nowrap; font-weight: 700; }}

    /* HORIZONTAL CHART */
    .h-row {{ display: flex; align-items: center; margin-bottom: 12px; cursor: pointer; height: 28px; }}
    .h-txt {{ width: 140px; text-align: right; font-size: 0.8rem; color: #ccc; margin-right: 15px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .h-tr {{ flex: 1; height: 100%; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden; position: relative; display: flex; }}
    .h-seg {{ height: 100%; transition: 0.2s; position: relative; }}
    .h-num {{ width: 35px; text-align: left; font-size: 0.9rem; color: var(--rose); font-weight: 900; margin-left: 10px; }}

    /* WALLS */
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; width: 100%; max-width: 1000px; padding: 20px; }}
    .w-item {{ background: #111; border: 1px solid #333; padding: 30px; border-radius: 20px; text-align: center; cursor: pointer; transition: 0.3s; }}
    .w-item:hover {{ border-color: var(--rose); transform: translateY(-10px); }}
    .w-num {{ font-size: 4rem; font-weight: 900; color: var(--rose); line-height: 1; }}
    .w-lbl {{ color: var(--jaune); font-weight: 700; text-transform: uppercase; margin-top: 10px; letter-spacing: 1px; }}

    /* WORK PAGE */
    .w-view {{ width: 100%; max-width: 800px; padding: 40px 20px; }}
    .w-head {{ font-size: 3rem; font-weight: 900; color: var(--jaune); line-height: 1; text-transform: uppercase; margin-bottom: 10px; }}
    .w-rev {{ background: #fff; color: #000; padding: 30px; border-radius: 15px; margin: 30px 0; line-height: 1.6; font-size: 1.1rem; font-weight: 500; display: block; }}
    .w-rev.hidden {{ display: none; }}
    .tag {{ display: inline-block; padding: 6px 15px; border: 1px solid #333; border-radius: 20px; margin: 4px; font-size: 0.8rem; cursor: pointer; color: #aaa; }}
    .tag:hover {{ border-color: white; color: white; }}
    .alink {{ color: var(--rose); font-weight: 900; text-decoration: underline; cursor: pointer; }}
    
    /* DETAIL PAGE */
    .d-head {{ font-size: 3rem; font-weight: 900; color: var(--rose); text-transform: uppercase; margin-bottom: 20px; }}
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
            <div class="f-row" style="margin-top:10px;">
                <div id="dd-genre"></div>
                <div id="dd-tag"></div>
            </div>
        </div>

        <div id="tl-cont" class="tl-cont"></div>

        <div class="histo-sec">
            <div style="color:var(--jaune); font-weight:900; margin-bottom:20px; border-left:4px solid var(--rose); padding-left:10px;">VOLUME MENSUEL</div>
            <div id="chart-vol" class="chart-box"></div>
            <div style="color:var(--jaune); font-weight:900; margin:40px 0 20px 0; border-left:4px solid var(--rose); padding-left:10px;">TOP GENRES</div>
            <div id="chart-mood" style="width:100%;"></div>
        </div>
    </div>

    <div id="media" class="page"><h1 style="color:var(--rose)">MÉDIAS WALL</h1><div id="wall-media" class="grid"></div></div>
    <div id="rank" class="page"><h1 style="color:var(--rose)">CLASSEMENT</h1><div id="wall-rank" class="grid"></div></div>
    <div id="mood" class="page"><h1 style="color:var(--rose)">MOODS</h1><div id="wall-mood" class="grid"></div></div>
    
    <div id="work" class="page"></div>
    <div id="detail" class="page"></div>

    <script>
        const DATA = {json.dumps(DB_DATA)};
        const STATS = {json.dumps(STATS_DATA)};
        const HISTO = {json.dumps(HISTO_DATA)};
        const GLOBALS = {json.dumps(GLOBALS_LIST)};
        const MEDIAS = {json.dumps(MEDIAS_LIST)};
        const COLORS = {{"Jeu vidéo": "#29B6F6", "Livre": "#66BB6A", "Film": "#EF5350", "Série": "#AB47BC", "Manga": "#FDD835", "Anime": "#FFA726"}};
        const RANK_ORDER = ["Parfait", "Coup de cœur", "Cool +", "Cool", "Sympa +", "Sympa", "Sans Rank"];

        let activeGlobal = "All", activeMedia = "All", activeRank = "All", activeGenres = new Set(), activeTags = new Set(), activeSearch = "";

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
            if(id === 'media') renderWall('wall-media', STATS.media, 'media');
            if(id === 'rank') renderWall('wall-rank', STATS.rank, 'rank');
            if(id === 'mood') renderWall('wall-mood', {{...STATS.genre, ...STATS.tag}}, 'mood');
        }}

        function updateFilters() {{
            renderRow('row-glob', ['All', ...GLOBALS], activeGlobal, 'global');
            
            if(activeGlobal !== 'All') {{
                const subs = MEDIAS.filter(m => m.global === activeGlobal && m.media !== activeGlobal).map(m => m.media);
                if(subs.length > 0) {{
                    document.getElementById('row-med').style.display = 'flex';
                    renderRow('row-med', ['All', ...subs], activeMedia, 'media');
                }} else document.getElementById('row-med').style.display = 'none';
            }} else document.getElementById('row-med').style.display = 'none';

            renderRow('row-rnk', ['All', ...RANK_ORDER], activeRank, 'rank');
            renderDD('dd-genre', 'GENRES', activeGenres, Object.keys(STATS.genre));
            renderDD('dd-tag', 'TAGS', activeTags, Object.keys(STATS.tag));
            renderTimeline();
            renderHisto();
        }}

        function renderRow(id, items, activeVal, type) {{
            const el = document.getElementById(id);
            el.innerHTML = items.map(i => {{
                let c = getCount(type, i);
                if (c === 0 && i !== 'All') return '';
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

        function renderDD(id, lbl, set, keys) {{
            const el = document.getElementById(id);
            el.innerHTML = `<div class="dd-wrap">
                <button class="btn-f ${{set.size > 0 ? 'active' : ''}}" onclick="this.nextElementSibling.classList.toggle('show')">${{lbl}} ${{set.size > 0 ? '('+set.size+')' : ''}}</button>
                <div class="dd-menu">${{keys.sort().map(k => `<div class="dd-item ${{set.has(k) ? 'sel' : ''}}" onclick="toggleGT('${{lbl}}', '${{k.replace(/'/g, "\\\\'")}}')">${{k}}</div>`).join('')}}</div>
            </div>${{set.size > 0 ? `<span class="reset-x" onclick="clearGT('${{lbl}}')">✕</span>` : ''}}`;
        }}

        function toggleGT(type, val) {{ (type === 'GENRES' ? activeGenres : activeTags).has(val) ? (type === 'GENRES' ? activeGenres : activeTags).delete(val) : (type === 'GENRES' ? activeGenres : activeTags).add(val); updateFilters(); }}
        function clearGT(type) {{ (type === 'GENRES' ? activeGenres : activeTags).clear(); updateFilters(); }}

        function renderTimeline() {{
            const cont = document.getElementById('tl-cont');
            cont.innerHTML = "";
            const list = DATA.filter(d => {{
                if(activeGlobal !== 'All' && d.global !== activeGlobal) return false;
                if(activeMedia !== 'All' && d.media !== activeMedia) return false;
                if(activeRank !== 'All' && d.rank !== activeRank) return false;
                if(activeGenres.size > 0 && !d.genres.some(g => activeGenres.has(g))) return false;
                if(activeTags.size > 0 && !d.tags.some(t => activeTags.has(t))) return false;
                if(activeSearch && !d.nom.toLowerCase().includes(activeSearch)) return false;
                return true;
            }});
            
            if(list.length === 0) {{ cont.innerHTML = "<div style='color:#666; text-align:center; margin-top:50px;'>Aucun résultat</div>"; return; }}

            let lastM = "";
            list.forEach(d => {{
                if(d.mois_display !== lastM) {{ cont.innerHTML += `<div class="month-lbl">${{d.mois_display}}</div>`; lastM = d.mois_display; }}
                cont.innerHTML += `<div class="card" onclick="goToWork('${{d.unique_key}}')">
                    <div><div class="c-tit">${{d.nom}}</div><div style="color:#888; font-size:0.8rem; font-weight:700;">${{d.date_aff}}</div></div>
                    <div class="c-rnk">${{d.rank}}</div>
                </div>`;
            }});
        }}

        function renderHisto() {{
            const box = document.getElementById('chart-vol'); box.innerHTML = "";
            const hData = Object.values(HISTO).sort((a,b) => a.sort - b.sort);
            const max = Math.max(...hData.map(h => h.total));
            hData.forEach(h => {{
                let segs = Object.entries(h.breakdown).map(([m, c]) => {{
                    let col = COLORS[m] || '#555';
                    return `<div class="c-seg" style="height:${{(c/h.total)*100}}%; background:${{col}};"></div>`;
                }}).join('');
                box.innerHTML += `<div class="c-col" style="height:${{(h.total/max)*100}}%">${{segs}}<div class="c-lbl">${{h.label}}</div><div class="c-val">${{h.total}}</div></div>`;
            }});

            const moodBox = document.getElementById('chart-mood'); moodBox.innerHTML = "";
            Object.entries(STATS.genre).sort((a,b)=>b[1]-a[1]).slice(0, 10).forEach(([k,v]) => {{
                moodBox.innerHTML += `<div class="h-row" onclick="forceFilter('genre','${{k.replace(/'/g, "\\\\'")}}')">
                    <div class="h-txt">${{k}}</div>
                    <div class="h-tr"><div class="h-seg" style="width:${{(v/30)*100}}%; background:var(--rose);"></div></div>
                    <div class="h-num">${{v}}</div>
                </div>`;
            }});
        }}

        function renderWall(id, obj, type) {{
            document.getElementById(id).innerHTML = Object.entries(obj).sort((a,b)=>b[1]-a[1]).map(([k,v]) => `
                <div class="w-item" onclick="showDetailPage('${{type}}', '${{k.replace(/'/g, "\\\\'")}}')">
                    <div class="w-num">${{v}}</div><div class="w-lbl">${{k}}</div>
                </div>`).join('');
        }}

        // PAGE DÉTAIL DÉDIÉE (NOUVEAU)
        function showDetailPage(type, val) {{
            const subset = DATA.filter(d => {{
                if(type === 'media') return d.media === val || d.global === val;
                if(type === 'rank') return d.rank === val;
                if(type === 'mood') return d.genres.includes(val) || d.tags.includes(val);
                return false;
            }});
            
            document.getElementById('detail').innerHTML = `
                <div class="w-view">
                    <button class="nav-btn" onclick="nav('${{type === 'mood' ? 'mood' : (type === 'rank' ? 'rank' : 'media')}}')" style="margin-bottom:30px;">RETOUR</button>
                    <div class="d-head">${{val}} <span style="font-size:1.5rem; color:#666;">(${{subset.length}})</span></div>
                    <div id="sub-wall" class="grid" style="padding:0; margin-bottom:40px;"></div>
                    ${{subset.map(d => `<div class="card" onclick="goToWork('${{d.unique_key}}')"><div><div class="c-tit">${{d.nom}}</div><div style="color:#888;">${{d.date_aff}}</div></div><div class="c-rnk">${{d.rank}}</div></div>`).join('')}}
                </div>`;
            nav('detail');
        }}

        function goToWork(key) {{
            const d = DATA.find(x => x.unique_key === key);
            if(!d) return;
            let rev = d.review && d.review !== 'nan' ? `<div class="w-rev">${{d.review}}</div>` : "";
            document.getElementById('work').innerHTML = `
                <div class="w-view">
                    <button class="nav-btn" onclick="nav('timeline')" style="margin-bottom:40px;">RETOUR DATABASE</button>
                    <div class="w-head">${{d.nom}}</div>
                    <div class="w-meta">${{d.date_full}} • ${{d.rank}}</div>
                    ${{rev}}
                    <div style="margin-top:30px;">
                        ${{d.genres.map(g=>`<span class="tag" onclick="forceFilter('genre','${{g}}')">${{g}}</span>`).join('')}} ${{d.tags.map(t=>`<span class="tag" style="color:var(--rose); border-color:var(--rose);" onclick="forceFilter('tag','${{t}}')">${{t}}</span>`).join('')}}
                    </div>
                </div>`;
            nav('work');
        }}

        function forceFilter(type, val) {{
            activeGenres.clear(); activeTags.clear(); activeGlobal="All"; activeRank="All";
            if(type==='genre') activeGenres.add(val); else activeTags.add(val);
            nav('timeline');
        }}

        function handleSearch() {{ activeSearch = document.getElementById('search').value.toLowerCase(); document.getElementById('search-x').style.display = activeSearch ? 'block' : 'none'; renderTimeline(); }}
        function clearSearch() {{ document.getElementById('search').value = ""; activeSearch = ""; handleSearch(); }}

        window.onclick = (e) => {{ if(!e.target.matches('.btn-f')) document.querySelectorAll('.dd-menu').forEach(m => m.classList.remove('show')); }};
    </script>
</body>
</html>
"""

components.html(html_code, height=2000, scrolling=True)
