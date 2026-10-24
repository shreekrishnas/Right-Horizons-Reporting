// ═══════════════════ Metric Builder ═══════════════════
// Drag fields from the field list onto Group by / Values / Filters. The view
// re-queries GA4 or Search Console on every change. Built views can be saved to
// "My board" and pinned to the Dashboard overview (stored in this browser).

const MB_STORE = 'rh_metric_board_v1';
let mbCatalog = null;
let mbState = null;          // the view being edited
let mbRange = { preset: '28d', start: '', end: '' };
let mbTimer = null;
let mbSeq = 0;
let mbLastResult = null;
const mbCache = new Map();

const MB_DEFAULTS = {
    ga4: { dimensions: ['sessionDefaultChannelGroup'], metrics: ['sessions', 'totalUsers', 'engagementRate'], visual: 'bar' },
    gsc: { dimensions: ['query'], metrics: ['clicks', 'impressions', 'ctr', 'position'], visual: 'table' },
};
const MB_LOWER_IS_BETTER = new Set(['bounceRate', 'position']);
const MB_VISUALS = [
    { id: 'table', label: 'Table' }, { id: 'bar', label: 'Bar' }, { id: 'line', label: 'Line' },
    { id: 'donut', label: 'Donut' }, { id: 'cards', label: 'Number cards' },
];

function _mbNewState(source) {
    const d = MB_DEFAULTS[source];
    return { id: '', title: '', source, dimensions: [...d.dimensions], metrics: [...d.metrics], filters: [],
             visual: d.visual, limit: 25, sort: null, compare: false };
}

// ── Storage (per browser) ──
function mbLoadBoard() {
    try { return JSON.parse(localStorage.getItem(MB_STORE) || '[]'); } catch (e) { return []; }
}
function mbSaveBoard(board) {
    try { localStorage.setItem(MB_STORE, JSON.stringify(board)); } catch (e) { /* storage blocked */ }
}

// ── Field helpers ──
function mbField(source, id) {
    if (!mbCatalog) return null;
    const c = mbCatalog[source];
    const d = c.dimensions.find(f => f.id === id);
    if (d) return { ...d, kind: 'dimension' };
    const m = c.metrics.find(f => f.id === id);
    return m ? { ...m, kind: 'metric' } : null;
}
function mbLabel(source, id) { const f = mbField(source, id); return f ? f.label : id; }

function mbFmt(source, id, v) {
    if (v === null || v === undefined || v === '') return '—';
    const f = mbField(source, id);
    const fmt = f ? f.fmt : 'text';
    const n = Number(v);
    switch (fmt) {
        case 'int': return Math.round(n).toLocaleString('en-IN');
        case 'ratio': return (n * 100).toFixed(1) + '%';
        case 'pct': return n.toFixed(2) + '%';
        case 'float': return n.toFixed(2);
        case 'sec': { const s = Math.round(n); return Math.floor(s / 60) + 'm ' + String(s % 60).padStart(2, '0') + 's'; }
        default: return String(v);
    }
}
function mbDelta(metric, now, prev) {
    if (prev === null || prev === undefined || !Number(prev)) return '';
    const pct = (Number(now) - Number(prev)) / Math.abs(Number(prev)) * 100;
    const good = MB_LOWER_IS_BETTER.has(metric) ? pct < 0 : pct > 0;
    const cls = Math.abs(pct) < 0.5 ? 'flat' : (good ? 'up' : 'down');
    return `<span class="mb-delta ${cls}">${pct >= 0 ? '▲' : '▼'} ${Math.abs(pct).toFixed(1)}%</span>`;
}

// ── Dates ──
function mbDates() {
    const fmt = d => d.toISOString().slice(0, 10);
    const today = new Date();
    const p = mbRange.preset;
    if (p === 'custom' && mbRange.start && mbRange.end) return { start: mbRange.start, end: mbRange.end };
    if (p === 'dashboard' && typeof dateStart !== 'undefined' && dateStart) return { start: dateStart, end: dateEnd };
    if (p === 'this_month') return { start: fmt(new Date(today.getFullYear(), today.getMonth(), 1)), end: fmt(today) };
    if (p === 'last_month') {
        const s = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        const e = new Date(today.getFullYear(), today.getMonth(), 0);
        return { start: fmt(s), end: fmt(e) };
    }
    const days = { '7d': 7, '28d': 28, '90d': 90 }[p] || 28;
    const s = new Date(today); s.setDate(s.getDate() - (days - 1));
    return { start: fmt(s), end: fmt(today) };
}

