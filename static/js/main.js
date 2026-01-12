let keywords = [];
let metadata = { categories: [], regions: [], departments: [] };
// Notification initialization
if ("Notification" in window) {
    if (Notification.permission !== "granted" && Notification.permission !== "denied") {
        Notification.requestPermission();
    }
}

let adsData = [];
let selectedAds = [];
let map = null;
let chart = null;
let currentSearchName = null;
let activeFilters = new Set();
let lastSeenCount = 0;
let selectedLocations = [];

function robustParseJSON(str, defaultVal = {}) {
    if (!str) return defaultVal;
    if (typeof str === 'object') return str;
    try {
        return JSON.parse(str);
    } catch (e) {
        try {
            // Handle single quote format from Python str()
            const fixed = str.replace(/'/g, '"')
                .replace(/True/g, 'true')
                .replace(/False/g, 'false')
                .replace(/None/g, 'null');
            return JSON.parse(fixed);
        } catch (e2) {
            console.error("Critical JSON parse failure", str);
            return defaultVal;
        }
    }
}

async function init() {
    try {
        const resp = await fetch('/api/metadata');
        metadata = await resp.json();

        const catSelect = document.getElementById('category-select');
        metadata.categories.sort((a, b) => a.name.localeCompare(b.name)).forEach(c => {
            if (c.id === '0') return;
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.innerText = c.name;
            catSelect.appendChild(opt);
        });

        loadWatches();
        await loadHistory();
        initMap();

        setInterval(checkForUpdates, 30000);
    } catch (e) {
        console.error("Metadata load error", e);
    }
}

async function checkForUpdates() {
    if (!currentSearchName) return;
    try {
        const resp = await fetch(`/api/ads?search_name=${encodeURIComponent(currentSearchName)}`);
        const ads = await resp.json();
        if (ads.length > lastSeenCount) {
            const diff = ads.length - lastSeenCount;
            const alert = document.getElementById('update-alert');
            const alertText = document.getElementById('update-alert-text');
            if (alertText) alertText.innerText = `${diff} nouvelle(s) annonce(s) disponible(s) ! Cliquez pour rafraîchir.`;
            if (alert) alert.style.display = 'block';
        }
    } catch (e) { }
}

function switchTab(tabId) {
    document.querySelectorAll('.tab:not(.subtab)').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));

    const targetTab = Array.from(document.querySelectorAll('.tab')).find(t => t.innerText.toLowerCase().includes(tabId.toLowerCase()));
    if (targetTab) targetTab.classList.add('active');

    const view = document.getElementById(`view-${tabId}`);
    if (view) view.classList.add('active');

    if (tabId === 'watches') loadWatches();
}

function switchSubTab(subId) {
    document.querySelectorAll('.subtab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.sub-view').forEach(s => {
        s.classList.remove('active');
        s.style.display = 'none';
    });

    const targetTab = Array.from(document.querySelectorAll('.subtab')).find(t => t.innerText.toLowerCase().includes(subId.toLowerCase()));
    if (targetTab) targetTab.classList.add('active');

    const targetView = document.getElementById(`sub-${subId}`);
    if (targetView) {
        targetView.classList.add('active');
        targetView.style.display = 'block';
    }

    if (subId === 'map') {
        setTimeout(() => { if (map) map.invalidateSize(); }, 200);
        renderMap();
    }
    if (subId === 'trends') renderTrends();
    if (subId === 'top') renderTopAds();
}

function renderTopAds() {
    const grid = document.getElementById('ads-grid-top');
    const header = document.getElementById('top-ai-header');
    const headerContent = document.getElementById('top-ai-header-content');

    const scoredAds = adsData
        .filter(ad => ad.ai_score !== null && ad.ai_score !== undefined)
        .sort((a, b) => b.ai_score - a.ai_score);

    if (scoredAds.length === 0) {
        if (header) header.style.display = 'block';
        if (headerContent) headerContent.innerHTML = `<h3>🤖 Aucune analyse disponible</h3><p>Lancez l'IA avec le bouton <b>"Analyser tout"</b> en haut.</p>`;
        if (grid) grid.innerHTML = '';
        return;
    }

    if (header) header.style.display = 'block';
    if (headerContent) headerContent.innerHTML = `<h3>🏆 Votre Sélection Elite</h3><p>L'IA a passé au crible <b>${adsData.length} annonces</b>. Voici les pépites détectées.</p>`;

    renderAds(scoredAds.slice(0, 10), 'ads-grid-top');
}

function updateKeywordCloud() {
    const cloud = document.getElementById('tag-cloud');
    const container = document.getElementById('tag-cloud-container');
    if (!cloud) return;

    const wordCounts = {};
    const stopWords = new Set(['le', 'la', 'les', 'du', 'des', 'de', 'un', 'une', 'et', 'en', 'pour', 'avec', 'dans', 'sur', 'très', 'étât', 'plus', 'avec', 'pour', 'tout']);

    adsData.forEach(ad => {
        const text = `${ad.title} ${ad.ai_summary || ''}`.toLowerCase();
        const matches = text.match(/[a-z0-9àâäéèêëïîôöùûüç]{4,}/g);
        if (matches) {
            matches.forEach(w => {
                if (!stopWords.has(w)) wordCounts[w] = (wordCounts[w] || 0) + 1;
            });
        }
    });

    const sortedWords = Object.entries(wordCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 20);

    if (sortedWords.length === 0) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';
    cloud.innerHTML = '';

    if (activeFilters.size > 0) {
        const clearBtn = document.createElement('div');
        clearBtn.className = 'keyword-tag active';
        clearBtn.innerHTML = 'Tout effacer ✕';
        clearBtn.onclick = () => { activeFilters.clear(); applyLocalFilters(); };
        cloud.appendChild(clearBtn);
    }

    sortedWords.forEach(([word, count]) => {
        const tag = document.createElement('div');
        tag.className = 'keyword-tag' + (activeFilters.has(word) ? ' active' : '');
        tag.innerHTML = `${word} <span style="opacity:0.6; font-size:0.7rem">${count}</span>`;
        tag.onclick = () => toggleFilter(word);
        cloud.appendChild(tag);
    });
}

function toggleFilter(word) {
    if (activeFilters.has(word)) activeFilters.delete(word);
    else activeFilters.add(word);
    applyLocalFilters();
}

function applyLocalFilters() {
    const filtered = adsData.filter(ad => {
        if (activeFilters.size === 0) return true;
        const text = `${ad.title} ${ad.ai_summary || ''}`.toLowerCase();
        return Array.from(activeFilters).every(f => text.includes(f));
    });
    renderAds(filtered, 'ads-grid-history', false);
    updateKeywordCloud();
}

