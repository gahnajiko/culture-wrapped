import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# ==========================================
# 1. MOTEUR DE DONNÉES (PYTHON)
# ==========================================
st.set_page_config(layout="wide", page_title="Rétrospective Culturelle")

@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1-CXmo-ghJwOdFtXsBV-lUBcSQN60itiaMEaYUYfWnl8"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns]
        # Nettoyage des colonnes vides
        df = df.dropna(subset=['Nom'])
        df = df[df['Nom'].str.strip() != '']
        
        # Mapping intelligent des colonnes
        col_map = {
            'global': next((c for c in df.columns if 'global' in c.lower()), 'Média global'),
            'media': next((c for c in df.columns if 'média' in c.lower() and 'global' not in c.lower()), 'Média'),
            'rank': next((c for c in df.columns if 'rank' in c.lower()), 'Rank'),
        }
        
        # Traitement des dates et sessions
        df['Fin'] = pd.to_datetime(df['Fin'], dayfirst=True, errors='coerce')
        df['Début'] = pd.to_datetime(df['Début'], dayfirst=True, errors='coerce')
        
        return df, col_map
    except:
        return pd.DataFrame(), {}

df, cmap = load_data()

# Préparation du JSON pour le JavaScript
db_export = []
stats = {"media": {}, "rank": {}, "genre": {}, "tag": {}}
histo_data = {}
unique_medias = []

if not df.empty:
    MOIS_FR = {1:'Janvier', 2:'Février', 3:'Mars', 4:'Avril', 5:'Mai', 6:'Juin', 7:'Juillet', 8:'Août', 9:'Septembre', 10:'Octobre', 11:'Novembre', 12:'Décembre'}
    EXCLUS = ["Septembre 2025", "Octobre 2025"]

    for row in df.itertuples():
        # Extraction sécurisée
        nom = str(getattr(row, 'Nom', ''))
        m_glob = str(getattr(row, cmap['global'], 'Autre'))
        m_det = str(getattr(row, cmap['media'], m_glob))
        rank = str(getattr(row, cmap['rank'], 'Sans Rank'))
        
        # Nettoyage Rank (ne pas prendre le nom si vide)
        if rank.lower() in ['nan', '']: rank = "Sans Rank"
        
        gs = [x.strip() for x in str(getattr(row, 'Genres', '')).split(',') if x.strip() and x.lower() != 'nan']
        ts = [x.strip() for x in str(getattr(row, 'Tags', '')).split(',') if x.strip() and x.lower() != 'nan']
        
        fin = row.Fin if pd.notnull(row.Fin) else row.Début
        if pd.isnull(fin): continue
        
        m_nom = f"{MOIS_FR[fin.month]} {fin.year}"
        if m_nom in EXCLUS: continue # Exclusion propre

        # Remplissage stats
        stats["media"][m_glob] = stats["media"].get(m_glob, 0) + 1
        stats["rank"][rank] = stats["rank"].get(rank, 0) + 1
        for g in gs: stats["genre"][g] = stats["genre"].get(g, 0) + 1
        for t in ts: stats["tag"][t] = stats["tag"].get(t, 0) + 1
        
        if not any(x['media'] == m_det for x in unique_medias):
            unique_medias.append({'media': m_det, 'global': m_glob})

        # Histo Data
        m_sort = int(fin.strftime("%Y%m"))
        if m_sort not in histo_data: histo_data[m_sort] = {"label": m_nom, "total": 0, "breakdown": {}, "sort": m_sort}
        histo_data[m_sort]["total"] += 1
        histo_data[m_sort]["breakdown"][m_glob] = histo_data[m_sort]["breakdown"].get(m_glob, 0) + 1

        db_export.append({
            "id": str(row.Index), "nom": nom, "unique_key": nom.lower(),
            "global": m_glob, "media": m_det, "rank": rank,
            "genres": gs, "tags": ts, "mois_display": m_nom, "sort": m_sort,
            "date_aff": fin.strftime("%d/%m"), "date_full": fin.strftime("%d/%m/%Y"),
            "review": str(getattr(row, 'Review', '')).replace('\n', '<br>')
        })

