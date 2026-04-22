"""
Migrate data from local PostgreSQL to Railway PostgreSQL
Copies all tables and data from source to destination database
"""

import os
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

load_dotenv()

# Source database (local)
SOURCE_DB = f"postgresql://postgres:{os.getenv('DB_PASSWORD', '1425')}@localhost:5432/occashare"

# Destination database (Railway)
DEST_DB = f"postgresql://occashare_user:mypassword@192.168.1.100:5432/occashare"

def migrate_data():
    """Copy all data from source to destination database"""
    
    try:
        print("🔄 Starting data migration...")
        
        # Connect to both databases
        source_engine = create_engine(SOURCE_DB)
        dest_engine = create_engine(DEST_DB)
        
        source_conn = source_engine.connect()
        dest_conn = dest_engine.connect()
        
        # Get list of all tables
        inspector = inspect(source_engine)
        tables = inspector.get_table_names()
        
        print(f"📊 Found {len(tables)} tables to migrate")
        
        for table in tables:
            print(f"\n  Migrating table: {table}")
            
            try:
                # Get table schema
                create_table_sql = f"""
                    SELECT table_name, column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """
                
                # Copy data
                copy_sql = f"SELECT * FROM {table}"
                result = source_conn.execute(text(copy_sql))
                rows = result.fetchall()
                
                if rows:
                    # Get column names
                    columns = [col for col in result.keys()]
                    col_str = ", ".join(columns)
                    
                    # Insert into destination
                    for row in rows:
                        placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
                        insert_sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                        
                        try:
                            dest_conn.execute(text(insert_sql), dict(zip(columns, row)))
                        except Exception as e:
                            print(f"    ⚠️  Warning on row: {e}")
                    
                    dest_conn.commit()
                    print(f"    ✓ Migrated {len(rows)} rows")
                else:
                    print(f"    - No data to migrate")
                    
            except Exception as e:
                print(f"    ✗ Error migrating {table}: {str(e)}")
                dest_conn.rollback()
        
        source_conn.close()
        dest_conn.close()
        
        print("\n✅ Data migration completed!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Verify connections before starting
    print("🔍 Checking database connections...")
    try:
        source_engine = create_engine(SOURCE_DB)
        source_engine.connect().close()
        print("✓ Local database connection OK")
    except Exception as e:
        print(f"✗ Local database error: {e}")
        exit(1)
    
    try:
        dest_engine = create_engine(DEST_DB)
        dest_engine.connect().close()
        print("✓ Railway database connection OK")
    except Exception as e:
        print(f"✗ Railway database error: {e}")
        exit(1)
    
    # Start migration
    migrate_data()