function renderAds(ads, gridId, rebuildCloud = true) {
    const grid = document.getElementById(gridId);
    if (!grid) return;

    // Show skeletons if grid is empty and we are transitioning (simulated or real)
    if (!ads || ads.length === 0 && !grid.children.length) {
        // Only if it's the history grid
        if (gridId === 'ads-grid-history' || gridId === 'ads-grid-live') {
            grid.innerHTML = '';
            for (let i = 0; i < 6; i++) {
                grid.innerHTML += `
                    <div class="skeleton-card">
                        <div class="skeleton skeleton-img"></div>
                        <div class="skeleton skeleton-text"></div>
                        <div class="skeleton skeleton-text short"></div>
                    </div>
                `;
            }
            return;
        }
    }

    if (gridId === 'ads-grid-live') {
        const count = document.getElementById('results-count');
        const update = document.getElementById('last-update');
        if (count) count.innerText = `${ads.length} trouvées`;
        if (update) update.innerText = `Dernier scan: ${new Date().toLocaleTimeString()}`;
    }

    if (rebuildCloud && gridId === 'ads-grid-history') {
        updateKeywordCloud();
    }

    grid.innerHTML = '';
    if (ads.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 4rem; color: #AAA;">Aucun résultat correspondant.</div>';
        return;
    }

    ads.forEach((ad, index) => {
        const card = document.createElement('div');
        card.className = 'ad-card' + (selectedAds.find(s => String(s.id) === String(ad.id)) ? ' selected' : '');
        card.setAttribute('data-id', ad.id);
        card.style.animationDelay = `${index * 0.05}s`;

        const img = ad.image_url || "data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' width='300' height='200' viewBox='0 0 300 200'%3e%3crect width='100%25' height='100%25' fill='%23eee'/%3e%3ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='16' fill='%23999'%3eImage non disponible%3c/text%3e%3c/svg%3e";
        const price = ad.price ? `${ad.price.toLocaleString()} €` : 'Prix sur demande';
        const dateStr = ad.date ? new Date(ad.date).toLocaleDateString() : 'Date inconnue';

        // Pepite Logic: High AI score and maybe below average price (if stats available)
        const isPepite = ad.ai_score >= 8.5;
        const pepiteBadge = isPepite ? '<div class="badge-pepite">✨ PÉPITE</div>' : '';

        const scoreBadge = ad.ai_score ? `
            <div class="ad-score-badge" style="color: ${ad.ai_score > 7 ? '#10B981' : '#F59E0B'}">
                <span>⭐</span> ${ad.ai_score}/10
            </div>
        ` : '';

        let newBadge = '';
        if (ad.date) {
            const adDate = new Date(ad.date);
            const now = new Date();
            if ((now - adDate) < (24 * 60 * 60 * 1000)) {
                newBadge = '<div class="badge-new">NOUVEAU</div>';
            }
        }

        const proBadge = ad.is_pro ? '<div class="badge-pro">PRO</div>' : '';
        const topBadge = (gridId === 'ads-grid-top' && index === 0) ? '<div class="badge-top-one">🏆 N°1</div>' : '';
        const isManual = ad.source === 'MANUAL';
        const sourceBadge = isManual ? '' : `<div class="badge-source">${ad.source || 'LBC'}</div>`;
        const dropBadge = ad.price_dropped ? '<div class="badge-drop">📉 BAISSE</div>' : '';

        const manualTop = ad.is_pro ? '38px' : '10px';
        const manualBadge = isManual ? `<div class="badge-manual" style="top:${manualTop}">📝 MANUEL</div>` : '';

        card.innerHTML = `
            ${proBadge} ${topBadge} ${newBadge} ${pepiteBadge} ${sourceBadge} ${dropBadge} ${manualBadge}
            <div class="ad-img-box">
                <div class="select-check" onclick="event.stopPropagation(); toggleAdSelection('${ad.id}')"></div>
                <button class="scam-check-btn" title="Vérifier arnaque" onclick="event.stopPropagation(); checkScam('${ad.id}')">🛡️</button>
                <button class="delete-ad-btn" title="Masquer l'annonce" onclick="event.stopPropagation(); hideAd('${ad.id}')">🗑️</button>
                <img src="${img}" class="ad-img" onclick="window.open('${ad.url}', '_blank')" onerror="this.onerror=null; this.src='data:image/svg+xml;charset=UTF-8,%3csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'300\' height=\'200\' viewBox=\'0 0 300 200\'%3e%3crect width=\'100%25\' height=\'100%25\' fill=\'%23eee\'/%3e%3ctext x=\'50%25\' y=\'50%25\' dominant-baseline=\'middle\' text-anchor=\'middle\' font-family=\'sans-serif\' font-size=\'16\' fill=\'%23999\'%3eImage non disponible%3c/text%3e%3c/svg%3e';">
                ${scoreBadge}
            </div>


            <div class="ad-info" onclick="window.open('${ad.url}', '_blank')">
                <div class="ad-title">${ad.title}</div>
                <div class="ad-price">${price}</div>
                <div class="ad-meta">
                    <span>📍 ${ad.location || 'France'}</span>
                    <span>🕒 ${dateStr}</span>
                </div>
                ${ad.ai_summary ? `<div class="ai-summary-box"><b>IA :</b> ${ad.ai_summary}</div>` : ''}
                ${ad.ai_tips ? `<div class="ai-tips-box"><span>💡</span> ${ad.ai_tips}</div>` : ''}
                <div class="ad-actions" style="margin-top:15px; display:flex; gap:10px;">
                     <button class="btn-micro" onclick="event.stopPropagation(); generateNegotiation('${ad.id}')">🤝 Négocier</button>
                     <button class="btn-micro" style="background:#4F46E5" onclick="event.stopPropagation(); showPriceHistory('${ad.id}')">📈 Historique</button>
                     <button class="btn-micro" style="background:#5865F2" onclick="event.stopPropagation(); shareToDiscord('${ad.id}')" title="Partager sur Discord">📢 Discord</button>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

async function loadHistory(searchName = null) {
    if (searchName === undefined) searchName = null;
    currentSearchName = searchName;
    const alert = document.getElementById('update-alert');
    if (alert) alert.style.display = 'none';

    const url = searchName ? `/api/ads?search_name=${encodeURIComponent(searchName)}` : '/api/ads';

    // Show skeletons immediately
    renderAds([], 'ads-grid-history');

    const resp = await fetch(url);
    const ads = await resp.json();
    adsData = ads;
    lastSeenCount = ads.length;
    activeFilters.clear();
    renderAds(ads, 'ads-grid-history');

    const stats = document.getElementById('current-search-stats');
    if (searchName && stats) {
        stats.innerText = `${ads.length} annonces archivées`;
    }
}

async function refreshCurrentSearch() {
    if (!currentSearchName) return;
    const btn = document.getElementById('btn-refresh-dashboard');
    const loader = document.getElementById('refresh-loader');

    if (btn) btn.disabled = true;
    if (loader) loader.style.display = 'inline-block';

    try {
        const resp = await fetch(`/api/searches/${encodeURIComponent(currentSearchName)}/refresh`, { method: 'POST' });
        const data = await resp.json();
        if (resp.ok) {
            showNotify(data.message);
            await loadHistory(currentSearchName);

            // Handle Findings (Notifications)
            if (data.pépites && data.pépites.length > 0) {
                notifyUser(`✨ ${data.pépites.length} Pépites trouvées !`, `De superbes opportunités pour "${currentSearchName}"`);
            }
            if (data.price_drops && data.price_drops.length > 0) {
                notifyUser(`📉 ${data.price_drops.length} Baisses de prix !`, `Des prix ont chuté dans votre veille "${currentSearchName}"`);
            }
        } else {
            showNotify(data.message || "Erreur lors de l'actualisation.");
        }
    } catch (e) {
        showNotify("Erreur technique de connexion.");
    } finally {
        if (btn) btn.disabled = false;
        if (loader) loader.style.display = 'none';
    }
}

async function performSearch() {
    const loader = document.getElementById('global-loader');
    if (loader) loader.style.display = 'block';

    const payload = {
        queries: keywords,
        category: document.getElementById('category-select').value,
        price_min: parseInt(document.getElementById('price-min').value) || null,
        price_max: parseInt(document.getElementById('price-max').value) || null,
        delivery: document.getElementById('delivery-toggle').checked,
        sort: document.getElementById('sort-select').value,
        owner_type: document.getElementById('owner-select').value === 'all' ? null : document.getElementById('owner-select').value,
        platforms: {
            lbc: document.getElementById('platform-lbc').checked,
            ebay: document.getElementById('platform-ebay').checked,
            vinted: document.getElementById('platform-vinted').checked
        },
        deep_search: document.getElementById('deep-search-toggle').checked ? 1 : 0
    };

    payload.locations = selectedLocations;
    // Fallback if list is empty but type is selected
    const currentLocType = document.getElementById('loc-type').value;
    if (selectedLocations.length === 0 && currentLocType !== 'none') {
        if (currentLocType === 'city') {
            const city = document.getElementById('loc-city').value;
            const radius = document.getElementById('loc-radius').value;
            if (city) payload.locations = [{ type: 'city', value: city, radius: radius }];
        } else {
            const val = document.getElementById('loc-select').value;
            if (val) payload.locations = [{ type: currentLocType === 'dept' ? 'department' : 'region', value: val }];
        }
    }

    try {
        const resp = await fetch('/api/quick-search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (resp.status === 401) {
            window.location.href = '/login';
            return;
        }
        if (!resp.ok) throw new Error("Search failed");

        const ads = await resp.json();
        adsData = ads;
        renderAds(ads, 'ads-grid-live');
        showNotify(`${ads.length} annonces dénichées !`);
    } catch (e) {
        showNotify("Oups, la recherche a échoué.");
        console.error(e);
    } finally {
        if (loader) loader.style.display = 'none';
    }
}

async function createWatchFromSearch() {
    const locNames = selectedLocations.map(l => l.value).join(', ');
    const sentence = keywords.join(' ') + (locNames ? ' ' + locNames : '');
    if (!sentence.trim()) {
        showNotify("Veuillez entrer au moins un mot-clé.");
        return;
    }

    const resp = await fetch('/api/searches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            sentence: sentence,
            queries: keywords,
            ai_context: document.getElementById('ai-context').value,
            initial_ads: adsData,
            refresh_mode: document.getElementById('refresh-mode').value,
            refresh_interval: document.getElementById('refresh-interval').value,
            platforms: {
                lbc: document.getElementById('platform-lbc').checked,
                ebay: document.getElementById('platform-ebay').checked,
                vinted: document.getElementById('platform-vinted').checked
            },
            locations: selectedLocations,
            deep_search: document.getElementById('deep-search-toggle').checked ? 1 : 0
        })

    });

    let result = {};
    try {
        result = await resp.json();
    } catch (e) {
        console.error("Failed to parse error response", e);
    }

    if (resp.ok) {
        showNotify("Veille enregistrée !");
        selectedLocations = [];
        renderLocations();
        switchTab('watches');
        loadWatches();
    } else {
        showNotify(`Erreur: ${result.message || "Échec de l'enregistrement"}`);
        console.error("Save Error:", result);
    }
}

async function loadWatches() {
    // Fetch stats first
    try {
        const statsResp = await fetch('/api/searches/stats');
        const stats = await statsResp.json();
        document.getElementById('stat-total-watches').innerText = stats.total_watches;
        document.getElementById('stat-total-ads').innerText = stats.total_ads;
        document.getElementById('stat-new-ads').innerText = stats.new_ads_total;
        window.watchStats = stats;
    } catch (e) { console.error("Stats error", e); }

    const resp = await fetch('/api/searches');
    const searches = await resp.json();
    const list = document.getElementById('active-watches-list');
    if (!list) return;
    list.innerHTML = '';

    if (searches.length === 0) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 4rem; color: #AAA;">Aucune veille active.</div>';
        return;
    }

    searches.forEach(s => {
        if (!s || !s.name) return;
        const item = document.createElement('div');
        item.className = 'search-container';
        item.style = "margin:0; padding:1.5rem; display:flex; flex-direction:column; gap:15px";
        const modeLabel = s.refresh_mode === 'auto' ? `Auto (${s.refresh_interval}m)` : (s.refresh_mode === 'none' ? 'Statique' : 'Manuel');

        const sStat = window.watchStats?.details?.find(d => d.name === s.name);
        const newBadge = (sStat && sStat.new_count > 0) ? `<div style="background:var(--primary); color:white; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:800; animation:pulse 2s infinite">NEW: ${sStat.new_count}</div>` : '';

        const platforms = robustParseJSON(s.platforms);
        const lbcIcon = platforms.lbc ? '🟠' : '';
        const ebayIcon = platforms.ebay ? '🔵' : '';
        const vintedIcon = platforms.vinted ? '🟢' : '';

        item.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start">
                 <div>
                    <div style="display:flex; align-items:center; gap:10px">
                        <div style="font-weight:800; color:var(--primary); font-size:1.1rem">${s.name}</div>
                        ${newBadge}
                    </div>
                    <div style="font-size:0.8rem; color:var(--text-muted); margin-top:4px">
                        ${s.query_text} | 
                        ${robustParseJSON(s.locations, []).length > 0 ? robustParseJSON(s.locations, []).map(l => l.value).join(', ') : (s.city || 'Toute France')} | 
                        ${modeLabel}
                    </div>
                 </div>
                 <button onclick="deleteWatch('${s.name}')" style="background:none; border:none; color:#AAA; cursor:pointer; font-size:1.5rem">×</button>
            </div>
            <div style="display:flex; gap:10px; align-items:center; margin-top:5px">
                 <div style="font-size:0.75rem; background:var(--bg); padding:3px 10px; border-radius:6px; color:var(--text-muted)">
                    📊 <b>${sStat ? sStat.total_count : '?'}</b> annonces
                 </div>
                 <div style="display:flex; gap:5px; font-size:0.9rem">
                    ${lbcIcon} ${ebayIcon} ${vintedIcon}
                 </div>
            </div>
            <div style="display:flex; gap:10px; margin-top:10px">
                <button class="btn-primary" style="flex:1; padding:0.6rem" onclick="openDashboard('${s.name}')">DASHBOARD</button>
                <button class="btn-primary" style="background:var(--card-bg); color:var(--text); border:1px solid var(--border); padding:0.6rem" onclick="openSearchSettings('${s.name}')">⚙️</button>
            </div>
        `;
        list.appendChild(item);
    });
}

