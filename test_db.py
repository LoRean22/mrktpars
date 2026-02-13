from core.db.connection import get_connection

conn = get_connection()
print("✅ MySQL подключён успешно")
conn.close()
