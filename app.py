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


def compute_supplier_portfolio(mat_map: dict) -> dict:
    """
    Greedy set-cover: find the fewest suppliers that can cover all company materials,
    using same-product multi-supplier options and >=95% compatible substitutes.
    """
    pid_list = list(mat_map.keys())
    if not pid_list:
        return None

    ph = ",".join("?" * len(pid_list))

    # All (product_id, supplier_id, supplier_name) rows for these materials
    direct_rows = db.execute_query(
        f"SELECT product_id, supplier_id, supplier_name FROM raw_material_master WHERE product_id IN ({ph})",
        tuple(pid_list)
    )
    # Name lookup for any product we'll encounter as a substitute
    all_product_names = {r[0]: mat_map[r[0]]["product_name"] for r in direct_rows if r[0] in mat_map}

    # All cached comparisons involving these materials — collect for diagnostics, filter >=0.95 for substitutes
    all_comp_rows = db.execute_query(
        f"""SELECT product_id_a, supplier_id_a, product_id_b, supplier_id_b, general_comparison_score
            FROM raw_material_comparisons
            WHERE product_id_a IN ({ph}) OR product_id_b IN ({ph})""",
        tuple(pid_list) * 2
    )
    comp_rows = [r for r in all_comp_rows if r[4] >= 0.95]
    max_score = max((r[4] for r in all_comp_rows), default=0.0)
    total_comps = len(all_comp_rows)

    # Collect substitute product ids we need names for
    sub_pids = set()
    for pid_a, sid_a, pid_b, sid_b, _ in comp_rows:
        if pid_a in mat_map and pid_b not in mat_map:
            sub_pids.add((pid_b, sid_b))
        if pid_b in mat_map and pid_a not in mat_map:
            sub_pids.add((pid_a, sid_a))

    # Bulk fetch substitute names + supplier names
    sub_lookup = {}  # (pid, sid) -> (product_name, supplier_name)
    if sub_pids:
        for pid, sid in sub_pids:
            rows = db.execute_query(
                "SELECT product_name, supplier_name FROM raw_material_master WHERE product_id=? AND supplier_id=? LIMIT 1",
                (pid, sid)
            )
            if rows:
                sub_lookup[(pid, sid)] = (rows[0][0], rows[0][1])

    # Build material_options: pid -> list of option dicts
    material_options = {pid: [] for pid in pid_list}

    # Direct (same product, any supplier)
    for pid, sid, sname in direct_rows:
        if pid in material_options:
            material_options[pid].append({
                "covering_pid": pid,
                "covering_pname": mat_map[pid]["product_name"],
                "supplier_id": sid,
                "supplier_name": sname,
                "is_substitute": False,
                "score": 1.0
            })

    # Substitutes from cached comparisons
    for pid_a, sid_a, pid_b, sid_b, score in comp_rows:
        # pid_a is a company material -> pid_b is a substitute option
        if pid_a in material_options and pid_b != pid_a:
            if (pid_b, sid_b) in sub_lookup:
                pname_b, sname_b = sub_lookup[(pid_b, sid_b)]
            elif (pid_b, sid_b) in [(r[0], r[1]) for r in direct_rows]:
                pname_b = mat_map.get(pid_b, {}).get("product_name", "")
                sname_b = next((r[2] for r in direct_rows if r[0] == pid_b and r[1] == sid_b), "")
            else:
                continue
            material_options[pid_a].append({
                "covering_pid": pid_b,
                "covering_pname": pname_b,
                "supplier_id": sid_b,
                "supplier_name": sname_b,
                "is_substitute": True,
                "score": score
            })
        # pid_b is a company material -> pid_a is a substitute option
        if pid_b in material_options and pid_a != pid_b:
            if (pid_a, sid_a) in sub_lookup:
                pname_a, sname_a = sub_lookup[(pid_a, sid_a)]
            elif pid_a in mat_map:
                pname_a = mat_map[pid_a]["product_name"]
                sname_a = next((r[2] for r in direct_rows if r[0] == pid_a and r[1] == sid_a), "")
            else:
                continue
            material_options[pid_b].append({
                "covering_pid": pid_a,
                "covering_pname": pname_a,
                "supplier_id": sid_a,
                "supplier_name": sname_a,
                "is_substitute": True,
                "score": score
            })

    # Build supplier coverage map
    supplier_coverage = defaultdict(list)
    supplier_names = {}
    for material_pid, options in material_options.items():
        for opt in options:
            sid = opt["supplier_id"]
            supplier_names[sid] = opt["supplier_name"]
            supplier_coverage[sid].append((material_pid, opt))

    # Greedy set cover
    uncovered = set(pid_list)
    chosen = []
    while uncovered:
        best_sid, best_covers = None, []
        for sid, covers in supplier_coverage.items():
            unc = [(mpid, opt) for mpid, opt in covers if mpid in uncovered]
            if len(unc) > len(best_covers):
                best_covers, best_sid = unc, sid
        if not best_sid:
            break
        # One option per material: prefer direct (not substitute), then highest score
        seen, deduped = set(), []
        for mpid, opt in sorted(best_covers, key=lambda x: (x[1]["is_substitute"], -x[1]["score"])):
            if mpid not in seen:
                seen.add(mpid)
                deduped.append((mpid, opt))
        covers_out = []
        for mpid, opt in deduped:
            current_sup_ids = {s["id"] for s in mat_map[mpid]["suppliers"]}
            current_sup_names = [s["name"] for s in mat_map[mpid]["suppliers"]]
            if opt["is_substitute"]:
                action = "substitute"
            elif best_sid in current_sup_ids:
                action = "keep"
            else:
                action = "switch_supplier"
            covers_out.append({
                "material_product_id": mpid,
                "material_product_name": mat_map[mpid]["product_name"],
                "via_product_name": opt["covering_pname"],
                "is_substitute": opt["is_substitute"],
                "score": round(opt["score"], 3),
                "current_suppliers": current_sup_names,
                "action": action
            })
        chosen.append({
            "supplier_id": best_sid,
            "supplier_name": supplier_names[best_sid],
            "covers": covers_out
        })
        for mpid, _ in best_covers:
            uncovered.discard(mpid)

    current_suppliers = set()
    for mdata in mat_map.values():
        for s in mdata["suppliers"]:
            current_suppliers.add(s["id"])

    return {
        "current_supplier_count": len(current_suppliers),
        "optimal_supplier_count": len(chosen),
        "reduction": len(current_suppliers) - len(chosen),
        "chosen_suppliers": chosen,
        "uncovered_count": len(uncovered),
        "uncovered_materials": [mat_map[pid]["product_name"] for pid in uncovered if pid in mat_map],
        "diagnostics": {
            "total_comparisons_cached": total_comps,
            "substitutes_found": len(comp_rows),
            "max_similarity_score": round(max_score, 3),
        }
    }

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

