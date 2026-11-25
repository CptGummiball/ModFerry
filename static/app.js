'use strict';
/* ModFerry frontend: plain JS, no build step. */
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const uniq = arr => [...new Set(arr)];

const TYPES = {
  mod:          {icon: '🧩', cfCats: ['minecraft', 'loader', 'java', 'environment'], mrLoaders: null, mrEnv: true},
  resourcepack: {icon: '🎨', cfCats: ['minecraft'], mrLoaders: ['minecraft'], fixedLoader: true},
  datapack:     {icon: '📜', cfCats: ['minecraft'], mrLoaders: ['datapack'], fixedLoader: true},
  shader:       {icon: '✨', cfCats: ['minecraft'], mrLoaders: ['iris', 'optifine', 'canvas', 'vanilla']},
  modpack:      {icon: '📦', cfCats: ['minecraft', 'loader'], mrLoaders: ['fabric', 'forge', 'neoforge', 'quilt'], mrEnv: true},
};
const MOD_LOADERS = ['fabric', 'forge', 'neoforge', 'quilt'];
const MR_ENVS = ['client_and_server', 'client_only', 'client_only_server_optional', 'server_only', 'server_only_client_optional',
  'singleplayer_only', 'dedicated_server_only', 'client_or_server', 'client_or_server_prefers_both'];
const RELATION_TYPES = ['requiredDependency', 'optionalDependency', 'embeddedLibrary', 'tool', 'incompatible', 'include'];
const MR_RELATION_TYPES = ['requiredDependency', 'optionalDependency', 'embeddedLibrary', 'incompatible'];

const S = {
  lang: 'en', dict: {}, info: null, type: 'mod', rows: [], versions: [], profiles: {},
  mrTags: {gameVersions: [], loaders: []}, busy: false, tokenStatus: {}, activeJob: null,
};

/* ------------------------------------------------------------ i18n */
function t(key, vars = {}) {
  let text = S.dict[key] ?? key;
  for (const [k, v] of Object.entries(vars)) text = text.split('{' + k + '}').join(v);
  return text;
}
async function loadLang(lang) {
  const res = await fetch('/i18n/' + lang + '.json');
  S.dict = await res.json();
  S.lang = lang;
  localStorage.setItem('modferry.lang', lang);
  document.documentElement.lang = lang;
  $('lang').value = lang;
  for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = t(el.dataset.i18n);
  for (const el of document.querySelectorAll('[data-i18n-ph]')) el.placeholder = t(el.dataset.i18nPh);
  for (const el of document.querySelectorAll('[data-i18n-title]')) el.title = t(el.dataset.i18nTitle);
}
function warnText(w) {
  if (!w) return '';
  const [key, ...rest] = w.split(':');
  return key.startsWith('warn.') ? t(key) + (rest.length ? ' ' + rest.join(':') : '') : w;
}

/* ------------------------------------------------------------ helpers */
async function api(url, method = 'GET', data = null) {
  const opt = {method, headers: {'X-ModFerry-Lang': S.lang}};
  if (data !== null) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(data); }
  const res = await fetch(url, opt);
  let json;
  try { json = await res.json(); } catch { throw Error(t('err.unreadable', {status: res.status})); }
  if (!res.ok) throw Error(json.error || 'HTTP ' + res.status);
  return json;
}
function notice(text, error = false) { const n = $('notice'); n.className = error ? 'error' : 'ok'; n.textContent = text; }
function clearNotice() { $('notice').className = 'hidden'; }
const selected = () => S.rows.filter(r => r.checked);
const cfg = () => TYPES[S.type];
const platformsOf = r => r.detected?.platforms || [];
const cfActive = r => platformsOf(r).includes('curseforge') && r.publishCF !== false;
const mrActive = r => platformsOf(r).includes('modrinth') && r.publishMR !== false;
const versionName = id => S.versions.find(v => v.id === id)?.name || ('ID ' + id);
const idsOf = (r, cat) => r.ids.filter(id => S.versions.some(v => v.id === id && v.category === cat));
const cfNames = (r, cat) => idsOf(r, cat).map(versionName);
const relLabel = type => t('rel.' + type);
const today = () => new Date().toISOString().slice(0, 10);

function mrLoaderOptions() {
  if (cfg().mrLoaders) return cfg().mrLoaders;
  const fromTags = S.mrTags.loaders.filter(l => l.types.includes('mod')).map(l => l.name);
  return uniq([...MOD_LOADERS, ...fromTags]);
}

/* ------------------------------------------------------------ detection → row values */
function suggestNumber(r) {
  const v = r.detected?.modVersion || '';
  if (!v) return '';
  if (S.type !== 'mod') return v;
  const loader = r.mrLoaders[0] || '', mc = r.mrGameVersions[0] || '', parts = [];
  if (loader && !v.toLowerCase().includes(loader)) parts.push(loader);
  if (mc && !v.includes(mc)) parts.push(mc);
  return parts.length ? v + (v.includes('+') ? '-' : '+') + parts.join('-') : v;
}
function inferMR(r) {
  const d = r.detected || {};
  if (!r.mrGameVersions.length && d.minecraft?.length) r.mrGameVersions = [...d.minecraft];
  if (!r.mrLoaders.length) {
    if (cfg().fixedLoader) r.mrLoaders = [cfg().mrLoaders[0]];
    else if (d.loaders?.length) r.mrLoaders = d.loaders.map(x => x.toLowerCase());
  }
  if (!r.mrVersionNumber) r.mrVersionNumber = suggestNumber(r);
}
function inferCF(r) {
  if (!S.versions.length) return;
  const d = r.detected || {}, warnings = [];
  for (const mc of d.minecraft || []) {
    const hits = S.versions.filter(v => v.category === 'minecraft' && v.name.toLowerCase() === mc.toLowerCase());
    if (hits.length === 1) r.ids = uniq([...r.ids, hits[0].id]);
    else if (hits.length > 1) warnings.push(t('warn.ambiguous', {v: mc, n: hits.length}));
    else warnings.push(t('warn.notOnCF', {v: mc}));
  }
  if (cfg().cfCats.includes('loader')) {
    const loaders = (d.loaders || []).map(x => x.toLowerCase());
    const hits = S.versions.filter(v => v.category === 'loader' && loaders.includes(v.name.toLowerCase()));
    if (hits.length === 1) r.ids = uniq([...r.ids, hits[0].id]);
  }
  if (cfg().cfCats.includes('java')) {
    const hits = S.versions.filter(v => v.category === 'java' && (d.java || []).some(j => v.name.toLowerCase() === ('java ' + j)));
    if (hits.length === 1) r.ids = uniq([...r.ids, hits[0].id]);
  }
  r.versionWarning = warnings.join(' · ');
}
function newRow(file) {
  return {...file, checked: false, displayName: file.name, ids: [], releaseType: $('release').value, relations: [],
    changelog: '', changelogOverride: false, mrGameVersions: [], mrLoaders: [], mrVersionNumber: '',
    mrEnvironment: 'client_and_server', publishMR: true, publishCF: true, serverPackId: null, serverPackName: '',
    versionWarning: '', cf: {status: 'ready', message: ''}, mr: {status: 'ready', message: ''}};
}

