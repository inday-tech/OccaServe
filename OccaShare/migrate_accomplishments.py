import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Creating 'accomplishments' table...")
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS accomplishments (
            id SERIAL PRIMARY KEY,
            caterer_id INTEGER REFERENCES caterer_profiles(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            content TEXT,
            image_url VARCHAR(255),
            is_public BOOLEAN DEFAULT TRUE,
            is_featured BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        try:
            cur.execute(create_table_query)
            conn.commit()
            print("Successfully created 'accomplishments' table.")
        except Exception as e:
            conn.rollback()
            print(f"Error creating table: {e}")
            
        cur.close()
        conn.close()
        print("Migration complete.")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    migrate()
