import sqlite3
import json
import os
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_bom(with_suppliers: bool = False) -> list:
    with sqlite3.connect(os.path.join(SCRIPT_DIR, "db.sqlite")) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                p.Id         AS fg_id,
                p.SKU        AS fg_sku,
                fg.Market,
                fg.MarketSearch,
                fg.MarketAdditional,
                rm_p.Id      AS rm_id,
                rm_p.SKU     AS rm_sku,
                rm.MaterialName
            FROM Product p
            JOIN Product_FinishedGood fg ON fg.ProductId = p.Id
            JOIN BOM b                   ON b.ProducedProductId = p.Id
            JOIN BOM_Component bc        ON bc.BOMId = b.Id
            JOIN Product rm_p            ON rm_p.Id = bc.ConsumedProductId
            JOIN Product_RawMaterial rm  ON rm.ProductId = rm_p.Id
            ORDER BY p.Id, rm_p.Id;
        """)
        rows = cursor.fetchall()

        suppliers_by_product = {}
        if with_suppliers:
            cursor.execute("""
                SELECT sp.ProductId, s.Name
                FROM Supplier_Product sp
                JOIN Supplier s ON s.Id = sp.SupplierId;
            """)
            for row in cursor.fetchall():
                suppliers_by_product.setdefault(row["ProductId"], []).append(row["Name"])

    fg_map = {}
    for row in rows:
        fg_id = row["fg_id"]
        if fg_id not in fg_map:
            fg_map[fg_id] = {
                "product_id": fg_id,
                "sku": row["fg_sku"],
                "market": row["Market"],
                "market_search": row["MarketSearch"],
                "market_additional": row["MarketAdditional"],
                "raw_materials": []
            }
        fg_map[fg_id]["raw_materials"].append({
            "product_id": row["rm_id"],
            "sku": row["rm_sku"],
            "material_name": row["MaterialName"],
            "suppliers": suppliers_by_product.get(row["rm_id"], [])
        })

    return list(fg_map.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-suppliers", action="store_true")
    parser.add_argument("--out", help="output file path (default: stdout)")
    args = parser.parse_args()

    data = fetch_bom(with_suppliers=args.with_suppliers)
    output = json.dumps(data, indent=2, ensure_ascii=False)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Wrote {len(data)} finished goods to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
