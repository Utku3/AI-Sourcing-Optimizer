from typing import Dict, Any, Optional

def build_embedding_text(product_json: Dict[str, Any]) -> str:
    """
    Build structured embedding text from product JSON data.

    Args:
        product_json: Structured product data from Qwen API

    Returns:
        Formatted text suitable for embedding generation
    """
    if not product_json:
        return ""

    # Extract key fields
    canonical_name = product_json.get("cleaned_canonical_name", "")
    ingredient_type = product_json.get("ingredient_type", "")
    functional_role = product_json.get("functional_role", "")
    application_domain = product_json.get("application_domain", "")
    physical_form = product_json.get("physical_form", "")
    taste = product_json.get("taste", "")

    # Build structured text
    parts = []

    if canonical_name:
        parts.append(canonical_name)

    if ingredient_type:
        parts.append(f"is a {ingredient_type}")

    if functional_role:
        parts.append(f"used as {functional_role}")

    if application_domain:
        parts.append(f"in {application_domain} products")

    if physical_form:
        parts.append(f"Physical form {physical_form}")

    if taste:
        parts.append(f"Taste {taste}")

    # Join with periods and capitalize first letter
    text = ". ".join(parts)
    if text:
        text = text[0].upper() + text[1:]
        if not text.endswith('.'):
            text += '.'

    return text