/* VaultBox - Vault Modular configurator. Vanilla JS, no dependencies. */
'use strict';
const $ = (s, r = document) => r.querySelector(s);
const enc = p => p.split('/').map(encodeURIComponent).join('/');
const thumbUrl = p => 'assets/thumbs/' + enc(p.replace(/\.stl$/i, '.png'));
const manualUrl = n => 'assets/manual/' + n + '.png';
const partUrl = p => 'parts/' + enc(p);
const pad = n => String(n).padStart(2, '0');

function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'dataset') Object.assign(e.dataset, v);
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return e;
}

let CAT = null;
const state = { draft: null, project: { name: '', vaults: [] }, hover: null };

/* ------------------------------------------------------------ persistence */
function save() { try { localStorage.setItem('vaultbox.project', JSON.stringify(state.project)); } catch (e) { /* ignore */ } }
function load() {
  try {
    const p = JSON.parse(localStorage.getItem('vaultbox.project') || 'null');
    if (p && Array.isArray(p.vaults)) {
      p.vaults = p.vaults.filter(d => CAT.variants.some(v => v.id === d.vid));
      state.project = p;
    }
  } catch (e) { /* ignore */ }
}

/* ------------------------------------------------------------ model */
const variantOf = id => CAT.variants.find(v => v.id === id);
function modeStep(v) {
  return {
    id: 'mode', title: 'How will it be used?', kind: 'radio',
    help: 'Manual p.4: five ways of using a Vault. Only options that fit the chosen use are shown below.',
    choices: CAT.modes.filter(m => v.modes.includes(m.id)).map(m => ({ id: m.id, label: m.label, sub: m.desc, img: m.img, files: [], thumb: false }))
  };
}
const stepsOf = v => [modeStep(v), ...v.steps];
const matches = (when, ans) => !when || Object.entries(when).every(([k, vals]) => vals.includes(ans[k]));
const visChoices = (s, ans) => (s.choices || []).filter(c => matches(c.when, ans));
function stepVisible(s, ans) {
  if (!matches(s.when, ans)) return false;
  if (s.kind === 'radio') return visChoices(s, ans).length > 0;
  return true;
}
function normalize(d) {
  const v = variantOf(d.vid);
  const ans = d.answers;
  let modeDone = !!ans.mode;
  for (const s of stepsOf(v)) {
    if (s.id !== 'mode' && !ans.mode) { delete ans[s.id]; continue; }
    if (!stepVisible(s, ans)) { delete ans[s.id]; continue; }
    if (s.kind !== 'radio') continue;
    const vc = visChoices(s, ans);
    if (!vc.some(c => c.id === ans[s.id])) {
      const def = vc.find(c => c.default) || (s.id === 'height' ? vc[0] : null) || (vc.length === 1 ? vc[0] : null);
      if (def) ans[s.id] = def.id; else delete ans[s.id];
    }
  }
  return d;
}
function visibleSteps(d) {
  const v = variantOf(d.vid);
  if (!d.answers.mode) return [stepsOf(v)[0]];
  return stepsOf(v).filter(s => stepVisible(s, d.answers));
}
const isComplete = d => visibleSteps(d).every(s => s.kind !== 'radio' || d.answers[s.id]);
function chosen(s, d) { return (s.choices || []).find(c => c.id === d.answers[s.id]); }
const qtyApplies = (s, c) => s.qty && c && (c.files.length || (c.hw || []).length) && (!s.qty.appliesTo || s.qty.appliesTo.includes(c.id));
function qtyOf(s, d, c) { return qtyApplies(s, c) ? (d.qty && d.qty[s.id] != null ? d.qty[s.id] : s.qty.default) : 1; }

/* collect printed parts + hardware for one vault draft */
function collect(d) {
  const v = variantOf(d.vid);
  const parts = new Map();
  const hw = [];
  const sel = [];
  const add = (f, mult, step) => {
    const q = f.q == null ? null : f.q * mult;
    const k = f.p;
    if (parts.has(k)) {
      const e = parts.get(k);
      if (e.q != null && q != null) e.q += q; else if (q != null) e.q = q;
      if (f.n && !e.n.includes(f.n)) e.n.push(f.n);
    } else parts.set(k, { p: f.p, l: f.l, q, n: f.n ? [f.n] : [], step });
  };
  for (const s of visibleSteps(d)) {
    if (s.kind === 'radio') {
      const c = chosen(s, d);
      if (!c) continue;
      sel.push([s.title, c.label]);
      const m = qtyOf(s, d, c);
      c.files.forEach(f => add(f, m, s.title));
      (c.hw || []).forEach(x => hw.push({ ...x, qty: x.qty == null ? null : x.qty * m, srcStep: s.title }));
    } else if (s.kind === 'fixed') {
      s.files.forEach(f => add(f, 1, s.title));
    } else if (s.kind === 'hwonly') {
      s.hw.forEach(x => hw.push({ ...x, srcStep: s.title }));
    }
  }
  return { parts: [...parts.values()], hw, sel };
}
const vaultName = d => { const v = variantOf(d.vid); return v.family + ' ' + (v.type === 'drawer' ? 'Drawer' : 'Sustainer') + (d.answers.height ? ' ' + d.answers.height : ''); };