function showNotify(msg) {
    const n = document.getElementById('notification');
    if (n) {
        n.innerText = msg;
        n.classList.add('show');
        setTimeout(() => n.classList.remove('show'), 3000);
    }
}

function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark' : 'light');
}

async function openDashboard(searchName) {
    if (!searchName) return;
    currentSearchName = searchName;
    const title = document.getElementById('current-search-name');
    if (title) title.innerText = searchName;
    switchTab('dashboard');
    switchSubTab('history');
    await loadHistory(searchName);

    // Mark as viewed
    fetch(`/api/searches/${encodeURIComponent(searchName)}/viewed`, { method: 'POST' });
}

async function deleteWatch(name) {
    if (!confirm(`Supprimer dÃ©finitivement la veille "${name}" ?`)) return;
    const resp = await fetch(`/api/searches/${encodeURIComponent(name)}`, { method: 'DELETE' });
    if (resp.ok) { showNotify("Supprimé."); loadWatches(); }
}

async function checkScam(adId) {
    const ad = adsData.find(a => String(a.id) === String(adId));
    if (!ad) return;
    showNotify("Analyse de risque...");
    const resp = await fetch('/api/scam-detector', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: ad.title, description: ad.description, price: ad.price })
    });
    const res = await resp.json();
    const modal = document.getElementById('compare-modal');
    const result = document.getElementById('compare-result');
    if (modal) modal.classList.add('show');
    if (result) result.innerHTML = `<h3>Scam Risk: ${res.risk_level} (${res.risk_score}%)</h3><ul>${res.reasons.map(r => `<li>${r}</li>`).join('')}</ul>`;
}

