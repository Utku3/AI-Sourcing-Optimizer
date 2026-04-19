from flask import Flask, render_template_string, jsonify
import json
from itertools import combinations
from collections import defaultdict
from db import db
from service import suggest_alternatives
from comparison_engine import compare_products
from enrich_raw_materials import start_watcher

app = Flask(__name__)
start_watcher(interval_seconds=60)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YumYum Camer</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:       #09090b;
  --s1:       #18181b;
  --s2:       #27272a;
  --s3:       #3f3f46;
  --border:   rgba(255,255,255,0.07);
  --border2:  rgba(255,255,255,0.12);
  --t1:       #fafafa;
  --t2:       #a1a1aa;
  --t3:       #71717a;
  --blue:     #3b82f6;
  --blue-bg:  rgba(59,130,246,0.10);
  --green:    #22c55e;
  --green-bg: rgba(34,197,94,0.10);
  --amber:    #f59e0b;
  --amber-bg: rgba(245,158,11,0.10);
  --red:      #ef4444;
  --red-bg:   rgba(239,68,68,0.10);
}

html, body { height: 100%; background: var(--bg); color: var(--t1); font-family: 'Inter', system-ui, sans-serif; font-size: 14px; line-height: 1.5; -webkit-font-smoothing: antialiased; }

/* ── Layout ── */
.app { display: flex; flex-direction: column; min-height: 100vh; }

header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 32px; height: 56px;
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 50; background: rgba(9,9,11,0.85);
  backdrop-filter: blur(12px);
}

.logo { font-size: 15px; font-weight: 700; letter-spacing: -0.3px; color: var(--t1); }
.logo span { color: var(--blue); }

nav { display: flex; gap: 2px; background: var(--s1); padding: 3px; border-radius: 8px; border: 1px solid var(--border); }
nav button {
  padding: 5px 16px; border: none; background: transparent; color: var(--t3);
  font-family: inherit; font-size: 13px; font-weight: 500; border-radius: 6px;
  cursor: pointer; transition: all 0.15s;
}
nav button.active { background: var(--s2); color: var(--t1); }
nav button:hover:not(.active) { color: var(--t2); }

.main { flex: 1; max-width: 1100px; width: 100%; margin: 0 auto; padding: 40px 32px; }

/* ── Tab content ── */
.tab-pane { display: none; }
.tab-pane.active { display: block; }

/* ── Page header ── */
.page-header { margin-bottom: 28px; }
.page-header h2 { font-size: 20px; font-weight: 600; letter-spacing: -0.3px; }
.page-header p { color: var(--t3); margin-top: 4px; font-size: 13px; }

/* ── Search ── */
.search-wrap { position: relative; }
.search-wrap svg { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--t3); pointer-events: none; }
.search-input {
  width: 100%; padding: 10px 12px 10px 38px;
  background: var(--s1); border: 1px solid var(--border2);
  border-radius: 8px; color: var(--t1); font-family: inherit; font-size: 14px;
  outline: none; transition: border-color 0.15s;
}
.search-input:focus { border-color: var(--blue); }
.search-input::placeholder { color: var(--t3); }

/* ── Company list ── */
.company-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px; margin-top: 16px;
}
.company-item {
  padding: 12px 16px; background: var(--s1); border: 1px solid var(--border);
  border-radius: 8px; cursor: pointer; transition: all 0.15s;
  display: flex; align-items: center; justify-content: space-between;
}
.company-item:hover { border-color: var(--border2); background: var(--s2); }
.company-item .cname { font-weight: 500; font-size: 13px; }
.company-item .arrow { color: var(--t3); font-size: 16px; }
.company-empty { color: var(--t3); text-align: center; padding: 48px 0; font-size: 13px; }

/* ── Back button ── */
.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  color: var(--t3); font-size: 13px; font-weight: 500; cursor: pointer;
  background: none; border: none; font-family: inherit;
  padding: 0; margin-bottom: 24px; transition: color 0.15s;
}
.back-btn:hover { color: var(--t1); }

