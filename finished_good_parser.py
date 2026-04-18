import sqlite3
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

KNOWN_MARKETS = [
    "thrive-market",
    "the-vitamin-shoppe",
    "sams-club",
    "iherb",
    "walmart",
    "amazon",
    "vitacost",
    "gnc",
    "target",
    "costco",
    "walgreens",
    "cvs",
]


def parse_sku(sku: str):
    # sku format: FG-{market}-{market_search} or FG-{market}-cen-{market_search}
    body = sku[3:]  # strip "FG-"
    market = next((m for m in KNOWN_MARKETS if body.startswith(m + "-")), None)
    if not market:
        return None
    remainder = body[len(market) + 1:]  # strip "{market}-"
    if remainder.startswith("cen-"):
        return {
            "market": market,
            "market_additional": "cen",
            "market_search": remainder[4:]
        }
    return {
        "market": market,
        "market_additional": None,
        "market_search": remainder
    }


def main():
    with sqlite3.connect(os.path.join(SCRIPT_DIR, "db.sqlite")) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Product_FinishedGood (
                ProductId        INTEGER PRIMARY KEY,
                Market           TEXT NOT NULL,
                MarketSearch     TEXT NOT NULL,
                MarketAdditional TEXT,
                FOREIGN KEY (ProductId) REFERENCES Product(Id)
            );
        """)

        cursor.execute("SELECT Id, SKU FROM Product WHERE SKU LIKE 'FG-%';")
        rows = cursor.fetchall()

        inserted = 0
        for product_id, sku in rows:
            try:
                parsed = parse_sku(sku)
                cursor.execute(
                    "INSERT OR REPLACE INTO Product_FinishedGood (ProductId, Market, MarketSearch, MarketAdditional) VALUES (?, ?, ?, ?);",
                    (product_id, parsed["market"], parsed["market_search"], parsed["market_additional"])
                )
                inserted += 1
            except Exception as e:
                print(f"Error parsing: {sku} -> {e}")

        conn.commit()

    print(f"Inserted {inserted} records into Product_FinishedGood")


if __name__ == "__main__":
    main()
