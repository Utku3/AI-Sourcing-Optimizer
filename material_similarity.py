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
    # Faster jaccard implementation
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
    # If absolute length difference is too large, similarity can't exceed threshold
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
            curr_row[j] = min(
                curr_row[j - 1] + 1,
                prev_row[j] + 1,
                prev_row[j - 1] + cost
            )
        prev_row[:] = curr_row

    dist = prev_row[len_b]
    return 1.0 - (dist / len_a)


def safe_div(n: float, d: float) -> float:
    return n / d if d else 0.0


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# -----------------------------
# Database fetch
# -----------------------------

def fetch_materials() -> List[Dict[str, Any]]:
    """
    Fetch raw materials and enrich them with suppliers and FG usage.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Raw materials
        cursor.execute("""
            SELECT
                p.Id         AS product_id,
                p.SKU        AS sku,
                p.CompanyId  AS company_id,
                rm.MaterialName,
                rm.UniqueId
            FROM Product p
            JOIN Product_RawMaterial rm ON rm.ProductId = p.Id
            ORDER BY rm.MaterialName, p.SKU;
        """)
        materials_rows = cursor.fetchall()

        # Suppliers by material
        cursor.execute("""
            SELECT
                sp.ProductId,
                sp.SupplierId,
                s.Name AS SupplierName
            FROM Supplier_Product sp
            JOIN Supplier s ON s.Id = sp.SupplierId;
        """)
        suppliers_by_material: Dict[int, List[Dict[str, Any]]] = {}
        for row in cursor.fetchall():
            suppliers_by_material.setdefault(row["ProductId"], []).append({
                "supplier_id": row["SupplierId"],
                "supplier_name": row["SupplierName"]
            })

        # FG usage by material
        cursor.execute("""
            SELECT
                bc.ConsumedProductId AS rm_id,
                fg_p.Id              AS fg_id,
                fg_p.SKU             AS fg_sku,
                fg_p.CompanyId       AS fg_company_id,
                fg.Market            AS market,
                fg.MarketSearch      AS market_search
            FROM BOM_Component bc
            JOIN BOM b                    ON b.Id = bc.BOMId
            JOIN Product fg_p             ON fg_p.Id = b.ProducedProductId
            JOIN Product_FinishedGood fg  ON fg.ProductId = fg_p.Id;
        """)
        used_in_by_material: Dict[int, List[Dict[str, Any]]] = {}
        for row in cursor.fetchall():
            used_in_by_material.setdefault(row["rm_id"], []).append({
                "product_id": row["fg_id"],
                "sku": row["fg_sku"],
                "company_id": row["fg_company_id"],
                "market": row["market"],
                "market_search": row["market_search"]
            })

    materials_list: List[Dict[str, Any]] = []
    for row in materials_rows:
        rm_id = row["product_id"]
        material_name = row["MaterialName"]
        suppliers = suppliers_by_material.get(rm_id, [])
        used_in_products = used_in_by_material.get(rm_id, [])

        materials_list.append({
            "material_name": material_name,
            "normalized_name": normalize_text(material_name),
            "tokens": tokenize_material_name(material_name),
            "product_id": rm_id,
            "sku": row["sku"],
            "company_id": row["company_id"],
            "unique_id": row["UniqueId"],
            "suppliers": suppliers,
            "used_in_products": used_in_products
        })

    return materials_list


# -----------------------------
# Feature engineering
# -----------------------------

def build_material_index(materials: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """
    Adds set-based fields used in similarity scoring.
    """
    index = {}
    for m in materials:
        supplier_ids = {str(s["supplier_id"]) for s in m["suppliers"]}
        fg_ids = {str(p["product_id"]) for p in m["used_in_products"]}
        fg_company_ids = {str(p["company_id"]) for p in m["used_in_products"]}
        markets = {
            normalize_text(p["market"])
            for p in m["used_in_products"]
            if p.get("market")
        }

        index[m["product_id"]] = {
            **m,
            "token_set": set(m["tokens"]),
            "supplier_id_set": supplier_ids,
            "fg_id_set": fg_ids,
            "fg_company_id_set": fg_company_ids,
            "market_set": markets
        }
    return index


def compute_name_similarity(mat_a: Dict[str, Any], mat_b: Dict[str, Any]) -> Tuple[float, Dict[str, float], List[str]]:
    """
    NameSimilarity is the strongest signal.
    Uses:
      - exact normalized equality
      - token overlap (Jaccard)
      - overlap coefficient
      - edit similarity
    """
    reasons = []
    name_a = mat_a["normalized_name"]
    name_b = mat_b["normalized_name"]

    exact_match = 1.0 if name_a == name_b and name_a != "" else 0.0
    token_jaccard = jaccard_similarity(mat_a["token_set"], mat_b["token_set"])
    token_overlap = overlap_coefficient(mat_a["token_set"], mat_b["token_set"])
    edit_sim = normalized_edit_similarity(name_a, name_b)

    name_similarity = (
        0.25 * exact_match +
        0.35 * token_jaccard +
        0.20 * token_overlap +
        0.20 * edit_sim
    )
    name_similarity = clamp(name_similarity)

    shared_tokens = sorted(mat_a["token_set"] & mat_b["token_set"])
    if shared_tokens:
        reasons.append(f"shared_tokens={shared_tokens}")
    if exact_match > 0:
        reasons.append("exact_normalized_name_match=1")
    if token_jaccard > 0:
        reasons.append(f"token_jaccard={token_jaccard:.3f}")
    if edit_sim > 0.6:
        reasons.append(f"edit_similarity={edit_sim:.3f}")

    breakdown = {
        "exact_match": exact_match,
        "token_jaccard": token_jaccard,
        "token_overlap": token_overlap,
        "edit_similarity": edit_sim
    }
    return name_similarity, breakdown, reasons


def compute_usage_similarity(mat_a: Dict[str, Any], mat_b: Dict[str, Any]) -> Tuple[float, Dict[str, float], List[str]]:
    """
    Usage similarity via shared FGs, shared FG companies, and shared markets.
    """
    reasons = []

    fg_jaccard = jaccard_similarity(mat_a["fg_id_set"], mat_b["fg_id_set"])
    fg_company_jaccard = jaccard_similarity(mat_a["fg_company_id_set"], mat_b["fg_company_id_set"])
    market_jaccard = jaccard_similarity(mat_a["market_set"], mat_b["market_set"])

    usage_similarity = (
        0.50 * fg_jaccard +
        0.30 * fg_company_jaccard +
        0.20 * market_jaccard
    )
    usage_similarity = clamp(usage_similarity)

    shared_fg_count = len(mat_a["fg_id_set"] & mat_b["fg_id_set"])
    shared_company_count = len(mat_a["fg_company_id_set"] & mat_b["fg_company_id_set"])
    shared_markets = sorted(mat_a["market_set"] & mat_b["market_set"])

    if shared_fg_count > 0:
        reasons.append(f"shared_fg_count={shared_fg_count}")
    if shared_company_count > 0:
        reasons.append(f"shared_fg_company_count={shared_company_count}")
    if shared_markets:
        reasons.append(f"shared_markets={shared_markets}")

    breakdown = {
        "fg_jaccard": fg_jaccard,
        "fg_company_jaccard": fg_company_jaccard,
        "market_jaccard": market_jaccard
    }
    return usage_similarity, breakdown, reasons


def compute_supplier_overlap(mat_a: Dict[str, Any], mat_b: Dict[str, Any]) -> Tuple[float, Dict[str, float], List[str]]:
    """
    Weak signal only.
    Uses Jaccard plus a normalized shared-supplier factor.
    """
    reasons = []

    suppliers_a = mat_a["supplier_id_set"]
    suppliers_b = mat_b["supplier_id_set"]

    supplier_jaccard = jaccard_similarity(suppliers_a, suppliers_b)
    shared_count = len(suppliers_a & suppliers_b)
    normalized_shared = safe_div(shared_count, math.sqrt(max(len(suppliers_a), 1) * max(len(suppliers_b), 1)))

    supplier_overlap = (
        0.60 * supplier_jaccard +
        0.40 * normalized_shared
    )
    supplier_overlap = clamp(supplier_overlap)

    if shared_count > 0:
        reasons.append(f"shared_supplier_count={shared_count}")
    if supplier_jaccard > 0:
        reasons.append(f"supplier_jaccard={supplier_jaccard:.3f}")

    breakdown = {
        "supplier_jaccard": supplier_jaccard,
        "normalized_shared": normalized_shared
    }
    return supplier_overlap, breakdown, reasons


def compute_company_pattern(mat_a: Dict[str, Any], mat_b: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Small signal.
    Same owning company gives a small boost, but not dominant.
    """
    reasons = []
    score = 1.0 if mat_a["company_id"] == mat_b["company_id"] else 0.0
    if score > 0:
        reasons.append("same_raw_material_company=1")
    return score, reasons


