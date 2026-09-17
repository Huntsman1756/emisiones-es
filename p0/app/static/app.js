/* P0 reviewer app — evidence-assisted review.
 * Mode is enforced server-side; this client only renders what the
 * case payload contains (MANUAL payloads have no graph/candidates).
 */
'use strict';

const S = {
  session: null, caseId: null, payload: null,
  decisions: {},            // field -> [decision]
  focusField: null,
  ev: {doc: null, meta: null, page: 1, scale: 1.6, hl: []},
  capturedEv: null,         // evidence pointer captured for manual add
  paused: false, t0: 0, acc: 0, tick: null,
};

const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g,
  c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const safeUrl = value => {
  try {
    const u = new URL(value);
    return ['https:', 'http:'].includes(u.protocol) ? u.href : null;
  } catch { return null; }
};
async function request(u, options) {
  try {
    const response = await fetch(u, options);
    const data = await response.json();
    if (!response.ok || data?.ok === false || data?.error)
      throw new Error(data?.error || `HTTP ${response.status}`);
    return data;
  } catch (error) {
    toast(`Request failed: ${error.message}. Changes may not be saved; verify before retrying.`, true);
    throw error;
  }
}
const api = {
  get: u => request(u),
  post: (u, b) => request(u, {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify(b)}),
};
let toastTimer;
window.addEventListener('unhandledrejection', e => {
  toast(e.reason?.message || 'Operation failed', true);
  e.preventDefault();
});

function toast(msg, isErr) {
  const t = $('toast');
  t.textContent = msg; t.className = 'show' + (isErr ? ' err' : '');
  clearTimeout(toastTimer);
  if (!isErr) toastTimer = setTimeout(() => t.className = '', 2600);
}

async function event(type, payload) {
  await api.post('/api/event', {case_id: S.caseId, event_type: type,
                                payload: payload || {}});
}

/* ---------- session / case list ---------- */
async function init() {
  S.session = await api.get('/api/session');
  const bar = $('case-list-bar');
  bar.innerHTML = '';
  S.session.items.forEach((it, i) => {
    const s = document.createElement('span');
    s.textContent = `${i + 1}.${it.case_id}${it.warmup ? ' (wu)' : ''}`;
    s.id = 'cl-' + it.case_id;
    if (it.status === 'DONE') s.classList.add('done');
    s.onclick = () => { if (!S.caseId) openCase(it.case_id); };
    bar.appendChild(s);
  });
  const next = S.session.items.find(i => i.status !== 'DONE');
  if (next) openCase(next.case_id);
  else toast('session complete');
}

async function openCase(caseId) {
  S.caseId = caseId;
  S.payload = await api.get(`/api/case/${caseId}`);
  if (S.payload.error) { toast('case not found', true); return; }
  S.decisions = {};
  (S.payload.decisions || []).forEach(d => {
    (S.decisions[d.field] = S.decisions[d.field] || []).push(d);
  });
  document.querySelectorAll('#case-list-bar span')
    .forEach(s => s.classList.remove('current'));
  const cur = $('cl-' + caseId); if (cur) cur.classList.add('current');
  renderHeader(); renderForm();
  if (S.payload.mode === 'ASSISTED') renderGraph();
  $('layout').className = S.payload.mode === 'MANUAL' ? 'manual' : '';
  // open primary doc in viewer
  const doc = (S.payload.documents || [])[0];
  if (doc) openDoc(doc.doc_id, 1, []);
  startTimer();
  await event('CASE_OPENED', {mode: S.payload.mode});
  window.onbeforeunload = () => 'review in progress';
}

function renderHeader() {
  const p = S.payload;
  $('case-id').textContent = p.case_id;
  $('case-isin').textContent = p.isin || '—';
  $('case-issuer').textContent = p.issuer || '';
  $('case-class').textContent = p.instrument_class || '';
  $('case-mode').textContent = p.mode;
}