/* ── Stats row ── */
.stats-row { display: flex; gap: 12px; margin-bottom: 32px; }
.stat-card {
  flex: 1; padding: 16px 20px; background: var(--s1);
  border: 1px solid var(--border); border-radius: 10px;
}
.stat-card .val { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
.stat-card .lbl { color: var(--t3); font-size: 12px; margin-top: 2px; }
.stat-card.highlight .val { color: var(--blue); }

/* ── Section title ── */
.section-title {
  font-size: 12px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--t3); margin-bottom: 12px;
}

/* ── Consolidation card ── */
.consolidation-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 40px; }
.consolidation-card {
  padding: 20px; background: var(--s1); border: 1px solid var(--border2);
  border-radius: 10px; border-left: 3px solid var(--blue);
}
.consolidation-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.consolidation-title { font-size: 12px; font-weight: 600; color: var(--blue); text-transform: uppercase; letter-spacing: 0.05em; }
.consolidation-body { display: grid; grid-template-columns: 1fr auto 1fr; gap: 12px; align-items: center; }
.c-material { background: var(--s2); padding: 12px; border-radius: 8px; }
.c-material .mat-name { font-weight: 600; font-size: 13px; margin-bottom: 2px; }
.c-material .mat-supplier { color: var(--t3); font-size: 12px; margin-bottom: 6px; }
.c-material .mat-fgs { display: flex; flex-wrap: wrap; gap: 4px; }
.c-arrow { text-align: center; color: var(--t3); font-size: 18px; }
.consolidation-footer { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); color: var(--t3); font-size: 12px; }

/* ── Material cards (company view) ── */
.material-list { display: flex; flex-direction: column; gap: 8px; }
.material-card {
  padding: 16px 20px; background: var(--s1); border: 1px solid var(--border);
  border-radius: 10px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;
}
.material-card .mat-name { font-weight: 600; font-size: 13px; }
.material-card .col-label { font-size: 11px; color: var(--t3); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; font-weight: 600; }

/* ── Tags / pills ── */
.tag {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 500; background: var(--s2); color: var(--t2); border: 1px solid var(--border2);
}
.tag.class  { background: var(--blue-bg);  color: var(--blue); border-color: transparent; }
.tag.strong { background: var(--green-bg); color: var(--green); border-color: transparent; }
.tag.possible{ background: var(--amber-bg); color: var(--amber); border-color: transparent; }
.tag.weak   { background: var(--red-bg);   color: var(--red);   border-color: transparent; }

