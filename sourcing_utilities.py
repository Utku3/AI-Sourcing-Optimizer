def compute_switch_penalty(current_item, candidate_item):
    """
    Computes a sourcing risk/penalty score between 0.0 and 1.0 for switching
    from a current_item to a candidate_item.
    """
    # 1. Exact same raw material (by ID or SKU)
    curr_sku = current_item.get("sku")
    cand_sku = candidate_item.get("sku")
    if curr_sku and cand_sku and curr_sku == cand_sku:
        return 0.0
    
    curr_uid = current_item.get("unique_id")
    cand_uid = candidate_item.get("unique_id")
    if curr_uid and cand_uid and curr_uid == cand_uid:
        return 0.0

    penalty = 0.0

    # Extract common fields
    current_name = current_item.get("material_name", "").lower().strip()
    candidate_name = candidate_item.get("material_name", "").lower().strip()
    
    current_supplier = current_item.get("supplier_id") or current_item.get("supplier")
    candidate_supplier = candidate_item.get("supplier_id") or candidate_item.get("supplier")

    # 2. Same normalized material name but different supplier
    if current_name == candidate_name:
        if current_supplier != candidate_supplier:
            penalty += 0.15  # Low penalty for supplier switch
    else:
        # 3. Similar material (Heuristic: partial string match)
        if current_name in candidate_name or candidate_name in current_name:
            penalty += 0.40  # Medium penalty for similar materials
        else:
            # 4. Different material
            penalty += 0.70  # High penalty for different materials

    # 5. Compliance mismatch (e.g. Organic vs Non-Organic)
    current_compliance = current_item.get("compliance", "").lower()
    candidate_compliance = candidate_item.get("compliance", "").lower()
    if current_compliance != candidate_compliance and current_compliance != "":
        penalty += 0.50  # Strong penalty for compliance mismatch

    # 6. Quality mismatch
    current_quality = current_item.get("quality_rating") or current_item.get("quality", 1.0)
    candidate_quality = candidate_item.get("quality_rating") or candidate_item.get("quality", 1.0)
    if candidate_quality < current_quality:
        penalty += 0.20  # Penalty for lower quality

    # 7. Extract ratio / form / strength mismatch
    current_form = current_item.get("form", "").lower()
    candidate_form = candidate_item.get("form", "").lower()
    if current_form != candidate_form:
        penalty += 0.15  # Penalty for different form (liquid vs powder)

    current_ratio = current_item.get("extract_ratio")
    candidate_ratio = candidate_item.get("extract_ratio")
    if current_ratio != candidate_ratio:
        penalty += 0.25  # Significant penalty for strength/ratio mismatch

    # Clamp result to max 1.0
    return min(1.0, penalty)


if __name__ == "__main__":
    # --- Example Inputs and Outputs ---
    
    print("--- Sourcing Switch Penalty Examples ---")

    # Example 1: Same material, different supplier
    item_a = {"material_name": "Vitamin C", "supplier": "Supplier A", "sku": "SKU-001"}
    item_b = {"material_name": "Vitamin C", "supplier": "Supplier B", "sku": "SKU-002"}
    print(f"Same material, diff supplier: {compute_switch_penalty(item_a, item_b)}")

    # Example 2: Organic to Non-Organic switch (Compliance mismatch)
    item_org = {"material_name": "Organic Cane Sugar", "compliance": "organic", "sku": "ORG-001"}
    item_non = {"material_name": "Cane Sugar", "compliance": "non-organic", "sku": "NON-001"}
    print(f"Organic to Non-Organic: {compute_switch_penalty(item_org, item_non)}")

    # Example 3: Different form (Powder vs Liquid)
    item_pow = {"material_name": "Zinc", "form": "powder", "sku": "ZN-P"}
    item_liq = {"material_name": "Zinc", "form": "liquid", "sku": "ZN-L"}
    print(f"Form mismatch (Powder vs Liquid): {compute_switch_penalty(item_pow, item_liq)}")

    # Example 4: Completely different materials
    item_calc = {"material_name": "Calcium Citrate", "sku": "CAL-01"}
    item_mag = {"material_name": "Magnesium Oxide", "sku": "MAG-01"}
    print(f"Different materials: {compute_switch_penalty(item_calc, item_mag)}")