/* ------------------------------------------------------------ changelog templates */
function fillTemplate(text, r) {
  if (!r) return text;
  const vars = {
    version: r.detected?.modVersion || r.mrVersionNumber || '',
    mc: cfNames(r, 'minecraft').join(', ') || r.mrGameVersions.join(', '),
    loader: cfNames(r, 'loader').join(', ') || r.mrLoaders.join(', '),
    name: r.displayName || r.name, file: r.name, date: today(),
  };
  return String(text || '').replace(/\{(version|mc|loader|name|file|date)\}/g, (_, k) => vars[k]);
}
const changelogOf = r => fillTemplate(r.changelogOverride ? r.changelog : $('changelog').value, r);
function latestSection(text) {
  const lines = text.split(/\r?\n/);
  const heads = lines.map((l, i) => (/^##\s/.test(l) ? i : -1)).filter(i => i >= 0);
  if (!heads.length) return text.trim();
  for (let k = 0; k < heads.length; k++) {
    const body = lines.slice(heads[k] + 1, heads[k + 1] ?? lines.length).join('\n').trim();
    if (body) return body;
  }
  return '';
}
let previewSerial = 0;
async function renderMarkdown(source, target) {
  const seq = ++previewSerial;
  if (!source.trim()) { target.innerHTML = `<span class="muted">${esc(t('changelog.empty'))}</span>`; return; }
  try {
    const out = await api('/api/markdown-preview', 'POST', {markdown: source});
    if (seq === previewSerial) target.innerHTML = out.html;
  } catch (e) { if (seq === previewSerial) target.textContent = e.message; }
}
function preview() {
  const sample = selected()[0] || S.rows[0];
  $('previewLabel').textContent = sample ? t('changelog.previewFor', {file: sample.name}) : t('changelog.preview');
  renderMarkdown(fillTemplate($('changelog').value, sample), $('preview'));
}

/* ------------------------------------------------------------ rendering */
function renderTypes() {
  $('projectTypes').innerHTML = Object.entries(TYPES).map(([k, v]) =>
    `<label><input type="radio" name="ptype" value="${k}" ${k === S.type ? 'checked' : ''}><span>${v.icon} ${esc(t('type.' + k))}</span></label>`).join('');
  $('typeHint').textContent = t('typeHint.' + S.type);
  const table = $('table');
  table.classList.toggle('no-loader', !cfg().cfCats.includes('loader'));
  table.classList.toggle('no-java', !cfg().cfCats.includes('java'));
  table.classList.toggle('no-env', !cfg().cfCats.includes('environment'));
  for (const c of ['loader', 'java', 'env']) {
    const cat = c === 'env' ? 'environment' : c;
    document.querySelector('.col-' + c + '-b').classList.toggle('hidden', !cfg().cfCats.includes(cat));
  }
  const accept = Object.keys(S.info?.extensions?.[S.type] || {}).join(',');
  $('fileInput').accept = accept;
}
function statusLine(r, key) {
  const enabled = key === 'cf' ? $('publishCF').checked : $('publishMR').checked;
  if (!enabled) return '';
  const active = key === 'cf' ? cfActive(r) : mrActive(r);
  const label = key === 'cf' ? 'CF' : 'MR';
  if (!active) return `<div class="off">${label}: ${esc(t('common.na'))}</div>`;
  const st = r[key];
  const msg = st.message || t('status.' + st.status);
  const link = st.url ? ` <a href="${esc(st.url)}" target="_blank" rel="noopener">↗</a>` : '';
  const cls = st.warning ? 'status-warning' : 'status-' + st.status;
  return `<div class="${cls}">${label}: ${esc(msg)}${link}</div>`;
}
function cfCell(r, cat) {
  if (!cfActive(r)) return `<span class="off">${esc(t('common.na'))}</span>`;
  const names = cfNames(r, cat);
  const empty = !names.length;
  const cls = empty && cat === 'minecraft' ? 'pill empty' : 'pill';
  return `<button class="edit" data-cat="${cat}"><span class="${cls}">${esc(names.join(', ') || t('common.notSet'))}</span></button>`;
}
function mrCell(r) {
  if (!platformsOf(r).includes('modrinth')) return `<span class="off">${esc(t('files.notForMR'))}</span>`;
  if (r.publishMR === false) return `<button class="editmr"><span class="off">${esc(t('files.mrOff'))}</span></button>`;
  const missing = !r.mrGameVersions.length || !r.mrLoaders.length || !r.mrVersionNumber;
  const summary = (r.mrGameVersions.length > 3 ? r.mrGameVersions.slice(0, 3).join(', ') + ' …' : r.mrGameVersions.join(', ')) || t('common.notSet');
  return `<button class="editmr"><span class="${missing ? 'pill empty' : 'pill'}">${esc(summary)} · ${esc(r.mrLoaders.join(', ') || '?')}</span></button>
    <div class="sub">${esc(r.mrVersionNumber || t('files.numberMissing'))}</div>`;
}
function fileCell(r) {
  const d = r.detected || {};
  const source = t('source.' + (d.source || 'filename'));
  const warn = [r.versionWarning, warnText(d.warning)].filter(Boolean).join(' · ');
  let extra = '';
  if (S.type === 'modpack' && platformsOf(r).includes('curseforge')) {
    extra = r.serverPackId
      ? `<div class="sub">🖥 ${esc(t('files.serverPack'))}: ${esc(r.serverPackName)} <button class="link rmserver">${esc(t('common.remove'))}</button></div>`
      : `<div class="sub"><button class="link addserver">+ ${esc(t('files.serverPack'))}</button></div>`;
  }
  const version = d.modVersion ? ` · v${esc(d.modVersion)}` : '';
  return `<div class="fn" title="${esc(r.name)}">${esc(r.name)}</div>
    <div class="sub">${(r.size / 1024 / 1024).toFixed(2)} MB · ${esc(source)}${version}</div>
    ${warn ? `<div class="sub warn">⚠ ${esc(warn)}</div>` : ''}${extra}
    <input class="displayname" aria-label="${esc(t('files.displayName'))}" title="${esc(t('files.displayName'))}" value="${esc(r.displayName)}">`;
}
function render() {
  $('count').textContent = S.rows.length;
  $('selectedCount').textContent = selected().length ? t('files.selected', {n: selected().length}) : '';
  $('selectAll').checked = S.rows.length > 0 && S.rows.every(r => r.checked);
  $('rows').innerHTML = S.rows.map(r => `<tr data-id="${esc(r.id)}">
    <td><input class="row-check" type="checkbox" ${r.checked ? 'checked' : ''} aria-label="${esc(r.name)}"></td>
    <td>${fileCell(r)}</td>
    <td>${cfCell(r, 'minecraft')}</td>
    <td class="col-loader">${cfCell(r, 'loader')}</td>
    <td class="col-java">${cfCell(r, 'java')}</td>
    <td class="col-env">${cfCell(r, 'environment')}</td>
    <td>${mrCell(r)}</td>
    <td><select class="row-release" aria-label="${esc(t('col.release'))}">${['release', 'beta', 'alpha'].map(v => `<option value="${v}" ${r.releaseType === v ? 'selected' : ''}>${esc(t('release.' + v))}</option>`).join('')}</select></td>
    <td><button class="editrelations">${r.relations.length} ✎${r.relations.some(x => x.type === 'include') ? ' ⚠' : ''}</button></td>
    <td><button class="editlog">${esc(r.changelogOverride ? t('files.logOwn') : t('files.logShared'))} ✎</button></td>
    <td class="status">${statusLine(r, 'cf')}${statusLine(r, 'mr')}</td>
    <td><button class="remove danger" title="${esc(t('common.remove'))}" ${S.busy ? 'disabled' : ''}>✕</button></td>
  </tr>`).join('') || `<tr><td colspan="12" class="muted" style="text-align:center;padding:24px">${esc(t('files.empty'))}</td></tr>`;
  const anyError = S.rows.some(r => (cfActive(r) && r.cf.status === 'error') || (mrActive(r) && r.mr.status === 'error'));
  $('retry').disabled = S.busy || !anyError;
  $('upload').disabled = S.busy || !S.rows.length;
  $('dryRun').disabled = S.busy || !S.rows.length;
  $('removeSelected').disabled = S.busy || !selected().length;
}

/* ------------------------------------------------------------ files */
async function uploadToBackend(files, extra = {}) {
  const fd = new FormData();
  files.forEach(f => fd.append('files', f, f.name));
  fd.append('projectType', S.type);
  for (const [k, v] of Object.entries(extra)) fd.append(k, v);
  const res = await fetch('/api/files', {method: 'POST', body: fd, headers: {'X-ModFerry-Lang': S.lang}});
  const out = await res.json().catch(() => ({}));
  if (!res.ok) throw Error(out.error || 'HTTP ' + res.status);
  return out.files;
}
async function addFiles(filelist) {
  if (S.busy) return;
  const allowed = Object.keys(S.info.extensions[S.type]);
  const list = [...filelist].filter(f => allowed.some(ext => f.name.toLowerCase().endsWith(ext)));
  if (!list.length) { notice(t('files.noneMatching', {ext: allowed.join(', ')}), true); return; }
  const known = new Set(S.rows.map(r => r.name + ':' + r.size));
  const incoming = list.filter(f => !known.has(f.name + ':' + f.size));
  if (!incoming.length) { notice(t('files.duplicates'), true); return; }
  notice(t('files.reading', {n: incoming.length}));
  try {
    const files = await uploadToBackend(incoming);
    const profile = S.profiles[$('profiles').value];
    for (const f of files) {
      const r = newRow(f);
      if (profile) applyProfileEntry(r, profile);
      inferMR(r);
      if (!r.ids.length) inferCF(r);
      S.rows.push(r);
    }
    render(); preview();
    notice(t('files.added', {n: files.length}));
  } catch (e) { notice(e.message, true); }
}
async function removeRow(id) {
  const r = S.rows.find(x => x.id === id);
  try {
    await api('/api/files/' + encodeURIComponent(id), 'DELETE');
    if (r?.serverPackId) await api('/api/files/' + encodeURIComponent(r.serverPackId), 'DELETE');
    S.rows = S.rows.filter(x => x.id !== id);
    render();
  } catch (e) { notice(e.message, true); }
}
async function clearRows() { for (const r of [...S.rows]) await removeRow(r.id); }

let serverPackTarget = null;
$('serverPackInput').onchange = async e => {
  const file = e.target.files[0]; e.target.value = '';
  const r = S.rows.find(x => x.id === serverPackTarget);
  if (!file || !r) return;
  try {
    const [stored] = await uploadToBackend([file], {purpose: 'serverpack'});
    if (r.serverPackId) await api('/api/files/' + encodeURIComponent(r.serverPackId), 'DELETE');
    r.serverPackId = stored.id; r.serverPackName = stored.name; render();
  } catch (err) { notice(err.message, true); }
};

async function setType(type, {ask = true} = {}) {
  if (type === S.type) return true;
  if (S.rows.length && ask && !confirm(t('project.typeChangeConfirm'))) { renderTypes(); return false; }
  if (S.rows.length) await clearRows();
  S.type = type;
  localStorage.setItem('modferry.type', type);
  renderTypes(); render();
  return true;
}

/* ------------------------------------------------------------ CurseForge version picker */
const CAT_LABEL = {minecraft: 'col.minecraft', loader: 'col.loader', java: 'Java', environment: 'col.env'};
let picker = null;
function openPicker(category, target) {
  if (!S.versions.length) { notice(t('cf.loadFirst'), true); return; }
  const row = S.rows.find(r => r.id === target);
  picker = {category, target, chosen: new Set(target === 'batch' ? [] : idsOf(row, category))};
  $('modalTitle').textContent = t(CAT_LABEL[category]) + (target === 'batch' ? ': ' + t('common.forSelected', {n: selected().length}) : ': ' + row.name);
  $('modalSearch').value = '';
  drawPicker();
  $('modalOverlay').classList.remove('hidden');
  $('modalSearch').focus();
}
function compareVersions(a, b) {
  const x = a.match(/\d+/g) || [], y = b.match(/\d+/g) || [];
  for (let i = 0; i < Math.max(x.length, y.length); i++) { const d = Number(y[i] || 0) - Number(x[i] || 0); if (d) return d; }
  return a.localeCompare(b);
}
function drawPicker() {
  const {category, chosen} = picker;
  const q = $('modalSearch').value.toLowerCase();
  const opts = S.versions.filter(v => v.category === category && v.name.toLowerCase().includes(q))
    .sort((a, b) => category === 'minecraft' ? compareVersions(a.name, b.name) : a.name.localeCompare(b.name, undefined, {numeric: true}));
  $('modalOptions').innerHTML = opts.slice(0, 400).map(v => `<div class="option"><input type="checkbox" id="opt_${v.id}" data-id="${v.id}" ${chosen.has(v.id) ? 'checked' : ''}>
    <label for="opt_${v.id}">${esc(v.name)} <small>(${esc(v.typeName || v.typeSlug || '?')})</small></label><small>ID ${v.id}</small></div>`).join('')
    || `<p class="muted">${esc(t('cf.noHits'))}</p>`;
  $('modalCount').textContent = t('common.chosen', {n: chosen.size});
}
function applyPicker() {
  const {category, target, chosen} = picker;
  const targets = target === 'batch' ? selected() : S.rows.filter(r => r.id === target);
  for (const r of targets) {
    r.ids = uniq([...r.ids.filter(id => !S.versions.some(v => v.id === id && v.category === category)), ...chosen]);
    if (category === 'minecraft') r.versionWarning = '';
  }
  closePicker(); render(); preview();
}
function closePicker() { picker = null; $('modalOverlay').classList.add('hidden'); }
$('modalSearch').oninput = drawPicker;
$('modalOptions').onchange = e => {
  const id = Number(e.target.dataset.id);
  if (!id || !picker) return;
  e.target.checked ? picker.chosen.add(id) : picker.chosen.delete(id);
  $('modalCount').textContent = t('common.chosen', {n: picker.chosen.size});
};
$('modalCancel').onclick = closePicker;
$('modalApply').onclick = applyPicker;

/* ------------------------------------------------------------ Modrinth editor */
let mrEdit = null;
function openMR(target) {
  const batch = target === 'batch';
  if (batch && !selected().length) { notice(t('common.selectFirst'), true); return; }
  const r = batch ? null : S.rows.find(x => x.id === target);
  mrEdit = {target, batch, versions: new Set(batch ? [] : r.mrGameVersions), loaders: new Set(batch ? [] : r.mrLoaders), touched: new Set()};
  $('mrTitle').textContent = 'Modrinth: ' + (batch ? t('common.forSelected', {n: selected().length}) : r.name);
  $('mrBatchHint').classList.toggle('hidden', !batch);
  $('mrNumberWrap').classList.toggle('hidden', batch);
  $('mrNumber').value = batch ? '' : r.mrVersionNumber;
  $('mrEnvWrap').classList.toggle('hidden', !cfg().mrEnv);
  $('mrEnv').innerHTML = MR_ENVS.map(e => `<option value="${e}">${esc(t('env.' + e))}</option>`).join('');
  $('mrEnv').value = batch ? 'client_and_server' : r.mrEnvironment;
  $('mrEnabled').checked = batch ? true : r.publishMR !== false;
  $('cfEnabled').checked = batch ? true : r.publishCF !== false;
  $('mrEnabled').parentElement.classList.toggle('hidden', !batch && !platformsOf(r).includes('modrinth'));
  $('cfEnabled').parentElement.classList.toggle('hidden', !batch && !platformsOf(r).includes('curseforge'));
  $('mrSearch').value = ''; $('mrVersionsFree').value = '';
  drawMRVersions(); drawMRLoaders();
  $('mrOverlay').classList.remove('hidden');
}
function drawMRVersions() {
  const q = $('mrSearch').value.toLowerCase();
  const snapshots = $('showSnapshots').checked;
  const tags = S.mrTags.gameVersions.filter(v => (snapshots || v.type === 'release') && v.version.toLowerCase().includes(q)).map(v => v.version);
  const all = uniq([...mrEdit.versions].filter(v => v.toLowerCase().includes(q)).concat(tags));
  $('mrVersions').innerHTML = all.slice(0, 500).map((v, i) => `<div class="option"><input type="checkbox" id="mrv_${i}" data-v="${esc(v)}" ${mrEdit.versions.has(v) ? 'checked' : ''}><label for="mrv_${i}">${esc(v)}</label></div>`).join('')
    || `<p class="muted">${esc(t('mr.loadTagsFirst'))}</p>`;
  $('mrCount').textContent = t('common.chosen', {n: mrEdit.versions.size});
}
function drawMRLoaders() {
  const options = uniq([...mrLoaderOptions(), ...mrEdit.loaders]);
  $('mrLoaders').innerHTML = options.map(l => `<label><input type="checkbox" data-l="${esc(l)}" ${mrEdit.loaders.has(l) ? 'checked' : ''}> ${esc(l)}</label>`).join('');
}
$('mrSearch').oninput = drawMRVersions;
$('mrVersions').onchange = e => {
  const v = e.target.dataset.v; if (!v) return;
  e.target.checked ? mrEdit.versions.add(v) : mrEdit.versions.delete(v);
  mrEdit.touched.add('versions');
  $('mrCount').textContent = t('common.chosen', {n: mrEdit.versions.size});
};
$('mrVersionsFree').oninput = () => mrEdit.touched.add('versions');
$('mrLoaders').onchange = e => { const l = e.target.dataset.l; if (!l) return; e.target.checked ? mrEdit.loaders.add(l) : mrEdit.loaders.delete(l); mrEdit.touched.add('loaders'); };
$('mrEnv').onchange = () => mrEdit.touched.add('env');
$('mrEnabled').onchange = () => mrEdit.touched.add('mr');
$('cfEnabled').onchange = () => mrEdit.touched.add('cf');
$('mrCancel').onclick = () => { mrEdit = null; $('mrOverlay').classList.add('hidden'); };
$('mrApply').onclick = () => {
  const free = $('mrVersionsFree').value.split(',').map(x => x.trim()).filter(Boolean);
  const versions = uniq([...mrEdit.versions, ...free]);
  const targets = mrEdit.batch ? selected() : S.rows.filter(r => r.id === mrEdit.target);
  const all = !mrEdit.batch;
  for (const r of targets) {
    if (all || mrEdit.touched.has('versions')) r.mrGameVersions = versions;
    if (all || mrEdit.touched.has('loaders')) r.mrLoaders = [...mrEdit.loaders];
    if (all || mrEdit.touched.has('env')) r.mrEnvironment = $('mrEnv').value;
    if (all || mrEdit.touched.has('mr')) r.publishMR = $('mrEnabled').checked;
    if (all || mrEdit.touched.has('cf')) r.publishCF = $('cfEnabled').checked;
    if (all) r.mrVersionNumber = $('mrNumber').value.trim();
  }
  mrEdit = null; $('mrOverlay').classList.add('hidden'); render();
};

/* ------------------------------------------------------------ dependencies */
let relationTarget = null;
function relationRow(entry = {slug: '', projectID: '', modrinthProjectID: '', type: 'requiredDependency'}) {
  const el = document.createElement('div');
  el.className = 'relation-entry';
  el.innerHTML = `<input class="relation-slug" placeholder="${esc(t('deps.slug'))}" value="${esc(entry.slug)}">
    <input class="relation-id" placeholder="${esc(t('deps.cfId'))}" value="${esc(entry.projectID)}">
    <input class="relation-mrid" placeholder="${esc(t('deps.mrId'))}" value="${esc(entry.modrinthProjectID)}">
    <select class="relation-kind">${RELATION_TYPES.map(v => `<option value="${v}" ${v === entry.type ? 'selected' : ''}>${esc(relLabel(v))}</option>`).join('')}</select>
    <button class="relation-remove danger" title="${esc(t('common.remove'))}">✕</button>`;
  el.querySelector('.relation-remove').onclick = () => el.remove();
  $('relationRows').append(el);
}
function openRelations(target) {
  if (S.busy) return;
  if (target === 'batch' && !selected().length) { notice(t('common.selectFirst'), true); return; }
  relationTarget = target;
  const row = S.rows.find(r => r.id === target);
  $('relationTitle').textContent = t('col.deps') + ': ' + (target === 'batch' ? t('common.forSelected', {n: selected().length}) : row.name);
  $('relationRows').innerHTML = '';
  (target === 'batch' ? [] : row.relations).forEach(relationRow);
  $('relationOverlay').classList.remove('hidden');
}
$('relationAdd').onclick = () => relationRow();
$('relationCancel').onclick = () => $('relationOverlay').classList.add('hidden');
$('relationApply').onclick = () => {
  const result = [];
  for (const el of $('relationRows').querySelectorAll('.relation-entry')) {
    const slug = el.querySelector('.relation-slug').value.trim().toLowerCase();
    const projectID = el.querySelector('.relation-id').value.trim();
    const modrinthProjectID = el.querySelector('.relation-mrid').value.trim();
    const type = el.querySelector('.relation-kind').value;
    if (!/^[a-z0-9][a-z0-9_-]{0,99}$/.test(slug)) { notice(t('deps.badSlug', {slug}), true); return; }
    if (projectID && !/^[1-9][0-9]*$/.test(projectID)) { notice(t('deps.badId', {slug}), true); return; }
    if (result.some(x => x.slug === slug && x.type === type)) { notice(t('deps.duplicate', {slug}), true); return; }
    result.push({slug, projectID, modrinthProjectID, type});
  }
  const targets = relationTarget === 'batch' ? selected() : S.rows.filter(r => r.id === relationTarget);
  targets.forEach(r => { r.relations = result.map(x => ({...x})); });
  $('relationOverlay').classList.add('hidden'); render(); clearNotice();
};

/* ------------------------------------------------------------ per-file changelog */
let logTarget = null;
function openLog(r) {
  logTarget = r.id;
  $('logTitle').textContent = t('col.changelog') + ': ' + r.name;
  $('logOverride').checked = r.changelogOverride;
  $('logText').value = r.changelogOverride ? r.changelog : $('changelog').value;
  $('logText').disabled = !r.changelogOverride;
  drawLogPreview();
  $('logOverlay').classList.remove('hidden');
}
function drawLogPreview() {
  const r = S.rows.find(x => x.id === logTarget);
  renderMarkdown(fillTemplate($('logOverride').checked ? $('logText').value : $('changelog').value, r), $('logPreview'));
}
$('logOverride').onchange = () => {
  $('logText').disabled = !$('logOverride').checked;
  if (!$('logOverride').checked) $('logText').value = $('changelog').value;
  drawLogPreview();
};
$('logText').oninput = () => { clearTimeout(window.logTimer); window.logTimer = setTimeout(drawLogPreview, 150); };
$('logCancel').onclick = () => $('logOverlay').classList.add('hidden');
$('logApply').onclick = () => {
  const r = S.rows.find(x => x.id === logTarget);
  if (r) { r.changelogOverride = $('logOverride').checked; r.changelog = r.changelogOverride ? $('logText').value : ''; }
  $('logOverlay').classList.add('hidden'); render();
};

/* ------------------------------------------------------------ profiles */
const pat = (s, v) => (v && s && s.includes(v) ? s.split(v).join('{v}') : s);
const unpat = (s, v) => String(s ?? '').split('{v}').join(v || '');
function currentSettings() {
  return {
    projectType: S.type, projectId: $('project').value, cfSlug: $('cfSlug').value, modrinthProject: $('modrinthProject').value,
    publishCF: $('publishCF').checked, publishMR: $('publishMR').checked, releaseType: $('release').value,
    changelog: $('changelog').value, manualRelease: $('manual').checked, mrStatus: $('mrStatus').value,
    mrFeatured: $('mrFeatured').checked, showSnapshots: $('showSnapshots').checked,
    entries: S.rows.map(r => {
      const v = r.detected?.modVersion || '';
      return {name: r.name, pattern: pat(r.name, v), displayName: pat(r.displayName, v), versionIds: r.ids,
        changelogOverride: r.changelogOverride, changelog: r.changelog, relations: r.relations,
        mrGameVersions: r.mrGameVersions, mrLoaders: r.mrLoaders, mrVersionNumber: pat(r.mrVersionNumber, v),
        mrEnvironment: r.mrEnvironment, publishMR: r.publishMR !== false, publishCF: r.publishCF !== false, releaseType: r.releaseType};
    }),
  };
}
function findEntry(r, profile) {
  const entries = profile.entries || [];
  const v = r.detected?.modVersion || '';
  return entries.find(e => e.name === r.name) || (v ? entries.find(e => e.pattern && e.pattern.includes('{v}') && e.pattern === pat(r.name, v)) : null);
}
function applyProfileEntry(r, profile) {
  const e = findEntry(r, profile);
  if (!e) return false;
  const v = r.detected?.modVersion || '';
  r.ids = e.versionIds || [];
  r.displayName = unpat(e.displayName, v) || r.name;
  r.changelogOverride = !!e.changelogOverride; r.changelog = e.changelog || '';
  r.relations = Array.isArray(e.relations) ? e.relations : [];
  r.mrGameVersions = e.mrGameVersions || []; r.mrLoaders = e.mrLoaders || [];
  r.mrVersionNumber = unpat(e.mrVersionNumber, v); r.mrEnvironment = e.mrEnvironment || 'client_and_server';
  r.publishMR = e.publishMR !== false; r.publishCF = e.publishCF !== false;
  r.releaseType = e.releaseType || profile.releaseType || 'release';
  return true;
}
async function refreshProfiles() {
  try {
    S.profiles = (await api('/api/profiles')).profiles;
    const value = $('profiles').value;
    $('profiles').innerHTML = `<option value="">${esc(t('project.chooseProfile'))}</option>` +
      Object.keys(S.profiles).sort().map(n => `<option value="${esc(n)}">${esc(n)}</option>`).join('');
    $('profiles').value = value;
  } catch (e) { notice(e.message, true); }
}
async function applyProfile() {
  const p = S.profiles[$('profiles').value];
  if (!p) return;
  if (!(await setType(p.projectType || 'mod'))) { $('profiles').value = ''; return; }
  $('project').value = p.projectId || ''; $('cfSlug').value = p.cfSlug || ''; $('modrinthProject').value = p.modrinthProject || '';
  $('publishCF').checked = p.publishCF !== false; $('publishMR').checked = p.publishMR !== false;
  $('release').value = p.releaseType || 'release'; $('changelog').value = p.changelog || ''; $('manual').checked = !!p.manualRelease;
  $('mrStatus').value = p.mrStatus || 'listed'; $('mrFeatured').checked = !!p.mrFeatured; $('showSnapshots').checked = !!p.showSnapshots;
  let matched = 0;
  for (const r of S.rows) if (applyProfileEntry(r, p)) matched++;
  preview(); render();
  notice(t('project.profileLoaded', {n: matched, total: S.rows.length}));
}
$('saveProfile').onclick = async () => {
  const name = prompt(t('project.profileName'), $('profiles').value || '');
  if (!name) return;
  try {
    await api('/api/profiles', 'POST', {name, settings: currentSettings()});
    await refreshProfiles(); $('profiles').value = name;
    notice(t('project.profileSaved'));
  } catch (e) { notice(e.message, true); }
};
$('delProfile').onclick = async () => {
  const name = $('profiles').value;
  if (!name || !confirm(t('project.profileDeleteConfirm', {name}))) return;
  await api('/api/profiles/' + encodeURIComponent(name), 'DELETE');
  $('profiles').value = ''; await refreshProfiles();
};
$('profiles').onchange = applyProfile;

/* ------------------------------------------------------------ remote data */
async function loadVersions() {
  try {
    $('apiState').textContent = t('state.loading');
    S.versions = (await api('/api/versions', 'POST', {token: $('token').value})).versions;
    for (const r of S.rows) if (!r.ids.length) inferCF(r);
    render();
    $('apiState').textContent = t('state.versionsLoaded', {n: S.versions.length});
    clearNotice();
  } catch (e) { $('apiState').textContent = t('state.versionsNotLoaded'); notice(e.message, true); }
}
async function loadMRTags() {
  try {
    S.mrTags = await api('/api/modrinth-tags');
    notice(t('mr.tagsLoaded', {v: S.mrTags.gameVersions.length, l: S.mrTags.loaders.length}));
  } catch (e) { notice(e.message, true); }
}

/* ------------------------------------------------------------ upload */
function payload(list) {
  return {
    projectType: S.type, token: $('token').value, projectId: $('project').value.trim(), cfSlug: $('cfSlug').value.trim(),
    modrinthToken: $('modrinthToken').value, modrinthProject: $('modrinthProject').value.trim(),
    publishCF: $('publishCF').checked, publishMR: $('publishMR').checked, releaseType: $('release').value,
    changelog: $('changelog').value, manualRelease: $('manual').checked, mrStatus: $('mrStatus').value, mrFeatured: $('mrFeatured').checked,
    entries: list.map(r => ({
      id: r.id, displayName: r.displayName, versionIds: r.ids, versionNames: cfNames(r, 'minecraft'),
      changelogOverride: true, changelog: changelogOf(r), relations: r.relations,
      mrGameVersions: r.mrGameVersions, mrLoaders: r.mrLoaders, mrVersionNumber: r.mrVersionNumber, mrEnvironment: r.mrEnvironment,
      publishMR: r.publishMR !== false, publishCF: r.publishCF !== false, releaseType: r.releaseType, serverPackId: r.serverPackId,
    })),
  };
}
function plan(mode) {
  const plans = [];
  for (const [platform, key, enabled, active] of [['curseforge', 'cf', $('publishCF').checked, cfActive], ['modrinth', 'mr', $('publishMR').checked, mrActive]]) {
    if (!enabled) continue;
    let list = S.rows.filter(active);
    const skipped = mode === 'all' ? list.filter(r => r[key].status === 'success').length : 0;
    list = mode === 'all' ? list.filter(r => r[key].status !== 'success') : list.filter(r => r[key].status === 'error');
    if (list.length) plans.push({platform, key, list, skipped});
  }
  return plans;
}
async function startUpload(mode) {
  if (S.busy) return;
  if (!$('publishCF').checked && !$('publishMR').checked) { notice(t('upload.noPlatform'), true); return; }
  const plans = plan(mode);
  if (!plans.length) { notice(t('upload.nothing'), true); return; }
  // Validate everything first so platform A is not uploaded when platform B would fail validation.
  const union = uniq(plans.flatMap(p => p.list));
  const check = await api('/api/dry-run', 'POST', {...payload(union), publishCF: plans.some(p => p.key === 'cf'), publishMR: plans.some(p => p.key === 'mr')}).catch(e => ({error: e.message}));
  if (check.error) { notice(check.error, true); return; }
  const problems = Object.entries(check).map(([k, v]) => {
    const label = k === 'curseforge' ? 'CurseForge: ' : 'Modrinth: ';
    if (!v.ok) return label + v.error;
    if (!v.hasToken) return label + t('upload.tokenMissing');
    return null;
  }).filter(Boolean);
  if (problems.length) { notice(problems.join('\n'), true); return; }
  const summary = plans.map(p => t('upload.planLine', {platform: p.platform === 'curseforge' ? 'CurseForge' : 'Modrinth', n: p.list.length})
    + (p.skipped ? ' ' + t('upload.skipped', {n: p.skipped}) : '')).join('\n');
  if (!confirm(t('upload.confirm') + '\n\n' + summary)) return;
  S.busy = true; render();
  let errors = 0;
  try {
    for (const p of plans) {
      for (const r of p.list) r[p.key] = {status: 'pending', message: ''};
      render();
      const out = await api('/api/upload', 'POST', {...payload(p.list), platform: p.platform});
      S.activeJob = out.jobId;
      errors += await pollJob(p);
    }
    notice(errors ? t('upload.doneErrors', {n: errors}) : t('upload.done'), !!errors);
  } catch (e) { notice(e.message, true); }
  finally { S.activeJob = null; S.busy = false; render(); loadHistory(); }
}
async function pollJob(p) {
  const label = p.platform === 'curseforge' ? 'CurseForge' : 'Modrinth';
  while (S.activeJob) {
    const job = await api('/api/upload/' + encodeURIComponent(S.activeJob));
    for (const r of S.rows) if (job.rows[r.id]) r[p.key] = job.rows[r.id];
    const states = Object.values(job.rows);
    const finished = states.filter(v => v.status === 'success' || v.status === 'error').length;
    const errors = states.filter(v => v.status === 'error').length;
    $('bar').value = 100 * finished / states.length;
    $('progress').textContent = t('upload.progress', {platform: label, done: finished, total: states.length, errors});
    render();
    if (job.done) { S.activeJob = null; return errors; }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  return 0;
}
async function dryRun() {
  const list = S.rows.filter(r => cfActive(r) || mrActive(r));
  try {
    const out = await api('/api/dry-run', 'POST', payload(list));
    const blocks = Object.entries(out).map(([platform, res]) => {
      const name = platform === 'curseforge' ? 'CurseForge' : 'Modrinth';
      if (!res.ok) return `<h3>${name}</h3><div class="error">${esc(res.error)}</div>`;
      return `<h3>${name} · ${esc(t('dry.files', {n: res.items.length}))}</h3><pre class="json">${esc(JSON.stringify(res.items, null, 2))}</pre>`;
    });
    $('dryBody').innerHTML = blocks.join('') || `<p class="muted">${esc(t('upload.noPlatform'))}</p>`;
    $('dryOverlay').classList.remove('hidden');
  } catch (e) { notice(e.message, true); }
}

/* ------------------------------------------------------------ history */
async function loadHistory() {
  try {
    const items = (await api('/api/history')).history;
    $('historyRows').innerHTML = items.slice(0, 300).map(h => `<tr>
      <td>${esc(h.time ? new Date(h.time).toLocaleString(S.lang) : '')}</td>
      <td><span class="badge ${h.platform === 'curseforge' ? 'cf' : 'mr'}">${h.platform === 'curseforge' ? 'CF' : 'MR'}</span></td>
      <td><div class="fn">${esc(h.displayName || h.file)}</div><div class="sub">${esc(h.file)} · ID ${esc(h.id)}</div></td>
      <td>${esc((h.versions || []).join(', '))}</td>
      <td>${esc(t('release.' + (h.releaseType || 'release')))}</td>
      <td>${h.url ? `<a href="${esc(h.url)}" target="_blank" rel="noopener">${esc(t('history.open'))} ↗</a>` : ''}</td>
    </tr>`).join('') || `<tr><td colspan="6" class="muted" style="text-align:center;padding:18px">${esc(t('history.empty'))}</td></tr>`;
  } catch (e) { notice(e.message, true); }
}
$('refreshHistory').onclick = loadHistory;
$('clearHistory').onclick = async () => { if (!confirm(t('history.clearConfirm'))) return; await api('/api/history', 'DELETE'); loadHistory(); };

/* ------------------------------------------------------------ tokens */
async function loadTokenStatus() {
  try { S.tokenStatus = await api('/api/tokens'); showTokenStatus(); } catch (e) { $('tokenState').textContent = e.message; }
}
function showTokenStatus() {
  const s = S.tokenStatus;
  if (!s.mode) return;
  $('tokenState').textContent = s.locked ? '🔒 ' + t('tokens.locked') :
    t('tokens.state', {mode: t(s.mode === 'windows-dpapi' ? 'tokens.modeDpapi' : 'tokens.modePass'),
      cf: t(s.curseforge ? 'tokens.saved' : 'tokens.notSaved'), mr: t(s.modrinth ? 'tokens.saved' : 'tokens.notSaved')});
  $('masterPasswordWrap').classList.toggle('hidden', s.mode === 'windows-dpapi');
}
$('unlockTokens').onclick = async () => {
  try { S.tokenStatus = await api('/api/tokens/unlock', 'POST', {password: $('masterPassword').value}); $('masterPassword').value = ''; showTokenStatus(); notice(t('tokens.unlocked')); }
  catch (e) { notice(e.message, true); }
};
$('saveTokens').onclick = async () => {
  const d = {};
  if ($('token').value.trim()) d.curseforge = $('token').value.trim();
  if ($('modrinthToken').value.trim()) d.modrinth = $('modrinthToken').value.trim();
  if (!Object.keys(d).length) { notice(t('tokens.enterOne'), true); return; }
  try { S.tokenStatus = await api('/api/tokens', 'POST', d); $('token').value = ''; $('modrinthToken').value = ''; showTokenStatus(); notice(t('tokens.stored')); }
  catch (e) { notice(e.message, true); }
};
for (const [id, platform] of [['deleteCFToken', 'curseforge'], ['deleteMRToken', 'modrinth']]) {
  $(id).onclick = async () => {
    if (!confirm(t('tokens.deleteConfirm', {platform}))) return;
    try { S.tokenStatus = await api('/api/tokens/' + platform, 'DELETE'); showTokenStatus(); notice(t('tokens.deleted')); } catch (e) { notice(e.message, true); }
  };
}

/* ------------------------------------------------------------ events */
$('addFiles').onclick = () => $('fileInput').click();
$('addFolder').onclick = () => $('folderInput').click();
$('fileInput').onchange = e => { addFiles(e.target.files); e.target.value = ''; };
$('folderInput').onchange = e => { addFiles(e.target.files); e.target.value = ''; };
for (const type of ['dragenter', 'dragover']) $('drop').addEventListener(type, e => { e.preventDefault(); $('drop').classList.add('drag'); });
for (const type of ['dragleave', 'drop']) $('drop').addEventListener(type, e => { e.preventDefault(); $('drop').classList.remove('drag'); });
$('drop').addEventListener('drop', e => addFiles(e.dataTransfer.files));
$('projectTypes').onchange = e => { if (e.target.name === 'ptype') setType(e.target.value); };

$('rows').addEventListener('change', e => {
  const r = S.rows.find(x => x.id === e.target.closest('tr')?.dataset.id);
  if (!r) return;
  if (e.target.classList.contains('row-release')) r.releaseType = e.target.value;
  if (e.target.classList.contains('row-check')) { r.checked = e.target.checked; preview(); }
  render();
});
$('rows').addEventListener('input', e => {
  if (!e.target.classList.contains('displayname')) return;
  const r = S.rows.find(x => x.id === e.target.closest('tr').dataset.id);
  if (r) r.displayName = e.target.value;
});
$('rows').addEventListener('click', e => {
  const b = e.target.closest('button');
  if (!b) return;
  const r = S.rows.find(x => x.id === b.closest('tr').dataset.id);
  if (!r) return;
  if (b.classList.contains('remove')) { if (!S.busy) removeRow(r.id); }
  else if (b.classList.contains('edit')) openPicker(b.dataset.cat, r.id);
  else if (b.classList.contains('editmr')) openMR(r.id);
  else if (b.classList.contains('editrelations')) openRelations(r.id);
  else if (b.classList.contains('editlog')) openLog(r);
  else if (b.classList.contains('addserver')) { serverPackTarget = r.id; $('serverPackInput').click(); }
  else if (b.classList.contains('rmserver')) { api('/api/files/' + encodeURIComponent(r.serverPackId), 'DELETE').catch(() => {}); r.serverPackId = null; r.serverPackName = ''; render(); }
});
$('selectAll').onchange = e => { S.rows.forEach(r => { r.checked = e.target.checked; }); render(); preview(); };
$('removeSelected').onclick = async () => { for (const r of selected()) await removeRow(r.id); };
document.querySelectorAll('[data-batch]').forEach(b => { b.onclick = () => (selected().length ? openPicker(b.dataset.batch, 'batch') : notice(t('common.selectFirst'), true)); });
$('batchMR').onclick = () => openMR('batch');
$('batchRelations').onclick = () => openRelations('batch');
$('batchRelease').onclick = () => {
  const list = selected();
  if (!list.length) { notice(t('common.selectFirst'), true); return; }
  list.forEach(r => { r.releaseType = $('batchReleaseType').value; });
  render(); notice(t('batch.releaseSet', {n: list.length}));
};
$('batchReset').onclick = () => {
  const list = selected();
  if (!list.length) { notice(t('common.selectFirst'), true); return; }
  if (!confirm(t('batch.resetConfirm', {n: list.length}))) return;
  list.forEach(r => { r.cf = {status: 'ready', message: ''}; r.mr = {status: 'ready', message: ''}; });
  render();
};
$('changelog').oninput = () => { clearTimeout(window.previewTimer); window.previewTimer = setTimeout(preview, 150); };
$('importChangelog').onclick = () => $('changelogInput').click();
$('changelogInput').onchange = async e => {
  const file = e.target.files[0]; e.target.value = '';
  if (!file) return;
  const text = await file.text();
  $('changelog').value = $('latestOnly').checked ? latestSection(text) : text;
  preview(); notice(t('changelog.imported', {file: file.name}));
};
$('loadVersions').onclick = loadVersions;
$('loadMRTags').onclick = loadMRTags;
$('publishCF').onchange = render;
$('publishMR').onchange = render;
$('upload').onclick = () => startUpload('all');
$('retry').onclick = () => startUpload('retry');
$('dryRun').onclick = dryRun;
$('dryClose').onclick = () => $('dryOverlay').classList.add('hidden');
for (const id of ['modalOverlay', 'mrOverlay', 'relationOverlay', 'logOverlay', 'dryOverlay']) {
  $(id).addEventListener('mousedown', e => { if (e.target === $(id)) $(id).classList.add('hidden'); });
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') document.querySelectorAll('.overlay:not(.hidden)').forEach(o => o.classList.add('hidden'));
});
$('lang').onchange = async () => { await loadLang($('lang').value); clearNotice(); renderTypes(); render(); preview(); showTokenStatus(); refreshProfiles(); loadHistory(); };
window.addEventListener('beforeunload', e => { if (S.busy) { e.preventDefault(); e.returnValue = ''; } });

/* ------------------------------------------------------------ start */
(async function init() {
  const stored = localStorage.getItem('modferry.lang');
  const lang = stored || ((navigator.language || 'en').toLowerCase().startsWith('de') ? 'de' : 'en');
  await loadLang(lang);
  S.info = await api('/api/info');
  $('appVersion').textContent = 'v' + S.info.version;
  const type = localStorage.getItem('modferry.type');
  if (type && TYPES[type]) S.type = type;
  renderTypes(); render(); preview();
  refreshProfiles(); loadTokenStatus(); loadHistory();
})();