function closeModal() {
    const modal = document.getElementById('compare-modal');
    if (modal) modal.classList.remove('show');
}

function toggleAdSelection(adId) {
    const sid = String(adId);
    const index = selectedAds.findIndex(a => String(a.id) === sid);
    const card = document.querySelector(`.ad-card[data-id="${adId}"]`);
    if (index > -1) {
        selectedAds.splice(index, 1);
        if (card) card.classList.remove('selected');
    } else {
        const ad = adsData.find(a => String(a.id) === sid);
        if (ad) {
            selectedAds.push(ad);
            if (card) card.classList.add('selected');
        }
    }
    updateCompareBar();
}

function updateCompareBar() {
    const bar = document.getElementById('compare-bar');
    const text = document.getElementById('compare-text');
    if (selectedAds.length > 0) {
        if (text) text.innerText = `${selectedAds.length} sélectionnée(s)`;
        if (bar) bar.classList.add('show');
    } else {
        if (bar) bar.classList.remove('show');
    }
}

function clearSelection() {
    selectedAds = [];
    document.querySelectorAll('.ad-card.selected').forEach(c => c.classList.remove('selected'));
    updateCompareBar();
}

function selectAllVisible() {
    adsData.forEach(ad => {
        if (!selectedAds.find(s => String(s.id) === String(ad.id))) {
            selectedAds.push(ad);
        }
    });
    document.querySelectorAll('.ad-card').forEach(c => c.classList.add('selected'));
    updateCompareBar();
}

async function hideSelectedAds() {
    if (selectedAds.length === 0) return;
    if (!confirm(`Masquer les ${selectedAds.length} annonces sélectionnées ?`)) return;

    const ids = selectedAds.map(a => String(a.id));
    showNotify("⏳ Archivage en cours...");

    for (const adId of ids) {
        try {
            await fetch(`/api/ads/${adId}/hide`, { method: 'POST' });
        } catch (e) { }
    }

    showNotify(`✅ ${ids.length} annonces masquées.`);
    adsData = adsData.filter(a => !ids.includes(String(a.id)));
    selectedAds = [];
    renderAds(adsData, 'ads-grid-history');
    updateCompareBar();
}


function addKeyword() {
    const input = document.getElementById('keyword-input');
    const val = input.value.trim();
    if (val && !keywords.includes(val)) {
        keywords.push(val);
        renderKeywords();
    }
    input.value = '';
}

function removeKeyword(kw) {
    keywords = keywords.filter(k => k !== kw);
    renderKeywords();
}

function renderKeywords() {
    const list = document.getElementById('keywords-list');
    if (!list) return;
    list.innerHTML = '';
    keywords.forEach(kw => {
        const tag = document.createElement('div');
        tag.className = 'keyword-tag';
        tag.innerHTML = `${kw} <span onclick="removeKeyword('${kw}')">×</span>`;
        list.appendChild(tag);
    });
}

function updateLocUI() {
    const type = document.getElementById('loc-type').value;
    const cityInput = document.getElementById('loc-city');
    const radiusInput = document.getElementById('loc-radius');
    const select = document.getElementById('loc-select');

    if (cityInput) cityInput.style.display = type === 'city' ? 'block' : 'none';
    if (radiusInput) radiusInput.style.display = type === 'city' ? 'block' : 'none';
    if (select) select.style.display = (type === 'dept' || type === 'region') ? 'block' : 'none';

    if (select && (type === 'dept' || type === 'region')) {
        select.innerHTML = '';
        if (type === 'dept') {
            metadata.departments.sort((a, b) => a.name.localeCompare(b.name)).forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.id; opt.innerText = d.name; select.appendChild(opt);
            });
        } else if (type === 'region') {
            metadata.regions.sort((a, b) => a.name.localeCompare(b.name)).forEach(r => {
                const opt = document.createElement('option');
                opt.value = r.id; opt.innerText = r.name; select.appendChild(opt);
            });
        }
    }
}

function addLocation() {
    const type = document.getElementById('loc-type').value;
    if (type === 'none') return;

    let location = { type: type === 'dept' ? 'department' : (type === 'region' ? 'region' : 'city') };

    if (type === 'city') {
        const city = document.getElementById('loc-city').value.trim();
        const radius = document.getElementById('loc-radius').value;
        if (!city) return;
        location.value = city;
        location.radius = radius;
    } else {
        const select = document.getElementById('loc-select');
        const val = select.value;
        const text = select.options[select.selectedIndex].text;
        if (!val) return;
        location.value = val;
    }

    if (selectedLocations.some(l => l.type === location.type && l.value === location.value)) return;

    selectedLocations.push(location);
    renderLocations();

    // Clear city input
    if (type === 'city') document.getElementById('loc-city').value = '';
}

function removeLocation(index) {
    selectedLocations.splice(index, 1);
    renderLocations();
}

function renderLocations() {
    const list = document.getElementById('locations-list');
    if (!list) return;
    list.innerHTML = '';
    selectedLocations.forEach((loc, index) => {
        const tag = document.createElement('div');
        tag.className = 'keyword-tag';
        let display = loc.value;
        if (loc.type === 'city') display += ` (+${loc.radius}km)`;
        tag.innerHTML = `${display} <span onclick="removeLocation(${index})" style="cursor:pointer; margin-left:5px">×</span>`;
        list.appendChild(tag);
    });
}


function initMap() {
    const el = document.getElementById('map');
    if (!el || map) return;
    map = L.map('map').setView([46.6, 1.8], 6);
    L.tileLayer('https://{s}.tile.osm.org/{z}/{x}/{y}.png').addTo(map);
}

function renderMap() {
    if (!map) initMap();
    if (!map) return;
    map.eachLayer(l => { if (l instanceof L.Marker) map.removeLayer(l); });
    adsData.forEach(ad => {
        if (ad.lat && ad.lng) {
            L.marker([ad.lat, ad.lng]).addTo(map).bindPopup(`<b>${ad.title}</b><br><a href="${ad.url}" target="_blank">Voir</a>`);
        }
    });
}

async function runComparison() {
    if (selectedAds.length < 2) return showNotify("Sélectionnez au moins 2 annonces.");

    showNotify("🤖 IA en cours de comparaison...");
    try {
        const resp = await fetch('/api/compare-ads', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ads: selectedAds })
        });
        const data = await resp.json();
        const modal = document.getElementById('compare-modal');
        const result = document.getElementById('compare-result');
        if (modal) modal.classList.add('show');
        if (result) {
            result.innerHTML = `
                <h3>📊 Comparatif Expert</h3>
                <div class="comparison-table-wrapper">
                    ${data.comparison_html || `<div style="padding:1rem">${data.analysis.replace(/\n/g, '<br>')}</div>`}
                </div>
            `;
        }
    } catch (e) {
        showNotify("Erreur lors de la comparaison.");
    }
}

