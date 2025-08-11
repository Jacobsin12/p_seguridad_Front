import sqlite3
import psycopg2
from psycopg2 import sql

# === CONFIGURACIÓN ===
SQLITE_FILE = "./main_database.db"  # Cambia esto por tu archivo SQLite local
POSTGRES_URL = "postgresql://user_service_w41h_user:zwRZBnJBIm2fIWmqV3ZBvyS5cNrLXbor@dpg-d2cn4hbuibrs738lft0g-a.oregon-postgres.render.com/user_service_w41h"  # Pega aquí la External Database URL de Render

def map_sqlite_type_to_postgres(sqlite_type):
    t = sqlite_type.upper()
    if "INT" in t:
        return "INTEGER"
    elif "CHAR" in t or "CLOB" in t or "TEXT" in t:
        return "TEXT"
    elif "BLOB" in t:
        return "BYTEA"
    elif "REAL" in t or "FLOA" in t or "DOUB" in t:
        return "REAL"
    elif "NUM" in t or "DEC" in t:
        return "NUMERIC"
    else:
        return "TEXT"

def migrate():
    # Conexiones
    sqlite_conn = sqlite3.connect(SQLITE_FILE)
    sqlite_cursor = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(POSTGRES_URL)
    pg_cursor = pg_conn.cursor()

    # Obtener todas las tablas SQLite
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in sqlite_cursor.fetchall()]
    print(f"Tablas encontradas: {tables}")

    for table in tables:
        print(f"\nMigrando tabla '{table}'")

        # Obtener columnas de SQLite
        sqlite_cursor.execute(f"PRAGMA table_info({table})")
        cols = sqlite_cursor.fetchall()  # (cid, name, type, notnull, dflt_value, pk)

        # Construir definición columnas para PostgreSQL
        col_defs = []
        for col in cols:
            name = col[1]
            typ = map_sqlite_type_to_postgres(col[2])
            notnull = "NOT NULL" if col[3] else ""
            default = f"DEFAULT {col[4]}" if col[4] is not None else ""
            pk = "PRIMARY KEY" if col[5] else ""
            col_def = f'"{name}" {typ} {notnull} {default} {pk}'.strip()
            col_defs.append(col_def)

        create_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)});'

        # Borrar tabla si existe y crear nueva
        pg_cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
        pg_cursor.execute(create_sql)
        pg_conn.commit()
        print(f"Tabla '{table}' creada.")

        # Insertar datos
        sqlite_cursor.execute(f"SELECT * FROM {table}")
        rows = sqlite_cursor.fetchall()
        if rows:
            col_names = [desc[0] for desc in sqlite_cursor.description]
            columns_str = ", ".join([f'"{c}"' for c in col_names])
            insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table),
                sql.SQL(columns_str),
                sql.SQL(", ").join(sql.Placeholder() * len(col_names))
            )
            for row in rows:
                pg_cursor.execute(insert_sql, row)
            pg_conn.commit()
            print(f"Insertados {len(rows)} registros en '{table}'.")
        else:
            print(f"No hay datos para insertar en '{table}'.")

    # Cerrar conexiones
    sqlite_conn.close()
    pg_conn.close()
    print("\n✅ Migración completada con éxito.")

if __name__ == "__main__":
    migrate()