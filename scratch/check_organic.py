import sqlite3
conn = sqlite3.connect('db.sqlite')
cur = conn.cursor()
cur.execute("SELECT SKU FROM Product WHERE SKU LIKE '%organic%'")
print(cur.fetchall())
conn.close()