/* ---------- timer ---------- */
function startTimer() {
  S.paused = false; S.t0 = Date.now(); S.acc = 0;
  clearInterval(S.tick);
  S.tick = setInterval(() => {
    if (!S.paused) {
      const s = Math.floor(S.acc + (Date.now() - S.t0) / 1000);
      $('timer').textContent =
        `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
    }
  }, 500);
}
$('btn-pause').onclick = async () => {
  if (!S.caseId) return;
  if (!S.paused) {
    S.acc += (Date.now() - S.t0) / 1000; S.paused = true;
    $('btn-pause').textContent = 'Resume';
    await event('CASE_PAUSED');
  } else {
    S.t0 = Date.now(); S.paused = false;
    $('btn-pause').textContent = 'Pause';
    await event('CASE_RESUMED');
  }
};
document.addEventListener('visibilitychange', () => {
  if (!S.caseId) return;
  event(document.hidden ? 'FOCUS_LOST' : 'FOCUS_GAINED');
});

/* ---------- graph ---------- */
function renderGraph() {
  const g = S.payload.graph || {status: 'INCOMPLETE', nodes: [], edges: []};
  $('graph-status').innerHTML =
    `<span class="badge">${esc(g.status || 'INCOMPLETE')}</span>`;
  const nn = $('graph-nodes'); nn.innerHTML = '';
  (g.nodes || []).forEach(n => {
    const d = document.createElement('div');
    d.className = 'gnode' + (n.is_case_doc ? ' case' : '') +
      (n.observed ? '' : ' no-pdf');
    d.innerHTML = `<div class="role">${esc(n.role)}</div>` +
      `<div class="mono">${esc(n.id)}</div>`;
    if (n.observed) d.onclick = () => {
      openDoc(n.id, 1, []); event('DOCUMENT_OPENED', {doc_id: n.id});
    };
    nn.appendChild(d);
  });
  const ne = $('graph-edges'); ne.innerHTML = '';
  (g.edges || []).forEach(e => {
    const d = document.createElement('div');
    d.className = 'gedge';
    const cls = e.state === 'AUTO_LINKED' ? 'st-auto' : 'st-review';
    d.innerHTML = `${esc(e.from)} <b>→</b> ${esc(e.to)}<br>` +
      `<span class="${cls}">${esc(e.state)}</span> ${esc(e.relation || '')}`;
    d.onclick = () => event('GRAPH_EDGE_FOLLOWED',
      {from: e.from, to: e.to});
    ne.appendChild(d);
  });
  const miss = (g.missing_expected_documents || []);
  $('graph-missing').textContent = miss.length ?
    'missing expected: ' + miss.join(', ') : '';
}

/* ---------- review form ---------- */
function renderForm() {
  const root = $('fields'); root.innerHTML = '';
  const fams = S.payload.field_families;
  const schemaById = {};
  S.payload.schema.fields.forEach(f => schemaById[f.id] = f);
  const candsByField = {};
  (S.payload.candidates || []).forEach(c => {
    (candsByField[c.schema_field] = candsByField[c.schema_field] || [])
      .push(c);
  });
  Object.keys(fams).forEach(fam => {
    const fh = document.createElement('div');
    fh.className = 'family';
    fh.innerHTML = `<h4>${esc(fam)}</h4>`;
    root.appendChild(fh);
    fams[fam].forEach(fid => {
      const f = schemaById[fid];
      if (!f) return;
      root.appendChild(fieldCard(f, candsByField[fid] || []));
    });
  });
  updateProgress();
}

function fieldCard(f, cands) {
  const card = document.createElement('div');
  card.className = 'field'; card.id = 'fld-' + f.id;
  card.tabIndex = 0;
  card.onfocus = () => {
    document.querySelectorAll('.field.focus')
      .forEach(x => x.classList.remove('focus'));
    card.classList.add('focus'); S.focusField = f.id;
  };
  const decs = S.decisions[f.id] || [];
  const st = decs.length ? decs[decs.length - 1].decision : 'OPEN';
  card.innerHTML =
    `<div class="fhead"><span><span class="fname">${esc(f.label)}</span>` +
    (f.critical ? '<span class="fcrit">CRITICAL</span>' : '') +
    `</span><span class="fstatus st-${esc(st)}">${esc(st)}</span></div>`;
  const body = document.createElement('div');
  card.appendChild(body);
  cands.forEach(c => body.appendChild(candRow(f, c)));
  decs.forEach(d => {
    const dv = document.createElement('div');
    dv.className = 'decision-val';
    dv.innerHTML = `${esc(d.decision)}: <b>${esc(fmtVal(d.value))}</b> ` +
      `<span class="dv-src">${esc(d.origin)}</span>`;
    body.appendChild(dv);
  });
  const acts = document.createElement('div');
  acts.className = 'factions';
  acts.innerHTML =
    `<button data-a="manual">add manually</button>` +
    `<button data-a="MISSING">missing</button>` +
    `<button data-a="NOT_APPLICABLE">n/a</button>`;
  acts.querySelector('[data-a=manual]').onclick =
    () => openManualModal(f.id);
  acts.querySelector('[data-a=MISSING]').onclick =
    () => decide(f.id, 'MISSING', {});
  acts.querySelector('[data-a=NOT_APPLICABLE]').onclick =
    () => decide(f.id, 'NOT_APPLICABLE', {});
  body.appendChild(acts);
  return card;
}

function fmtVal(v) {
  if (v == null) return '';
  if (Array.isArray(v)) return v.map(fmtVal).join(' | ');
  if (typeof v === 'object')
    return Object.entries(v).map(([k, x]) => `${k}=${fmtVal(x)}`)
      .join(' ');
  return String(v);
}

function candRow(f, c) {
  const r = document.createElement('div');
  r.className = 'cand';
  const ev0 = (c.evidence || [])[0] || {};
  r.innerHTML =
    `<span class="cval">${esc(fmtVal(c.value))}</span>` +
    `<span class="cex" title="${esc(ev0.excerpt || '')}">` +
    `${esc(ev0.excerpt || '')}</span>` +
    `<span class="csrc">${esc(ev0.doc_id || '')} p${esc(ev0.page || '?')}</span>` +
    `<button data-a="ev">E</button>` +
    `<button data-a="CONFIRMED">C</button>` +
    `<button data-a="REJECTED">R</button>` +
    `<button data-a="CONFLICT">X</button>`;
  r.querySelector('[data-a=ev]').onclick = () => {
    jumpEvidence(c); };
  r.querySelector('[data-a=CONFIRMED]').onclick =
    () => decide(f.id, 'CONFIRMED', {candidate: c, value: c.value});
  r.querySelector('[data-a=REJECTED]').onclick =
    () => decide(f.id, 'REJECTED', {candidate: c});
  r.querySelector('[data-a=CONFLICT]').onclick =
    () => decide(f.id, 'CONFLICT', {candidate: c, value: c.value});
  return r;
}

async function decide(field, decision, opt) {
  const body = {
    case_id: S.caseId, field, decision,
    value: opt.value ?? null,
    candidate_id: opt.candidate ? opt.candidate.candidate_id : null,
    origin: opt.manual ? 'MANUAL_DISCOVERY' :
      (opt.candidate ? 'MACHINE_CANDIDATE' : 'MANUAL_DISCOVERY'),
    evidence_pointers: opt.pointers || [],
  };
  const res = await api.post('/api/decision', body);
  if (!res.ok) { toast(res.error, true); return; }
  const evMap = {CONFIRMED: 'CANDIDATE_CONFIRMED',
                 REJECTED: 'CANDIDATE_REJECTED',
                 CONFLICT: 'CANDIDATE_CONFLICT'};
  await event(opt.manual ? 'MANUAL_FIELD_ADDED' :
              (evMap[decision] || 'STATUS_CHANGED'),
              {field, decision});
  (S.decisions[field] = S.decisions[field] || []).push(res.decision);
  renderForm(); refocus(field);
}

function refocus(fid) {
  const el = $('fld-' + fid);
  if (el) { el.classList.add('focus'); S.focusField = fid; }
}

function updateProgress() {
  const total = S.payload.schema.fields.length;
  const done = Object.keys(S.decisions).length;
  const crit = S.payload.schema.fields.filter(f => f.critical);
  const critDone = crit.filter(f => S.decisions[f.id]).length;
  $('progress').textContent = `${done}/${total} fields`;
  $('progress-critical').textContent =
    `critical ${critDone}/${crit.length}`;
}

/* ---------- evidence viewer ---------- */
async function openDoc(docId, page, hl) {
  const meta = await api.get(`/api/doc/${docId}/meta`);
  if (meta.error) { toast('no document ' + docId, true); return; }
  S.ev = {doc: docId, meta, page: page || 1, scale: S.ev.scale, hl: hl || []};
  $('ev-doc').textContent = docId;
  $('ev-fullpdf').href = `/api/doc/${docId}/file`;
  renderPage();
}

function renderPage() {
  const {doc, meta, page, scale, hl} = S.ev;
  const n = meta.pages.length;
  S.ev.page = Math.min(Math.max(1, page), n);
  $('ev-page').textContent = `p${S.ev.page}/${n}`;
  const pg = meta.pages[S.ev.page - 1];
  const cv = $('ev-canvas');
  cv.innerHTML = '';
  const img = document.createElement('img');
  img.src = `/api/doc/${doc}/page/${S.ev.page}.png?scale=${scale}`;
  cv.appendChild(img);
  hl.forEach(h => {
    if (h.page !== S.ev.page || !h.bbox) return;
    const [l, t, r, b] = h.bbox;   // BOTTOMLEFT points
    const d = document.createElement('div');
    d.className = 'ev-hl' + (h.sel ? ' sel' : '');
    d.style.left = (l * scale) + 'px';
    d.style.top = ((pg.height - t) * scale) + 'px';
    d.style.width = ((r - l) * scale) + 'px';
    d.style.height = ((t - b) * scale) + 'px';
    cv.appendChild(d);
  });
}

$('ev-prev').onclick = () => { S.ev.page--; renderPage(); };
$('ev-next').onclick = () => { S.ev.page++; renderPage(); };
$('ev-zoom-in').onclick = () => { S.ev.scale *= 1.25; renderPage(); };
$('ev-zoom-out').onclick = () => { S.ev.scale /= 1.25; renderPage(); };
$('ev-search-btn').onclick = doSearch;
$('ev-search').onkeydown = e => { if (e.key === 'Enter') doSearch(); };

async function doSearch() {
  const q = $('ev-search').value.trim();
  if (!q || !S.ev.doc) return;
  const res = await api.get(
    `/api/doc/${S.ev.doc}/search?q=${encodeURIComponent(q)}`);
  const box = $('ev-search-results'); box.innerHTML = '';
  res.matches.forEach(m => {
    const d = document.createElement('div');
    d.className = 'sr';
    d.textContent = `p${m.page}: ${m.excerpt.slice(0, 70)}`;
    d.onclick = () => {
      S.ev.hl = [{page: m.page, bbox: m.bbox, sel: true}];
      S.ev.page = m.page; renderPage();
    };
    box.appendChild(d);
  });
  event('PDF_SEARCH', {doc_id: S.ev.doc, q,
                      n_matches: res.matches.length});
}

function jumpEvidence(c) {
  const ev0 = (c.evidence || [])[0];
  if (!ev0 || !ev0.doc_id) { toast('candidate has no evidence', true); return; }
  openDoc(ev0.doc_id, ev0.page || 1,
          [{page: ev0.page, bbox: ev0.bbox, sel: true}]);
  event('EVIDENCE_JUMP', {candidate_id: c.candidate_id,
                          doc_id: ev0.doc_id, page: ev0.page});
}

/* ---------- manual discovery ---------- */
let mmField = null;
function openManualModal(fid) {
  mmField = fid;
  $('mm-value').value = ''; $('mm-excerpt').value = '';
  $('mm-evidence').textContent = S.capturedEv ?
    `evidence: ${S.capturedEv.doc_id} p${S.capturedEv.page}` :
    'no evidence captured — use "capture evidence" in the viewer first';
  $('modal-manual').classList.remove('hidden');
}
$('mm-cancel').onclick = () => $('modal-manual').classList.add('hidden');
$('ev-capture').onclick = () => {
  if (!S.ev.doc) return;
  S.capturedEv = {doc_id: S.ev.doc, page: S.ev.page,
                  sha256: S.ev.meta.sha256};
  toast(`evidence captured: ${S.ev.doc} p${S.ev.page}`);
};
$('mm-ok').onclick = async () => {
  const v = $('mm-value').value.trim();
  if (!v) { toast('value required', true); return; }
  const ptr = S.capturedEv ?
    [{...S.capturedEv, excerpt: $('mm-excerpt').value.trim() || null}] : [];
  $('modal-manual').classList.add('hidden');
  await decide(mmField, 'CONFIRMED',
               {value: v, manual: true, pointers: ptr});
};

/* ---------- submit ---------- */
window.onerror = (msg, src, line) => {
  if (S.caseId) event('UI_ERROR', {msg: String(msg).slice(0, 200),
                                   line});
};

$('btn-submit').onclick = async () => {
  if (!S.caseId) return;
  const crit = S.payload.schema.fields.filter(f => f.critical);
  const unresolved = crit.filter(f => !S.decisions[f.id]).map(f => f.id);
  if (unresolved.length &&
      !confirm('Critical field unresolved: ' + unresolved.join(', ') +
               '\nSubmit anyway?')) return;
  const notes = $('reviewer-notes').value.trim();
  await event('CASE_SUBMITTED');
  const res = await api.post('/api/submit', {
    case_id: S.caseId,
    reviewer_notes: notes ? [notes] : []});
  if (!res.ok) { toast(res.error, true); return; }
  window.onbeforeunload = null;
  clearInterval(S.tick);
  const it = S.session.items.find(i => i.case_id === S.caseId);
  if (it) it.status = 'DONE';
  const cur = $('cl-' + S.caseId); if (cur) cur.classList.add('done');
  toast(`submitted — ${res.review.active_seconds.toFixed(0)}s active`);
  S.caseId = null;
  const next = S.session.items.find(i => i.status !== 'DONE');
  if (next) setTimeout(() => openCase(next.case_id), 400);
};

/* ---------- keyboard ---------- */
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || !S.caseId) return;
  const k = e.key.toLowerCase();
  const order = S.payload.schema.fields.map(f => f.id);
  if (k === 'j' || k === 'k') {
    const i = order.indexOf(S.focusField);
    const n = order[Math.min(Math.max(0,
      i + (k === 'j' ? 1 : -1)), order.length - 1)] || order[0];
    const el = $('fld-' + n);
    if (el) { el.focus(); el.scrollIntoView({block: 'nearest'}); }
    e.preventDefault();
    return;
  }
  if (!S.focusField) return;
  const cands = (S.payload.candidates || [])
    .filter(c => c.schema_field === S.focusField);
  const c0 = cands[0];
  if (k === 'e' && c0) jumpEvidence(c0);
  else if (k === 'c' && c0)
    decide(S.focusField, 'CONFIRMED', {candidate: c0, value: c0.value});
  else if (k === 'r' && c0)
    decide(S.focusField, 'REJECTED', {candidate: c0});
  else if (k === 'x' && c0)
    decide(S.focusField, 'CONFLICT', {candidate: c0, value: c0.value});
  else if (k === 'm') decide(S.focusField, 'MISSING', {});
  else if (k === 'n') decide(S.focusField, 'NOT_APPLICABLE', {});
});

init();