# ==========================================
# 2. INTERFACE (HTML / CSS / JS)
# ==========================================
html_code = f"""
<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;700;900&display=swap" rel="stylesheet">
<style>
    :root {{ --bg: #050505; --card: #111; --rose: #F58AFF; --jaune: #F9FCBB; --font: 'Outfit', sans-serif; }}
    body {{ background: var(--bg); color: white; font-family: var(--font); margin: 0; padding: 0; }}
    
    /* NAV */
    .nav {{ display: flex; justify-content: center; gap: 30px; padding: 30px; position: sticky; top: 0; background: rgba(5,5,5,0.9); z-index: 100; }}
    .nav-btn {{ background: transparent; border: none; color: #666; font-weight: 900; text-transform: uppercase; cursor: pointer; letter-spacing: 2px; transition: 0.2s; }}
    .nav-btn:hover, .nav-btn.active {{ color: white; text-shadow: 0 0 10px var(--rose); }}

    .page {{ display: none; flex-direction: column; align-items: center; padding: 20px; }}
    .active-page {{ display: flex; }}

    /* HUB */
    .h-stat {{ font-size: 11rem; font-weight: 900; color: var(--rose); line-height: 1; text-shadow: 0 0 40px rgba(245, 138, 255, 0.2); }}

    /* FILTRES */
    .filter-area {{ width: 100%; max-width: 900px; display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 30px; }}
    .search-wrap {{ position: relative; width: 350px; }}
    .search-in {{ width: 100%; background: #111; border: 1px solid #333; color: white; padding: 12px 40px; border-radius: 30px; text-align: center; font-weight: bold; outline: none; }}
    .search-x {{ position: absolute; right: 15px; top: 50%; transform: translateY(-50%); color: #ff5555; cursor: pointer; display: none; font-weight: 900; }}
    .f-row {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }}
    .btn-f {{ background: #151515; border: 1px solid #333; color: #777; padding: 6px 14px; border-radius: 20px; cursor: pointer; font-size: 0.75rem; font-weight: 700; transition: 0.2s; }}
    .btn-f.active {{ border-color: var(--rose); color: white; background: rgba(245, 138, 255, 0.1); }}

    /* DROPDOWNS */
    .dd-wrap {{ position: relative; display: inline-block; }}
    .dd-menu {{ display: none; position: absolute; background: #111; border: 1px solid var(--rose); border-radius: 10px; width: 220px; max-height: 300px; overflow-y: auto; z-index: 1000; top: 110%; left: 50%; transform: translateX(-50%); }}
    .dd-menu.show {{ display: block; }}
    .dd-item {{ padding: 10px; color: #aaa; font-size: 0.8rem; border-bottom: 1px solid #222; cursor: pointer; text-align: left; }}
    .dd-item:hover {{ background: #222; color: white; }}
    .dd-item.sel {{ color: var(--rose); font-weight: 900; }}

    /* CARDS */
    .card {{ background: var(--card); border-left: 5px solid var(--rose); padding: 20px; margin-bottom: 15px; border-radius: 12px; width: 100%; max-width: 650px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; }}
    .card:hover {{ transform: translateX(5px); background: #181818; }}
    .c-rnk {{ border: 1px solid var(--rose); color: var(--rose); padding: 4px 10px; border-radius: 8px; font-weight: 900; font-size: 0.75rem; text-transform: uppercase; }}

    /* HISTOGRAMMES */
    .histo-sec {{ width: 100%; max-width: 850px; margin-top: 50px; border-top: 1px dashed #333; padding-top: 30px; }}
    .chart-box {{ height: 200px; display: flex; align-items: flex-end; justify-content: center; gap: 10px; margin-bottom: 50px; }}
    .c-col {{ flex: 1; background: rgba(255,255,255,0.05); border-radius: 4px; position: relative; display: flex; flex-direction: column-reverse; cursor: pointer; }}
    .c-seg {{ width: 100%; transition: 0.2s; }}
    .c-seg:hover {{ filter: brightness(1.4); }}
    .c-lbl {{ position: absolute; bottom: -30px; left: 50%; transform: translateX(-50%) rotate(-45deg); font-size: 0.65rem; color: #666; white-space: nowrap; }}
    
    /* GRID WALLS */
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; width: 100%; max-width: 1000px; }}
    .w-item {{ background: #111; border: 1px solid #333; padding: 30px; border-radius: 20px; text-align: center; cursor: pointer; transition: 0.3s; }}
    .w-item:hover {{ border-color: var(--rose); transform: translateY(-5px); }}
    .w-num {{ font-size: 4rem; font-weight: 900; color: var(--rose); }}
    .w-lbl {{ color: var(--jaune); font-weight: 700; text-transform: uppercase; margin-top: 10px; letter-spacing: 1px; }}

    /* WORK PAGE */
    .w-rev {{ background: white; color: black; padding: 30px; border-radius: 15px; margin: 20px 0; line-height: 1.6; }}
    .tag {{ display: inline-block; padding: 6px 15px; border: 1px solid #333; border-radius: 20px; margin: 4px; font-size: 0.8rem; cursor: pointer; }}
    .alink {{ color: var(--rose); font-weight: bold; text-decoration: underline; cursor: pointer; }}
</style>
</head>
<body>

    <div class="nav">
        <button class="nav-btn" onclick="nav('hub')">Home</button>
        <button class="nav-btn" onclick="nav('timeline')">Database</button>
        <button class="nav-btn" onclick="nav('media')">Médias</button>
        <button class="nav-btn" onclick="nav('rank')">Classement</button>
        <button class="nav-btn" onclick="nav('mood')">Moods</button>
    </div>

    <div id="hub" class="page active-page" style="justify-content:center;">
        <div style="letter-spacing:10px; color:var(--jaune); font-weight:700;">RÉTROSPECTIVE</div>
        <div class="h-stat">{len(db_export)}</div>
        <button class="h-btn" onclick="nav('timeline')">EXPLORER</button>
    </div>

    <div id="timeline" class="page">
        <div class="filter-area">
            <div class="search-wrap">
                <input type="text" id="search" class="search-in" placeholder="RECHERCHER..." oninput="handleSearch()">
                <span id="search-x" class="search-x" onclick="clearSearch()">✕</span>
            </div>
            <div id="row-glob" class="f-row"></div>
            <div id="row-med" class="f-row" style="display:none; margin-top:10px;"></div>
            <div id="row-rnk" class="f-row" style="margin-top:10px;"></div>
            <div class="f-row" style="margin-top:10px;">
                <div id="dd-genre"></div>
                <div id="dd-tag"></div>
            </div>
        </div>
        <div id="tl-cont" class="tl-cont"></div>
        <div class="histo-sec">
            <div style="color:var(--jaune); font-weight:900; margin-bottom:20px; border-left:4px solid var(--rose); padding-left:10px;">VOLUME MENSUEL</div>
            <div id="chart-vol" class="chart-box"></div>
            <div style="color:var(--jaune); font-weight:900; margin:40px 0 20px 0; border-left:4px solid var(--rose); padding-left:10px;">RÉPARTITION MOODS</div>
            <div id="chart-mood" style="width:100%;"></div>
        </div>
    </div>

    <div id="media" class="page"><h1>MÉDIAS WALL</h1><div id="wall-media" class="grid"></div></div>
    <div id="rank" class="page"><h1>CLASSEMENT</h1><div id="wall-rank" class="grid"></div></div>
    <div id="mood" class="page"><h1>MOODS</h1><div id="wall-mood" class="grid"></div></div>
    <div id="work" class="page"></div>

    <script>
        const DATA = {json.dumps(db_export)};
        const STATS = {json.dumps(stats)};
        const HISTO = {json.dumps(histo_data)};
        const MEDIAS = {json.dumps(unique_medias)};
        const COLORS = {{"Jeu vidéo": "#29B6F6", "Livre": "#66BB6A", "Film": "#EF5350", "Série": "#AB47BC", "Manga": "#FDD835", "Anime": "#FFA726"}};
        const RANK_ORDER = ["Parfait", "Coup de cœur", "Cool +", "Cool", "Sympa +", "Sympa", "Sans Rank"];

        let activeGlobal = "All", activeMedia = "All", activeRank = "All", activeGenres = new Set(), activeTags = new Set(), activeSearch = "";

        function nav(id) {{
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active-page'));
            document.getElementById(id).classList.add('active-page');
            window.scrollTo(0,0);
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            [...document.querySelectorAll('.nav-btn')].filter(b => b.innerText.toLowerCase() === id).forEach(b => b.classList.add('active'));
            if(id === 'timeline') update();
            if(id === 'media') renderWall('wall-media', STATS.media, 'media');
            if(id === 'rank') renderWall('wall-rank', STATS.rank, 'rank');
            if(id === 'mood') renderWall('wall-mood', {{...STATS.genre, ...STATS.tag}}, 'mood');
        }}

        function update() {{
            renderRow('row-glob', ['All', ...Object.keys(STATS.media).sort()], activeGlobal, 'global');
            if(activeGlobal !== 'All') {{
                const subs = MEDIAS.filter(m => m.global === activeGlobal).map(m => m.media);
                if(subs.length > 1) {{
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
                let count = DATA.filter(d => {{
                    if(i === 'All') return true;
                    return (type === 'global' ? d.global === i : (type === 'media' ? d.media === i : d.rank === i));
                }}).length;
                if(count === 0 && i !== 'All') return '';
                return `<button class="btn-f ${{i === activeVal ? 'active' : ''}}" onclick="setF('${{type}}', '${{i.replace(/'/g, "\\\\'")}}')">${{i}} (${{count}})</button>`;
            }}).join('');
        }}

        function setF(type, val) {{
            if(type === 'global') {{ activeGlobal = val; activeMedia = 'All'; }}
            if(type === 'media') activeMedia = val;
            if(type === 'rank') activeRank = val;
            update();
        }}

        function renderDD(id, lbl, set, keys) {{
            const el = document.getElementById(id);
            el.innerHTML = `
                <div class="dd-wrap">
                    <button class="btn-f ${{set.size > 0 ? 'active' : ''}}" onclick="this.nextElementSibling.classList.toggle('show')">${{lbl}} ${{set.size > 0 ? '('+set.size+')' : ''}}</button>
                    <div class="dd-menu">${{keys.sort().map(k => `<div class="dd-item ${{set.has(k) ? 'sel' : ''}}" onclick="toggleGT('${{lbl}}', '${{k.replace(/'/g, "\\\\'")}}')">${{k}}</div>`).join('')}}</div>
                </div>
                ${{set.size > 0 ? `<span class="reset-x" onclick="clearGT('${{lbl}}')">✕</span>` : ''}}`;
        }}

        function toggleGT(type, val) {{
            const set = (type === 'GENRES' ? activeGenres : activeTags);
            set.has(val) ? set.delete(val) : set.add(val);
            update();
        }}

        function clearGT(type) {{ (type === 'GENRES' ? activeGenres : activeTags).clear(); update(); }}

        function renderTimeline() {{
            const cont = document.getElementById('tl-cont');
            cont.innerHTML = "";
            const filtered = DATA.filter(d => {{
                if(activeGlobal !== 'All' && d.global !== activeGlobal) return false;
                if(activeMedia !== 'All' && d.media !== activeMedia) return false;
                if(activeRank !== 'All' && d.rank !== activeRank) return false;
                if(activeGenres.size > 0 && !d.genres.some(g => activeGenres.has(g))) return false;
                if(activeTags.size > 0 && !d.tags.some(t => activeTags.has(t))) return false;
                if(activeSearch && !d.nom.toLowerCase().includes(activeSearch)) return false;
                return true;
            }});
            
            let lastM = "";
            filtered.forEach(d => {{
                if(d.mois_display !== lastM) {{ cont.innerHTML += `<div class="month-lbl">${{d.mois_display}}</div>`; lastM = d.mois_display; }}
                cont.innerHTML += `<div class="card" onclick="goToWork('${{d.unique_key}}')">
                    <div><div class="c-tit">${{d.nom}}</div><div class="c-sub">${{d.date_aff}}</div></div>
                    <div class="c-rnk">${{d.rank}}</div>
                </div>`;
            }});
        }}

        function renderHisto() {{
            const box = document.getElementById('chart-vol'); box.innerHTML = "";
            const hData = Object.values(HISTO).sort((a,b) => a.sort - b.sort);
            const max = Math.max(...hData.map(h => h.total));
            hData.forEach(h => {{
                let segs = Object.entries(h.breakdown).map(([med, cnt]) => `<div class="c-seg" style="height:${{(cnt/h.total)*100}}%; background:${{COLORS[med]||'#555'}}"></div>`).join('');
                box.innerHTML += `<div class="c-col" style="height:${{(h.total/max)*100}}%">${{segs}}<div class="c-lbl">${{h.label}}</div></div>`;
            }});

            const moodBox = document.getElementById('chart-mood'); moodBox.innerHTML = "";
            Object.entries(STATS.genre).sort((a,b)=>b[1]-a[1]).slice(0, 8).forEach(([k,v]) => {{
                moodBox.innerHTML += `<div class="h-row" onclick="jumpMood('${{k}}')"><div class="h-txt">${{k}}</div><div class="h-tr"><div class="h-fill" style="width:${{(v/30)*100}}%"></div></div><div class="h-num">${{v}}</div></div>`;
            }});
        }}

        function jumpMood(v) {{ activeGenres.clear(); activeGenres.add(v); nav('timeline'); }}

        function renderWall(id, obj, type) {{
            document.getElementById(id).innerHTML = Object.entries(obj).sort((a,b)=>b[1]-a[1]).map(([k,v]) => `
                <div class="w-item" onclick="jumpWall('${{type}}', '${{k.replace(/'/g, "\\\\'")}}')">
                    <div class="w-num">${{v}}</div><div class="w-lbl">${{k}}</div>
                </div>`).join('');
        }}

        function jumpWall(type, val) {{
            activeGlobal = "All"; activeMedia = "All"; activeRank = "All"; activeGenres.clear(); activeTags.clear();
            if(type === 'media') {{ if(STATS.media[val]) activeGlobal = val; else {{ let m = MEDIAS.find(x=>x.media===val); activeGlobal=m.global; activeMedia=val; }} }}
            if(type === 'rank') activeRank = val;
            nav('timeline');
        }}

        function goToWork(key) {{
            const d = DATA.find(x => x.unique_key === key);
            if(!d) return;
            let rev = d.review;
            DATA.forEach(o => {{ if(o.unique_key !== key) rev = rev.replace(new RegExp('\\\\b('+o.nom+')\\\\b', 'gi'), `<span class="alink" onclick="goToWork('${{o.unique_key}}')">$1</span>`); }});
            document.getElementById('work').innerHTML = `<div class="w-view">
                <button class="nav-btn" onclick="nav('timeline')">RETOUR</button>
                <div class="w-head" style="margin-top:20px;">${{d.nom}}</div>
                <div class="w-meta">${{d.rank}} • ${{d.date_full}}</div>
                ${{rev ? `<div class="w-rev">${{rev}}</div>` : ''}}
                <div>${{d.genres.map(g=>`<span class="tag">${{g}}</span>`).join('')}} ${{d.tags.map(t=>`<span class="tag" style="color:var(--rose); border-color:var(--rose);">${{t}}</span>`).join('')}}</div>
            </div>`;
            nav('work');
        }}

        function handleSearch() {{
            activeSearch = document.getElementById('search').value.toLowerCase();
            document.getElementById('search-x').style.display = activeSearch ? 'block' : 'none';
            renderTimeline();
        }}
        function clearSearch() {{ document.getElementById('search').value = ""; activeSearch = ""; handleSearch(); }}

        window.onclick = (e) => {{ if(!e.target.matches('.btn-f')) document.querySelectorAll('.dd-menu').forEach(m => m.classList.remove('show')); }};
    </script>
</body>
</html>
"""

# INJECTION FINALE DANS STREAMLIT
components.html(html_code, height=1200, scrolling=True)