// ── Query ──
async function mbQuery(spec, dates, domain) {
    const body = {
        domain: domain || currentDomain, source: spec.source, dimensions: spec.dimensions, metrics: spec.metrics,
        filters: spec.filters, limit: spec.visual === 'cards' ? 1 : spec.limit, sort: spec.sort,
        compare: !!spec.compare, start: dates.start, end: dates.end,
    };
    if (spec.visual === 'cards') body.dimensions = [];
    const key = JSON.stringify(body);
    if (mbCache.has(key)) return mbCache.get(key);
    const res = await api('/api/explore', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    mbCache.set(key, res);
    if (mbCache.size > 60) mbCache.delete(mbCache.keys().next().value);
    return res;
}

// ── Init ──
async function initMetricBuilder() {
    if (!mbCatalog) {
        try { mbCatalog = await api('/api/explore/fields'); }
        catch (e) { document.getElementById('mb-canvas').innerHTML = '<div class="mb-empty">Could not load the field list. Refresh the page to try again.</div>'; return; }
    }
    if (!mbState) mbState = _mbNewState('ga4');
    mbRenderAll();
    mbRun();
    mbRenderBoard();
}

function mbRenderAll() {
    document.querySelectorAll('#mb-source button').forEach(b => b.classList.toggle('active', b.dataset.src === mbState.source));
    document.querySelectorAll('#mb-range button').forEach(b => b.classList.toggle('active', b.dataset.range === mbRange.preset));
    document.getElementById('mb-custom').hidden = mbRange.preset !== 'custom';
    document.getElementById('mb-compare').checked = !!mbState.compare;
    document.getElementById('mb-limit').value = String(mbState.limit);
    document.getElementById('mb-title').value = mbState.title || '';
    const acct = document.getElementById('mb-account');
    if (acct) acct.textContent = (domains[currentDomain] && domains[currentDomain].label) || currentDomain;
    mbRenderFields();
    mbRenderShelves();
    mbRenderVisuals();
    mbRenderSort();
}

// ── Field list ──
function mbRenderFields() {
    const box = document.getElementById('mb-fields');
    const q = (document.getElementById('mb-field-search').value || '').toLowerCase();
    const c = mbCatalog[mbState.source];
    const match = f => !q || f.label.toLowerCase().includes(q);
    const groups = {};
    c.dimensions.filter(match).forEach(f => (groups[f.group] = groups[f.group] || []).push(f));
    let html = '<div class="mb-fgroup-title">Dimensions <small>group by these</small></div>';
    Object.entries(groups).forEach(([g, fs]) => {
        html += `<div class="mb-fsub">${esc(g)}</div>`;
        fs.forEach(f => { html += mbFieldChip(f, 'dimension'); });
    });
    const mets = c.metrics.filter(match);
    html += '<div class="mb-fgroup-title">Metrics <small>numbers to show</small></div>';
    mets.forEach(f => { html += mbFieldChip(f, 'metric'); });
    if (!Object.keys(groups).length && !mets.length) html += '<div class="mb-hint">No fields match.</div>';
    box.innerHTML = html;
    box.querySelectorAll('.mb-field').forEach(el => {
        el.addEventListener('dragstart', e => mbDragStart(e, { from: 'fields', id: el.dataset.id }));
        el.addEventListener('dragend', mbDragEnd);
        el.querySelector('.mb-add').addEventListener('click', () => mbAdd(el.dataset.id, el.dataset.kind === 'metric' ? 'metrics' : 'dimensions'));
        el.querySelector('.mb-addf').addEventListener('click', () => mbAdd(el.dataset.id, 'filters'));
    });
}
function mbFieldChip(f, kind) {
    const used = mbState.dimensions.includes(f.id) || mbState.metrics.includes(f.id);
    return `<div class="mb-field ${kind}${used ? ' used' : ''}" draggable="true" data-id="${esc(f.id)}" data-kind="${kind}">
        <span class="mb-ico">${kind === 'metric' ? '#' : 'Aa'}</span><span class="mb-fl">${esc(f.label)}</span>
        <button type="button" class="mb-add" title="Add to ${kind === 'metric' ? 'Values' : 'Group by'}" aria-label="Add ${esc(f.label)}">+</button>
        <button type="button" class="mb-addf" title="Filter by ${esc(f.label)}" aria-label="Filter by ${esc(f.label)}">⚲</button>
    </div>`;
}

// ── Shelves ──
const MB_SHELVES = { dimensions: 'mb-shelf-dims', metrics: 'mb-shelf-mets', filters: 'mb-shelf-filters' };

function mbRenderShelves() {
    Object.entries(MB_SHELVES).forEach(([shelf, id]) => {
        const el = document.getElementById(id);
        const items = mbState[shelf];
        const hint = { dimensions: 'Drop dimensions here, e.g. Channel, Country, Date',
                       metrics: 'Drop metrics here, e.g. Sessions, Clicks',
                       filters: 'Drop any field here to filter' }[shelf];
        if (!items.length) { el.innerHTML = `<span class="mb-placeholder">${hint}</span>`; return; }
        el.innerHTML = items.map((it, i) => {
            const fid = shelf === 'filters' ? it.field : it;
            const f = mbField(mbState.source, fid);
            const kind = f ? f.kind : 'dimension';
            const summary = shelf === 'filters' ? mbFilterSummary(it) : '';
            return `<span class="mb-pill ${kind}${shelf === 'filters' ? ' filter' : ''}" draggable="true" data-shelf="${shelf}" data-i="${i}" tabindex="0">
                ${shelf === 'filters' ? '<span class="mb-pill-btn" role="button">' : ''}<b>${esc(mbLabel(mbState.source, fid))}</b>${summary ? ` <span class="mb-fs">${summary}</span>` : ''}${shelf === 'filters' ? '</span>' : ''}
                <button type="button" class="mb-x" aria-label="Remove">×</button></span>`;
        }).join('');
        el.querySelectorAll('.mb-pill').forEach(p => {
            const i = +p.dataset.i;
            p.addEventListener('dragstart', e => mbDragStart(e, { from: shelf, index: i }));
            p.addEventListener('dragend', mbDragEnd);
            p.querySelector('.mb-x').addEventListener('click', ev => { ev.stopPropagation(); mbState[shelf].splice(i, 1); mbChanged(); });
            if (shelf === 'filters') {
                p.addEventListener('click', () => mbOpenFilter(i));
                p.addEventListener('keydown', ev => { if (ev.key === 'Enter') mbOpenFilter(i); });
            }
        });
    });
}

function mbFilterSummary(f) {
    const v = f.values || [];
    if (!v.length) return '<i>(choose values)</i>';
    const opTxt = { in: 'is', not_in: 'is not', contains: 'contains', not_contains: "doesn't contain", starts_with: 'starts with',
                    ends_with: 'ends with', equals: '=', not_equals: '≠', gt: '>', lt: '<', gte: '≥', lte: '≤' }[f.op] || f.op;
    const shown = v.length > 2 ? `${esc(v[0])}, ${esc(v[1])} +${v.length - 2}` : v.map(esc).join(', ');
    return `${opTxt} ${shown}`;
}

function mbAdd(id, shelf, index) {
    const f = mbField(mbState.source, id);
    if (!f) return;
    if (shelf === 'filters') {
        const flt = { field: id, op: f.kind === 'metric' ? 'gt' : 'in', values: [] };
        if (index === undefined) mbState.filters.push(flt); else mbState.filters.splice(index, 0, flt);
        mbChanged(false);
        mbOpenFilter(index === undefined ? mbState.filters.length - 1 : index);
        return;
    }
    const target = f.kind === 'metric' ? 'metrics' : 'dimensions';
    if (shelf !== target) { mbToast(f.kind === 'metric' ? 'Metrics go in Values' : 'Dimensions go in Group by'); shelf = target; }
    if (mbState[shelf].includes(id)) return;
    if (shelf === 'dimensions' && mbState.dimensions.length >= 4) { mbToast('Up to 4 dimensions'); return; }
    if (shelf === 'metrics' && mbState.metrics.length >= 8) { mbToast('Up to 8 metrics'); return; }
    if (index === undefined) mbState[shelf].push(id); else mbState[shelf].splice(index, 0, id);
    mbChanged();
}

// ── Drag and drop ──
let mbDrag = null;
function mbDragStart(e, payload) {
    mbDrag = payload;
    e.dataTransfer.effectAllowed = 'move';
    try { e.dataTransfer.setData('text/plain', JSON.stringify(payload)); } catch (_) { /* some browsers */ }
    e.currentTarget.classList.add('dragging');
    document.getElementById('view-builder').classList.add('mb-dragging');
}
function mbDragEnd(e) {
    e.currentTarget.classList.remove('dragging');
    document.getElementById('view-builder').classList.remove('mb-dragging');
    document.querySelectorAll('.mb-shelf.over').forEach(s => s.classList.remove('over'));
    mbDrag = null;
}
function mbSetupDrop() {
    Object.entries(MB_SHELVES).forEach(([shelf, id]) => {
        const el = document.getElementById(id);
        el.addEventListener('dragover', e => { e.preventDefault(); el.classList.add('over'); });
        el.addEventListener('dragleave', e => { if (!el.contains(e.relatedTarget)) el.classList.remove('over'); });
        el.addEventListener('drop', e => {
            e.preventDefault(); el.classList.remove('over');
            const d = mbDrag; if (!d) return;
            const pill = e.target.closest('.mb-pill');
            const at = pill ? +pill.dataset.i : undefined;
            if (d.from === 'fields') { mbAdd(d.id, shelf, at); return; }
            const item = mbState[d.from][d.index];
            const fid = d.from === 'filters' ? item.field : item;
            if (d.from === shelf) {           // reorder within a shelf
                mbState[shelf].splice(d.index, 1);
                const to = at === undefined ? mbState[shelf].length : (at > d.index ? at - 1 : at);
                mbState[shelf].splice(to, 0, item);
                mbChanged(shelf !== 'filters');
                return;
            }
            mbState[d.from].splice(d.index, 1); // move between shelves
            mbAdd(fid, shelf, at);
        });
    });
    const fields = document.getElementById('mb-fields');   // drop back on the list removes
    fields.addEventListener('dragover', e => { if (mbDrag && mbDrag.from !== 'fields') e.preventDefault(); });
    fields.addEventListener('drop', e => {
        e.preventDefault();
        if (mbDrag && mbDrag.from !== 'fields') { mbState[mbDrag.from].splice(mbDrag.index, 1); mbChanged(); }
    });
}

// ── Filter editor ──
async function mbOpenFilter(i) {
    const f = mbState.filters[i]; if (!f) return;
    const fld = mbField(mbState.source, f.field);
    const pop = document.getElementById('mb-filter-pop');
    const isMetric = fld.kind === 'metric';
    const ops = isMetric
        ? [['gt', 'greater than'], ['lt', 'less than'], ['gte', 'at least'], ['lte', 'at most']]
        : [['in', 'is one of'], ['not_in', 'is not one of'], ['contains', 'contains'], ['not_contains', "doesn't contain"],
           ['starts_with', 'starts with'], ['ends_with', 'ends with']];
    pop.hidden = false;
    pop.innerHTML = `
        <div class="mb-pop-hd"><b>Filter: ${esc(fld.label)}</b><button type="button" class="mb-x" id="mb-pop-close" aria-label="Close">×</button></div>
        <div class="mb-pop-row"><select id="mb-pop-op">${ops.map(([v, l]) => `<option value="${v}"${f.op === v ? ' selected' : ''}>${l}</option>`).join('')}</select></div>
        <div id="mb-pop-body"></div>
        <div class="mb-pop-ft"><button type="button" class="mb-btn ghost" id="mb-pop-clear">Clear</button><button type="button" class="mb-btn" id="mb-pop-apply">Apply filter</button></div>`;
    const draft = { op: f.op, values: [...(f.values || [])] };
    const body = () => document.getElementById('mb-pop-body');
    const renderBody = async () => {
        if (isMetric || !['in', 'not_in'].includes(draft.op)) {
            const hint = isMetric && mbField(mbState.source, f.field).fmt === 'ratio' ? ' (use 0.5 for 50%)' : '';
            body().innerHTML = `<input id="mb-pop-text" class="mb-input" type="${isMetric ? 'number' : 'text'}" step="any" placeholder="${isMetric ? 'Number' + hint : 'Text'}" value="${esc(draft.values[0] || '')}">`;
            const t = document.getElementById('mb-pop-text');
            t.addEventListener('input', () => { draft.values = t.value === '' ? [] : [t.value]; });
            t.focus();
            return;
        }
        body().innerHTML = `<input id="mb-pop-search" class="mb-input" type="search" placeholder="Search values…">
            <div class="mb-vals" id="mb-pop-vals"><div class="mb-hint">Loading values…</div></div>`;
        const load = async (q) => {
            const dates = mbDates();
            let vals = [];
            try {
                vals = await api(`/api/explore/values?domain=${currentDomain}&source=${mbState.source}&field=${encodeURIComponent(f.field)}&start=${dates.start}&end=${dates.end}&q=${encodeURIComponent(q || '')}`);
            } catch (e) { document.getElementById('mb-pop-vals').innerHTML = '<div class="mb-hint">Could not load values.</div>'; return; }
            const all = [...new Set([...draft.values, ...vals.map(v => v.value)])];
            const counts = Object.fromEntries(vals.map(v => [v.value, v.count]));
            document.getElementById('mb-pop-vals').innerHTML = all.length ? all.map((v, k) => `
                <label class="mb-val"><input type="checkbox" id="mb-v-${k}" value="${esc(v)}"${draft.values.includes(v) ? ' checked' : ''}>
                <span>${esc(v || '(empty)')}</span><small>${counts[v] !== undefined ? Math.round(counts[v]).toLocaleString('en-IN') : ''}</small></label>`).join('')
                : '<div class="mb-hint">No values in this period.</div>';
            document.querySelectorAll('#mb-pop-vals input').forEach(cb => cb.addEventListener('change', () => {
                draft.values = cb.checked ? [...new Set([...draft.values, cb.value])] : draft.values.filter(x => x !== cb.value);
            }));
        };
        let st;
        document.getElementById('mb-pop-search').addEventListener('input', e => { clearTimeout(st); st = setTimeout(() => load(e.target.value), 300); });
        load('');
    };
    document.getElementById('mb-pop-op').addEventListener('change', e => {
        const wasList = ['in', 'not_in'].includes(draft.op), isList = ['in', 'not_in'].includes(e.target.value);
        draft.op = e.target.value;
        if (wasList !== isList) { draft.values = []; renderBody(); }
    });
    document.getElementById('mb-pop-close').addEventListener('click', () => { pop.hidden = true; });
    document.getElementById('mb-pop-clear').addEventListener('click', () => { draft.values = []; renderBody(); });
    document.getElementById('mb-pop-apply').addEventListener('click', () => {
        mbState.filters[i] = { field: f.field, op: draft.op, values: draft.values };
        pop.hidden = true; mbChanged();
    });
    renderBody();
}

// ── Visual / sort controls ──
function mbRenderVisuals() {
    const box = document.getElementById('mb-visuals');
    box.innerHTML = MB_VISUALS.map(v => `<button type="button" data-v="${v.id}" class="${mbState.visual === v.id ? 'active' : ''}">${v.label}</button>`).join('');
    box.querySelectorAll('button').forEach(b => b.addEventListener('click', () => { mbState.visual = b.dataset.v; mbChanged(); }));
}
function mbRenderSort() {
    const sel = document.getElementById('mb-sort');
    const opts = [['', 'Default order']];
    mbState.metrics.forEach(m => { opts.push([m + '|desc', mbLabel(mbState.source, m) + ' — high to low'], [m + '|asc', mbLabel(mbState.source, m) + ' — low to high']); });
    mbState.dimensions.forEach(d => { opts.push([d + '|asc', mbLabel(mbState.source, d) + ' — A to Z']); });
    const cur = mbState.sort ? `${mbState.sort.field}|${mbState.sort.desc ? 'desc' : 'asc'}` : '';
    sel.innerHTML = opts.map(([v, l]) => `<option value="${v}"${v === cur ? ' selected' : ''}>${esc(l)}</option>`).join('');
}

function mbChanged(run = true) {
    if (mbState.sort && !mbState.metrics.concat(mbState.dimensions).includes(mbState.sort.field)) mbState.sort = null;
    mbRenderFields(); mbRenderShelves(); mbRenderVisuals(); mbRenderSort();
    if (run) { clearTimeout(mbTimer); mbTimer = setTimeout(mbRun, 250); }
}

// ── Run & render ──
async function mbRun() {
    const canvas = document.getElementById('mb-canvas');
    if (!mbState.metrics.length) { canvas.innerHTML = '<div class="mb-empty">Drag at least one metric into <b>Values</b> to see numbers.</div>'; return; }
    const seq = ++mbSeq;
    canvas.classList.add('loading');
    try {
        const res = await mbQuery(mbState, mbDates());
        if (seq !== mbSeq) return;
        mbLastResult = res;
        mbRenderResult(canvas, mbState, res, 'mb-main');
    } catch (e) {
        if (seq !== mbSeq) return;
        const msg = String(e.message || e).replace(/^\d+:\s*/, '');
        let detail = msg; try { detail = JSON.parse(msg).detail || msg; } catch (_) {}
        canvas.innerHTML = `<div class="mb-empty err">Couldn't load this view: ${esc(detail)}</div>`;
    } finally { if (seq === mbSeq) canvas.classList.remove('loading'); }
}

function mbRenderResult(el, spec, res, cid) {
    const src = spec.source;
    const tot = res.totals || {};
    const ptot = res.compare ? res.compare.totals : null;
    const cards = spec.metrics.map(m => `<div class="mb-kpi"><span class="l">${esc(mbLabel(src, m))}</span>
        <span class="v">${mbFmt(src, m, tot[m])}</span>${ptot ? mbDelta(m, tot[m], ptot[m]) + `<span class="p">vs ${mbFmt(src, m, ptot[m])}</span>` : ''}</div>`).join('');
    let body = '';
    const rows = res.rows || [];
    const dims = res.dimensions || [];
    if (spec.visual === 'cards' || !dims.length) {
        el.innerHTML = `<div class="mb-kpis big">${cards}</div>${mbPeriodNote(res)}`;
        return;
    }
    if (!rows.length) { el.innerHTML = `<div class="mb-kpis">${cards}</div><div class="mb-empty">No data for these filters and dates.</div>`; return; }
    if (spec.visual === 'table') {
        const showPrev = !!res.compare && rows.some(r => r._prev);
        body = `<div class="mb-table-wrap"><table class="mb-table"><thead><tr>${dims.map(d => `<th>${esc(mbLabel(src, d))}</th>`).join('')}
            ${spec.metrics.map(m => `<th class="n">${esc(mbLabel(src, m))}</th>${showPrev ? '<th class="n">Change</th>' : ''}`).join('')}</tr></thead><tbody>
            ${rows.map(r => `<tr>${dims.map(d => `<td class="t">${esc(r[d])}</td>`).join('')}
            ${spec.metrics.map(m => `<td class="n">${mbFmt(src, m, r[m])}</td>${showPrev ? `<td class="n">${r._prev ? mbDelta(m, r[m], r._prev[m]) : '<span class="mb-delta flat">new</span>'}</td>` : ''}`).join('')}</tr>`).join('')}
            </tbody></table></div>`;
        el.innerHTML = `<div class="mb-kpis">${cards}</div>${body}${mbPeriodNote(res)}`;
        return;
    }
    el.innerHTML = `<div class="mb-kpis">${cards}</div><div class="mb-chart"><canvas id="${cid}"></canvas></div>${mbPeriodNote(res)}`;
    mbDrawChart(cid, spec, res);
}

function mbPeriodNote(res) {
    const s = d => new Date(d + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    let t = `${s(res.start)} – ${s(res.end)}`;
    if (res.compare) t += ` · compared with ${s(res.compare.start)} – ${s(res.compare.end)}`;
    if (res.row_count > (res.rows || []).length) t += ` · showing ${res.rows.length} of ${res.row_count.toLocaleString('en-IN')} rows`;
    return `<div class="mb-note">${t}</div>`;
}

function mbDrawChart(cid, spec, res) {
    const src = spec.source;
    const dims = res.dimensions, mets = spec.metrics, rows = res.rows;
    const pal = (typeof CHART_COLORS !== 'undefined' && CHART_COLORS.palette) || ['#7C3AED', '#0EA5E9', '#10B981', '#F59E0B', '#EC4899'];
    const scaleVal = (m, v) => { const f = mbField(src, m); return f && f.fmt === 'ratio' ? +(v * 100).toFixed(2) : +Number(v).toFixed(2); };
    const tick = m => v => { const f = mbField(src, m); return f && (f.fmt === 'ratio' || f.fmt === 'pct') ? v + '%' : Number(v).toLocaleString('en-IN'); };
    let labels, datasets;
    if (dims.length >= 2) {                     // pivot: first dim on axis, second dim as series, first metric
        const m = mets[0];
        labels = [...new Set(rows.map(r => r[dims[0]]))];
        const series = [...new Set(rows.map(r => r[dims[1]]))].slice(0, 8);
        datasets = series.map((sv, i) => ({
            label: sv, data: labels.map(l => { const r = rows.find(x => x[dims[0]] === l && x[dims[1]] === sv); return r ? scaleVal(m, r[m]) : 0; }),
            backgroundColor: pal[i % pal.length], borderColor: pal[i % pal.length], fill: false,
        }));
    } else {
        labels = rows.map(r => r[dims[0]]);
        const twoAxes = spec.visual !== 'donut' && mets.length === 2;
        datasets = mets.map((m, i) => ({
            label: mbLabel(src, m), data: rows.map(r => scaleVal(m, r[m])),
            backgroundColor: pal[i % pal.length], borderColor: pal[i % pal.length],
            fill: spec.visual === 'line' && mets.length === 1 ? undefined : false,
            yAxisID: twoAxes && i === 1 ? 'y1' : 'y',
        }));
    }
    if (dims[0] === 'date') labels = labels.map(d => new Date(d + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }));
    labels = labels.map(l => String(l).length > 40 ? String(l).slice(0, 38) + '…' : l);
    if (spec.visual === 'donut') {
        const m = mets[0];
        makeChart(cid, { type: 'doughnut', data: { labels, datasets: [{ label: mbLabel(src, m), data: rows.map(r => scaleVal(m, r[m])), backgroundColor: labels.map((_, i) => pal[i % pal.length]) }] },
            options: { plugins: { legend: { position: 'right', labels: { boxWidth: 10, font: { size: 11 } } } } } });
        return;
    }
    const scales = { y: { beginAtZero: true, ticks: { callback: tick(mets[0]) } } };
    if (datasets.some(d => d.yAxisID === 'y1')) scales.y1 = { position: 'right', beginAtZero: true, grid: { drawOnChartArea: false }, ticks: { callback: tick(mets[1]) } };
    const horizontal = spec.visual === 'bar' && dims[0] !== 'date' && labels.length > 6;
    if (horizontal) { scales.x = scales.y; delete scales.y; if (scales.y1) { delete scales.y1; datasets.forEach(d => { d.yAxisID = undefined; d.xAxisID = 'x'; }); } }
    makeChart(cid, {
        type: spec.visual === 'line' ? 'line' : 'bar', data: { labels, datasets },
        options: { indexAxis: horizontal ? 'y' : 'x', scales, plugins: { legend: { display: datasets.length > 1, labels: { boxWidth: 10, font: { size: 11 } } } } },
    });
}

// ── Board: save, pin, open ──
function mbSaveView() {
    const board = mbLoadBoard();
    const title = (document.getElementById('mb-title').value || '').trim() || mbAutoTitle(mbState);
    const spec = JSON.parse(JSON.stringify({ ...mbState, title }));
    const i = spec.id ? board.findIndex(b => b.id === spec.id) : -1;
    if (i >= 0) { spec.pinned = board[i].pinned; board[i] = spec; }
    else { spec.id = 'w' + Date.now().toString(36); spec.pinned = false; board.push(spec); }
    mbState.id = spec.id; mbState.title = title;
    document.getElementById('mb-title').value = title;
    mbSaveBoard(board); mbRenderBoard();
    mbToast(i >= 0 ? 'View updated on your board' : 'Saved to your board');
}
function mbAutoTitle(s) {
    const m = s.metrics.map(x => mbLabel(s.source, x)).slice(0, 2).join(' & ');
    return s.dimensions.length && s.visual !== 'cards' ? `${m} by ${mbLabel(s.source, s.dimensions[0])}` : m;
}
function mbNewView() {
    mbState = _mbNewState(mbState ? mbState.source : 'ga4');
    document.getElementById('mb-filter-pop').hidden = true;
    mbRenderAll(); mbRun();
}
function mbOpenView(id) {
    const w = mbLoadBoard().find(b => b.id === id); if (!w) return;
    mbState = JSON.parse(JSON.stringify(w));
    mbRenderAll(); mbRun();
    document.getElementById('view-builder').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function mbTogglePin(id) {
    const board = mbLoadBoard(); const w = board.find(b => b.id === id); if (!w) return;
    w.pinned = !w.pinned; mbSaveBoard(board); mbRenderBoard();
    mbToast(w.pinned ? 'Pinned to the Dashboard overview' : 'Removed from the Dashboard');
    if (typeof renderPinnedWidgets === 'function') renderPinnedWidgets();
}
function mbDeleteView(id) {
    const tile = document.querySelector(`.mb-tile[data-id="${id}"]`);
    if (tile && !tile.classList.contains('confirm')) { tile.classList.add('confirm'); setTimeout(() => tile.classList.remove('confirm'), 3000); return; }
    mbSaveBoard(mbLoadBoard().filter(b => b.id !== id)); mbRenderBoard();
    if (typeof renderPinnedWidgets === 'function') renderPinnedWidgets();
}

async function mbRenderTiles(container, widgets, dates, opts = {}) {
    if (!widgets.length) { container.innerHTML = opts.empty || ''; return; }
    container.innerHTML = widgets.map(w => `
        <div class="mb-tile ${w.visual === 'cards' ? 'short' : ''}" data-id="${w.id}" ${opts.draggable ? 'draggable="true"' : ''}>
            <div class="mb-tile-hd"><div><b>${esc(w.title)}</b><small>${esc(mbCatalog[w.source].label)}${w.filters.length ? ` · ${w.filters.length} filter${w.filters.length > 1 ? 's' : ''}` : ''}</small></div>
            <div class="mb-tile-act">${opts.actions ? `
                <button type="button" data-a="open" title="Edit in builder">Edit</button>
                <button type="button" data-a="pin" class="${w.pinned ? 'on' : ''}" title="${w.pinned ? 'Unpin from Dashboard' : 'Pin to Dashboard'}">${w.pinned ? 'Pinned' : 'Pin'}</button>
                <button type="button" data-a="del" title="Delete"><span class="del-a">Delete</span><span class="del-b">Confirm?</span></button>` : `<button type="button" data-a="open" title="Edit in Metric Builder">Edit</button>`}</div></div>
            <div class="mb-tile-body loading" id="mbt-${opts.prefix}-${w.id}"></div>
        </div>`).join('');
    container.querySelectorAll('.mb-tile').forEach(t => {
        const id = t.dataset.id;
        t.querySelectorAll('[data-a]').forEach(b => b.addEventListener('click', () => {
            const a = b.dataset.a;
            if (a === 'open') { if (opts.fromDashboard) switchView('builder'); mbOpenView(id); }
            if (a === 'pin') mbTogglePin(id);
            if (a === 'del') mbDeleteView(id);
        }));
        if (opts.draggable) {
            t.addEventListener('dragstart', e => { e.dataTransfer.effectAllowed = 'move'; try { e.dataTransfer.setData('text/plain', id); } catch (_) {} t.classList.add('dragging'); mbDrag = { from: 'board', id }; });
            t.addEventListener('dragend', () => { t.classList.remove('dragging'); mbDrag = null; });
            t.addEventListener('dragover', e => { if (mbDrag && mbDrag.from === 'board') e.preventDefault(); });
            t.addEventListener('drop', e => {
                e.preventDefault(); if (!mbDrag || mbDrag.from !== 'board' || mbDrag.id === id) return;
                const board = mbLoadBoard();
                const from = board.findIndex(b => b.id === mbDrag.id); const [it] = board.splice(from, 1);
                board.splice(board.findIndex(b => b.id === id), 0, it);
                mbSaveBoard(board); mbRenderBoard();
                if (typeof renderPinnedWidgets === 'function') renderPinnedWidgets();
            });
        }
    });
    await Promise.all(widgets.map(async w => {
        const el = document.getElementById(`mbt-${opts.prefix}-${w.id}`);
        try { const res = await mbQuery(w, dates); mbRenderResult(el, { ...w, limit: Math.min(w.limit, 15) }, { ...res, rows: (res.rows || []).slice(0, w.visual === 'table' ? 10 : 15) }, `mbc-${opts.prefix}-${w.id}`); }
        catch (e) { el.innerHTML = '<div class="mb-empty err">Couldn\'t load this view for the current account.</div>'; }
        finally { el.classList.remove('loading'); }
    }));
}

function mbRenderBoard() {
    const box = document.getElementById('mb-board'); if (!box || !mbCatalog) return;
    const board = mbLoadBoard();
    document.getElementById('mb-board-count').textContent = board.length ? `${board.length} saved view${board.length > 1 ? 's' : ''} · drag to reorder` : '';
    mbRenderTiles(box, board, mbDates(), {
        actions: true, draggable: true, prefix: 'b',
        empty: '<div class="mb-empty">Views you save appear here. Build one above, then click <b>Save to board</b>. Pin a view to show it on the Dashboard.</div>',
    });
}

// Pinned views on the Dashboard overview — use the dashboard's account and date range.
async function renderPinnedWidgets() {
    const sec = document.getElementById('pinned-section'); if (!sec) return;
    const pinned = mbLoadBoard().filter(w => w.pinned);
    sec.hidden = !pinned.length;
    if (!pinned.length) return;
    if (!mbCatalog) { try { mbCatalog = await api('/api/explore/fields'); } catch (e) { sec.hidden = true; return; } }
    mbRenderTiles(document.getElementById('pinned-widgets'), pinned, { start: dateStart, end: dateEnd }, { prefix: 'p', fromDashboard: true });
}

function mbExportCsv() {
    const res = mbLastResult; if (!res || !res.rows) return;
    const cols = [...res.dimensions, ...res.metrics];
    const q = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const lines = [cols.map(c => q(mbLabel(res.source, c))).join(',')].concat(
        (res.rows.length ? res.rows : [res.totals]).map(r => cols.map(c => q(res.metrics.includes(c) ? mbFmt(res.source, c, r[c]) : r[c])).join(',')));
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = `${(mbState.title || mbAutoTitle(mbState)).replace(/[^\w]+/g, '_')}_${res.start}_${res.end}.csv`;
    a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

function mbToast(msg) {
    const t = document.getElementById('mb-toast'); if (!t) return;
    t.textContent = msg; t.hidden = false; clearTimeout(t._h); t._h = setTimeout(() => { t.hidden = true; }, 2200);
}

// ── Wire controls once ──
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('view-builder')) return;
    mbSetupDrop();
    document.querySelectorAll('#mb-source button').forEach(b => b.addEventListener('click', () => {
        if (mbState.source === b.dataset.src) return;
        mbState = _mbNewState(b.dataset.src); mbRenderAll(); mbRun();
    }));
    document.querySelectorAll('#mb-range button').forEach(b => b.addEventListener('click', () => {
        mbRange.preset = b.dataset.range;
        if (b.dataset.range === 'custom' && !mbRange.start) { const d = mbDates(); mbRange.start = d.start; mbRange.end = d.end; }
        document.getElementById('mb-start').value = mbRange.start; document.getElementById('mb-end').value = mbRange.end;
        mbRenderAll(); if (b.dataset.range !== 'custom') { mbRun(); mbRenderBoard(); }
    }));
    ['mb-start', 'mb-end'].forEach(id => document.getElementById(id).addEventListener('change', () => {
        mbRange.start = document.getElementById('mb-start').value; mbRange.end = document.getElementById('mb-end').value;
        if (mbRange.start && mbRange.end && mbRange.start <= mbRange.end) { mbRun(); mbRenderBoard(); }
    }));
    document.getElementById('mb-compare').addEventListener('change', e => { mbState.compare = e.target.checked; mbRun(); });
    document.getElementById('mb-limit').addEventListener('change', e => { mbState.limit = +e.target.value; mbRun(); });
    document.getElementById('mb-sort').addEventListener('change', e => {
        const v = e.target.value; mbState.sort = v ? { field: v.split('|')[0], desc: v.split('|')[1] === 'desc' } : null; mbRun();
    });
    document.getElementById('mb-field-search').addEventListener('input', mbRenderFields);
    document.getElementById('mb-save').addEventListener('click', mbSaveView);
    document.getElementById('mb-new').addEventListener('click', mbNewView);
    document.getElementById('mb-csv').addEventListener('click', mbExportCsv);
    document.getElementById('mb-title').addEventListener('input', e => { mbState.title = e.target.value; });
});
