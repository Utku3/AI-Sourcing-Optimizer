import sqlite3
import json
import os
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "db.sqlite")


def fetch_materials() -> list:
    """
    Fetches raw materials and their associated suppliers and finished goods.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Fetch all Raw Materials
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

        # 2. Fetch all Supplier assignments for Raw Materials
        cursor.execute("""
            SELECT 
                sp.ProductId, 
                s.Name AS SupplierName
            FROM Supplier_Product sp
            JOIN Supplier s ON s.Id = sp.SupplierId;
        """)
        suppliers_by_material = {}
        for row in cursor.fetchall():
            suppliers_by_material.setdefault(row["ProductId"], []).append(row["SupplierName"])

        # 3. Fetch all BOM associations (which RM is used in which FG)
        cursor.execute("""
            SELECT
                bc.ConsumedProductId AS rm_id,
                fg_p.Id              AS fg_id,
                fg_p.SKU             AS fg_sku,
                fg_p.CompanyId       AS fg_company_id,
                fg.Market,
                fg.MarketSearch
            FROM BOM_Component bc
            JOIN BOM b                  ON b.Id = bc.BOMId
            JOIN Product fg_p           ON fg_p.Id = b.ProducedProductId
            JOIN Product_FinishedGood fg ON fg.ProductId = fg_p.Id;
        """)
        used_in_by_material = {}
        for row in cursor.fetchall():
            used_in_by_material.setdefault(row["rm_id"], []).append({
                "product_id": row["fg_id"],
                "sku": row["fg_sku"],
                "company_id": row["fg_company_id"],
                "market": row["Market"],
                "market_search": row["MarketSearch"]
            })

    # Assemble the final data structure
    materials_list = []
    for row in materials_rows:
        rm_id = row["product_id"]
        materials_list.append({
            "material_name": row["MaterialName"],
            "product_id": rm_id,
            "sku": row["sku"],
            "company_id": row["company_id"],
            "unique_id": row["UniqueId"],
            "suppliers": suppliers_by_material.get(rm_id, []),
            "used_in_products": used_in_by_material.get(rm_id, [])
        })

    return materials_list


def main():
    parser = argparse.ArgumentParser(description="Query materials with their suppliers and parent products.")
    parser.add_argument("--out", help="Output JSON file path (default: print to stdout)")
    args = parser.parse_args()

    try:
        data = fetch_materials()
        output = json.dumps(data, indent=2, ensure_ascii=False)

        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Successfully exported data for {len(data)} materials to {args.out}")
        else:
            print(output)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
