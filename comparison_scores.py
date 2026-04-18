from typing import Dict, Any
import math

def calculate_taste_score(product_a_json: Dict[str, Any], product_b_json: Dict[str, Any]) -> float:
    """
    Calculate taste compatibility score between two products.

    Args:
        product_a_json: JSON data for product A
        product_b_json: JSON data for product B

    Returns:
        Float between 0.0 and 1.0
    """
    taste_a = product_a_json.get("taste", "").lower()
    taste_b = product_b_json.get("taste", "").lower()

    if not taste_a or not taste_b:
        return 0.5  # Neutral score when taste info is missing

    # Simple compatibility matrix
    compatible_pairs = [
        ("sweet", "sweet"),
        ("sour", "sour"),
        ("neutral", "neutral"),
        ("neutral", "sweet"),
        ("neutral", "sour"),
        ("sweet", "neutral"),
        ("sour", "neutral")
    ]

    if (taste_a, taste_b) in compatible_pairs or (taste_b, taste_a) in compatible_pairs:
        return 0.9
    else:
        return 0.3

def calculate_usage_score(product_a_json: Dict[str, Any], product_b_json: Dict[str, Any]) -> float:
    """
    Calculate usage compatibility score based on functional role and application domain.

    Args:
        product_a_json: JSON data for product A
        product_b_json: JSON data for product B

    Returns:
        Float between 0.0 and 1.0
    """
    role_a = product_a_json.get("functional_role", "").lower()
    role_b = product_b_json.get("functional_role", "").lower()
    domain_a = product_a_json.get("application_domain", "").lower()
    domain_b = product_b_json.get("application_domain", "").lower()

    role_score = 1.0 if role_a == role_b else 0.5
    domain_score = 1.0 if domain_a == domain_b else 0.7

    return (role_score + domain_score) / 2.0

def calculate_feasibility_score(product_a_json: Dict[str, Any], product_b_json: Dict[str, Any]) -> float:
    """
    Calculate feasibility score based on physical form and ingredient type compatibility.

    Args:
        product_a_json: JSON data for product A
        product_b_json: JSON data for product B

    Returns:
        Float between 0.0 and 1.0
    """
    form_a = product_a_json.get("physical_form", "").lower()
    form_b = product_b_json.get("physical_form", "").lower()
    type_a = product_a_json.get("ingredient_type", "").lower()
    type_b = product_b_json.get("ingredient_type", "").lower()

    form_score = 1.0 if form_a == form_b else 0.8
    type_score = 1.0 if type_a == type_b else 0.6

    return (form_score + type_score) / 2.0

def calculate_confidence_score(product_a_json: Dict[str, Any], product_b_json: Dict[str, Any]) -> float:
    """
    Calculate confidence score based on the confidence values from Qwen API.

    Args:
        product_a_json: JSON data for product A
        product_b_json: JSON data for product B

    Returns:
        Float between 0.0 and 1.0
    """
    conf_a = product_a_json.get("confidence", 0.5)
    conf_b = product_b_json.get("confidence", 0.5)

    # Average of both confidences
    return (conf_a + conf_b) / 2.0

def calculate_general_score(taste_score: float, feasibility_score: float,
                          usage_score: float, confidence_score: float) -> float:
    """
    Calculate general comparison score using weighted average.

    Formula: 0.30 * usage_score + 0.30 * feasibility_score + 0.20 * taste_score + 0.20 * confidence_score

    Args:
        taste_score: Taste compatibility score
        feasibility_score: Feasibility score
        usage_score: Usage compatibility score
        confidence_score: Confidence score

    Returns:
        Float between 0.0 and 1.0
    """
    return (0.30 * usage_score +
            0.30 * feasibility_score +
            0.20 * taste_score +
            0.20 * confidence_score)

def get_comparison_label(general_score: float) -> str:
    """
    Get comparison label based on general score.

    Args:
        general_score: General comparison score

    Returns:
        Label string
    """
    if general_score >= 0.80:
        return "strong substitute"
    elif general_score >= 0.60:
        return "possible substitute"
    else:
        return "weak substitute"

def get_comparison_reason(general_score: float, taste_score: float,
                         feasibility_score: float, usage_score: float,
                         confidence_score: float) -> str:
    """
    Generate a human-readable reason for the comparison.

    Args:
        general_score: General comparison score
        taste_score: Taste score
        feasibility_score: Feasibility score
        usage_score: Usage score
        confidence_score: Confidence score

    Returns:
        Reason string
    """
    reasons = []

    if usage_score > 0.8:
        reasons.append("similar functional roles")
    if feasibility_score > 0.8:
        reasons.append("compatible physical forms")
    if taste_score > 0.8:
        reasons.append("matching taste profiles")
    if confidence_score > 0.8:
        reasons.append("high confidence in data")

    if not reasons:
        reasons.append("limited compatibility data")

    reason_text = ", ".join(reasons)
    return f"Based on {reason_text}. General compatibility: {general_score:.2f}"