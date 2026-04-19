import logging
import json
from typing import Dict, Any, List
from db import db
from comparison_engine import compare_products, check_organic_status

logger = logging.getLogger(__name__)

def suggest_alternatives(product_id: int, supplier_id: int = None) -> Dict[str, Any]:
    """
    Suggest alternative raw materials for a given product.

    Args:
        product_id: Product ID to find alternatives for
        supplier_id: Optional supplier ID (if None, uses first available supplier)

    Returns:
        Dictionary with source product and list of alternatives
    """
    # Get source product data
    if supplier_id is None:
        # First check enriched data in raw_material_master
        query = "SELECT DISTINCT supplier_id FROM raw_material_master WHERE product_id = ? LIMIT 1"
        rows = db.execute_query(query, (product_id,))
        if rows:
            supplier_id = rows[0][0]
        else:
            # Fall back to base tables
            source_data = db.get_raw_materials_with_suppliers()
            source_candidates = [s for s in source_data if s["product_id"] == product_id]
            if not source_candidates:
                raise ValueError(f"No data found for product {product_id}")
            supplier_id = source_candidates[0]["supplier_id"]

    source_product = db.get_raw_material_master(product_id, supplier_id)
    if not source_product:
        raise ValueError(f"Product {product_id} from supplier {supplier_id} not found in enriched data")

    source_class = source_product["product_class"]

    # Get all products in the same class, deduplicated by (product_id, supplier_id)
    candidates = db.get_products_by_class(source_class)
    seen_pairs = set()
    deduped = []
    for c in candidates:
        if c["product_id"] == product_id and c["supplier_id"] == supplier_id:
            continue
        key = (c["product_name"].strip().lower(), c["supplier_id"])
        if key not in seen_pairs:
            seen_pairs.add(key)
            deduped.append(c)
    candidates = deduped

    alternatives = []

    for candidate in candidates:
        try:
            # Compare with source product
            comparison = compare_products(
                product_id, supplier_id,
                candidate["product_id"], candidate["supplier_id"]
            )

            # Only include if score >= 0.60
            if comparison["general_comparison_score"] >= 0.60:
                alternatives.append({
                    "product_id": candidate["product_id"],
                    "supplier_id": candidate["supplier_id"],
                    "supplier_name": candidate.get("supplier_name", ""),
                    "product_name": candidate["product_name"],
                    "comparison": comparison
                })

        except Exception as e:
            logger.warning(f"Failed to compare with {candidate['product_name']}: {e}")
            continue

    # Sort by general score descending
    alternatives.sort(key=lambda x: x["comparison"]["general_comparison_score"], reverse=True)

    # Check organic status for source product
    source_organic_status = check_organic_status(source_product["product_json"])

    return {
        "source_product": {
            "product_id": product_id,
            "supplier_id": supplier_id,
            "product_name": source_product["product_name"],
            "product_class": source_class
        },
        "source_product_organic": source_organic_status["is_organic"],
        "alternatives": alternatives
    }