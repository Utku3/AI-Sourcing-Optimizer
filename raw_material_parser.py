import sqlite3
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


#Parser function for solving the format TYPE-C_ID-Name-..-DB_ID
def parse_sku(sku: str):
    parts = sku.split("-")
    if parts[0] == "RM":
        return {
            "type": parts[0],
            "customer_id": parts[1],
            "material_name": " ".join(parts[2:-1]).replace("-", " ").lower(),
            "unique_id": parts[-1]
        }


#Connect the database to work on it
conn = sqlite3.connect(os.path.join(SCRIPT_DIR, "db.sqlite"))
cursor = conn.cursor()

#Select only productsstarting with RM -> only raw materials are collected
cursor.execute(f"SELECT SKU FROM Product WHERE SKU LIKE 'RM-%';")
rows = cursor.fetchall()

#Process basic labeling for every raw material to start with analysis
data = []
for row in rows:
    sku = row[0]
    
    try:
        parsed = parse_sku(sku)
        parsed["raw_sku"] = sku
        data.append(parsed)
    except Exception as e:
        # bozuk data varsa atla veya logla
        print(f"Error parsing: {sku} -> {e}")

#Save the file as json to use it later in the pipeline
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Exported {len(data)} records to output.json")