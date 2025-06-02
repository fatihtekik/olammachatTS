import sqlite3
import os
import sys

def view_sqlite_db(db_path):
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in the database.")
            conn.close()
            return
            
        print(f"\nDatabase: {db_path}")
        print("\nTables found:")
        for table in tables:
            table_name = table[0]
            print(f"\n--- Table: {table_name} ---")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print("\nSchema:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
                
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"\nRow count: {count}")
            
            # Show sample data (max 5 rows)
            if count > 0:
                print("\nSample data:")
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                rows = cursor.fetchall()
                for row in rows:
                    print(f"  {row}")
                    
        conn.close()
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

if __name__ == "__main__":
    # Try the database in the backend directory first
    db_path = os.path.join("backend", "ollamachat.db")
    if not os.path.exists(db_path):
        # Try the database in the current directory
        db_path = "ollamachat.db"
    
    if len(sys.argv) > 1:
        # If path is provided as command line argument
        db_path = sys.argv[1]
    
    view_sqlite_db(db_path)