/* ------------------------------------------------------------ images */
function setImg(img, urls) {
  const list = urls.filter(Boolean);
  let i = 0;
  const next = () => { if (i < list.length) img.src = list[i++]; else { img.removeAttribute('src'); img.style.visibility = 'hidden'; } };
  img.style.visibility = 'visible';
  img.onerror = next;
  next();
}
function choiceImgs(c) {
  const out = [];
  if (c.img) out.push(manualUrl(c.img));
  if (c.thumb) out.push(thumbUrl(c.thumb));
  else if (c.thumb !== false && c.files && c.files[0]) out.push(thumbUrl(c.files[0].p));
  return out;
}
function setHero(urls, cap) {
  setImg($('#heroImg'), urls);
  $('#heroCap').textContent = cap || '';
}

/* ------------------------------------------------------------ views */
function render() {
  const keepY = window.scrollY;
  const main = $('#main');
  main.replaceChildren();
  if (!state.draft) renderPicker(main); else renderWizard(main);
  renderSide();
  renderCrumbs();
  $('#projCount').textContent = state.project.vaults.length;
  window.scrollTo(0, keepY);
}

function renderCrumbs() {
  const c = $('#crumbs');
  const d = state.draft;
  const items = [['Vault', !d], ['Use', d && !d.answers.mode], ['Options', d && d.answers.mode && !isComplete(d)], ['Ready to add', d && isComplete(d)]];
  c.replaceChildren(...items.map(([t, on]) => h('span', { class: on ? 'on' : '' }, t)));
}

function renderPicker(main) {
  main.append(h('h2', {}, 'Choose a vault'),
    h('p', { class: 'lead' }, '50 size variants: ' + CAT.variants.filter(v => v.type === 'drawer').length + ' drawer and ' + CAT.variants.filter(v => v.type === 'sustainer').length + ' sustainer families. The number is the depth in Gridfinity units (3 to 7).'));
  if (state.project.vaults.length) {
    main.append(h('div', { class: 'note' }, 'Project in progress: ' + state.project.vaults.length + ' vault(s). Pick another to add, or open Project to build.'));
  }
  for (const type of ['drawer', 'sustainer']) {
    const g = h('div', { class: 'group' }, h('h3', {}, type === 'drawer' ? 'Drawers (slide-out boxes)' : 'Sustainers (hinged lid)'));
    const letters = [...new Set(CAT.variants.filter(v => v.type === type).map(v => v.letter + (v.sq ? '²' : '')))];
    const order = ['S', 'M', 'L', 'L²', 'XL', 'XL²'];
    letters.sort((a, b) => order.indexOf(a) - order.indexOf(b));
    for (const L of letters) {
      g.append(h('h3', {}, L + ' family'));
      const chips = h('div', { class: 'chips' });
      CAT.variants.filter(v => v.type === type && (v.letter + (v.sq ? '²' : '')) === L).forEach(v => {
        chips.append(h('button', {
          class: 'chip', type: 'button',
          onmouseenter: () => setHero(vHero(v), v.family + ' ' + type),
          onfocus: () => setHero(vHero(v), v.family + ' ' + type),
          onclick: () => pickVault(v.id)
        }, v.family, h('small', {}, v.heights.join(' ')))); 
      });
      g.append(chips);
    }
    main.append(g);
  }
  if (!state.hover) setHero([manualUrl('type_drawers')], 'Drawers and sustainers');
}

const vHero = v => [v.hero && thumbUrl(v.hero), manualUrl(v.heroImg)];
function pickVault(vid) {
  const v = variantOf(vid);
  state.draft = normalize({ vid, answers: {}, qty: {} });
  setHero(vHero(v), v.family + ' ' + v.type);
  render();
  window.scrollTo(0, 0);
}

