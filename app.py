import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURATION DU SERVEUR (PYTHON)
# ==========================================
st.set_page_config(layout="wide", page_title="Culture Dashboard", page_icon="🧬")

# Cache pour ne pas recharger le Sheet à chaque clic (10 min)
@st.cache_data(ttl=600)
def load_data():
    # Ton Sheet en lecture seule (CSV public)
    sheet_id = "1-CXmo-ghJwOdFtXsBV-lUBcSQN60itiaMEaYUYfWnl8"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        df = pd.read_csv(url)
        # Nettoyage brutal des colonnes
        df.columns = [c.strip() for c in df.columns]
        
        # Conversion Dates (Gestion des erreurs)
        df['Début'] = pd.to_datetime(df['Début'], dayfirst=True, errors='coerce')
        df['Fin'] = pd.to_datetime(df['Fin'], dayfirst=True, errors='coerce')
        
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data()

# ==========================================
# 2. PRÉPARATION DES DONNÉES (JSON)
# ==========================================
# On prépare tout ici pour que le JS n'ait plus qu'à afficher (pas de calculs foireux en JS)

db_export = []
stats = {"media": {}, "rank": {}, "genre": {}, "tag": {}}
histo_data = {} # Pour les graphiques en bas
unique_globals = set()
unique_medias = []

if not df.empty:
    # Mois en Français pour l'affichage
    MOIS = {1:'Janvier', 2:'Février', 3:'Mars', 4:'Avril', 5:'Mai', 6:'Juin', 7:'Juillet', 8:'Août', 9:'Septembre', 10:'Octobre', 11:'Novembre', 12:'Décembre'}

    for row in df.itertuples():
        nom = str(getattr(row, 'Nom', '')).strip()
        if not nom or nom.lower() == 'nan': continue
        
        # Données de base
        m_glob = str(getattr(row, 'Média_global', 'Autre')).strip()
        m_det = str(getattr(row, 'Média', m_glob)).strip()
        rank = str(getattr(row, 'Rank', 'Sans Rank')).strip()
        review = str(getattr(row, 'Review', '')).replace('\n', '<br>')
        if review == 'nan': review = ""
        
        genres = [g.strip() for g in str(getattr(row, 'Genres', '')).split(',') if g.strip()]
        tags = [t.strip() for t in str(getattr(row, 'Tags', '')).split(',') if t.strip()]
        
        # Gestion des Dates (Pour éviter "Undefined")
        fin = row.Fin if pd.notnull(row.Fin) else row.Début
        d_aff = fin.strftime("%d/%m") if pd.notnull(fin) else "?"
        d_full = fin.strftime("%d/%m/%Y") if pd.notnull(fin) else "?"
        
        # Mois de tri (YYYYMM) et affichage
        m_sort = int(fin.strftime("%Y%m")) if pd.notnull(fin) else 0
        m_lbl = f"{MOIS.get(fin.month, '')} {fin.year}" if pd.notnull(fin) else "Inconnu"

        # Remplissage Stats (Compteurs)
        stats["media"][m_glob] = stats["media"].get(m_glob, 0) + 1
        stats["rank"][rank] = stats["rank"].get(rank, 0) + 1
        for g in genres: stats["genre"][g] = stats["genre"].get(g, 0) + 1
        for t in tags: stats["tag"][t] = stats["tag"].get(t, 0) + 1
        
        unique_globals.add(m_glob)
        # On évite les doublons dans la liste des sous-médias
        if not any(d['media'] == m_det for d in unique_medias):
            unique_medias.append({'media': m_det, 'global': m_glob})

        # Remplissage Histo (Graphiques Chronologiques)
        if m_sort > 0:
            if m_sort not in histo_data: 
                histo_data[m_sort] = {"label": m_lbl, "total": 0, "breakdown": {}}
            histo_data[m_sort]["total"] += 1
            histo_data[m_sort]["breakdown"][m_glob] = histo_data[m_sort]["breakdown"].get(m_glob, 0) + 1

        # L'objet final pour le JS
        db_export.append({
            "id": str(row.Index), # ID unique
            "nom": nom,
            "unique_key": nom.lower(), # Pour l'auto-link
            "global": m_glob,
            "media": m_det,
            "rank": rank,
            "genres": genres,
            "tags": tags,
            "review": review,
            "sort_key": m_sort,
            "mois_display": m_lbl,
            "date_aff": d_aff,
            "date_full": d_full
        })