/* ── Portfolio optimization ── */
.portfolio-card {
  background: var(--s1); border: 1px solid var(--border2);
  border-left: 3px solid var(--green); border-radius: 10px;
  margin-bottom: 10px; overflow: hidden;
}
.portfolio-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid var(--border);
}
.portfolio-title { font-size: 13px; font-weight: 600; color: var(--t1); }
.portfolio-subtitle { font-size: 12px; color: var(--t3); margin-top: 2px; }
.portfolio-savings { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; }
.portfolio-savings .from { color: var(--red); text-decoration: line-through; opacity: 0.8; }
.portfolio-savings .arr { color: var(--t3); font-weight: 400; }
.portfolio-savings .to { color: var(--green); }
.portfolio-suppliers { padding: 12px 20px; display: flex; flex-direction: column; gap: 10px; }
.pf-supplier-block {
  background: var(--s2); border: 1px solid var(--border); border-radius: 8px; overflow: hidden;
}
.pf-supplier-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; border-bottom: 1px solid var(--border);
}
.pf-supplier-name { font-weight: 600; font-size: 13px; color: var(--t1); }
.pf-supplier-count { font-size: 11px; color: var(--t3); }
.pf-mat-table { width: 100%; border-collapse: collapse; }
.pf-mat-table td { padding: 9px 14px; border-bottom: 1px solid var(--border); font-size: 12px; vertical-align: middle; }
.pf-mat-table tr:last-child td { border-bottom: none; }
.pf-mat-table .col-mat { width: 35%; }
.pf-mat-table .col-cur { width: 35%; color: var(--t3); }
.pf-mat-table .col-action { width: 30%; text-align: right; }
.pf-mat-name { font-weight: 500; color: var(--t1); }
.pf-replaces { font-size: 11px; color: var(--t3); margin-top: 2px; }
.pf-score { font-size: 10px; color: var(--amber); margin-left: 4px; }
.pf-cur-label { font-size: 10px; color: var(--t3); margin-bottom: 2px; text-transform: uppercase; letter-spacing: 0.04em; }
.pf-cur-names { color: var(--t2); }
.action-pill {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 600;
}
.action-pill.keep    { background: var(--green-bg); color: var(--green); }
.action-pill.switch  { background: var(--amber-bg); color: var(--amber); }
.action-pill.subst   { background: var(--blue-bg);  color: var(--blue);  }
.portfolio-uncovered { padding: 0 20px 14px; color: var(--red); font-size: 12px; }