function renderWizard(main) {
  const d = state.draft, v = variantOf(d.vid);
  main.append(h('h2', {}, v.family + ' ' + (v.type === 'drawer' ? 'drawer' : 'sustainer')),
    h('p', { class: 'lead' }, v.type === 'drawer' ? 'Slide-out drawer in the ' + v.letter + ' size, depth ' + v.depth + '.' : 'Hinged-lid sustainer in the ' + v.letter + ' size, depth ' + v.depth + '.'));
  if (v.note) main.append(h('div', { class: 'note' }, v.note));
  for (const s of visibleSteps(d)) main.append(renderStep(s, d));
  if (!d.answers.mode) main.append(h('p', { class: 'help' }, 'Choose how it will be used and the matching options appear.'));
  const ok = isComplete(d);
  main.append(h('div', { class: 'actions' },
    h('button', { class: 'btn', type: 'button', onclick: () => { state.draft = null; render(); } }, 'Back to vault picker'),
    h('button', { class: 'btn', type: 'button', disabled: !ok, onclick: () => addDraft(false) }, 'Add to project, then add another vault'),
    h('button', { class: 'btn primary', type: 'button', disabled: !ok, onclick: () => addDraft(true) }, 'Add to project and review')));
}

function renderStep(s, d) {
  const g = h('section', { class: 'group', id: 'step-' + s.id }, h('h3', {}, s.title));
  if (s.help) g.append(h('p', { class: 'help' }, s.help));
  if (s.kind === 'radio') {
    const cards = h('div', { class: 'cards' });
    for (const c of visChoices(s, d.answers)) {
      const imgs = choiceImgs(c);
      const im = h('div', { class: 'im' });
      if (imgs.length) { const i = h('img', { alt: '', loading: 'lazy' }); setImg(i, imgs); im.append(i); } else im.append(h('span', { class: 'ph' }, c.id === 'none' ? '\u2205' : '\u25A3'));
      const sel = d.answers[s.id] === c.id;
      const nfiles = c.files.length;
      cards.append(h('button', {
        class: 'card' + (sel ? ' sel' : ''), type: 'button', 'aria-pressed': sel ? 'true' : 'false',
        onmouseenter: () => imgs.length && setHero(imgs, s.title + ': ' + c.label),
        onfocus: () => imgs.length && setHero(imgs, s.title + ': ' + c.label),
        onclick: () => { d.answers[s.id] = c.id; normalize(d); if (imgs.length) setHero(imgs, s.title + ': ' + c.label); render(); }
      }, h('span', { class: 'tick' }, '\u2713'), im,
        h('div', { class: 'tx' }, h('b', {}, c.label), c.sub && h('span', {}, c.sub), nfiles > 0 && h('span', {}, nfiles + (nfiles === 1 ? ' file' : ' files')))));
    }
    g.append(cards);
    const c = chosen(s, d);
    if (qtyApplies(s, c)) {
      const inp = h('input', { type: 'number', min: s.qty.min, max: s.qty.max, value: qtyOf(s, d, c) });
      inp.addEventListener('change', () => { d.qty[s.id] = Math.max(s.qty.min, Math.min(s.qty.max, parseInt(inp.value, 10) || s.qty.default)); render(); });
      g.append(h('div', { class: 'qty' }, s.qty.label, inp, s.qty.note && h('span', {}, s.qty.note)));
    }
  } else if (s.kind === 'fixed') {
    const l = h('div', { class: 'fixedlist' });
    s.files.forEach(f => {
      const i = h('img', { alt: '', loading: 'lazy' });
      setImg(i, [thumbUrl(f.p)]);
      l.append(h('div', { class: 'fx', onmouseenter: () => setHero([thumbUrl(f.p)], f.l) }, h('div', { class: 'im' }, i), h('div', { class: 'tx' }, f.l, f.n && h('span', {}, f.n), f.q != null && h('span', {}, 'x' + f.q))));
    });
    g.append(l);
  } else if (s.kind === 'hwonly') {
    g.append(hwTable(s.hw));
  }
  return g;
}

function hwTable(list) {
  return h('div', { class: 'hwl' }, list.map(x => h('div', {}, h('span', {}, (x.qty == null ? '?' : 'x' + x.qty) + '  ' + x.item), h('span', { class: 'hint' }, x.per || ''))));
}