# Tri final pour la timeline
db_export = sorted(db_export, key=lambda x: x['sort_key'], reverse=True)

# ==========================================
# 3. L'INTERFACE (HTML/CSS/JS COMPLET)
# ==========================================
# C'est ici qu'on remet TON design exact.

html_code = f"""
<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;700;900&display=swap" rel="stylesheet">
<style>
    :root {{ --bg: #050505; --card: #111111; --rose: #F58AFF; --jaune: #F9FCBB; --font: 'Outfit', sans-serif; }}
    
    /* RESET & BASE */
    body {{ background: var(--bg); color: white; font-family: var(--font); margin: 0; padding: 0; overflow-x: hidden; }}
    * {{ box-sizing: border-box; }}
    
    /* NAVIGATION */
    .nav-bar {{ display: flex; justify-content: center; gap: 15px; padding: 20px; background: rgba(5,5,5,0.9); position: sticky; top: 0; z-index: 100; backdrop-filter: blur(10px); flex-wrap: wrap; }}
    .nav-btn {{ background: transparent; border: 1px solid #333; color: #888; padding: 8px 20px; border-radius: 30px; cursor: pointer; font-weight: 700; text-transform: uppercase; transition: 0.2s; font-size: 0.8rem; }}
    .nav-btn:hover, .nav-btn.active {{ border-color: var(--rose); color: var(--rose); background: rgba(245, 138, 255, 0.05); }}

    /* PAGES SYSTEM */
    .page {{ display: none; min-height: 100vh; flex-direction: column; align-items: center; padding-bottom: 50px; }}
    .active-page {{ display: flex; }}

    /* HUB */
    .h-title {{ color: var(--jaune); letter-spacing: 5px; font-weight: 700; margin-top: 10vh; }}
    .h-stat {{ font-size: 10rem; font-weight: 900; color: var(--rose); line-height: 1; text-shadow: 0 0 40px rgba(245, 138, 255, 0.3); margin: 10px 0; }}
    .h-sub {{ color: #666; font-weight: 700; margin-bottom: 40px; letter-spacing: 2px; }}
    .h-btn {{ padding: 15px 50px; background: var(--rose); color: #000; border: none; border-radius: 50px; font-weight: 900; font-size: 1.2rem; cursor: pointer; transition: 0.2s; }}
    .h-btn:hover {{ transform: scale(1.05); box-shadow: 0 0 20px var(--rose); }}

    /* FILTERS AREA */
    .filter-area {{ width: 100%; max-width: 900px; display: flex; flex-direction: column; gap: 10px; margin: 20px 0; align-items: center; }}
    
    /* SEARCH BAR */
    .search-wrap {{ position: relative; width: 300px; }}
    .search-in {{ width: 100%; background: #111; border: 1px solid #333; color: white; padding: 10px 35px 10px 20px; border-radius: 30px; text-align: center; font-weight: bold; outline: none; }}
    .search-in:focus {{ border-color: var(--rose); }}
    .search-x {{ position: absolute; right: 10px; top: 50%; transform: translateY(-50%); color: #ff5555; cursor: pointer; display: none; font-weight: 900; font-size: 1.2rem; }}

    /* FILTER ROWS */
    .f-row {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; width: 100%; }}
    .btn-f {{ background: #151515; border: 1px solid #333; color: #777; padding: 5px 12px; border-radius: 20px; cursor: pointer; font-size: 0.75rem; font-weight: 700; transition: 0.2s; }}
    .btn-f:hover {{ color: white; border-color: #666; }}
    .btn-f.active {{ border-color: var(--rose); color: white; background: rgba(245, 138, 255, 0.1); }}

    /* DROPDOWNS (Genres/Tags) */
    .dd-wrap {{ position: relative; display: inline-block; }}
    .dd-menu {{ display: none; position: absolute; background: #111; border: 1px solid var(--rose); border-radius: 10px; padding: 5px; width: 200px; max-height: 300px; overflow-y: auto; z-index: 1000; top: 110%; left: 50%; transform: translateX(-50%); box-shadow: 0 10px 40px rgba(0,0,0,0.8); }}
    .dd-menu.show {{ display: block; }}
    .dd-item {{ padding: 8px 12px; cursor: pointer; color: #aaa; font-size: 0.8rem; border-bottom: 1px solid #222; text-align: left; }}
    .dd-item:hover {{ color: white; background: #222; }}
    .dd-item.sel {{ color: var(--rose); font-weight: 900; }}

    /* TIMELINE */
    .tl-cont {{ width: 100%; max-width: 700px; }}
    .month-lbl {{ font-size: 3rem; font-weight: 900; color: transparent; -webkit-text-stroke: 1px var(--jaune); text-align: center; margin: 50px 0 20px 0; text-transform: uppercase; }}
    
    .card {{ background: var(--card); border-left: 4px solid var(--rose); padding: 15px 20px; margin-bottom: 12px; border-radius: 8px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: 0.2s; }}
    .card:hover {{ transform: translateX(5px); background: #181818; }}
    .c-tit {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 4px; }}
    .c-sub {{ font-size: 0.75rem; color: #666; text-transform: uppercase; font-weight: 700; }}
    .c-rnk {{ border: 1px solid var(--rose); color: var(--rose); padding: 3px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 900; }}

    /* HISTOGRAMMES (LE RETOUR) */
    .histo-sec {{ width: 100%; max-width: 800px; margin-top: 60px; border-top: 1px dashed #333; padding-top: 30px; }}
    .chart-box {{ height: 180px; display: flex; align-items: flex-end; justify-content: center; gap: 8px; margin-bottom: 40px; }}
    .chart-col {{ width: 20px; background: var(--rose); border-radius: 3px 3px 0 0; position: relative; cursor: pointer; opacity: 0.8; }}
    .chart-col:hover {{ opacity: 1; filter: brightness(1.2); }}
    .c-val {{ position: absolute; top: -20px; left: 50%; transform: translateX(-50%); font-size: 0.6rem; color: var(--rose); font-weight: 900; }}
    .c-lbl {{ position: absolute; bottom: -20px; left: 50%; transform: translateX(-50%) rotate(-45deg); font-size: 0.6rem; color: #666; white-space: nowrap; }}
    
    /* Horizontal Chart (Moods) */
    .h-row {{ display: flex; align-items: center; margin-bottom: 5px; cursor: pointer; }}
    .h-txt {{ width: 100px; text-align: right; font-size: 0.7rem; color: #aaa; margin-right: 10px; font-weight: 700; }}
    .h-tr {{ flex: 1; height: 15px; background: #1a1a1a; border-radius: 3px; overflow: hidden; }}
    .h-fill {{ height: 100%; background: var(--rose); }}
    .h-num {{ width: 30px; text-align: left; font-size: 0.7rem; color: var(--rose); font-weight: 900; margin-left: 8px; }}

    /* WALL GRIDS */
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; width: 100%; max-width: 1000px; }}
    .w-item {{ background: #111; border: 1px solid #333; padding: 25px; text-align: center; border-radius: 12px; cursor: pointer; transition: 0.2s; }}
    .w-item:hover {{ border-color: var(--rose); transform: translateY(-5px); }}
    .w-num {{ font-size: 3rem; font-weight: 900; color: var(--rose); }}
    .w-lbl {{ font-size: 0.8rem; color: var(--jaune); font-weight: 700; margin-top: 10px; text-transform: uppercase; }}

    /* WORK DETAIL PAGE */
    .w-view {{ width: 100%; max-width: 700px; }}
    .w-head {{ font-size: 2.5rem; font-weight: 900; color: var(--jaune); line-height: 1.1; margin-bottom: 10px; }}
    .w-meta {{ color: var(--rose); font-weight: 700; margin-bottom: 20px; }}
    .w-rev {{ background: #111; padding: 25px; border-left: 3px solid var(--rose); color: #ccc; line-height: 1.6; border-radius: 10px; margin-bottom: 20px; }}
    .tag {{ display: inline-block; padding: 4px 10px; border: 1px solid #333; border-radius: 15px; font-size: 0.7rem; margin: 3px; cursor: pointer; color: #888; }}
    .tag:hover {{ border-color: white; color: white; }}
    .alink {{ color: var(--rose); text-decoration: underline; cursor: pointer; font-weight: 700; }}

</style>
</head>
<body>

    <div class="nav-bar">
        <button class="nav-btn" onclick="nav('hub')">HOME</button>
        <button class="nav-btn" onclick="nav('timeline')">DATABASE</button>
        <button class="nav-btn" onclick="nav('media')">MÉDIAS</button>
        <button class="nav-btn" onclick="nav('rank')">RANKING</button>
        <button class="nav-btn" onclick="nav('mood')">MOODS</button>
    </div>

    <div id="hub" class="page active-page" style="justify-content:center;">
        <div class="h-title">RÉTROSPECTIVE</div>
        <div class="h-stat">{len(db_export)}</div>
        <div class="h-sub">ŒUVRES TERMINÉES</div>
        <button class="h-btn" onclick="nav('timeline')">DÉMARRER</button>
    </div>

    <div id="timeline" class="page">
        <div class="filter-area">
            <div class="search-wrap">
                <input type="text" id="search" class="search-in" placeholder="RECHERCHER..." oninput="handleSearch()">
                <span id="search-x" class="search-x" onclick="clearSearch()">✕</span>
            </div>
            <div class="f-row" id="row-glob"></div>
            <div class="f-row" id="row-med" style="display:none;"></div>
            <div class="f-row" id="row-rnk"></div>
            <div class="f-row">
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

    <div id="media" class="page"><h1 style="color:var(--rose);">MÉDIAS</h1><div id="wall-media" class="grid"></div></div>
    <div id="rank" class="page"><h1 style="color:var(--rose);">CLASSEMENT</h1><div id="wall-rank" class="grid"></div></div>
    <div id="mood" class="page"><h1 style="color:var(--rose);">MOODS</h1><div id="wall-mood" class="grid"></div></div>

    <div id="work" class="page"></div>

    <script>
        // DONNÉES INJECTÉES PAR PYTHON
        const DATA = {json.dumps(db_export)};
        const STATS = {{
            media: {json.dumps(stats["media"])},
            rank: {json.dumps(stats["rank"])},
            genre: {json.dumps(stats["genre"])},
            tag: {json.dumps(stats["tag"])}
        }};
        const HISTO = {json.dumps(histo_data)};
        const GLOBALS = {json.dumps(sorted(list(unique_globals)))};
        const MEDIAS = {json.dumps(unique_medias)};
        const RANK_ORDER = ["Parfait", "Coup de cœur", "Cool +", "Cool", "Sympa +", "Sympa", "Sans Rank"];

        // ÉTAT
        let activeGlobal = "All", activeMedia = "All", activeRank = "All";
        let activeGenres = new Set(), activeTags = new Set();
        let activeSearch = "";

        // NAVIGATION
        function nav(id) {{
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active-page'));
            document.getElementById(id).classList.add('active-page');
            window.scrollTo(0,0);
            
            // Boutons actifs
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            [...document.querySelectorAll('.nav-btn')].filter(b => b.innerText.includes(id.toUpperCase())).forEach(b => b.classList.add('active'));

            if(id==='timeline') initFilters();
            if(id==='media') renderWall('wall-media', STATS.media, 'media');
            if(id==='rank') renderWall('wall-rank', STATS.rank, 'rank');
            if(id==='mood') renderWall('wall-mood', {{...STATS.genre, ...STATS.tag}}, 'mood');
        }}

        // FILTRES
        function initFilters() {{
            // GLOBAL ROW
            renderRow('row-glob', ['All', ...GLOBALS], activeGlobal, (v) => {{ activeGlobal = v; activeMedia = 'All'; update(); }});
            
            // MEDIA ROW (Dynamique)
            if(activeGlobal !== 'All') {{
                const subs = MEDIAS.filter(m => m.global === activeGlobal && m.media !== activeGlobal).map(m => m.media);
                if(subs.length > 0) {{
                    document.getElementById('row-med').style.display = 'flex';
                    renderRow('row-med', ['All', ...subs], activeMedia, (v) => {{ activeMedia = v; update(); }});
                }} else document.getElementById('row-med').style.display = 'none';
            }} else document.getElementById('row-med').style.display = 'none';

            // RANK ROW
            renderRow('row-rnk', ['All', ...RANK_ORDER], activeRank, (v) => {{ activeRank = v; update(); }});

            // DROPDOWNS
            renderDD('dd-genre', 'GENRES', activeGenres, Object.keys(STATS.genre), (v) => {{ activeGenres.has(v)?activeGenres.delete(v):activeGenres.add(v); update(); }});
            renderDD('dd-tag', 'TAGS', activeTags, Object.keys(STATS.tag), (v) => {{ activeTags.has(v)?activeTags.delete(v):activeTags.add(v); update(); }});

            renderTimeline();
            renderHisto();
        }}

        function update() {{ initFilters(); }}

        function renderRow(id, items, activeVal, clickFn) {{
            const el = document.getElementById(id);
            el.innerHTML = items.map(i => {{
                // Calcul count dynamique (Simulation simple)
                let c = 0; // Optimisation: on pourrait calculer le vrai count ici
                return `<button class="btn-f ${{i===activeVal?'active':''}}" onclick="window.clickF('${{id}}', '${{i}}')">${{i}}</button>`;
            }}).join('');
            
            // Hack pour passer la fonction au scope global
            window.clickF = (rid, val) => clickFn(val);
        }}

        function renderDD(id, lbl, set, keys, fn) {{
            document.getElementById(id).innerHTML = `
                <div class="dd-wrap">
                    <button class="btn-f ${{set.size>0?'active':''}}" onclick="this.nextElementSibling.classList.toggle('show')">${{lbl}} ${{set.size>0?'('+set.size+')':''}}</button>
                    <div class="dd-menu">
                        ${{keys.sort().map(k => `<div class="dd-item ${{set.has(k)?'sel':''}}" onclick="window.clickDD('${{id}}', '${{k.replace(/'/g, "\\\\'")}}')">${{k}}</div>`).join('')}}
                    </div>
                </div>
                ${{set.size>0 ? `<span class="reset-x" onclick="window.clearDD('${{id}}')">✕</span>` : ''}}`;
            
            window.clickDD = (did, val) => fn(val);
            window.clearDD = (did) => {{ set.clear(); update(); }};
        }}

        // VISIBILITÉ
        function isVisible(d) {{
            if(activeGlobal !== 'All' && d.global !== activeGlobal) return false;
            if(activeMedia !== 'All' && d.media !== activeMedia) return false;
            if(activeRank !== 'All' && d.rank !== activeRank) return false;
            if(activeGenres.size > 0 && !d.genres.some(g => activeGenres.has(g))) return false;
            if(activeTags.size > 0 && !d.tags.some(t => activeTags.has(t))) return false;
            if(activeSearch && !d.nom.toLowerCase().includes(activeSearch)) return false;
            return true;
        }}

        // TIMELINE RENDU
        function renderTimeline() {{
            const c = document.getElementById('tl-cont');
            c.innerHTML = "";
            const list = DATA.filter(isVisible);
            
            if(list.length === 0) {{ c.innerHTML = "<div style='text-align:center; color:#666; margin-top:40px;'>Aucun résultat.</div>"; return; }}

            let lastM = "";
            list.forEach(d => {{
                if(d.mois_display !== lastM) {{ c.innerHTML += `<div class="month-lbl">${{d.mois_display}}</div>`; lastM = d.mois_display; }}
                c.innerHTML += `
                    <div class="card" onclick="goToWork('${{d.unique_key}}')">
                        <div>
                            <div class="c-tit">${{d.nom}}</div>
                            <div class="c-sub">${{d.media}} • ${{d.date_aff}}</div>
                        </div>
                        <div class="c-rnk">${{d.rank}}</div>
                    </div>`;
            }});
        }}

        // HISTOGRAMMES
        function renderHisto() {{
            const box = document.getElementById('chart-vol');
            box.innerHTML = "";
            const data = Object.values(HISTO).sort((a,b)=>a.sort_key - b.sort_key); // Utiliser sort_key si dispo, sinon clés
            if(data.length === 0) return;
            
            const max = Math.max(...data.map(d => d.total));
            data.forEach(d => {{
                box.innerHTML += `
                    <div class="chart-col" style="height:${{(d.total/max)*100}}%" title="${{d.label}}: ${{d.total}}">
                        <div class="c-val">${{d.total}}</div>
                        <div class="c-lbl">${{d.label}}</div>
                    </div>`;
            }});

            const moodBox = document.getElementById('chart-mood');
            moodBox.innerHTML = "";
            // Top 10 Genres
            Object.entries(STATS.genre).sort((a,b)=>b[1]-a[1]).slice(0, 10).forEach(([k,v]) => {{
                moodBox.innerHTML += `
                    <div class="h-row" onclick="forceGenre('${{k.replace(/'/g, "\\\\'")}}')">
                        <div class="h-txt">${{k}}</div>
                        <div class="h-tr"><div class="h-fill" style="width:${{(v/30)*100}}%"></div></div>
                        <div class="h-num">${{v}}</div>
                    </div>`;
            }});
        }}

        function forceGenre(g) {{
            activeGlobal = "All"; activeMedia = "All"; activeRank = "All"; activeGenres.clear(); activeTags.clear();
            activeGenres.add(g);
            nav('timeline');
        }}

        // WALLS
        function renderWall(id, obj, type) {{
            document.getElementById(id).innerHTML = Object.entries(obj).sort((a,b)=>b[1]-a[1]).map(([k,v]) => `
                <div class="w-item" onclick="wallClick('${{type}}', '${{k.replace(/'/g, "\\\\'")}}')">
                    <div class="w-num">${{v}}</div>
                    <div class="w-lbl">${{k}}</div>
                </div>`).join('');
        }}

        function wallClick(type, val) {{
            activeGlobal = "All"; activeMedia = "All"; activeRank = "All"; activeGenres.clear(); activeTags.clear();
            if(type === 'media') {{
                if(GLOBALS.includes(val)) activeGlobal = val;
                else {{
                    const m = MEDIAS.find(x => x.media === val);
                    if(m) {{ activeGlobal = m.global; activeMedia = val; }}
                }}
            }}
            if(type === 'rank') activeRank = val;
            if(type === 'mood') {{ if(STATS.genre[val]) activeGenres.add(val); else activeTags.add(val); }}
            nav('timeline');
        }}

        // WORK PAGE
        function goToWork(key) {{
            const d = DATA.find(x => x.unique_key === key);
            if(!d) return;
            
            let rev = d.review;
            // Auto link basic
            DATA.forEach(o => {{
                if(o.unique_key !== key) {{
                    const r = new RegExp(`\\\\b(${{o.nom}})\\\\b`, 'gi');
                    rev = rev.replace(r, `<span class="alink" onclick="goToWork('${{o.unique_key}}')">$1</span>`);
                }}
            }});

            const p = document.getElementById('work');
            p.innerHTML = `
                <div class="w-view">
                    <button class="nav-btn" onclick="nav('timeline')" style="margin-bottom:20px;">RETOUR</button>
                    <div class="w-head">${{d.nom}}</div>
                    <div class="w-meta">${{d.media}} • ${{d.rank}} • ${{d.date_full}}</div>
                    <div class="w-rev">${{rev || "Pas de review."}}</div>
                    <div>${{d.genres.map(g=>`<span class="tag">${{g}}</span>`).join('')}} ${{d.tags.map(t=>`<span class="tag" style="color:var(--rose)">${{t}}</span>`).join('')}}</div>
                </div>`;
            nav('work');
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

        window.onclick = function(e) {{
            if (!e.target.matches('.btn-f')) {{
                document.querySelectorAll('.dd-menu').forEach(x => x.classList.remove('show'));
            }}
        }}
    </script>
</body>
</html>
"""

components.html(html_code, height=1200, scrolling=True)