def compute_support_and_confidence(
    mat_a: Dict[str, Any],
    mat_b: Dict[str, Any],
    name_similarity: float,
    usage_similarity: float,
    supplier_overlap: float
) -> Tuple[float, float, Dict[str, float], List[str]]:
    """
    Confidence is not the same as similarity.
    It answers: how much do we trust the score?
    """
    reasons = []

    fg_count_a = len(mat_a["fg_id_set"])
    fg_count_b = len(mat_b["fg_id_set"])
    supplier_count_a = len(mat_a["supplier_id_set"])
    supplier_count_b = len(mat_b["supplier_id_set"])

    # Data support from usage + supplier coverage
    fg_support = clamp(min(fg_count_a, fg_count_b) / 5.0)  # saturates after 5
    supplier_support = clamp(min(supplier_count_a, supplier_count_b) / 3.0)  # saturates after 3
    data_support = clamp(0.65 * fg_support + 0.35 * supplier_support)

    # Coverage
    usage_coverage = 1.0 if fg_count_a > 0 and fg_count_b > 0 else 0.0
    supplier_coverage = 1.0 if supplier_count_a > 0 and supplier_count_b > 0 else 0.0

    # Agreement: if weak signal wildly disagrees, confidence should not be too high
    components = [name_similarity]
    if usage_coverage > 0:
        components.append(usage_similarity)
    if supplier_coverage > 0:
        components.append(supplier_overlap)

    mean_signal = sum(components) / len(components)
    variance = sum((x - mean_signal) ** 2 for x in components) / len(components)
    std_dev = math.sqrt(variance)

    signal_agreement = clamp(1.0 - std_dev)

    confidence = (
        0.40 * data_support +
        0.25 * signal_agreement +
        0.20 * usage_coverage +
        0.15 * supplier_coverage
    )
    confidence = clamp(confidence)

    if data_support > 0:
        reasons.append(f"data_support={data_support:.3f}")
    reasons.append(f"signal_agreement={signal_agreement:.3f}")
    reasons.append(f"fg_counts=({fg_count_a},{fg_count_b})")
    reasons.append(f"supplier_counts=({supplier_count_a},{supplier_count_b})")

    breakdown = {
        "fg_support": fg_support,
        "supplier_support": supplier_support,
        "data_support": data_support,
        "usage_coverage": usage_coverage,
        "supplier_coverage": supplier_coverage,
        "signal_agreement": signal_agreement
    }
    return confidence, data_support, breakdown, reasons


