import sqlite3
import json
import os
import argparse
import math
import re
from itertools import combinations
from typing import Dict, List, Set, Tuple, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "db.sqlite")

# -----------------------------
# Text normalization utilities
# -----------------------------

STOPWORDS = {
    "and", "or", "with", "for", "the", "a", "an",
    "powder", "extract", "oil", "natural", "organic"
}

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"[\-_]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize_material_name(name: str) -> List[str]:
    normalized = normalize_text(name)
    # Split between letters and numbers to catch things like 'coq10' -> 'coq', '10'
    text = re.sub(r"([a-z])([0-9])", r"\1 \2", normalized)
    text = re.sub(r"([0-9])([a-z])", r"\1 \2", text)
    tokens = [t for t in text.split() if t and t not in STOPWORDS]
    return tokens

def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    if not set_a and not set_b:
        return 0.0
    inter_len = len(set_a.intersection(set_b))
    if inter_len == 0:
        return 0.0
    union_len = len(set_a) + len(set_b) - inter_len
    return inter_len / union_len

def overlap_coefficient(set_a: Set[str], set_b: Set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    inter_len = len(set_a.intersection(set_b))
    return inter_len / min(len(set_a), len(set_b))

def normalized_edit_similarity(a: str, b: str, limit: float = 0.0) -> float:
    """
    Optimized Levenshtein similarity with 2-row DP and length-based early exit.
    """
    a = normalize_text(a)
    b = normalize_text(b)
    if a == b: return 1.0
    if not a or not b: return 0.0
    len_a, len_b = len(a), len(b)
    if limit > 0:
        max_possible = 1.0 - (abs(len_a - len_b) / max(len_a, len_b))
        if max_possible < limit:
            return 0.0
    if len_a < len_b:
        a, b = b, a
        len_a, len_b = len_b, len_a
    prev_row = list(range(len_b + 1))
    curr_row = [0] * (len_b + 1)
    for i in range(1, len_a + 1):
        curr_row[0] = i
        for j in range(1, len_b + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr_row[j] = min(curr_row[j - 1] + 1, prev_row[j] + 1, prev_row[j - 1] + cost)
        prev_row[:] = curr_row
    dist = prev_row[len_b]
    return 1.0 - (dist / len_a)

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

# -----------------------------
# Database fetch
# -----------------------------

def fetch_materials() -> List[Dict[str, Any]]:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.Id AS product_id, p.SKU AS sku, p.CompanyId AS company_id,
                   rm.MaterialName, rm.UniqueId
            FROM Product p
            JOIN Product_RawMaterial rm ON rm.ProductId = p.Id
            ORDER BY rm.MaterialName, p.SKU;
        """)
        materials_rows = cursor.fetchall()
        cursor.execute("""
            SELECT bc.ConsumedProductId AS rm_id, fg_p.Id AS fg_id, fg_p.SKU AS fg_sku,
                   fg_p.CompanyId AS fg_company_id, fg.Market AS market
            FROM BOM_Component bc
            JOIN BOM b ON b.Id = bc.BOMId
            JOIN Product fg_p ON fg_p.Id = b.ProducedProductId
            JOIN Product_FinishedGood fg ON fg.ProductId = fg_p.Id;
        """)
        used_in_by_material = {}
        for row in cursor.fetchall():
            used_in_by_material.setdefault(row["rm_id"], []).append({
                "product_id": row["fg_id"], "company_id": row["fg_company_id"], "market": row["market"]
            })
    materials_list = []
    for row in materials_rows:
        rm_id = row["product_id"]
        material_name = row["MaterialName"]
        used_in_products = used_in_by_material.get(rm_id, [])
        materials_list.append({
            "material_name": material_name, "normalized_name": normalize_text(material_name),
            "tokens": tokenize_material_name(material_name), "product_id": rm_id,
            "used_in_products": used_in_products
        })
    return materials_list

def build_material_index(materials: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    index = {}
    for m in materials:
        fg_ids = {str(p["product_id"]) for p in m["used_in_products"]}
        fg_company_ids = {str(p["company_id"]) for p in m["used_in_products"]}
        markets = {normalize_text(p["market"]) for p in m["used_in_products"] if p.get("market")}
        index[m["product_id"]] = {
            **m, "token_set": set(m["tokens"]), "fg_id_set": fg_ids,
            "fg_company_id_set": fg_company_ids, "market_set": markets
        }
    return index

# -----------------------------
# Similarity Components
# -----------------------------

def compute_name_similarity(mat_a: Dict[str, Any], mat_b: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
    name_a, name_b = mat_a["normalized_name"], mat_b["normalized_name"]
    exact_match = 1.0 if name_a == name_b and name_a != "" else 0.0
    token_jaccard = jaccard_similarity(mat_a["token_set"], mat_b["token_set"])
    token_overlap = overlap_coefficient(mat_a["token_set"], mat_b["token_set"])
    edit_sim = normalized_edit_similarity(name_a, name_b)
    # Calibrated sub-weights for Name Similarity
    score = clamp(0.30*exact_match + 0.35*token_jaccard + 0.15*token_overlap + 0.20*edit_sim)
    return score, {"exact": exact_match, "jaccard": token_jaccard, "overlap": token_overlap, "edit": edit_sim}

def compute_usage_similarity(mat_a: Dict[str, Any], mat_b: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
    fg_jaccard = jaccard_similarity(mat_a["fg_id_set"], mat_b["fg_id_set"])
    fg_company_jaccard = jaccard_similarity(mat_a["fg_company_id_set"], mat_b["fg_company_id_set"])
    market_jaccard = jaccard_similarity(mat_a["market_set"], mat_b["market_set"])
    score = clamp(0.50*fg_jaccard + 0.30*fg_company_jaccard + 0.20*market_jaccard)
    return score, {"fg": fg_jaccard, "company": fg_company_jaccard, "market": market_jaccard}

# -----------------------------
# Scoring and Candidate Generation
# -----------------------------

def score_pair(mat_a: Dict[str, Any], mat_b: Dict[str, Any]) -> Dict[str, Any]:
    name_sim, name_details = compute_name_similarity(mat_a, mat_b)
    usage_sim, usage_details = compute_usage_similarity(mat_a, mat_b)

    # Weights: 70% Name, 30% Usage (Rebalanced from 0.60/0.25 to hit 1.0 total)
    base_similarity = (0.70 * name_sim) + (0.30 * usage_sim)
    
    # New metrics for thresholding
    signal_conflict = abs(name_sim - usage_sim)
    data_richness = clamp(min(len(mat_a["used_in_products"]), len(mat_b["used_in_products"])) / 5.0)

    # Refined Hard Floor
    final_similarity = base_similarity
    if name_sim < 0.15 and usage_sim < 0.8:
        final_similarity = min(base_similarity, 0.15)
    elif name_sim < 0.30:
        final_similarity = min(base_similarity, 0.45)

    feasible = 1 if (name_sim >= 0.4 and final_similarity >= 0.5) or (final_similarity >= 0.75 and data_richness >= 0.6) else 0

    return {
        "required_component": mat_a["material_name"],
        "candidate_component": mat_b["material_name"],
        "feasible": feasible,
        "final_similarity": round(final_similarity, 4),
        "metrics": {
            "name_similarity": round(name_sim, 4),
            "usage_similarity": round(usage_sim, 4),
            "signal_conflict": round(signal_conflict, 4),
            "data_richness": round(data_richness, 4)
        },
        "details": {"name": name_details, "usage": usage_details}
    }

def generate_candidate_pairs(materials: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    indexed = build_material_index(materials)
    token_idx, fg_idx = {}, {}
    for m in materials:
        pid = m["product_id"]
        for t in m["tokens"]: token_idx.setdefault(t, set()).add(pid)
        for fg in m["used_in_products"]: fg_idx.setdefault(fg["product_id"], set()).add(pid)
    
    candidate_id_pairs = set()
    for mats in token_idx.values():
        if len(mats) > 1:
            for id_a, id_b in combinations(sorted(mats), 2): candidate_id_pairs.add((id_a, id_b))
    for mats in fg_idx.values():
        if len(mats) > 1:
            for id_a, id_b in combinations(sorted(mats), 2): candidate_id_pairs.add((id_a, id_b))
            
    return [(indexed[id_a], indexed[id_b]) for id_a, id_b in candidate_id_pairs]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="Output JSON file path")
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()
    try:
        materials = fetch_materials()
        candidate_pairs = generate_candidate_pairs(materials)
        rows_by_req = {}
        for mat_a, mat_b in candidate_pairs:
            row = score_pair(mat_a, mat_b)
            rows_by_req.setdefault(mat_a["material_name"], []).append(row)
        
        final_results = []
        for req_name, rows in rows_by_req.items():
            final_results.extend(sorted(rows, key=lambda r: (r["feasible"], r["final_similarity"]), reverse=True)[:args.top_k])
            
        output = json.dumps({"results": final_results}, indent=2, ensure_ascii=False)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f: f.write(output)
            print(f"Exported {len(final_results)} candidates to {args.out}")
        else: print(output)
    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    main()