/* ── Detail panel ── */
.detail-btn {
  display: inline-flex; align-items: center; gap: 5px;
  margin-top: 14px; padding: 6px 14px; background: var(--s2);
  border: 1px solid var(--border2); border-radius: 6px;
  font-family: inherit; font-size: 12px; font-weight: 500;
  color: var(--t2); cursor: pointer; transition: all 0.15s;
}
.detail-btn:hover { background: var(--s3); color: var(--t1); }
.detail-panel { margin-top: 14px; border-top: 1px solid var(--border); padding-top: 14px; display: none; }
.detail-panel.open { display: block; }
.detail-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.detail-table th {
  text-align: left; padding: 7px 10px;
  background: var(--s2); color: var(--t3);
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
}
.detail-table th:last-child { width: 56px; text-align: center; }
.detail-table td { padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.detail-table tr:last-child td { border-bottom: none; }
.detail-table .attr-col { color: var(--t3); font-weight: 500; width: 130px; white-space: nowrap; }
.detail-table .match-col { text-align: center; }
.detail-table .match { color: var(--green); }
.detail-table .mismatch { color: var(--amber); }
.detail-loading { color: var(--t3); font-size: 12px; padding: 6px 0; }
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
      <div class="stat-card"><div class="val">${supplierSet.size}</div><div class="lbl">Current Suppliers</div></div>
      ${d.supplier_portfolio && d.supplier_portfolio.reduction > 0
        ? `<div class="stat-card highlight"><div class="val" style="color:var(--green)">${d.supplier_portfolio.optimal_supplier_count}</div><div class="lbl">Optimal Suppliers (save ${d.supplier_portfolio.reduction})</div></div>`
        : `<div class="stat-card highlight"><div class="val">${ops.length}</div><div class="lbl">Consolidation Opportunities</div></div>`
      }
    </div>`;

  const pf = d.supplier_portfolio;
  const pfHasActions = pf && pf.chosen_suppliers.some(s => s.covers.some(c => c.action !== 'keep'));
  if (pf && pf.optimal_supplier_count > 0 && (pf.reduction > 0 || pfHasActions)) {
    const savedStr = pf.reduction > 0
      ? `<span class="from">${pf.current_supplier_count}</span><span class="arr">→</span><span class="to">${pf.optimal_supplier_count} suppliers</span>`
      : `<span class="to">${pf.optimal_supplier_count} suppliers</span>`;
    html += `<div class="section-title">Supplier Portfolio Optimization</div>
    <div class="portfolio-card">
      <div class="portfolio-header">
        <div>
          <div class="portfolio-title">Minimum Supplier Set</div>
          <div class="portfolio-subtitle">Covers all materials using direct sourcing or ≥95% compatible substitutes only</div>
        </div>
        <div class="portfolio-savings">${savedStr}</div>
      </div>
      <div style="padding:8px 20px;border-bottom:1px solid var(--border);display:flex;gap:20px;font-size:11px;color:var(--t3);">
        <span>Comparisons cached: <strong style="color:var(--t2)">${pf.diagnostics.total_comparisons_cached}</strong></span>
        <span>≥95% substitutes found: <strong style="color:var(--t2)">${pf.diagnostics.substitutes_found}</strong></span>
        <span>Highest similarity: <strong style="color:var(--t2)">${Math.round(pf.diagnostics.max_similarity_score * 100)}%</strong></span>
      </div>
      <div class="portfolio-suppliers">`;
    pf.chosen_suppliers.forEach((sup, i) => {
      html += `<div class="pf-supplier-block">
        <div class="pf-supplier-header">
          <div class="pf-supplier-name">${i + 1}. ${escHtml(sup.supplier_name)}</div>
          <div class="pf-supplier-count">${sup.covers.length} material${sup.covers.length !== 1 ? 's' : ''}</div>
        </div>
        <table class="pf-mat-table"><tbody>`;
      sup.covers.forEach(c => {
        const curNames = c.current_suppliers.length ? c.current_suppliers.map(s => escHtml(s)).join(', ') : '—';
        let actionPill, matCell;
        if (c.action === 'keep') {
          actionPill = '<span class="action-pill keep">No change</span>';
        } else if (c.action === 'switch_supplier') {
          actionPill = '<span class="action-pill switch">Switch supplier</span>';
        } else {
          actionPill = `<span class="action-pill subst">New product ≈${Math.round(c.score*100)}%</span>`;
        }
        if (c.is_substitute) {
          matCell = `<div class="pf-mat-name">${escHtml(c.via_product_name)}<span class="pf-score">≈${Math.round(c.score*100)}%</span></div>
            <div class="pf-replaces">replaces: ${escHtml(c.material_product_name)}</div>`;
        } else {
          matCell = `<div class="pf-mat-name">${escHtml(c.material_product_name)}</div>`;
        }
        html += `<tr>
          <td class="col-mat">${matCell}</td>
          <td class="col-cur">
            <div class="pf-cur-label">Current supplier${c.current_suppliers.length !== 1 ? 's' : ''}</div>
            <div class="pf-cur-names">${curNames}</div>
          </td>
          <td class="col-action">${actionPill}</td>
        </tr>`;
      });
      html += `</tbody></table></div>`;
    });
    html += `</div>`;
    if (pf.uncovered_count > 0) {
      html += `<div class="portfolio-uncovered">⚠ ${pf.uncovered_count} material${pf.uncovered_count !== 1 ? 's' : ''} could not be covered: ${pf.uncovered_materials.map(m => escHtml(m)).join(', ')}</div>`;
    }
    html += `</div>`;
  }

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
        <button class="detail-btn" onclick="toggleDetail(this, ${op.material_a.product_id}, ${op.material_b.product_id})">+ View Details</button>
        <div class="detail-panel"></div>
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
            ${escHtml(a.supplier_name || 'Supplier ID ' + a.supplier_id)}
          </div>
        </div>
        <div class="score-big">
          <div class="val ${cls}">${Math.round(c.general_comparison_score*100)}%</div>
          <div class="lbl">${capFirst(c.comparison_label)}</div>
        </div>
      </div>
      ${scoreBarRows(c)}
      ${c.comparison_reason ? `<div class="reason-text">${escHtml(c.comparison_reason)}</div>` : ''}
      <button class="detail-btn" onclick="toggleDetail(this, ${src.product_id}, ${a.product_id})">+ View Details</button>
      <div class="detail-panel"></div>
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
        <button class="detail-btn" onclick="toggleDetail(this, ${sel[1].id}, ${sel[2].id})">+ View Details</button>
        <div class="detail-panel"></div>
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
// ── Detail panel toggle ───────────────────────────────
function toggleDetail(btn, idA, idB) {
  const panel = btn.nextElementSibling;
  if (panel.classList.contains('open')) {
    panel.classList.remove('open');
    btn.innerHTML = '&#43; View Details';
    return;
  }
  panel.classList.add('open');
  btn.innerHTML = '&#8722; Hide Details';
  if (panel.dataset.loaded) return;
  panel.dataset.loaded = '1';
  panel.innerHTML = '<div class="detail-loading">Loading attribute breakdown…</div>';
  fetch('/api/detail/' + idA + '/' + idB)
    .then(r => r.json())
    .then(d => {
      if (d.error) {
        panel.innerHTML = '<div class="detail-loading" style="color:var(--red)">' + escHtml(d.error) + '</div>';
        return;
      }
      let html = '<table class="detail-table"><thead><tr>'
        + '<th class="attr-col">Attribute</th>'
        + '<th>' + escHtml(d.product_a.name) + '</th>'
        + '<th>' + escHtml(d.product_b.name) + '</th>'
        + '<th>Match</th>'
        + '</tr></thead><tbody>';
      d.differences.forEach(row => {
        const cls = row.match ? 'match' : 'mismatch';
        const icon = row.match ? '✓' : '≠';
        html += '<tr>'
          + '<td class="attr-col">' + escHtml(row.attribute) + '</td>'
          + '<td>' + escHtml(row.value_a) + '</td>'
          + '<td>' + escHtml(row.value_b) + '</td>'
          + '<td class="match-col ' + cls + '">' + icon + '</td>'
          + '</tr>';
      });
      html += '</tbody></table>';
      panel.innerHTML = html;
    })
    .catch(e => {
      panel.innerHTML = '<div class="detail-loading" style="color:var(--red)">' + escHtml(String(e)) + '</div>';
    });
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
        "SELECT MIN(product_id), product_name FROM raw_material_master GROUP BY product_name ORDER BY product_name"
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
        material_rows = []
        try:
            material_rows = db.execute_query("""
                SELECT DISTINCT rm.product_id, rm.product_name,
                                rm.supplier_id, rm.supplier_name, rm.product_class
                FROM raw_material_master rm
                JOIN BOM_Component bc ON rm.product_id = bc.ConsumedProductId
                JOIN BOM b            ON bc.BOMId = b.Id
                JOIN Product fp       ON b.ProducedProductId = fp.Id
                WHERE fp.CompanyId = ?
            """, (company_id,))
        except Exception:
            pass

        # Fallback: materials where this company is listed as supplier
        if not material_rows:
            try:
                material_rows = db.execute_query("""
                    SELECT DISTINCT product_id, product_name, supplier_id, supplier_name, product_class
                    FROM raw_material_master WHERE supplier_name = ?
                """, (company_name,))
            except Exception:
                pass

        # Second fallback: find via Supplier table by name match
        if not material_rows:
            try:
                material_rows = db.execute_query("""
                    SELECT DISTINCT rm.product_id, rm.product_name,
                                    rm.supplier_id, rm.supplier_name, rm.product_class
                    FROM raw_material_master rm
                    JOIN Supplier s ON rm.supplier_id = s.Id
                    WHERE s.Name = ?
                """, (company_name,))
            except Exception:
                pass

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
                SELECT DISTINCT p.SKU FROM Product p
                JOIN BOM b ON p.Id = b.ProducedProductId
                JOIN BOM_Component bc ON b.Id = bc.BOMId
                WHERE bc.ConsumedProductId = ?
            """, (pid,))
            mdata["finished_goods"] = [r[0] for r in fg_rows if r[0]]

        # Consolidation: compare all material pairs regardless of class
        consolidation_ops = []
        all_mats = list(mat_map.values())
        for mat_a, mat_b in combinations(all_mats, 2):
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

        portfolio = None
        try:
            portfolio = compute_supplier_portfolio(mat_map)
        except Exception as e:
            app.logger.error(f"Portfolio computation failed: {e}")

        return jsonify({
            "company_name": company_name,
            "materials": list(mat_map.values()),
            "consolidation_opportunities": consolidation_ops,
            "supplier_portfolio": portfolio,
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


@app.route('/api/debug/scores')
def api_debug_scores():
    """Return score distribution and top pairs across all cached comparisons."""
    try:
        rows = db.execute_query(
            """SELECT rmc.product_id_a, rmc.product_id_b,
                      rmc.general_comparison_score, rmc.comparison_label,
                      ma.product_name, mb.product_name,
                      ma.supplier_name, mb.supplier_name
               FROM raw_material_comparisons rmc
               LEFT JOIN raw_material_master ma
                 ON rmc.product_id_a = ma.product_id AND rmc.supplier_id_a = ma.supplier_id
               LEFT JOIN raw_material_master mb
                 ON rmc.product_id_b = mb.product_id AND rmc.supplier_id_b = mb.supplier_id
               ORDER BY rmc.general_comparison_score DESC"""
        )
        total = len(rows)
        above_95 = sum(1 for r in rows if r[2] >= 0.95)
        above_80 = sum(1 for r in rows if r[2] >= 0.80)
        above_60 = sum(1 for r in rows if r[2] >= 0.60)
        top20 = [
            {
                "score": round(r[2], 3),
                "label": r[3],
                "product_a": r[4] or f"id={r[0]}",
                "supplier_a": r[6] or "?",
                "product_b": r[5] or f"id={r[1]}",
                "supplier_b": r[7] or "?",
            }
            for r in rows[:20]
        ]
        return jsonify({
            "total_comparisons": total,
            "above_95_pct": above_95,
            "above_80_pct": above_80,
            "above_60_pct": above_60,
            "top_20_pairs": top20,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/detail/<int:product_id_a>/<int:product_id_b>')
def api_detail(product_id_a, product_id_b):
    try:
        rows_a = db.execute_query(
            "SELECT supplier_id FROM raw_material_master WHERE product_id = ? LIMIT 1", (product_id_a,))
        rows_b = db.execute_query(
            "SELECT supplier_id FROM raw_material_master WHERE product_id = ? LIMIT 1", (product_id_b,))
        if not rows_a or not rows_b:
            return jsonify({"error": "One or both products not found"}), 404

        mat_a = db.get_raw_material_master(product_id_a, rows_a[0][0])
        mat_b = db.get_raw_material_master(product_id_b, rows_b[0][0])
        if not mat_a or not mat_b:
            return jsonify({"error": "Product data not found"}), 404

        pj_a = mat_a["product_json"]
        pj_b = mat_b["product_json"]

        ATTRIBUTES = [
            ("general_class",          "Category"),
            ("taste",                  "Taste"),
            ("physical_form",          "Physical Form"),
            ("functional_role",        "Functional Role"),
            ("application_domain",     "Application Domain"),
            ("ingredient_type",        "Ingredient Type"),
            ("cleaned_canonical_name", "Canonical Name"),
            ("confidence",             "AI Confidence"),
        ]

        differences = []
        for key, label in ATTRIBUTES:
            raw_a = pj_a.get(key, None)
            raw_b = pj_b.get(key, None)
            if isinstance(raw_a, float):
                val_a = f"{raw_a:.2f}"
            else:
                val_a = str(raw_a) if raw_a is not None else "—"
            if isinstance(raw_b, float):
                val_b = f"{raw_b:.2f}"
            else:
                val_b = str(raw_b) if raw_b is not None else "—"
            differences.append({
                "attribute": label,
                "value_a": val_a,
                "value_b": val_b,
                "match": val_a.lower() == val_b.lower() and val_a != "—"
            })

        return jsonify({
            "product_a": {"name": mat_a["product_name"], "supplier": mat_a["supplier_name"]},
            "product_b": {"name": mat_b["product_name"], "supplier": mat_b["supplier_name"]},
            "differences": differences,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
