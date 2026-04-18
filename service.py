import logging
from typing import Dict, Any, List
from db import db
from comparison_engine import compare_products

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
        # Find any supplier for this product
        source_data = db.get_raw_materials_with_suppliers()
        source_candidates = [s for s in source_data if s["product_id"] == product_id]
        if not source_candidates:
            raise ValueError(f"No data found for product {product_id}")
        supplier_id = source_candidates[0]["supplier_id"]

    source_product = db.get_raw_material_master(product_id, supplier_id)
    if not source_product:
        raise ValueError(f"Product {product_id} from supplier {supplier_id} not found in enriched data")

    source_class = source_product["product_class"]

    # Get all products in the same class
    candidates = db.get_products_by_class(source_class)

    # Remove the source product itself
    candidates = [c for c in candidates if not (c["product_id"] == product_id and c["supplier_id"] == supplier_id)]

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
                    "product_name": candidate["product_name"],
                    "comparison": comparison
                })

        except Exception as e:
            logger.warning(f"Failed to compare with {candidate['product_name']}: {e}")
            continue

    # Sort by general score descending
    alternatives.sort(key=lambda x: x["comparison"]["general_comparison_score"], reverse=True)

    return {
        "source_product": {
            "product_id": product_id,
            "supplier_id": supplier_id,
            "product_name": source_product["product_name"],
            "product_class": source_class
        },
        "alternatives": alternatives
    }