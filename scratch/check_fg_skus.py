import sqlite3
conn = sqlite3.connect('db.sqlite')
cur = conn.cursor()
cur.execute("SELECT SKU FROM Product WHERE Type='finished-good' LIMIT 20")
print(cur.fetchall())
conn.close()
