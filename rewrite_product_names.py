#!/usr/bin/env python3
"""
Rewrite product_name in raw_material_master using the clean name parsed from Product.SKU.
SKU format: RM-C{company_id}-{word1}-{word2}-...-{unique_id}
Clean name: join the middle words, title-cased.
Also updates cleaned_canonical_name inside product_json.
"""

import sqlite3
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_sku_name(sku: str) -> str | None:
    """Extract clean material name from SKU. Returns None if SKU doesn't match RM format."""
    parts = sku.split("-")
    # Need at least: RM, C{x}, one name word, unique_id
    if len(parts) < 4 or parts[0] != "RM":
        return None
    name_parts = parts[2:-1]
    if not name_parts:
        return None
    return " ".join(name_parts).title()


def main():
    db_path = os.path.join(SCRIPT_DIR, "db.sqlite")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT rmm.product_id, rmm.supplier_id, rmm.product_json, p.SKU
            FROM raw_material_master rmm
            JOIN Product p ON rmm.product_id = p.Id
            WHERE p.SKU LIKE 'RM-%'
        """)
        rows = cursor.fetchall()
        print(f"Found {len(rows)} enriched products with RM- SKUs")

        updated, skipped = 0, 0
        for product_id, supplier_id, product_json_str, sku in rows:
            clean_name = parse_sku_name(sku)
            if not clean_name:
                print(f"  Skipped (bad SKU format): {sku}")
                skipped += 1
                continue

            try:
                pj = json.loads(product_json_str) if product_json_str else {}
            except Exception:
                pj = {}
            pj["cleaned_canonical_name"] = clean_name

            cursor.execute("""
                UPDATE raw_material_master
                SET product_name = ?, product_json = ?
                WHERE product_id = ? AND supplier_id = ?
            """, (clean_name, json.dumps(pj), product_id, supplier_id))
            updated += 1

        conn.commit()
        print(f"Done. Updated: {updated}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