async function hideAd(adId) {
    if (!confirm("Voulez-vous vraiment masquer cette annonce ?")) return;

    try {
        const resp = await fetch(`/api/ads/${adId}/hide`, { method: 'POST' });
        if (resp.ok) {
            showNotify("✅ Annonce archivée.");
            // Remove from local data and re-render
            adsData = adsData.filter(a => String(a.id) !== String(adId));
            selectedAds = selectedAds.filter(a => String(a.id) !== String(adId));

            // Remove the element directly for smooth UX or re-render
            const card = document.querySelector(`.ad-card[data-id="${adId}"]`);
            if (card) {
                card.style.opacity = '0';
                card.style.transform = 'scale(0.8)';
                setTimeout(() => card.remove(), 300);
            }
        } else {
            showNotify("❌ Erreur lors de l'archivage.");
        }
    } catch (e) {
        showNotify("Erreur technique.");
    }
}

async function generateNegotiation(adId) {
    showNotify("Génération du brouillon...");
    try {
        const resp = await fetch('/api/negotiate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ad_id: adId })
        });
        const data = await resp.json();
        const modal = document.getElementById('compare-modal');
        const result = document.getElementById('compare-result');
        if (modal) modal.classList.add('show');
        if (result) {
            result.innerHTML = `
                <h3>🤝 Stratégie de Négociation</h3>
                <div style="background:var(--bg); padding:1.5rem; border-radius:12px; font-family:serif; line-height:1.6; border:1px solid var(--border)">
                    ${data.draft.replace(/\n/g, '<br>')}
                </div>
                <button class="btn-primary" style="margin-top:20px; width:100%" onclick="copyNegotiationToClipboard(\`${data.draft.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`)">📋 Copier le message</button>
            `;
        }
    } catch (e) {
        showNotify("Erreur de génération.");
    }
}

async function showPriceHistory(adId) {
    const resp = await fetch(`/api/ads/${adId}/history`);
    const history = await resp.json();

    const modal = document.getElementById('compare-modal');
    const result = document.getElementById('compare-result');
    if (modal) modal.classList.add('show');

    if (history.length === 0) {
        result.innerHTML = "<h3>📈 Historique des Prix</h3><p>Aucun changement détecté pour le moment.</p>";
        return;
    }

    let html = "<h3>📈 Historique des Prix</h3><div style='max-height:300px; overflow-y:auto'><ul>";
    history.forEach(h => {
        html += `<li><b>${h.price}€</b> - le ${new Date(h.date).toLocaleDateString()}</li>`;
    });
    html += "</ul></div>";
    result.innerHTML = html;
}

function notifyUser(title, body) {
    if ("Notification" in window && Notification.permission === "granted") {
        new Notification(title, { body: body, icon: '/static/img/logo.png' });
    }
    showNotify(title);
}

window.copyNegotiationToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
        showNotify("✅ Message copié !");
    });
};

function renderTrends() {
    const canvas = document.getElementById('priceChart');
    if (!canvas) return;

    const dataPoints = adsData
        .filter(ad => ad.price && ad.date)
        .map(ad => ({
            x: new Date(ad.date),
            y: ad.price,
            title: ad.title
        }))
        .sort((a, b) => a.x - b.x);

    if (chart) chart.destroy();

    const ctx = canvas.getContext('2d');
    chart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Annonces (Prix vs Date)',
                data: dataPoints,
                backgroundColor: 'rgba(255, 110, 20, 0.6)',
                borderColor: '#FF6E14',
                borderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: { display: true, text: 'Analyse du Marché (Scatter Plot)', color: 'var(--text-dark)' },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const p = context.raw;
                            return `${p.title}: ${p.y}€`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'day', displayFormats: { day: 'dd/MM' } },
                    title: { display: true, text: 'Date de publication', color: 'var(--text-muted)' },
                    grid: { color: 'rgba(0,0,0,0.05)' }
                },
                y: {
                    title: { display: true, text: 'Prix (€)', color: 'var(--text-muted)' },
                    grid: { color: 'rgba(0,0,0,0.05)' }
                }
            }
        }
    });
}

function runComparison() {
    if (selectedAds.length < 2) return showNotify("Sélectionnez au moins 2 annonces pour comparer.");

    const modal = document.getElementById('compare-modal');
    const result = document.getElementById('compare-result');
    if (modal) modal.classList.add('show');

    let html = `<h3>📊 Comparatif des Offres</h3>`;
    html += `<table class="compare-table">
        <thead>
            <tr>
                <th>Critère</th>
                ${selectedAds.map(ad => `<th>${ad.title.substring(0, 30)}...</th>`).join('')}
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>💰 Prix</td>
                ${selectedAds.map(ad => `<td>${ad.price ? ad.price + '€' : 'N/A'}</td>`).join('')}
            </tr>
            <tr>
                <td>📍 Lieu</td>
                ${selectedAds.map(ad => `<td>${ad.location || 'N/A'}</td>`).join('')}
            </tr>
            <tr>
                <td>⭐ Score IA</td>
                ${selectedAds.map(ad => `<td>${ad.ai_score || '-'} / 10</td>`).join('')}
            </tr>
            <tr>
                <td>🤖 Points Forts</td>
                ${selectedAds.map(ad => `<td><small>${ad.ai_summary || 'Non analysé'}</small></td>`).join('')}
            </tr>
            <tr>
                <td>🔗 Action</td>
                ${selectedAds.map(ad => `<td><button class="btn-primary" style="padding:4px 10px; font-size:0.7rem" onclick="window.open('${ad.url}', '_blank')">Voir</button></td>`).join('')}
            </tr>
        </tbody>
    </table>`;

    result.innerHTML = html;
}


/* --- AI Chat --- */
let chatOpen = false;
function toggleChat() {
    chatOpen = !chatOpen;
    const win = document.getElementById('ai-chat-window');
    if (win) win.classList.toggle('show', chatOpen);
}

async function sendChatMessage() {
    const input = document.getElementById('ai-chat-input');
    const msg = input.value.trim();
    if (!msg) return;
    appendMessage('user', msg);
    input.value = '';
    const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: msg, search_name: currentSearchName })
    });
    const data = await resp.json();
    appendMessage('ai', data.response);
}

/* --- AI Status Polling --- */
let aiStatusInterval = null;

function toggleEmbeddedStatus(forceOpen = null) {
    const panel = document.getElementById('ai-status-embedded');
    if (!panel) return;

    if (forceOpen !== null) {
        panel.style.display = forceOpen ? 'block' : 'none';
    } else {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
}

let lastStatusLog = "";
async function updateAiStatus() {
    try {
        const resp = await fetch('/api/ai-status');
        const data = await resp.json();

        // const title = document.getElementById('ai-status-title'); // Removed in bottom panel design
        const log = document.getElementById('ai-status-log');
        const logContainer = document.getElementById('ai-status-log-container');
        const progressFill = document.getElementById('ai-status-progress');
        const progressContainer = document.getElementById('ai-status-progress-container');
        const badge = document.getElementById('ai-status-badge');

        // if (title) title.innerText = ... // Removed

        if (log && data.message && data.message !== lastStatusLog) {
            lastStatusLog = data.message;
            // Simplified log for embedded view
            log.innerHTML = `<div style="padding:2px 0">${data.message}</div>`;

            // Also log to the full system console
            logSystem(data.message, data.status === 'error' ? 'error' : 'info');
        }

        // Auto-show if running and hidden (Persistence)
        const panel = document.getElementById('ai-status-embedded');
        if (data.status === 'loading' && panel && panel.style.display === 'none') {
            panel.style.display = 'block';
            if (!aiStatusInterval) aiStatusInterval = setInterval(updateAiStatus, 1000); // Resume polling if stopped
        }

        if (progressFill && data.total > 0) {
            if (progressContainer) progressContainer.style.display = 'block';
            const percent = (data.progress / data.total) * 100;
            progressFill.style.width = percent + '%';
        } else {
            if (progressContainer) progressContainer.style.display = 'none';
        }

        if (badge) {
            badge.className = 'status-badge ' + (data.status === 'waiting' ? 'badge-waiting' : (data.status === 'error' ? 'badge-error' : (data.status === 'idle' ? 'badge-success' : 'badge-loading')));
            badge.innerText = data.status === 'waiting' ? 'PAUSE' : (data.status === 'error' ? 'ERREUR' : (data.status === 'idle' ? 'FINI' : 'TRAVAIL'));
        }

        if (data.status === 'idle' && aiStatusInterval) {
            // Keep it open, but stop polling once it's idle
            clearInterval(aiStatusInterval);
            aiStatusInterval = null;
            showNotify("✅ L'IA a terminé d'analyser vos annonces.");
            if (currentSearchName) loadHistory(currentSearchName);
        }
    } catch (e) {
        console.error("AI Status poll error", e);
    }
}


function startAiStatusPolling() {
    if (aiStatusInterval) clearInterval(aiStatusInterval);

    // Reset Log
    const log = document.getElementById('ai-status-log');
    if (log) log.innerHTML = '';
    lastStatusLog = "";

    // Open Panel
    toggleEmbeddedStatus(true);

    aiStatusInterval = setInterval(updateAiStatus, 1000);
    updateAiStatus(); // Run once
}

// Check status on load
document.addEventListener('DOMContentLoaded', () => {
    // Initial check if AI is running (persistence)
    updateAiStatus().then(() => {
        // If updateAiStatus detected running state, it would have started polling? 
        // Actually updateAiStatus doesn't start polling. Let's do it here.
        fetch('/api/ai-status').then(r => r.json()).then(d => {
            if (d.status === 'loading') {
                startAiStatusPolling();
            }
        });
    });
});

async function stopAiAnalysis() {
    // Direct stop without confirmation as requested
    // if (!confirm("Voulez-vous vraiment arrêter l'analyse en cours ?")) return;
    try {
        await fetch('/api/stop-analysis', { method: 'POST' });
        showNotify("Arrêt demandé...");
    } catch (e) {
        console.error(e);
    }
}

/* --- Feedback --- */
function openFeedbackModal() {
    document.getElementById('feedback-modal').classList.add('show');
}
function closeFeedbackModal() {
    document.getElementById('feedback-modal').classList.remove('show');
}
async function submitFeedback() {
    const type = document.querySelector('input[name="feedback-type"]:checked').value;
    const msg = document.getElementById('feedback-msg').value;

    if (!msg.trim()) {
        showNotify("Erreur: Message vide !");
        return;
    }

    try {
        const resp = await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: type, message: msg })
        });

        if (resp.ok) {
            showNotify("✅ Merci ! Votre retour a bien été enregistré. (Stocké en base)");
            document.getElementById('feedback-msg').value = '';
            closeFeedbackModal();
        } else {
            showNotify("Erreur lors de l'envoi.");
        }
    } catch (e) {
        console.error(e);
        showNotify("Erreur technique: " + e.message);
    }
}

/* --- System Logging --- */
let miniLogQueue = ["Initializing...", "System Ready.", "Waiting for action..."];

function logSystem(message, type = 'info') {
    // 1. Full Logs
    const container = document.getElementById('full-system-logs');
    if (container) {
        const time = new Date().toLocaleTimeString();
        const color = type === 'error' ? '#f48771' : (type === 'success' ? '#89d185' : '#d4d4d4');
        const entry = document.createElement('div');
        entry.style.fontFamily = 'monospace';
        entry.style.borderBottom = '1px solid #333';
        entry.style.padding = '2px 0';
        entry.innerHTML = `<span style="color:#569cd6">[${time}]</span> <span style="color:${color}">${message}</span>`;
        container.appendChild(entry);

        const scrollContainer = document.getElementById('full-system-log-container');
        if (scrollContainer) scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }

    // 2. Mini Header Logs (Last 3)
    const miniContainer = document.getElementById('header-log-mini');
    if (miniContainer) {
        // Add new message
        miniLogQueue.push(message);
        if (miniLogQueue.length > 3) miniLogQueue.shift();

        // Render
        miniContainer.innerHTML = miniLogQueue.map((m, i) => {
            // Last item gets color highlight, others fade
            const opacity = (i + 1) / 3;
            const style = i === 2 ? (type === 'error' ? 'color:#f48771' : (type === 'success' ? 'color:#89d185' : 'color:#fff')) : `opacity:${opacity}`;
            return `<div style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; ${style}">${m}</div>`;
        }).join('');
    }
}

