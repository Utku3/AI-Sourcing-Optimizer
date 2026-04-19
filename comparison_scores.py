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

    # Groups of mutually compatible tastes
    compatible_groups = [
        {"sweet", "neutral"},
        {"sour", "acidic", "tart", "neutral"},
        {"salty", "savory", "umami", "neutral"},
        {"bitter", "neutral"},
        {"spicy", "pungent", "neutral"},
        {"astringent", "neutral"},
    ]
    # Exact same taste is always compatible
    if taste_a == taste_b:
        return 0.9
    for group in compatible_groups:
        if taste_a in group and taste_b in group:
            return 0.9
    return 0.3

def calculate_usage_score(product_a_json: Dict[str, Any], product_b_json: Dict[str, Any]) -> float:
    """
    application_domain (55%) + functional_role (45%).
    Both weighted more heavily than before; mismatches penalise harder.
    """
    role_a   = product_a_json.get("functional_role", "").lower()
    role_b   = product_b_json.get("functional_role", "").lower()
    domain_a = product_a_json.get("application_domain", "").lower()
    domain_b = product_b_json.get("application_domain", "").lower()

    role_score   = 1.0 if role_a   == role_b   else 0.35
    domain_score = 1.0 if domain_a == domain_b else 0.45

    return 0.55 * domain_score + 0.45 * role_score

def calculate_feasibility_score(product_a_json: Dict[str, Any], product_b_json: Dict[str, Any]) -> float:
    """
    category/general_class (40%) + physical_form (35%) + ingredient_type (25%).
    Category mismatch is a hard zero — different categories are not substitutes.
    """
    cat_a  = product_a_json.get("general_class", "").lower()
    cat_b  = product_b_json.get("general_class", "").lower()
    form_a = product_a_json.get("physical_form", "").lower()
    form_b = product_b_json.get("physical_form", "").lower()
    type_a = product_a_json.get("ingredient_type", "").lower()
    type_b = product_b_json.get("ingredient_type", "").lower()

    cat_score  = 1.0 if (cat_a and cat_b and cat_a == cat_b) else (0.5 if not cat_a or not cat_b else 0.0)
    form_score = 1.0 if form_a == form_b else 0.65
    type_score = 1.0 if type_a == type_b else 0.50

    return 0.40 * cat_score + 0.35 * form_score + 0.25 * type_score

def same_canonical_name(product_a_json: Dict[str, Any], product_b_json: Dict[str, Any]) -> bool:
    """True when both products share the same cleaned canonical name (case-insensitive)."""
    name_a = product_a_json.get("cleaned_canonical_name", "").strip().lower()
    name_b = product_b_json.get("cleaned_canonical_name", "").strip().lower()
    return bool(name_a and name_b and name_a == name_b)

def name_similarity(product_a_json: Dict[str, Any], product_b_json: Dict[str, Any]) -> float:
    """
    Gradient name similarity using word-token Jaccard on cleaned canonical names.
    Same name → 1.0, shared words → proportional boost, no overlap → 0.0.
    Ignores common filler words that carry no identity signal.
    """
    _STOP = {"and", "or", "of", "the", "with", "for", "from", "in", "a", "an"}
    name_a = product_a_json.get("cleaned_canonical_name", "").lower().strip()
    name_b = product_b_json.get("cleaned_canonical_name", "").lower().strip()
    if not name_a or not name_b:
        return 0.0
    if name_a == name_b:
        return 1.0
    tokens_a = set(name_a.split()) - _STOP
    tokens_b = set(name_b.split()) - _STOP
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def calculate_confidence_score(product_a_json: Dict[str, Any], product_b_json: Dict[str, Any]) -> float:
    """
    Name similarity score — ranges 0.0–1.0 based on shared words in canonical names.
    Same name → 1.0 (direct substitute). Partial overlap → proportional positive boost.
    No overlap → 0.0 (small penalty given the low 6% weight).
    """
    return name_similarity(product_a_json, product_b_json)

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
    # feasibility (incl. category): 44%, usage (domain+role): 42%, taste: 8%, canonical name: 6%
    return (0.44 * feasibility_score +
            0.42 * usage_score       +
            0.08 * taste_score       +
            0.06 * confidence_score)

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