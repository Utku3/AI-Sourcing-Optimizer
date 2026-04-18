import logging
import json
from typing import Dict, Any, Optional
from db import db
from comparison_scores import (
    calculate_taste_score,
    calculate_usage_score,
    calculate_feasibility_score,
    calculate_confidence_score,
    calculate_general_score,
    get_comparison_label,
    get_comparison_reason
)

logger = logging.getLogger(__name__)

def check_organic_status(product_json: str) -> Dict[str, Any]:
    """
    Check if a product is organic based on cleaned name and metadata.
    
    Args:
        product_json: JSON string with product data
        
    Returns:
        {"is_organic": bool, "warning": str or None}
    """
    try:
        data = json.loads(product_json)
        cleaned_name = data.get("cleaned_canonical_name", "").lower()
        
        # Keywords that indicate organic
        organic_keywords = ["organic", "certified organic", "bio", "biodynamic", "natural"]
        
        is_organic = any(keyword in cleaned_name for keyword in organic_keywords)
        
        if not is_organic:
            warning = f"⚠️  WARNING: The material '{data.get('cleaned_canonical_name', 'Unknown')}' may not be organic"
            return {"is_organic": False, "warning": warning}
        else:
            return {"is_organic": True, "warning": None}
    except Exception as e:
        logger.error(f"Error checking organic status: {e}")
        return {"is_organic": False, "warning": None}

def compare_products(product_id_a: int, supplier_id_a: int,
                    product_id_b: int, supplier_id_b: int) -> Dict[str, Any]:
    """
    Compare two raw materials and return structured comparison data.

    Args:
        product_id_a: Product ID for material A
        supplier_id_a: Supplier ID for material A
        product_id_b: Product ID for material B
        supplier_id_b: Supplier ID for material B

    Returns:
        Dictionary with comparison results including organic status warnings
    """
    # Get product data
    product_a = db.get_raw_material_master(product_id_a, supplier_id_a)
    product_b = db.get_raw_material_master(product_id_b, supplier_id_b)

    if not product_a or not product_b:
        raise ValueError("One or both products not found in enriched data")

    product_a_json = product_a["product_json"]
    product_b_json = product_b["product_json"]

    # Check organic status for both products
    organic_status_a = check_organic_status(product_a_json)
    organic_status_b = check_organic_status(product_b_json)

    # Calculate sub-scores
    taste_score = calculate_taste_score(product_a_json, product_b_json)
    usage_score = calculate_usage_score(product_a_json, product_b_json)
    feasibility_score = calculate_feasibility_score(product_a_json, product_b_json)
    confidence_score = calculate_confidence_score(product_a_json, product_b_json)

    # Calculate general score
    general_score = calculate_general_score(
        taste_score, feasibility_score, usage_score, confidence_score
    )

    # Get label and reason
    comparison_label = get_comparison_label(general_score)
    comparison_reason = get_comparison_reason(
        general_score, taste_score, feasibility_score, usage_score, confidence_score
    )

    # Build warnings list
    warnings = []
    if organic_status_a["warning"]:
        warnings.append(f"Product A: {organic_status_a['warning']}")
    if organic_status_b["warning"]:
        warnings.append(f"Product B: {organic_status_b['warning']}")

    # Prepare result
    result = {
        "product_id_a": product_id_a,
        "product_id_b": product_id_b,
        "taste_score": taste_score,
        "feasibility_score": feasibility_score,
        "usage_score": usage_score,
        "confidence_score": confidence_score,
        "general_comparison_score": general_score,
        "comparison_label": comparison_label,
        "comparison_reason": comparison_reason,
        "product_a_organic": organic_status_a["is_organic"],
        "product_b_organic": organic_status_b["is_organic"],
        "warnings": warnings if warnings else None
    }

    # Store in database
    try:
        db.insert_comparison(result)
        logger.info(f"Stored comparison between {product_id_a} and {product_id_b}")
    except Exception as e:
        logger.error(f"Failed to store comparison: {e}")

    return result