function renderSide() {
  const box = $('#summary');
  box.replaceChildren();
  const d = state.draft;
  if (!d) {
    box.append(h('h4', {}, 'Project'), h('div', {}, state.project.vaults.length ? state.project.vaults.length + ' vault(s) added' : 'Nothing added yet'));
    return;
  }
  const v = variantOf(d.vid), r = collect(d);
  const dl = h('dl', {});
  const row = (a, b) => dl.append(h('dt', {}, a), h('dd', {}, b));
  row('Vault', v.family + ' ' + v.type);
  r.sel.forEach(([a, b]) => row(a, b));
  box.append(h('h4', {}, 'This vault'), dl,
    h('div', { class: 'hint', style: 'margin-top:8px' }, r.parts.length + ' printed file(s), ' + r.hw.length + ' hardware line(s)'));
}

/* ------------------------------------------------------------ project */
function addDraft(finish) {
  const d = state.draft;
  if (!isComplete(d)) return;
  state.project.vaults.push(JSON.parse(JSON.stringify(d)));
  state.draft = null;
  save();
  render();
  if (finish) openProject();
  else window.scrollTo(0, 0);
}
function openProject() { renderProject(); $('#projDrawer').hidden = false; }
function closeProject() { $('#projDrawer').hidden = true; }

function renderProject() {
  const list = $('#projList');
  list.replaceChildren();
  if (!state.project.vaults.length) list.append(h('div', { class: 'empty' }, 'No vaults yet. Pick one and add it to the project.'));
  state.project.vaults.forEach((d, i) => {
    const r = collect(d);
    list.append(h('div', { class: 'pv' },
      h('div', { class: 'h' }, h('span', {}, pad(i + 1) + '  ' + vaultName(d)),
        h('span', {}, h('button', { type: 'button', onclick: () => { state.project.vaults.splice(i, 1); state.draft = d; save(); closeProject(); render(); } }, 'Edit'),
          h('button', { type: 'button', onclick: () => { state.project.vaults.splice(i + 1, 0, JSON.parse(JSON.stringify(d))); save(); render(); renderProject(); } }, 'Duplicate'),
          h('button', { type: 'button', onclick: () => { state.project.vaults.splice(i, 1); save(); render(); renderProject(); } }, 'Remove'))),
      h('div', { class: 'd' }, r.sel.map(x => x[1]).join(' / ')),
      h('div', { class: 'd' }, r.parts.length + ' printed file(s)')));
  });
  $('#projName').value = state.project.name || '';
  $('#buildBtn').disabled = !state.project.vaults.length;
  $('#buildFolderBtn').disabled = !state.project.vaults.length;
  $('#buildFolderBtn').hidden = !('showDirectoryPicker' in window);
  $('#buildHint').textContent = 'Build downloads <name>.zip (a folder named after the project, with all STL files, BOM.txt and Hardware.txt) into your browser download location, normally ~/Downloads. ' +
    ('showDirectoryPicker' in window ? '"Build to a folder" lets you pick ~/Downloads and writes the folder directly, with a numeric suffix if it exists.' : '');
}

