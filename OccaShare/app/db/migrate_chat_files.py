from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL, engine
from app.db.models import Base

def migrate():
    # 1. Create any new tables (though none new here, just columns)
    print("Ensuring tables are up to date...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Add new columns to 'chat_messages' table
    with engine.connect() as conn:
        print("Adding file columns to 'chat_messages'...")
        
        # message_type
        try:
            conn.execute(text("ALTER TABLE chat_messages ADD COLUMN message_type VARCHAR DEFAULT 'text';"))
            conn.commit()
            print("Successfully added 'message_type'.")
        except Exception as e:
            print(f"Skipping 'message_type': {e}")
            conn.rollback()

        # file_url
        try:
            conn.execute(text("ALTER TABLE chat_messages ADD COLUMN file_url VARCHAR;"))
            conn.commit()
            print("Successfully added 'file_url'.")
        except Exception as e:
            print(f"Skipping 'file_url': {e}")
            conn.rollback()

        # file_name
        try:
            conn.execute(text("ALTER TABLE chat_messages ADD COLUMN file_name VARCHAR;"))
            conn.commit()
            print("Successfully added 'file_name'.")
        except Exception as e:
            print(f"Skipping 'file_name': {e}")
            conn.rollback()

        # Allow content to be nullable (since a message can be just a file)
        try:
            conn.execute(text("ALTER TABLE chat_messages ALTER COLUMN content DROP NOT NULL;"))
            conn.commit()
            print("Successfully made 'content' nullable.")
        except Exception as e:
            print(f"Skipping NULL adjustment: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
