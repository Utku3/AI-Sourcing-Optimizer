import re

def clean_product_name(name: str) -> str:
    """
    Clean and normalize product names.

    Args:
        name: Raw product name

    Returns:
        Cleaned product name
    """
    if not name:
        return ""

    # Convert to lowercase
    cleaned = name.lower()

    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Remove special characters but keep hyphens and spaces
    cleaned = re.sub(r'[^\w\s-]', '', cleaned)

    # Remove common prefixes/suffixes if any
    # This could be expanded based on domain knowledge

    return cleaned

def extract_key_terms(name: str) -> list[str]:
    """
    Extract key terms from product name for better matching.

    Args:
        name: Product name

    Returns:
        List of key terms
    """
    cleaned = clean_product_name(name)
    # Split by spaces and hyphens, remove duplicates
    terms = re.split(r'[\s-]+', cleaned)
    return list(set(term for term in terms for term in terms if len(term) > 2))