function copySystemLogs() {
    const container = document.getElementById('full-system-logs');
    if (!container) return;
    navigator.clipboard.writeText(container.innerText).then(() => {
        showNotify("Logs copiés dans le presse-papier !");
    });
}

function clearSystemLogs() {
    const container = document.getElementById('full-system-logs');
    if (container) container.innerHTML = '';
}

function showNotify(message) {
    const notification = document.getElementById('notification');
    notification.innerText = message;
    notification.classList.add('show');

    // Log to system console too
    logSystem(message, message.includes('Erreur') || message.includes('❌') ? 'error' : 'success');

    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}


function appendMessage(role, text) {
    const container = document.getElementById('ai-chat-messages');
    if (!container) return;
    const div = document.createElement('div');
    div.className = 'message ' + role;
    div.innerHTML = (typeof marked !== 'undefined') ? marked.parse(text) : text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function openHelpModal() {
    const modal = document.getElementById('help-modal');
    if (modal) modal.classList.add('show');
}

function closeHelpModal() {
    const modal = document.getElementById('help-modal');
    if (modal) modal.classList.remove('show');
}

function openManualAdModal() {
    const m = document.getElementById('manual-ad-modal');
    if (m) m.classList.add('show');
}


async function submitManualAd() {
    const url = document.getElementById('manual-ad-url').value;
    const resp = await fetch('/api/add-manual-ad', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, search_name: currentSearchName })
    });
    if (resp.ok) { showNotify("Ajouté."); document.getElementById('manual-ad-modal').classList.remove('show'); loadHistory(currentSearchName); }
}

function setViewMode(mode) {
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    const btn = document.getElementById('btn-view-' + mode);
    if (btn) btn.classList.add('active');
    ['ads-grid-history', 'ads-grid-live', 'ads-grid-top'].forEach(g => {
        const el = document.getElementById(g);
        if (el) el.classList.toggle('list-mode', mode === 'list');
    });
}