/* ------------------------------------------------------------ build plan */
const safeName = n => n.replace(/[\\/:*?"<>|\u0000-\u001f]/g, '-').replace(/\s+/g, ' ').trim().replace(/^\.+/, '');
const baseName = p => p.split('/').pop();

function buildPlan(name) {
  const files = [];          // {src, out}
  const bom = [], hwt = [];
  const today = new Date().toISOString().slice(0, 10);
  bom.push('VAULT MODULAR - BILL OF MATERIALS', 'Project : ' + name, 'Date    : ' + today, 'Modules : ' + state.project.vaults.length, '');
  const totals = new Map();
  const unknown = [];
  const noQty = [];
  state.project.vaults.forEach((d, i) => {
    const v = variantOf(d.vid), r = collect(d), n = pad(i + 1);
    bom.push('='.repeat(72), 'MODULE ' + n + ': ' + vaultName(d), '='.repeat(72), 'Selections:');
    r.sel.forEach(([a, b]) => bom.push('  - ' + a + ': ' + b));
    if (v.note) bom.push('', 'NOTE: ' + v.note);
    bom.push('', 'Printed parts (file in this folder  |  qty to print  |  notes):');
    r.parts.forEach(p => {
      const out = n + '_' + baseName(p.p);
      files.push({ src: p.p, out });
      const q = p.q == null ? 'qty not in manual' : 'x' + p.q;
      if (p.q == null) noQty.push(n + '_' + p.l);
      const notes = p.n.map(x => x.replace(/^qty not in manual;?\s*/, '').trim()).filter(Boolean);
      bom.push('  ' + out + '  |  ' + q + (notes.length ? '  |  ' + notes.join('; ') : ''));
    });
    bom.push('');
    hwt.push('MODULE ' + n + ': ' + vaultName(d));
    if (!r.hw.length) hwt.push('  (no hardware listed in the manual for this selection)');
    r.hw.forEach(x => {
      const label = (x.qty == null ? '  ?  ' : '  x' + x.qty + ' ') + x.item + (x.per ? '  (' + x.per + ')' : '') + (x.src ? '  [' + x.src + ']' : '');
      hwt.push(label);
      const t = totals.get(x.item) || { qty: 0, unk: false };
      if (x.qty == null) t.unk = true; else t.qty += x.qty;
      totals.set(x.item, t);
    });
    hwt.push('');
  });
  // BOM tail: merged counts per source file name, so identical parts across modules are visible at a glance
  const merged = new Map();
  state.project.vaults.forEach(d => collect(d).parts.forEach(p => {
    const e = merged.get(p.p) || { l: p.l, q: 0, unk: false, n: 0 };
    if (p.q == null) e.unk = true; else e.q += p.q;
    e.n += 1; merged.set(p.p, e);
  }));
  bom.push('='.repeat(72), 'MERGED TOTALS (identical source file across modules)', '='.repeat(72));
  [...merged.values()].sort((a, b) => a.l.localeCompare(b.l)).forEach(e =>
    bom.push('  ' + e.l + '  |  appears in ' + e.n + ' module(s)  |  ' + (e.unk ? 'qty not in manual' : 'x' + e.q)));
  bom.push('', 'Source: USSA Vault Modular manual (hardware pp.17-19, assembly PDFs). "qty not in manual" means the manual states no count - check the assembly pages.');
  const head = ['REQUIRED HARDWARE (not printed)', 'Project: ' + name, 'Date   : ' + today, '', 'TOTALS - ALL MODULES'];
  [...totals.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([k, t]) =>
    head.push('  ' + (t.qty ? 'x' + t.qty : '?') + '  ' + k + (t.unk ? '   (+ more, qty not in manual for some uses)' : '')));
  head.push('', 'PER MODULE', '');
  const hwText = head.concat(hwt, ['Quantities come from the manual hardware list. Items marked ? have no quantity in the manual.']).join('\n') + '\n';
  return { files, bomText: bom.join('\n') + '\n', hwText, count: files.length };
}

/* ------------------------------------------------------------ zip (store only, streaming CRC) */
const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
function crcUpdate(crc, buf) { let c = crc; for (let i = 0; i < buf.length; i++) c = CRC[(c ^ buf[i]) & 255] ^ (c >>> 8); return c; }
const u16 = n => [n & 255, (n >> 8) & 255];
const u32 = n => [n & 255, (n >>> 8) & 255, (n >>> 16) & 255, (n >>> 24) & 255];

async function makeZip(root, entries, onProgress, log) {
  const parts = [], central = [];
  let offset = 0, i = 0;
  const now = new Date();
  const dosT = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1);
  const dosD = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
  for (const e of entries) {
    const nameBytes = new TextEncoder().encode(root + '/' + e.out);
    let crc = 0xFFFFFFFF, size = 0;
    const chunks = [];
    if (e.text != null) {
      const b = new TextEncoder().encode(e.text); chunks.push(b); crc = crcUpdate(crc, b); size = b.length;
    } else {
      const res = await fetch(partUrl(e.src));
      if (!res.ok) throw new Error('fetch failed (' + res.status + '): ' + e.src);
      const rd = res.body.getReader();
      for (;;) { const { done, value } = await rd.read(); if (done) break; chunks.push(value); crc = crcUpdate(crc, value); size += value.length; }
    }
    crc = (crc ^ 0xFFFFFFFF) >>> 0;
    if (size >= 0xFFFFFFFF || offset >= 0xFFFFFFF0) throw new Error('Zip64 needed (file or archive over 4 GB). Use "Build to a folder" instead.');
    const lh = new Uint8Array([0x50, 0x4b, 3, 4, 20, 0, 0, 8, 0, 0, ...u16(dosT), ...u16(dosD), ...u32(crc), ...u32(size), ...u32(size), ...u16(nameBytes.length), 0, 0, ...nameBytes]);
    parts.push(lh, new Blob(chunks));
    central.push(new Uint8Array([0x50, 0x4b, 1, 2, 20, 0, 20, 0, 0, 8, 0, 0, ...u16(dosT), ...u16(dosD), ...u32(crc), ...u32(size), ...u32(size), ...u16(nameBytes.length), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...u32(offset), ...nameBytes]));
    offset += lh.length + size;
    i++; onProgress(i / entries.length); log('added ' + e.out + ' (' + (size / 1048576).toFixed(1) + ' MB)');
  }
  const cdStart = offset;
  let cdSize = 0;
  central.forEach(c => { parts.push(c); cdSize += c.length; });
  if (entries.length > 65534) throw new Error('Too many files for a basic zip.');
  parts.push(new Uint8Array([0x50, 0x4b, 5, 6, 0, 0, 0, 0, ...u16(entries.length), ...u16(entries.length), ...u32(cdSize), ...u32(cdStart), 0, 0]));
  return new Blob(parts, { type: 'application/zip' });
}

function logTo(msg) { const l = $('#buildLog'); l.hidden = false; l.textContent += msg + '\n'; l.scrollTop = l.scrollHeight; }
function setProg(f) { $('#buildProg').hidden = false; $('#buildBar').style.width = Math.round(f * 100) + '%'; }

function entriesFor(plan) {
  return [...plan.files.map(f => ({ src: f.src, out: f.out })), { out: 'BOM.txt', text: plan.bomText }, { out: 'Hardware.txt', text: plan.hwText }];
}
function getName() {
  const n = safeName($('#projName').value || '');
  if (!n) { $('#projName').focus(); $('#buildHint').textContent = 'Give the project a name first.'; return null; }
  state.project.name = n; save();
  return n;
}
async function buildZip() {
  const name = getName(); if (!name) return;
  const btn = $('#buildBtn'); btn.disabled = true; $('#buildLog').textContent = ''; setProg(0);
  try {
    const plan = buildPlan(name);
    logTo('Fetching ' + plan.count + ' STL file(s) from parts/ ...');
    const blob = await makeZip(name, entriesFor(plan), setProg, logTo);
    const a = h('a', { href: URL.createObjectURL(blob), download: name + '.zip' });
    document.body.append(a); a.click(); a.remove();
    logTo('Done: ' + name + '.zip (' + (blob.size / 1048576).toFixed(1) + ' MB). Check your browser downloads.');
  } catch (e) { logTo('ERROR: ' + e.message); } finally { btn.disabled = false; }
}
async function buildFolder() {
  const name = getName(); if (!name) return;
  $('#buildLog').textContent = ''; setProg(0);
  try {
    const parent = await window.showDirectoryPicker({ mode: 'readwrite', id: 'vaultbox', startIn: 'downloads' });
    let folder = name, n = 1;
    for (;;) { try { await parent.getDirectoryHandle(folder); n++; folder = name + ' (' + n + ')'; } catch (e) { break; } }
    const dir = await parent.getDirectoryHandle(folder, { create: true });
    const plan = buildPlan(folder);
    const ents = entriesFor(plan);
    let i = 0;
    for (const e of ents) {
      const fh = await dir.getFileHandle(e.out, { create: true });
      const w = await fh.createWritable();
      if (e.text != null) await w.write(e.text);
      else { const res = await fetch(partUrl(e.src)); if (!res.ok) { await w.abort(); throw new Error('fetch failed (' + res.status + '): ' + e.src); } await res.body.pipeTo(w); }
      if (e.text != null) await w.close();
      i++; setProg(i / ents.length); logTo('wrote ' + e.out);
    }
    logTo('Done: folder "' + folder + '" with ' + ents.length + ' files.');
  } catch (e) { if (e.name !== 'AbortError') logTo('ERROR: ' + e.message); }
}

/* ------------------------------------------------------------ boot */
async function boot() {
  try {
    const r = await fetch('data/catalog.json');
    if (!r.ok) throw new Error(r.status);
    CAT = await r.json();
  } catch (e) {
    $('#main').replaceChildren(h('div', { class: 'note' }, 'Could not load data/catalog.json. Open this page through a web server, not file://. From the VaultBox folder run: ./serve.sh and open http://localhost:8765/'));
    return;
  }
  load();
  $('#projBtn').addEventListener('click', openProject);
  $('#projClose').addEventListener('click', closeProject);
  $('#projDrawer').addEventListener('click', e => { if (e.target.id === 'projDrawer') closeProject(); });
  $('#buildBtn').addEventListener('click', buildZip);
  $('#buildFolderBtn').addEventListener('click', buildFolder);
  $('#projName').addEventListener('input', e => { state.project.name = e.target.value; save(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeProject(); });
  render();
}
boot();
