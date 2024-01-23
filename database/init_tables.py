import sqlite3 as sql3
con = sql3.connect("database/database.db")
cur = con.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS Users (username TEXT, password_hash TEXT)
            """)

con.commit()
con.close()