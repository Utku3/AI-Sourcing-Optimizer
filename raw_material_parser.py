import sqlite3
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_sku(sku: str):
    parts = sku.split("-")
    if parts[0] == "RM":
        return {
            "company_id": int(parts[1][1:]),  # C1 -> 1
            "material_name": " ".join(parts[2:-1]).lower(),
            "unique_id": parts[-1]
        }


def main():
    with sqlite3.connect(os.path.join(SCRIPT_DIR, "db.sqlite")) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Product_RawMaterial (
                ProductId    INTEGER PRIMARY KEY,
                CompanyId    INTEGER NOT NULL,
                MaterialName TEXT NOT NULL,
                UniqueId     TEXT NOT NULL,
                FOREIGN KEY (ProductId) REFERENCES Product(Id),
                FOREIGN KEY (CompanyId) REFERENCES Company(Id)
            );
        """)

        cursor.execute("SELECT Id, SKU FROM Product WHERE SKU LIKE 'RM-%';")
        rows = cursor.fetchall()

        inserted = 0
        for product_id, sku in rows:
            try:
                parsed = parse_sku(sku)
                cursor.execute(
                    "INSERT OR REPLACE INTO Product_RawMaterial (ProductId, CompanyId, MaterialName, UniqueId) VALUES (?, ?, ?, ?);",
                    (product_id, parsed["company_id"], parsed["material_name"], parsed["unique_id"])
                )
                inserted += 1
            except Exception as e:
                print(f"Error parsing: {sku} -> {e}")

        conn.commit()

    print(f"Inserted {inserted} records into Product_RawMaterial")


if __name__ == "__main__":
    main()
