import sqlite3
conn = sqlite3.connect('db.sqlite')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM Product_RawMaterial LIMIT 5")
rows = [dict(r) for r in cur.fetchall()]
print(rows)
conn.close()