/* ── Materials tab ── */
.selectors-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.selector-wrap { position: relative; }
.selector-label { font-size: 12px; font-weight: 600; color: var(--t3); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
.selector-dropdown {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0; z-index: 100;
  background: var(--s1); border: 1px solid var(--border2); border-radius: 8px;
  max-height: 220px; overflow-y: auto; display: none;
}
.selector-dropdown.open { display: block; }
.selector-option {
  padding: 9px 14px; cursor: pointer; font-size: 13px;
  transition: background 0.1s; border-bottom: 1px solid var(--border);
}
.selector-option:last-child { border-bottom: none; }
.selector-option:hover { background: var(--s2); }
.selected-chip {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: var(--blue-bg); border: 1px solid var(--blue);
  border-radius: 8px; margin-top: 8px; font-size: 13px;
}
.selected-chip .clear { cursor: pointer; color: var(--t3); font-size: 16px; line-height: 1; transition: color 0.15s; }
.selected-chip .clear:hover { color: var(--t1); }

.mat-actions { display: flex; gap: 10px; margin-top: 24px; }
.btn {
  padding: 9px 20px; border: none; border-radius: 8px; font-family: inherit;
  font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.btn-primary { background: var(--blue); color: #fff; }
.btn-primary:hover { background: #2563eb; }
.btn-primary:disabled { background: var(--s3); color: var(--t3); cursor: not-allowed; }
.btn-ghost { background: var(--s1); color: var(--t2); border: 1px solid var(--border2); }
.btn-ghost:hover:not(:disabled) { background: var(--s2); }
.btn-ghost:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── Results ── */
.results-wrap { margin-top: 32px; }

.alt-list { display: flex; flex-direction: column; gap: 10px; }
.alt-card {
  padding: 20px; background: var(--s1); border: 1px solid var(--border);
  border-radius: 10px; transition: border-color 0.15s;
}
.alt-card:hover { border-color: var(--border2); }
.alt-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; }
.alt-name { font-weight: 600; font-size: 14px; }
.alt-supplier { color: var(--t3); font-size: 12px; margin-top: 2px; }
.score-big { text-align: right; }
.score-big .val { font-size: 28px; font-weight: 700; letter-spacing: -1px; }
.score-big .val.strong  { color: var(--green); }
.score-big .val.possible{ color: var(--amber); }
.score-big .val.weak    { color: var(--red);   }
.score-big .lbl { font-size: 11px; color: var(--t3); }

.score-bars { display: flex; flex-direction: column; gap: 8px; }
.score-row { display: grid; grid-template-columns: 90px 1fr 36px; gap: 10px; align-items: center; }
.score-row .name { font-size: 12px; color: var(--t3); }
.bar-track { height: 4px; background: var(--s2); border-radius: 2px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 2px; transition: width 0.7s cubic-bezier(0.16,1,0.3,1); }
.bar-fill.strong  { background: var(--green); }
.bar-fill.possible{ background: var(--amber); }
.bar-fill.weak    { background: var(--red);   }
.score-row .pct { font-size: 12px; color: var(--t2); text-align: right; font-variant-numeric: tabular-nums; }

.score-row.overall .name { font-weight: 600; color: var(--t2); }
.score-row.overall .bar-track { height: 6px; }

.reason-text { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); color: var(--t3); font-size: 12px; line-height: 1.6; }

/* ── No match state ── */
.no-match {
  text-align: center; padding: 56px 32px; background: var(--s1);
  border: 1px solid var(--border); border-radius: 10px;
}
.no-match .icon { font-size: 32px; margin-bottom: 12px; }
.no-match h3 { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.no-match p { color: var(--t3); font-size: 13px; max-width: 360px; margin: 0 auto; }

/* ── Loading / empty ── */
.loader { display: flex; align-items: center; justify-content: center; padding: 60px; }
.spinner { width: 20px; height: 20px; border: 2px solid var(--s3); border-top-color: var(--blue); border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.empty-state { text-align: center; padding: 60px 32px; color: var(--t3); }
.empty-state h3 { font-size: 15px; font-weight: 600; color: var(--t2); margin-bottom: 6px; }

/* ── Organic badge ── */
.organic-badge { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 4px; }
.organic-badge.yes { background: var(--green-bg); color: var(--green); }
.organic-badge.no  { background: var(--s2); color: var(--t3); }

/* ── Comparison view ── */
.compare-card {
  background: var(--s1); border: 1px solid var(--border2);
  border-radius: 12px; overflow: hidden;
}
.compare-header {
  display: grid; grid-template-columns: 1fr auto 1fr;
  padding: 24px; border-bottom: 1px solid var(--border); align-items: center; gap: 16px;
}
.compare-product .name { font-size: 15px; font-weight: 600; }
.compare-product .supplier { color: var(--t3); font-size: 12px; margin-top: 2px; }
.compare-vs { text-align: center; }
.compare-vs .vs-text { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--t3); }
.compare-scores { padding: 24px; display: flex; flex-direction: column; gap: 12px; }
.compare-overall {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 24px; background: var(--s2);
}
.compare-overall .label { font-size: 13px; font-weight: 600; }
.compare-overall-score { font-size: 32px; font-weight: 700; letter-spacing: -1px; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--s3); border-radius: 3px; }
</style>
</head>
<body>
<div class="app">

<header>
  <div class="logo">YumYum <span>Camer</span></div>
  <nav>
    <button class="active" onclick="switchTab('companies', this)">Companies</button>
    <button onclick="switchTab('materials', this)">Materials</button>
  </nav>
</header>

<div class="main">

  <!-- ── COMPANIES TAB ── -->
  <div id="tab-companies" class="tab-pane active">

    <!-- Search state -->
    <div id="co-search-view">
      <div class="page-header">
        <h2>Companies</h2>
        <p>Select a company to analyse its raw material portfolio and find consolidation opportunities.</p>
      </div>
      <div class="search-wrap">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <input class="search-input" id="co-search" placeholder="Search companies…" oninput="filterCompanies(this.value)" autocomplete="off">
      </div>
      <div class="company-grid" id="co-grid"></div>
    </div>

    <!-- Detail state -->
    <div id="co-detail-view" style="display:none">
      <button class="back-btn" onclick="showCompanySearch()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 18-6-6 6-6"/></svg>
        All Companies
      </button>
      <div id="co-detail-content">
        <div class="loader"><div class="spinner"></div></div>
      </div>
    </div>

  </div>

  <!-- ── MATERIALS TAB ── -->
  <div id="tab-materials" class="tab-pane">
    <div class="page-header">
      <h2>Materials</h2>
      <p>Find alternatives for a single material, or compare two materials head-to-head.</p>
    </div>

    <div class="selectors-grid">
      <!-- Material 1 -->
      <div>
        <div class="selector-label">Material</div>
        <div class="selector-wrap" id="sel1-wrap">
          <div class="search-wrap">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            <input class="search-input" id="mat1-input" placeholder="Search materials…" oninput="filterMat(1, this.value)" onfocus="openDrop(1)" autocomplete="off">
          </div>
          <div class="selector-dropdown" id="mat1-drop"></div>
        </div>
        <div id="mat1-chip" style="display:none"></div>
      </div>

      <!-- Material 2 -->
      <div>
        <div class="selector-label">Compare with <span style="color:var(--t3);font-weight:400">(optional)</span></div>
        <div class="selector-wrap" id="sel2-wrap">
          <div class="search-wrap">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            <input class="search-input" id="mat2-input" placeholder="Search materials…" oninput="filterMat(2, this.value)" onfocus="openDrop(2)" autocomplete="off">
          </div>
          <div class="selector-dropdown" id="mat2-drop"></div>
        </div>
        <div id="mat2-chip" style="display:none"></div>
      </div>
    </div>

    <div class="mat-actions">
      <button class="btn btn-primary" id="btn-alternatives" disabled onclick="runAlternatives()">Find Alternatives</button>
      <button class="btn btn-ghost"   id="btn-compare"      disabled onclick="runCompare()">Compare Products</button>
    </div>

    <div id="mat-results" class="results-wrap"></div>
  </div>

</div><!-- /main -->
</div><!-- /app -->

<script>
const COMPANIES = {{ companies_json|safe }};
const PRODUCTS  = {{ products_json|safe }};

// ── Tab switching ──────────────────────────────────────
function switchTab(name, btn) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
}

// ── Companies ──────────────────────────────────────────
renderCompanyGrid(COMPANIES);

function renderCompanyGrid(list) {
  const grid = document.getElementById('co-grid');
  if (!list.length) {
    grid.innerHTML = '<div class="company-empty">No companies found.</div>';
    return;
  }
  grid.innerHTML = list.map(c => `
    <div class="company-item" onclick="loadCompany(${c.id}, '${escHtml(c.name)}')">
      <span class="cname">${escHtml(c.name)}</span>
      <span class="arrow">›</span>
    </div>`).join('');
}

function filterCompanies(q) {
  const filtered = q.trim()
    ? COMPANIES.filter(c => c.name.toLowerCase().includes(q.toLowerCase()))
    : COMPANIES;
  renderCompanyGrid(filtered);
}

function showCompanySearch() {
  document.getElementById('co-search-view').style.display = '';
  document.getElementById('co-detail-view').style.display = 'none';
}

function loadCompany(id, name) {
  document.getElementById('co-search-view').style.display = 'none';
  document.getElementById('co-detail-view').style.display = '';
  document.getElementById('co-detail-content').innerHTML = '<div class="loader"><div class="spinner"></div></div>';

  fetch('/api/company/' + id)
    .then(r => r.json())
    .then(data => renderCompanyDetail(data))
    .catch(e => {
      document.getElementById('co-detail-content').innerHTML =
        `<div class="no-match"><div class="icon">⚠</div><h3>Failed to load</h3><p>${escHtml(String(e))}</p></div>`;
    });
}

function renderCompanyDetail(d) {
  if (d.error) {
    document.getElementById('co-detail-content').innerHTML =
      `<div class="no-match"><div class="icon">⚠</div><h3>Error</h3><p>${escHtml(d.error)}</p></div>`;
    return;
  }

  const ops = d.consolidation_opportunities || [];
  const mats = d.materials || [];
  const supplierSet = new Set();
  mats.forEach(m => m.suppliers.forEach(s => supplierSet.add(s.name)));

  let html = `
    <div class="page-header">
      <h2>${escHtml(d.company_name)}</h2>
    </div>
    <div class="stats-row">
      <div class="stat-card"><div class="val">${mats.length}</div><div class="lbl">Raw Materials</div></div>
      <div class="stat-card"><div class="val">${supplierSet.size}</div><div class="lbl">Unique Suppliers</div></div>
      <div class="stat-card highlight"><div class="val">${ops.length}</div><div class="lbl">Consolidation Opportunities</div></div>
    </div>`;

  if (ops.length) {
    html += `<div class="section-title">Consolidation Opportunities</div>
    <div class="consolidation-list">`;
    ops.forEach(op => {
      const cls = scoreClass(op.score);
      html += `
      <div class="consolidation-card">
        <div class="consolidation-header">
          <span class="consolidation-title">Supplier Consolidation</span>
          <span class="tag ${cls}">${Math.round(op.score*100)}% — ${capFirst(op.label)}</span>
        </div>
        <div class="consolidation-body">
          <div class="c-material">
            <div class="mat-name">${escHtml(op.material_a.product_name)}</div>
            <div class="mat-supplier">${escHtml(op.material_a.supplier_name)}</div>
            <div class="mat-fgs">${(op.finished_goods_a||[]).slice(0,3).map(g=>`<span class="tag">${escHtml(g)}</span>`).join('')}</div>
          </div>
          <div class="c-arrow">⇌</div>
          <div class="c-material">
            <div class="mat-name">${escHtml(op.material_b.product_name)}</div>
            <div class="mat-supplier">${escHtml(op.material_b.supplier_name)}</div>
            <div class="mat-fgs">${(op.finished_goods_b||[]).slice(0,3).map(g=>`<span class="tag">${escHtml(g)}</span>`).join('')}</div>
          </div>
        </div>
        <div class="consolidation-footer">These materials could be sourced from a single supplier — reducing procurement complexity and potentially negotiating better volume pricing.</div>
      </div>`;
    });
    html += `</div>`;
  }

  if (mats.length) {
    html += `<div class="section-title" style="margin-top:${ops.length?'0':'0'}">All Materials</div>
    <div class="material-list">`;
    mats.forEach(m => {
      html += `
      <div class="material-card">
        <div>
          <div class="col-label">Material</div>
          <div class="mat-name">${escHtml(m.product_name)}</div>
          ${m.product_class ? `<div style="margin-top:6px"><span class="tag class">${escHtml(m.product_class)}</span></div>` : ''}
        </div>
        <div>
          <div class="col-label">Used in</div>
          <div style="display:flex;flex-wrap:wrap;gap:4px">
            ${m.finished_goods.length
              ? m.finished_goods.slice(0,4).map(g=>`<span class="tag">${escHtml(g)}</span>`).join('') + (m.finished_goods.length>4?`<span class="tag">+${m.finished_goods.length-4}</span>`:'')
              : '<span style="color:var(--t3);font-size:12px">—</span>'}
          </div>
        </div>
        <div>
          <div class="col-label">Suppliers</div>
          <div style="display:flex;flex-direction:column;gap:4px">
            ${m.suppliers.slice(0,3).map(s=>`<span style="font-size:12px;color:var(--t2)">${escHtml(s.name)}</span>`).join('')}
          </div>
        </div>
      </div>`;
    });
    html += `</div>`;
  } else {
    html += `<div class="empty-state"><h3>No enriched materials found</h3><p style="color:var(--t3);font-size:13px;margin-top:4px">Run the enrichment pipeline to populate data for this company.</p></div>`;
  }

  document.getElementById('co-detail-content').innerHTML = html;
}

// ── Materials tab ──────────────────────────────────────
let sel = { 1: null, 2: null };

function filterMat(n, q) {
  const drop = document.getElementById('mat'+n+'-drop');
  const list = q.trim()
    ? PRODUCTS.filter(p => p.name.toLowerCase().includes(q.toLowerCase())).slice(0,40)
    : PRODUCTS.slice(0,40);
  drop.innerHTML = list.map(p =>
    `<div class="selector-option" onclick="selectMat(${n}, ${p.id}, '${escHtml(p.name)}')">${escHtml(p.name)}</div>`
  ).join('') || '<div class="selector-option" style="color:var(--t3)">No results</div>';
  drop.classList.add('open');
}

function openDrop(n) {
  filterMat(n, document.getElementById('mat'+n+'-input').value);
}

function selectMat(n, id, name) {
  sel[n] = { id, name };
  document.getElementById('mat'+n+'-drop').classList.remove('open');
  document.getElementById('mat'+n+'-input').value = '';
  document.getElementById('mat'+n+'-input').placeholder = 'Search materials…';

  const chip = document.getElementById('mat'+n+'-chip');
  chip.style.display = '';
  chip.innerHTML = `<div class="selected-chip"><span>${escHtml(name)}</span><span class="clear" onclick="clearMat(${n})">×</span></div>`;

  updateMatButtons();
}

function clearMat(n) {
  sel[n] = null;
  document.getElementById('mat'+n+'-chip').style.display = 'none';
  document.getElementById('mat'+n+'-chip').innerHTML = '';
  document.getElementById('mat-results').innerHTML = '';
  updateMatButtons();
}

function updateMatButtons() {
  document.getElementById('btn-alternatives').disabled = !sel[1];
  document.getElementById('btn-compare').disabled = !(sel[1] && sel[2]);
}

// Close dropdowns on outside click
document.addEventListener('click', e => {
  if (!e.target.closest('#sel1-wrap')) document.getElementById('mat1-drop').classList.remove('open');
  if (!e.target.closest('#sel2-wrap')) document.getElementById('mat2-drop').classList.remove('open');
  if (!e.target.closest('#co-search-view')) {}
});

function runAlternatives() {
  const res = document.getElementById('mat-results');
  res.innerHTML = '<div class="loader"><div class="spinner"></div></div>';
  fetch('/api/suggest/' + sel[1].id)
    .then(r => r.json())
    .then(d => renderAlternatives(d))
    .catch(e => res.innerHTML = errHtml(e));
}

function renderAlternatives(d) {
  const res = document.getElementById('mat-results');
  if (d.error) { res.innerHTML = errHtml(d.error); return; }

  const alts = d.alternatives || [];
  const src = d.source_product;

  let html = `<div class="section-title">Alternatives for ${escHtml(src.product_name)}</div>`;

  if (!alts.length) {
    html += `<div class="no-match"><div class="icon">🔍</div><h3>No alternatives found</h3><p>No materials with a similarity score above 60% were found in the same class.</p></div>`;
    res.innerHTML = html; return;
  }

  html += `<div class="alt-list">`;
  alts.forEach(a => {
    const c = a.comparison;
    const cls = scoreClass(c.general_comparison_score);
    html += `
    <div class="alt-card">
      <div class="alt-header">
        <div>
          <div class="alt-name">${escHtml(a.product_name)}</div>
          <div class="alt-supplier" style="margin-top:4px;display:flex;gap:6px;align-items:center">
            Supplier ID ${a.supplier_id}
          </div>
        </div>
        <div class="score-big">
          <div class="val ${cls}">${Math.round(c.general_comparison_score*100)}%</div>
          <div class="lbl">${capFirst(c.comparison_label)}</div>
        </div>
      </div>
      ${scoreBarRows(c)}
      ${c.comparison_reason ? `<div class="reason-text">${escHtml(c.comparison_reason)}</div>` : ''}
    </div>`;
  });
  html += `</div>`;
  res.innerHTML = html;
}

function runCompare() {
  const res = document.getElementById('mat-results');
  res.innerHTML = '<div class="loader"><div class="spinner"></div></div>';
  fetch('/api/compare/' + sel[1].id + '/' + sel[2].id)
    .then(r => r.json())
    .then(d => renderComparison(d, sel[1].name, sel[2].name))
    .catch(e => res.innerHTML = errHtml(e));
}

function renderComparison(d, nameA, nameB) {
  const res = document.getElementById('mat-results');
  if (d.error) { res.innerHTML = errHtml(d.error); return; }

  const score = d.general_comparison_score;
  const cls = scoreClass(score);

  if (score < 0.60) {
    res.innerHTML = `
      <div class="no-match">
        <div class="icon">✗</div>
        <h3>Not Compatible</h3>
        <p><strong>${escHtml(nameA)}</strong> and <strong>${escHtml(nameB)}</strong> have a compatibility score of ${Math.round(score*100)}% — too low to consider as substitutes.</p>
      </div>`;
    return;
  }

  res.innerHTML = `
    <div class="compare-card">
      <div class="compare-header">
        <div class="compare-product">
          <div class="name">${escHtml(nameA)}</div>
          ${d.product_a_organic ? '<span class="organic-badge yes">✓ Organic</span>' : '<span class="organic-badge no">Not Organic</span>'}
        </div>
        <div class="compare-vs"><span class="vs-text">vs</span></div>
        <div class="compare-product" style="text-align:right">
          <div class="name">${escHtml(nameB)}</div>
          ${d.product_b_organic ? '<span class="organic-badge yes">✓ Organic</span>' : '<span class="organic-badge no">Not Organic</span>'}
        </div>
      </div>
      <div class="compare-scores">
        ${scoreBarRows(d)}
        ${d.comparison_reason ? `<div class="reason-text">${escHtml(d.comparison_reason)}</div>` : ''}
      </div>
      <div class="compare-overall">
        <div>
          <div class="label">Overall Compatibility</div>
          <div style="margin-top:4px"><span class="tag ${cls}">${capFirst(d.comparison_label)}</span></div>
        </div>
        <div class="compare-overall-score ${cls}">${Math.round(score*100)}%</div>
      </div>
    </div>`;
}

// ── Helpers ───────────────────────────────────────────
function scoreClass(s) {
  return s >= 0.80 ? 'strong' : s >= 0.60 ? 'possible' : 'weak';
}
function capFirst(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function errHtml(e) {
  return `<div class="no-match"><div class="icon">⚠</div><h3>Something went wrong</h3><p>${escHtml(String(e))}</p></div>`;
}
function scoreBarRows(c) {
  const rows = [
    ['Taste',       c.taste_score],
    ['Usage',       c.usage_score],
    ['Feasibility', c.feasibility_score],
    ['Confidence',  c.confidence_score],
  ];
  const overall = c.general_comparison_score;
  const oc = scoreClass(overall);
  let html = '<div class="score-bars">';
  rows.forEach(([name, val]) => {
    const pct = Math.round(val*100);
    const cls = scoreClass(val);
    html += `<div class="score-row">
      <span class="name">${name}</span>
      <div class="bar-track"><div class="bar-fill ${cls}" style="width:${pct}%"></div></div>
      <span class="pct">${pct}%</span>
    </div>`;
  });
  html += `<div class="score-row overall">
    <span class="name">Overall</span>
    <div class="bar-track"><div class="bar-fill ${oc}" style="width:${Math.round(overall*100)}%"></div></div>
    <span class="pct">${Math.round(overall*100)}%</span>
  </div>`;
  html += '</div>';
  return html;
}
</script>
</body>
</html>"""


@app.route('/')
def index():
    companies_rows = db.execute_query("SELECT Id, Name FROM Company ORDER BY Name")
    products_rows  = db.execute_query(
        "SELECT DISTINCT product_id, product_name FROM raw_material_master ORDER BY product_name"
    )
    return render_template_string(
        HTML_TEMPLATE,
        companies_json=json.dumps([{"id": r[0], "name": r[1]} for r in companies_rows]),
        products_json=json.dumps([{"id": r[0], "name": r[1]} for r in products_rows]),
    )


@app.route('/api/company/<int:company_id>')
def api_company(company_id):
    try:
        company_rows = db.execute_query("SELECT Id, Name FROM Company WHERE Id = ?", (company_id,))
        if not company_rows:
            return jsonify({"error": "Company not found"}), 404
        company_name = company_rows[0][1]

        # Find raw materials used in this company's finished goods via BOM
        try:
            material_rows = db.execute_query("""
                SELECT DISTINCT rm.product_id, rm.product_name,
                                rm.supplier_id, rm.supplier_name, rm.product_class
                FROM raw_material_master rm
                JOIN BOM_Component bc ON rm.product_id = bc.ConsumedProductId
                JOIN BOM b            ON bc.BOMId = b.Id
                JOIN Product fp       ON b.ProducedProductId = fp.Id
                WHERE fp.ManufacturerId = ?
            """, (company_id,))
        except Exception:
            # Fallback: materials where this company is the supplier
            material_rows = db.execute_query("""
                SELECT DISTINCT product_id, product_name, supplier_id, supplier_name, product_class
                FROM raw_material_master WHERE supplier_name = ?
            """, (company_name,))

        # Group by product_id
        mat_map = {}
        for pid, pname, sid, sname, pclass in material_rows:
            if pid not in mat_map:
                mat_map[pid] = {"product_id": pid, "product_name": pname,
                                "product_class": pclass or "", "suppliers": [], "finished_goods": []}
            if not any(s["id"] == sid for s in mat_map[pid]["suppliers"]):
                mat_map[pid]["suppliers"].append({"id": sid, "name": sname})

        # Finished goods for each material
        for pid, mdata in mat_map.items():
            fg_rows = db.execute_query("""
                SELECT DISTINCT p.Name FROM Product p
                JOIN BOM b ON p.Id = b.ProducedProductId
                JOIN BOM_Component bc ON b.Id = bc.BOMId
                WHERE bc.ConsumedProductId = ?
            """, (pid,))
            mdata["finished_goods"] = [r[0] for r in fg_rows if r[0]]

        # Consolidation: compare same-class material pairs with different product_ids
        by_class = defaultdict(list)
        for mdata in mat_map.values():
            by_class[mdata["product_class"]].append(mdata)

        consolidation_ops = []
        for class_mats in by_class.values():
            if len(class_mats) < 2:
                continue
            for mat_a, mat_b in combinations(class_mats, 2):
                sup_a = mat_a["suppliers"][0] if mat_a["suppliers"] else None
                sup_b = mat_b["suppliers"][0] if mat_b["suppliers"] else None
                if not sup_a or not sup_b:
                    continue
                try:
                    comp = compare_products(
                        mat_a["product_id"], sup_a["id"],
                        mat_b["product_id"], sup_b["id"]
                    )
                    if comp["general_comparison_score"] >= 0.65:
                        consolidation_ops.append({
                            "material_a": {
                                "product_id": mat_a["product_id"],
                                "product_name": mat_a["product_name"],
                                "supplier_name": sup_a["name"],
                            },
                            "material_b": {
                                "product_id": mat_b["product_id"],
                                "product_name": mat_b["product_name"],
                                "supplier_name": sup_b["name"],
                            },
                            "score":  comp["general_comparison_score"],
                            "label":  comp["comparison_label"],
                            "reason": comp["comparison_reason"],
                            "finished_goods_a": mat_a["finished_goods"],
                            "finished_goods_b": mat_b["finished_goods"],
                        })
                except Exception:
                    pass

        consolidation_ops.sort(key=lambda x: x["score"], reverse=True)

        return jsonify({
            "company_name": company_name,
            "materials": list(mat_map.values()),
            "consolidation_opportunities": consolidation_ops,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/suggest/<int:product_id>')
def api_suggest(product_id):
    try:
        return jsonify(suggest_alternatives(product_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/compare/<int:product_id_a>/<int:product_id_b>')
def api_compare(product_id_a, product_id_b):
    try:
        rows_a = db.execute_query(
            "SELECT supplier_id FROM raw_material_master WHERE product_id = ? LIMIT 1", (product_id_a,))
        rows_b = db.execute_query(
            "SELECT supplier_id FROM raw_material_master WHERE product_id = ? LIMIT 1", (product_id_b,))
        if not rows_a:
            return jsonify({"error": f"Product {product_id_a} not found"}), 404
        if not rows_b:
            return jsonify({"error": f"Product {product_id_b} not found"}), 404
        return jsonify(compare_products(product_id_a, rows_a[0][0], product_id_b, rows_b[0][0]))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