function runDashboardSort() {
    const sort = document.getElementById('dashboard-sort').value;
    if (sort === 'price-asc') adsData.sort((a, b) => (a.price || 0) - (b.price || 0));
    else if (sort === 'score-desc') adsData.sort((a, b) => (b.ai_score || 0) - (a.ai_score || 0));
    else if (sort === 'date-desc') adsData.sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0));
    renderAds(adsData, 'ads-grid-history');
}

function openGemBuilder() { document.getElementById('gem-builder-modal').classList.add('show'); }
function closeGemModal() { document.getElementById('gem-builder-modal').classList.remove('show'); }
async function buildGem() {
    const goal = document.getElementById('gem-goal').value;
    const resp = await fetch('/api/gem-builder', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ goal }) });
    const data = await resp.json();
    const preview = document.getElementById('gem-preview');
    if (preview) { preview.innerText = data.instructions; preview.style.display = 'block'; }
    const btn = document.getElementById('btn-use-gem');
    if (btn) btn.style.display = 'block';
}
function useGem() { document.getElementById('ai-context').value = document.getElementById('gem-preview').innerText; closeGemModal(); }

async function runBatchAnalysis() {
    const loader = document.getElementById('global-loader');
    if (loader) loader.style.display = 'block';

    startAiStatusPolling();

    // Prepare payload
    let payload = {};

    // If we have live ads in memory (adsData), send them to be saved & analyzed
    // Limit to avoiding sending massive payloads if unnecessary, but 200 items is fine.
    if (adsData && adsData.length > 0) {
        // Enrich with current search name if possible
        const cleanAds = adsData.map(ad => ({
            ...ad,
            search_name: currentSearchName || 'Live Search'
        }));
        payload.ads_data = cleanAds;
        payload.ad_ids = cleanAds.map(a => a.id); // Valid IDs
    }

    const resp = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const res = await resp.json();
    showNotify(res.message);
    loadHistory(currentSearchName);
    if (loader) loader.style.display = 'none';
}

/* --- Selective Analysis & Settings --- */
async function runSelectiveAnalysis() {
    if (selectedAds.length === 0) return showNotify("Sélectionnez au moins une annonce.");
    const prompt = document.getElementById('selective-prompt').value.trim();
    if (!prompt) return showNotify("Veuillez entrer un prompt pour cette analyse.");

    showNotify(`Lancement de l'analyse sur ${selectedAds.length} annonce(s)...`);
    const adIds = selectedAds.map(ad => ad.id);

    startAiStatusPolling();

    try {
        const resp = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ad_ids: adIds, custom_prompt: prompt })
        });
        const data = await resp.json();
        if (resp.ok) {
            showNotify(data.message);
            await loadHistory(currentSearchName);
            clearSelection();
            document.getElementById('selective-prompt').value = '';
        } else showNotify(data.message || "Erreur IA.");
    } catch (e) {
        showNotify("Erreur technique de connexion.");
    }
}

async function openGlobalSettings() {
    try {
        const resp = await fetch('/api/settings');
        const s = await resp.json();

        document.getElementById('global-google-api-key').value = s.google_api_key || '';
        document.getElementById('global-discord-webhook').value = s.discord_webhook || '';
        document.getElementById('global-default-ai-context').value = s.default_ai_context || '';
        document.getElementById('global-default-refresh-mode').value = s.default_refresh_mode || 'manual';
        document.getElementById('global-default-refresh-interval').value = s.default_refresh_interval || 60;

        const platforms = s.default_platforms || { lbc: true, ebay: false, vinted: false };
        document.getElementById('global-default-lbc').checked = !!platforms.lbc;
        document.getElementById('global-default-ebay').checked = !!platforms.ebay;
        document.getElementById('global-default-vinted').checked = !!platforms.vinted;

        document.getElementById('global-settings-modal').classList.add('show');
    } catch (e) {
        showNotify("Erreur lors du chargement des paramètres.");
    }
}

function closeGlobalSettings() {
    document.getElementById('global-settings-modal').classList.remove('show');
}

async function saveGlobalSettings() {
    const payload = {
        google_api_key: document.getElementById('global-google-api-key').value,
        discord_webhook: document.getElementById('global-discord-webhook').value,
        default_ai_context: document.getElementById('global-default-ai-context').value,
        default_refresh_mode: document.getElementById('global-default-refresh-mode').value,
        default_refresh_interval: parseInt(document.getElementById('global-default-refresh-interval').value) || 60,
        default_platforms: {
            lbc: document.getElementById('global-default-lbc').checked,
            ebay: document.getElementById('global-default-ebay').checked,
            vinted: document.getElementById('global-default-vinted').checked
        }
    };

    try {
        const resp = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (resp.ok) {
            showNotify("Configuration globale enregistrée !");
            closeGlobalSettings();
        } else {
            showNotify("Erreur lors de l'enregistrement.");
        }
    } catch (e) {
        showNotify("Erreur technique.");
    }
}

async function clearAllAnalyses() {
    if (!currentSearchName) return;
    if (!confirm(`Supprimer TOUTES les analyses IA pour la veille "${currentSearchName}" ?`)) return;

    try {
        const resp = await fetch('/api/clear-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ search_name: currentSearchName })
        });
        const data = await resp.json();
        if (resp.ok) {
            showNotify("Analyses réinitialisées.");
            await loadHistory(currentSearchName);
        } else showNotify("Erreur lors de la suppression.");
    } catch (e) {
        showNotify("Erreur technique.");
    }
}

async function clearSelectedAnalyses() {
    if (selectedAds.length === 0) return;
    if (!confirm(`Supprimer les analyses pour les ${selectedAds.length} annonce(s) sélectionnée(s) ?`)) return;

    const adIds = selectedAds.map(ad => ad.id);
    try {
        const resp = await fetch('/api/clear-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ad_ids: adIds })
        });
        const data = await resp.json();
        if (resp.ok) {
            showNotify(`${adIds.length} analyses supprimées.`);
            await loadHistory(currentSearchName);
            clearSelection();
        } else showNotify("Erreur lors de la suppression.");
    } catch (e) {
        showNotify("Erreur technique.");
    }
}

async function openSearchSettings(name) {
    if (!name) name = currentSearchName;
    if (!name) return;
    currentSearchName = name;
    const resp = await fetch(`/api/searches/${encodeURIComponent(name)}`);
    const s = await resp.json();

    document.getElementById('settings-watch-name').innerText = s.name;
    document.getElementById('settings-ai-context').value = s.ai_context || '';
    document.getElementById('settings-query-text').value = s.query_text || '';
    document.getElementById('settings-discord-webhook').value = s.discord_webhook || '';
    document.getElementById('settings-refresh-mode').value = s.refresh_mode || 'manual';
    document.getElementById('settings-refresh-interval').value = s.refresh_interval || 60;
    document.getElementById('settings-deep-search').checked = !!s.deep_search;


    const platforms = robustParseJSON(s.platforms, { lbc: true, ebay: false, vinted: false });
    document.getElementById('settings-platform-lbc').checked = !!platforms.lbc;
    document.getElementById('settings-platform-ebay').checked = !!platforms.ebay;
    document.getElementById('settings-platform-vinted').checked = !!platforms.vinted;

    document.getElementById('settings-interval-group').style.display = (s.refresh_mode === 'auto' ? 'block' : 'none');
    document.getElementById('search-settings-modal').classList.add('show');
}

