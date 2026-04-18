import sqlite3
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def parse_sku(sku: str):
    parts = sku.split("-")
    if parts[0] == "FG":
        if parts[1] == "iherb" and len(parts) == 3:
            return{
                "type": parts[0],
                "market": parts[1],
                "market-additional": "",
                "market-search": parts[2]            
            }
        if parts[1] == "iherb" and parts[2] == "cen" and len(parts) == 4:
            return{
                "type": parts[0],
                "market": parts[1],
                "market-additional": parts[2],
                "market-search": parts[3]            
                }

def main():
    #Select only products starting with RM -> only raw materials are collected
    data = []
    with sqlite3.connect(os.path.join(SCRIPT_DIR, "db.sqlite")) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SKU FROM Product WHERE SKU LIKE 'FG-%';")
        rows = cursor.fetchall()

    #Process basic labeling for every raw material to start with analysis
    for row in rows:
        sku = row[0]
        try:
            parsed = parse_sku(sku)
            parsed["raw_sku"] = sku
            data.append(parsed)
        except Exception as e:
            print(f"Error parsing: {sku} -> {e}")

    #Save the file as json to use it later in the pipeline
    with open(os.path.join(SCRIPT_DIR, "parsed_finished_good.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(data)} records to output.json")

if __name__ == "__main__":
    main()        

