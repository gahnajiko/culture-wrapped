import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# 1. SETUP SERVEUR
st.set_page_config(layout="wide", page_title="Rétrospective Culturelle")

@st.cache_data(ttl=60)
def load_and_process_data():
    sheet_id = "1-CXmo-ghJwOdFtXsBV-lUBcSQN60itiaMEaYUYfWnl8"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns]
        df = df.dropna(subset=['Nom'])
        
        # Paramètres d'exclusion
        EXCLUS = ["Septembre 2025", "Octobre 2025", "Juillet 2024"]
        MOIS_FR = {1:'Janvier', 2:'Février', 3:'Mars', 4:'Avril', 5:'Mai', 6:'Juin', 7:'Juillet', 8:'Août', 9:'Septembre', 10:'Octobre', 11:'Novembre', 12:'Décembre'}
        
        db_export = []
        stats = {"media": {}, "rank": {}, "genre": {}, "tag": {}}
        histo_data = {}
        unique_medias = []

        for row in df.itertuples():
            nom = str(getattr(row, 'Nom', ''))
            m_glob = str(getattr(row, 'Média_global', 'Autre')).strip()
            m_det = str(getattr(row, 'Média', m_glob)).strip()
            rank = str(getattr(row, 'Rank', 'Sans Rank')).strip()
            if rank.lower() in ['nan', '']: rank = "Sans Rank"
            
            review = str(getattr(row, 'Review', ''))
            genres = [g.strip() for g in str(getattr(row, 'Genres', '')).split(',') if g.strip() and g.lower() != 'nan']
            tags = [t.strip() for t in str(getattr(row, 'Tags', '')).split(',') if t.strip() and t.lower() != 'nan']

            # --- LOGIQUE DE SESSION (DATES MULTIPLES) ---
            debut = pd.to_datetime(getattr(row, 'Début', None), dayfirst=True, errors='coerce')
            fin = pd.to_datetime(getattr(row, 'Fin', None), dayfirst=True, errors='coerce')
            ref_date = fin if pd.notnull(fin) else debut
            
            active_months = []
            if pd.notnull(ref_date):
                start_range = debut if pd.notnull(debut) else ref_date
                periode = pd.period_range(start=start_range, end=ref_date, freq='M')
                for p in periode:
                    m_name = f"{MOIS_FR[p.month]} {p.year}"
                    if m_name not in EXCLUS:
                        active_months.append({"lbl": m_name, "sort": int(p.strftime("%Y%m"))})

            for m in active_months:
                # Stats
                stats["media"][m_glob] = stats["media"].get(m_glob, 0) + 1
                stats["rank"][rank] = stats["rank"].get(rank, 0) + 1
                for g in genres: stats["genre"][g] = stats["genre"].get(g, 0) + 1
                for t in tags: stats["tag"][t] = stats["tag"].get(t, 0) + 1
                
                if m["sort"] not in histo_data:
                    histo_data[m["sort"]] = {"label": m["lbl"], "total": 0, "breakdown": {}}
                histo_data[m["sort"]]["total"] += 1
                histo_data[m["sort"]]["breakdown"][m_glob] = histo_data[m["sort"]]["breakdown"].get(m_glob, 0) + 1

                db_export.append({
                    "id": str(row.Index), "nom": nom, "unique_key": nom.lower(),
                    "media": m_det, "global": m_glob, "rank": rank,
                    "genres": genres, "tags": tags, "review": review,
                    "mois_display": m["lbl"], "sort_key": m["sort"],
                    "curr_d": ref_date.strftime("%d/%m") if pd.notnull(ref_date) else "?"
                })
        
        return json.dumps(db_export), json.dumps(stats), json.dumps(histo_data)
    except Exception as e:
        st.error(f"Erreur : {e}")
        return "[]", "{}", "{}"

DB_JSON, STATS_JSON, HISTO_JSON = load_and_process_data()