async function saveSearchSettings() {
    const payload = {
        query_text: document.getElementById('settings-query-text').value,
        ai_context: document.getElementById('settings-ai-context').value,
        discord_webhook: document.getElementById('settings-discord-webhook').value,
        refresh_mode: document.getElementById('settings-refresh-mode').value,
        refresh_interval: parseInt(document.getElementById('settings-refresh-interval').value) || 60,
        platforms: {
            lbc: document.getElementById('settings-platform-lbc').checked,
            ebay: document.getElementById('settings-platform-ebay').checked,
            vinted: document.getElementById('settings-platform-vinted').checked
        },
        deep_search: document.getElementById('settings-deep-search').checked ? 1 : 0
    };


    try {
        const resp = await fetch(`/api/searches/${encodeURIComponent(currentSearchName)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (resp.ok) {
            showNotify("Paramètres mis à jour !");
            document.getElementById('search-settings-modal').classList.remove('show');
            loadWatches();
        } else showNotify("Erreur lors de la sauvegarde.");
    } catch (e) {
        showNotify("Erreur technique.");
    }
}

async function testDiscord() {
    const webhook = document.getElementById('global-discord-webhook').value;
    if (!webhook) return showNotify("Webook requis pour tester.");

    showNotify("Envoi du test Discord...");
    try {
        const resp = await fetch('/api/settings/test-discord', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ discord_webhook: webhook })
        });
        const data = await resp.json();
        if (resp.ok) showNotify("🚀 Test Discord envoyé !");
        else showNotify("❌ Erreur: " + (data.error || "Échec"));
    } catch (e) {
        showNotify("Erreur de connexion au serveur.");
    }
}

/* --- Export Top 10 --- */
function openExportModal() {
    const modal = document.getElementById('export-modal');
    if (modal) {
        modal.classList.add('show');
        generateExportText();
    }
}

function generateExportText() {
    const includeAI = document.getElementById('export-include-ai').checked;
    const topAds = adsData
        .filter(ad => ad.ai_score !== null)
        .sort((a, b) => b.ai_score - a.ai_score)
        .slice(0, 10);

    let text = `🏆 TOP 10 AFFAIRES - ${currentSearchName || 'Veille'}\n`;
    text += `Généré le ${new Date().toLocaleString()}\n`;
    text += `==========================================\n\n`;

    topAds.forEach((ad, i) => {
        text += `${i + 1}. ${ad.title.toUpperCase()}\n`;
        text += `   💰 Prix : ${ad.price ? ad.price.toLocaleString() + '€' : 'N/A'}\n`;
        text += `   📍 Lieu : ${ad.location || 'N/A'}\n`;
        if (includeAI && ad.ai_score) {
            text += `   ⭐ Note IA : ${ad.ai_score}/10\n`;
            text += `   🤖 Résumé : ${ad.ai_summary || 'N/A'}\n`;
        }
        text += `   🔗 Lien : ${ad.url}\n\n`;
    });

    document.getElementById('export-text').value = text;
}

function copyToClipboard() {
    const textarea = document.getElementById('export-text');
    textarea.select();
    document.execCommand('copy');
    showNotify("✅ Top 10 copié dans le presse-papier !");
    document.getElementById('export-modal').classList.remove('show');
}

async function submitManualAd() {
    const url = document.getElementById('manual-ad-url').value.trim();
    if (!url) return showNotify("Veuillez entrer une URL.");

    showNotify("⏳ Ajout de l'annonce en cours...");
    try {
        const resp = await fetch('/api/ads/manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, search_name: currentSearchName || 'Ajout Manuel' })
        });
        const data = await resp.json();
        if (resp.ok) {
            showNotify("✅ Annonce ajoutée avec succès !");
            document.getElementById('manual-ad-modal').classList.remove('show');
            document.getElementById('manual-ad-url').value = '';
            await loadHistory(currentSearchName);
        } else {
            showNotify("❌ " + (data.message || data.error || "Erreur lors de l'ajout."));
        }
    } catch (e) {
        showNotify("Erreur technique de connexion.");
    }
}

async function shareToDiscord(adId) {

    try {
        const resp = await fetch(`/api/ads/${adId}/share-discord`, { method: 'POST' });
        const data = await resp.json();
        if (resp.ok) showNotify("📢 " + data.message);
        else showNotify("❌ " + (data.error || "Erreur lors de l'envoi."));
    } catch (e) {
        showNotify("Erreur technique de connexion.");
    }
}

async function saveSelectedAdsToWatch() {
    if (selectedAds.length === 0) return showNotify("Sélection vide.");

    // Create logic to choose watch
    const watches = await getWatchNames();
    let options = watches.map(w => `<option value="${w}">${w}</option>`).join('');
    options += `<option value="__NEW__">➕ Nouvelle veille...</option>`;

    const html = `
        <div class="form-group">
            <label>Choisir une veille de destination :</label>
            <select id="target-watch-select" onchange="document.getElementById('new-watch-name-group').style.display = (this.value==='__NEW__'?'block':'none')">
                ${options}
            </select>
        </div>
        <div class="form-group" id="new-watch-name-group" style="display:none">
            <label>Nom de la nouvelle veille :</label>
            <input type="text" id="target-new-watch-name" placeholder="Ex: Vélos Specialized">
        </div>
        <div style="margin-top:10px; display:flex; gap:10px">
            <button class="btn-primary" onclick="submitAddToWatch()">Valider</button>
            <button class="btn-link" onclick="closeModal()">Annuler</button>
        </div>
    `;

    const modal = document.getElementById('compare-modal');
    const result = document.getElementById('compare-result');
    if (result) result.innerHTML = `<h3>💾 Sauvegarder la sélection</h3>${html}`;
    if (modal) modal.classList.add('show');
}

async function getWatchNames() {
    const resp = await fetch('/api/searches');
    const data = await resp.json();
    return data.map(s => s.name);
}

async function submitAddToWatch() {
    const select = document.getElementById('target-watch-select');
    let targetName = select.value;

    if (targetName === '__NEW__') {
        targetName = document.getElementById('target-new-watch-name').value.trim();
        if (!targetName) return showNotify("Nom de veille requis.");

        // Create new watch first
        const resp = await fetch('/api/searches', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sentence: targetName, queries: [targetName],
                locations: [], platforms: { lbc: true }
            })
        });
        if (!resp.ok) return showNotify("Erreur créat. veille.");
    }

    const adIds = selectedAds.map(a => a.id);
    const result = await fetch('/api/ads/move-to-watch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ad_ids: adIds, target_watch: targetName })
    });

    if (result.ok) {
        showNotify(`✅ ${adIds.length} annonces transférées vers "${targetName}".`);
        closeModal();
        clearSelection();
        loadWatches(); // Refresh sidebar
    } else {
        showNotify("Erreur lors du transfert.");
    }
}

if (localStorage.getItem('theme') === 'dark') document.body.classList.add('dark-theme');
document.addEventListener('DOMContentLoaded', init);

let showingManualOnly = false;
function toggleManualFilter() {
    showingManualOnly = !showingManualOnly;
    const btn = document.getElementById('btn-filter-manual');
    if (btn) btn.classList.toggle('active', showingManualOnly);

    if (showingManualOnly) {
        const manualAds = adsData.filter(a => a.source === 'MANUAL');
        renderAds(manualAds, 'ads-grid-history');
        showNotify(`Affichage de ${manualAds.length} annonces manuelles.`);
    } else {
        renderAds(adsData, 'ads-grid-history'); // Restore full list
    }
}
