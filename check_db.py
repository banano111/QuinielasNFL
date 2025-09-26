import sqlite3

conn = sqlite3.connect('quinielas.db')
cursor = conn.cursor()

# Ver tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tablas:", tables)

# Ver esquema de cada tabla
for table in tables:
    table_name = table[0]
    print(f"\nEsquema de {table_name}:")
    cursor.execute(f"PRAGMA table_info({table_name})")
    schema = cursor.fetchall()
    for column in schema:
        print(f"  {column[1]} {column[2]}")

conn.close()