# -----------------------------
# Pair scoring
# -----------------------------
def build_inverted_indices(materials: List[Dict[str, Any]]) -> Dict[str, Dict[Any, Set[int]]]:
    """
    Builds indices to quickly find materials sharing tokens, suppliers, or products.
    """
    token_idx = {}
    supplier_idx = {}
    fg_idx = {}
    
    for m in materials:
        pid = m["product_id"]
        for t in m["tokens"]:
            token_idx.setdefault(t, set()).add(pid)
        for s in m["suppliers"]:
            supplier_idx.setdefault(str(s["supplier_id"]), set()).add(pid)
        for fg in m["used_in_products"]:
            fg_idx.setdefault(fg["product_id"], set()).add(pid)
            
    return {
        "tokens": token_idx,
        "suppliers": supplier_idx,
        "fgs": fg_idx
    }


def generate_candidate_pairs(
    materials: List[Dict[str, Any]],
    min_name_gate: float = 0.15
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    Optimized candidate generation via inverted indices.
    Avoids O(N^2) comparison entirely.
    """
    indexed = build_material_index(materials)
    indices = build_inverted_indices(materials)
    
    candidate_id_pairs = set()
    
    # 1. Share at least one token
    for mats in indices["tokens"].values():
        if len(mats) > 1:
            for id_a, id_b in combinations(sorted(mats), 2):
                candidate_id_pairs.add((id_a, id_b))
                
    # 2. Share at least one supplier
    for mats in indices["suppliers"].values():
        if len(mats) > 1:
            for id_a, id_b in combinations(sorted(mats), 2):
                candidate_id_pairs.add((id_a, id_b))
                
    # 3. Share at least one FG
    for mats in indices["fgs"].values():
        if len(mats) > 1:
            for id_a, id_b in combinations(sorted(mats), 2):
                candidate_id_pairs.add((id_a, id_b))
    
    final_pairs = []
    for id_a, id_b in candidate_id_pairs:
        final_pairs.append((indexed[id_a], indexed[id_b]))

    return final_pairs


def score_pair(mat_a: Dict[str, Any], mat_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns one pairwise candidate row.
    """
    name_similarity, name_breakdown, reasons_name = compute_name_similarity(mat_a, mat_b)
    usage_similarity, usage_breakdown, reasons_usage = compute_usage_similarity(mat_a, mat_b)
    supplier_overlap, supplier_breakdown, reasons_supplier = compute_supplier_overlap(mat_a, mat_b)
    company_pattern, reasons_company = compute_company_pattern(mat_a, mat_b)

    # Base weighted score
    base_similarity = (
        0.60 * name_similarity +
        0.25 * usage_similarity +
        0.10 * supplier_overlap +
        0.05 * company_pattern
    )
    base_similarity = clamp(base_similarity)

    # Hard floor: Refined to be less aggressive if usage/suppliers provide very strong signals
    hard_floor_triggered = False
    if name_similarity < 0.15:
        # If names are completely different, cap at 0.15 unless we have extreme evidence
        # (usually synonyms will have at least some name overlap or trigram match, 
        # but pure synonyms might rely only on usage/suppliers)
        limit = 0.15
        if usage_similarity > 0.8 or supplier_overlap > 0.8:
            limit = 0.35
        final_similarity = min(base_similarity, limit)
        hard_floor_triggered = True
    elif name_similarity < 0.30:
        final_similarity = min(base_similarity, 0.45)
        hard_floor_triggered = True
    else:
        final_similarity = base_similarity

    final_similarity = clamp(final_similarity)

    confidence, data_support, confidence_breakdown, reasons_conf = compute_support_and_confidence(
        mat_a=mat_a,
        mat_b=mat_b,
        name_similarity=name_similarity,
        usage_similarity=usage_similarity,
        supplier_overlap=supplier_overlap
    )

    # Feasibility rule: moderate name shimilarity OR very high shared signals
    feasible = 0
    if name_similarity >= 0.4 and final_similarity >= 0.5:
        feasible = 1
    elif final_similarity >= 0.75 and confidence >= 0.6:
        feasible = 1

    reasons = []
    reasons.extend(reasons_name)
    reasons.extend(reasons_usage)
    reasons.extend(reasons_supplier)
    reasons.extend(reasons_company)
    reasons.extend(reasons_conf)
    if hard_floor_triggered:
        reasons.append("hard_floor_triggered=1")

    return {
        "required_component_id": mat_a["product_id"],
        "required_component_name": mat_a["material_name"],
        "candidate_component_id": mat_b["product_id"],
        "candidate_component_name": mat_b["material_name"],
        "feasible": feasible,
        "confidence": round(confidence, 4),
        "final_similarity": round(final_similarity, 4),
        "score_breakdown": {
            "name_similarity": round(name_similarity, 4),
            "usage_similarity": round(usage_similarity, 4),
            "supplier_overlap": round(supplier_overlap, 4),
            "company_pattern": round(company_pattern, 4),
            "base_similarity": round(base_similarity, 4),
            "name_details": {k: round(v, 4) for k, v in name_breakdown.items()},
            "usage_details": {k: round(v, 4) for k, v in usage_breakdown.items()},
            "supplier_details": {k: round(v, 4) for k, v in supplier_breakdown.items()},
            "confidence_details": {k: round(v, 4) for k, v in confidence_breakdown.items()}
        },
        "reasons": reasons
    }



def build_similarity_table(
    materials: List[Dict[str, Any]],
    top_k_per_material: int = 20
) -> List[Dict[str, Any]]:
    """
    Builds pairwise candidate table and keeps top K candidates per required material.
    Also writes both directions:
      A -> B
      B -> A
    """
    candidate_pairs = generate_candidate_pairs(materials)
    rows_by_required: Dict[int, List[Dict[str, Any]]] = {}

    for mat_a, mat_b in candidate_pairs:
        row_ab = score_pair(mat_a, mat_b)
        row_ba = score_pair(mat_b, mat_a)

        rows_by_required.setdefault(mat_a["product_id"], []).append(row_ab)
        rows_by_required.setdefault(mat_b["product_id"], []).append(row_ba)

    final_rows = []
    for required_id, rows in rows_by_required.items():
        rows_sorted = sorted(
            rows,
            key=lambda r: (
                r["feasible"],
                r["final_similarity"],
                r["confidence"]
            ),
            reverse=True
        )
        final_rows.extend(rows_sorted[:top_k_per_material])

    return final_rows


# -----------------------------
# Main
# -----------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate pairwise raw material similarity / candidate substitution table."
    )
    parser.add_argument(
        "--out",
        help="Output JSON file path (default: print to stdout)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Keep top K candidates per required material (default: 20)"
    )
    args = parser.parse_args()

    try:
        materials = fetch_materials()
        results = build_similarity_table(materials, top_k_per_material=args.top_k)

        payload = {
            "meta": {
                "material_count": len(materials),
                "result_row_count": len(results),
                "method_version": "rm_similarity_v1",
                "notes": [
                    "This is a similarity-based candidate table, not regulatory proof.",
                    "Supplier overlap is treated as a weak supporting signal only.",
                    "Hard floor caps final similarity when name similarity is too low."
                ]
            },
            "results": results
        }

        output = json.dumps(payload, indent=2, ensure_ascii=False)

        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Successfully exported {len(results)} candidate rows to {args.out}")
        else:
            print(output)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()