# 2. L'INTERFACE HTML/JS/CSS
html_code = f"""
<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;700;900&display=swap" rel="stylesheet">
<style>
    :root {{ --bg: #050505; --card: #111; --rose: #F58AFF; --jaune: #F9FCBB; --font: 'Outfit', sans-serif; }}
    body {{ background: var(--bg); color: white; font-family: var(--font); margin: 0; padding: 0; overflow-x: hidden; }}
    
    /* NAV */
    .nav {{ display: flex; justify-content: center; gap: 40px; padding: 40px; position: sticky; top: 0; background: rgba(5,5,5,0.9); z-index: 100; }}
    .nav-btn {{ background: transparent; border: none; color: white; font-weight: 900; text-transform: uppercase; cursor: pointer; letter-spacing: 2px; transition: 0.2s; opacity: 0.5; font-size: 1rem; }}
    .nav-btn:hover, .nav-btn.active {{ opacity: 1; text-shadow: 0 0 10px var(--rose); }}

    .page {{ display: none; flex-direction: column; align-items: center; padding: 20px; min-height: 100vh; }}
    .active-page {{ display: flex; }}

    /* HUB */
    .h-stat {{ font-size: 12rem; font-weight: 900; color: var(--rose); line-height: 1; text-shadow: 0 0 40px rgba(245, 138, 255, 0.3); margin: 20px 0; }}
    
    /* FILTERS */
    .filter-area {{ width: 100%; max-width: 900px; display: flex; flex-direction: column; align-items: center; gap: 15px; margin-bottom: 40px; }}
    .search-wrap {{ position: relative; width: 400px; }}
    .search-in {{ width: 100%; background: #111; border: 1px solid #333; color: white; padding: 12px 40px; border-radius: 30px; text-align: center; font-weight: bold; outline: none; text-transform: uppercase; }}
    .search-x {{ position: absolute; right: 15px; top: 50%; transform: translateY(-50%); color: #ff5555; cursor: pointer; display: none; font-weight: 900; }}
    .f-row {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; }}
    .btn-f {{ background: #151515; border: 1px solid #333; color: #777; padding: 8px 18px; border-radius: 30px; cursor: pointer; font-size: 0.85rem; font-weight: 700; transition: 0.2s; }}
    .btn-f.active {{ border-color: var(--rose); color: white; background: rgba(245, 138, 255, 0.1); }}

    /* DROPDOWNS */
    .dd-wrap {{ position: relative; display: inline-block; }}
    .dd-menu {{ display: none; position: absolute; background: #111; border: 1px solid var(--rose); border-radius: 10px; width: 250px; max-height: 400px; overflow-y: auto; z-index: 1000; top: 110%; left: 50%; transform: translateX(-50%); }}
    .dd-menu.show {{ display: block; }}
    .dd-item {{ padding: 12px; color: #aaa; font-size: 0.9rem; border-bottom: 1px solid #222; cursor: pointer; text-align: left; }}
    .dd-item:hover {{ background: #222; color: white; }}
    .dd-item.sel {{ color: var(--rose); font-weight: 900; }}

    /* CARDS */
    .card {{ background: var(--card); border-left: 5px solid var(--rose); padding: 25px; margin-bottom: 15px; border-radius: 15px; width: 100%; max-width: 700px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; transition: 0.2s; }}
    .card:hover {{ transform: translateX(8px); background: #181818; }}
    .c-tit {{ font-size: 1.4rem; font-weight: 700; color: white; }}
    .c-sub {{ font-size: 0.9rem; color: #666; font-weight: 700; margin-top: 5px; }}

    /* HISTOGRAMMES */
    .histo-sec {{ width: 100%; max-width: 900px; margin-top: 80px; border-top: 1px dashed #333; padding-top: 40px; }}
    .chart-box {{ height: 250px; display: flex; align-items: flex-end; justify-content: center; gap: 15px; margin-bottom: 60px; }}
    .c-col {{ flex: 1; background: rgba(255,255,255,0.05); border-radius: 6px; position: relative; display: flex; flex-direction: column-reverse; cursor: pointer; }}
    .c-seg {{ width: 100%; transition: 0.2s; position: relative; }}
    .c-seg:hover {{ filter: brightness(1.5); }}
    .c-lbl {{ position: absolute; bottom: -40px; left: 50%; transform: translateX(-50%) rotate(-30deg); font-size: 0.8rem; color: #888; white-space: nowrap; font-weight: bold; }}
    
    /* GRIDS */
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 25px; width: 100%; max-width: 1100px; padding: 40px; }}
    .w-item {{ background: #111; border: 1px solid #333; padding: 40px; border-radius: 25px; text-align: center; cursor: pointer; transition: 0.3s; }}
    .w-item:hover {{ border-color: var(--rose); transform: translateY(-10px); }}
    .w-num {{ font-size: 5rem; font-weight: 900; color: var(--rose); line-height: 1; }}

    /* WORK PAGE */
    .w-rev {{ background: white; color: black; padding: 40px; border-radius: 20px; margin: 30px 0; line-height: 1.8; font-size: 1.1rem; font-weight: 500; }}
    .alink {{ color: var(--rose); font-weight: 900; text-decoration: underline; cursor: pointer; }}
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
        <div style="letter-spacing:12px; color:var(--jaune); font-weight:900;">RÉTROSPECTIVE</div>
        <div class="h-stat" id="hub-count">0</div>
        <div style="letter-spacing:6px; color:#555; font-weight:900; margin-bottom:50px;">ŒUVRES TERMINÉES</div>
        <button class="h-btn" onclick="nav('timeline')">EXPLORER LA DATABASE</button>
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
            <div class="f-row">
                <div id="dd-genre"></div>
                <div id="dd-tag"></div>
            </div>
        </div>
        <div id="tl-cont" class="tl-cont"></div>
        <div class="histo-sec">
            <div class="month-lbl" style="font-size:2rem; margin-bottom:40px;">Statistiques</div>
            <div id="chart-vol" class="chart-box"></div>
            <div id="chart-mood" style="width:100%; margin-top:50px;"></div>
        </div>
    </div>

    <div id="media" class="page"><h1>MÉDIAS WALL</h1><div id="wall-media" class="grid"></div></div>
    <div id="rank" class="page"><h1>CLASSEMENT</h1><div id="wall-rank" class="grid"></div></div>
    <div id="mood" class="page">
        <h1 style="color:var(--rose)">GENRES</h1><div id="wall-genre" class="grid"></div>
        <h1 style="color:var(--rose); margin-top:80px;">TAGS</h1><div id="wall-tag" class="grid"></div>
    </div>
    <div id="work" class="page"></div>
    <div id="detail-page" class="page"></div>

    <script>
        const DATA = {DB_JSON};
        const STATS = {STATS_JSON};
        const HISTO = {HISTO_JSON};
        const COLORS = {{"Jeu vidéo": "#29B6F6", "Livre": "#66BB6A", "Film": "#EF5350", "Série": "#AB47BC", "Manga": "#FDD835", "Anime": "#FFA726", "DÉMO": "#7986CB"}};
        const RANK_ORDER = ["Parfait", "Coup de cœur", "Cool +", "Cool", "Sympa +", "Sympa", "Sans Rank"];

        let activeGlobal = "All", activeMedia = "All", activeRank = "All", activeGenres = new Set(), activeTags = new Set(), activeSearch = "";

        function nav(id) {{
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active-page'));
            document.getElementById(id).classList.add('active-page');
            window.scrollTo(0,0);
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            [...document.querySelectorAll('.nav-btn')].filter(b => b.innerText.toLowerCase() === id.replace('timeline','database')).forEach(b => b.classList.add('active'));
            if(id === 'hub') document.getElementById('hub-count').innerText = DATA.filter(d => true).length;
            if(id === 'timeline') update();
        }}

        function update() {{
            renderRow('row-glob', ['All', ...Object.keys(STATS.media).sort()], activeGlobal, 'global');
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
                    return (type === 'global' ? d.global === i : d.rank === i);
                }}).length;
                if(count === 0 && i !== 'All') return '';
                return `<button class="btn-f ${{i === activeVal ? 'active' : ''}}" onclick="setF('${{type}}', '${{i.replace(/'/g, "\\\\'")}}')">${{i}} (${{count}})</button>`;
            }}).join('');
        }}

        function setF(type, val) {{
            if(type === 'global') {{ activeGlobal = val; activeMedia = 'All'; }}
            if(type === 'rank') activeRank = val;
            update();
        }}

        function renderDD(id, lbl, set, keys) {{
            const el = document.getElementById(id);
            el.innerHTML = `<div class="dd-wrap">
                <button class="btn-f ${{set.size > 0 ? 'active' : ''}}" onclick="this.nextElementSibling.classList.toggle('show')">${{lbl}} ${{set.size > 0 ? '('+set.size+')' : ''}}</button>
                <div class="dd-menu">${{keys.sort().map(k => `<div class="dd-item ${{set.has(k) ? 'sel' : ''}}" onclick="toggleGT('${{lbl}}', '${{k.replace(/'/g, "\\\\'")}}')">${{k}}</div>`).join('')}}</div>
            </div>${{set.size > 0 ? `<span class="reset-x" onclick="clearGT('${{lbl}}')">✕</span>` : ''}}`;
        }}

        function toggleGT(type, val) {{ (type === 'GENRES' ? activeGenres : activeTags).has(val) ? (type === 'GENRES' ? activeGenres : activeTags).delete(val) : (type === 'GENRES' ? activeGenres : activeTags).add(val); update(); }}
        function clearGT(type) {{ (type === 'GENRES' ? activeGenres : activeTags).clear(); update(); }}

        function renderTimeline() {{
            const cont = document.getElementById('tl-cont'); cont.innerHTML = "";
            const filtered = DATA.filter(d => {{
                if(activeGlobal !== 'All' && d.global !== activeGlobal) return false;
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
                    <div><div class="c-tit">${{d.nom}}</div><div class="c-sub">${{d.curr_d}}</div></div>
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
        }}

        function goToWork(key) {{
            const d = DATA.find(x => x.unique_key === key);
            if(!d) return;
            let rev = d.review && d.review !== 'nan' ? `<div class="w-rev">${{d.review}}</div>` : "";
            document.getElementById('work').innerHTML = `<div class="w-view">
                <button class="nav-btn" onclick="nav('timeline')" style="margin-bottom:40px;">RETOUR</button>
                <div class="w-head">${{d.nom}}</div>
                <div class="w-meta">${{d.rank}} • ${{d.mois_display}}</div>
                ${{rev}}
                <div>${{d.genres.map(g=>`<span class="tag" onclick="forceFilter('genre','${{g}}')">${{g}}</span>`).join('')}} ${{d.tags.map(t=>`<span class="tag" style="color:var(--rose)" onclick="forceFilter('tag','${{t}}')">${{t}}</span>`).join('')}}</div>
            </div>`;
            nav('work');
        }}

        function forceFilter(type, val) {{
            activeGenres.clear(); activeTags.clear(); activeGlobal="All"; activeRank="All";
            if(type==='genre') activeGenres.add(val); else activeTags.add(val);
            nav('timeline');
        }}

        function renderWall(id, obj, type) {{
            document.getElementById(id).innerHTML = Object.entries(obj).sort((a,b)=>b[1]-a[1]).map(([k,v]) => `
                <div class="w-item" onclick="forceFilter('${{type}}','${{k.replace(/'/g, "\\\\'")}}')">
                    <div class="w-num">${{v}}</div><div class="w-lbl">${{k}}</div>
                </div>`).join('');
        }}

        function handleSearch() {{ activeSearch = document.getElementById('search').value.toLowerCase(); document.getElementById('search-x').style.display = activeSearch ? 'block' : 'none'; renderTimeline(); }}
        function clearSearch() {{ document.getElementById('search').value = ""; activeSearch = ""; handleSearch(); }}

        window.onclick = (e) => {{ if(!e.target.matches('.btn-f')) document.querySelectorAll('.dd-menu').forEach(m => m.classList.remove('show')); }};
    </script>
</body>
</html>
"""

components.html(html_code, height=2000, scrolling=True)
