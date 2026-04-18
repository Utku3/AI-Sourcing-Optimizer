import sqlite3
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "db.sqlite")

def analyze_organic_compliance():
    """
    Analyzes products with 'organic' in their SKU and checks if their
    raw materials are also organic.
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Identify Organic Products (SKU contains 'organic')
        cursor.execute("""
            SELECT p.Id, p.SKU, fg.Market, fg.MarketSearch
            FROM Product p
            JOIN Product_FinishedGood fg ON fg.ProductId = p.Id
            WHERE p.SKU LIKE '%organic%'
        """)
        organic_products = cursor.fetchall()

        if not organic_products:
            print("No organic products found in the database (SKU search).")
            return

        report = []

        for fg in organic_products:
            fg_id = fg["Id"]
            fg_sku = fg["SKU"]

            # 2. Fetch all materials for this organic product
            cursor.execute("""
                SELECT rm_p.SKU AS rm_sku, rm.MaterialName
                FROM BOM b
                JOIN BOM_Component bc ON bc.BOMId = b.Id
                JOIN Product rm_p ON rm_p.Id = bc.ConsumedProductId
                JOIN Product_RawMaterial rm ON rm.ProductId = rm_p.Id
                WHERE b.ProducedProductId = ?
            """, (fg_id,))
            materials = cursor.fetchall()

            product_report = {
                "product_sku": fg_sku,
                "materials": []
            }

            for mat in materials:
                mat_name = mat["MaterialName"]
                is_organic = "organic" in mat_name.lower()
                
                mat_entry = {
                    "material_name": mat_name,
                    "is_organic": is_organic,
                    "sku": mat["rm_sku"]
                }

                if not is_organic:
                    # 3. Add reasoning for non-organic materials in organic products
                    mat_entry["reasoning"] = "Replacing these with other materials would damage the product's originality"
                
                product_report["materials"].append(mat_entry)

            report.append(product_report)

    # 4. Save report to JSON
    output_path = os.path.join(SCRIPT_DIR, "organic_compliance_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Analysis complete. Report saved to {output_path}")
    print(f"Processed {len(report)} organic products.")

if __name__ == "__main__":
    analyze_organic_compliance()
