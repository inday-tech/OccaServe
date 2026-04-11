import logging
from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_kyc_columns():
    """
    Safely adds missing columns to the identity_verifications table.
    """
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    # List of columns to check and add
    # Format: (column_name, column_type)
    columns_to_add = [
        ("id_number", "VARCHAR"),
        ("selfie_2_url", "VARCHAR"),
        ("selfie_3_url", "VARCHAR"),
        ("failure_reason", "TEXT"),
        ("fraud_score", "INTEGER DEFAULT 0"),
        ("ip_address", "VARCHAR"),
        ("device_info", "JSONB"),
        ("liveness_status", "VARCHAR"),
        ("verified_at", "TIMESTAMPTZ")
    ]
    
    with engine.connect() as conn:
        logger.info("Starting KYC schema migration...")
        
        for col_name, col_type in columns_to_add:
            try:
                # Check if column exists
                check_query = text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='identity_verifications' AND column_name='{col_name}';
                """)
                result = conn.execute(check_query).fetchone()
                
                if not result:
                    logger.info(f"Adding column '{col_name}' to 'identity_verifications'...")
                    conn.execute(text(f"ALTER TABLE identity_verifications ADD COLUMN {col_name} {col_type};"))
                    conn.commit()
                    logger.info(f"Successfully added '{col_name}'.")
                else:
                    logger.info(f"Column '{col_name}' already exists.")
                    
            except Exception as e:
                logger.error(f"Error adding column '{col_name}': {e}")
                conn.rollback()
        
        logger.info("KYC schema migration completed.")

def fix_not_null_constraints():
    """
    Removes NOT NULL constraints from document_url and selfie_url.
    """
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        logger.info("Dropping NOT NULL constraints on KYC columns...")
        try:
            conn.execute(text("ALTER TABLE identity_verifications ALTER COLUMN document_url DROP NOT NULL;"))
            conn.execute(text("ALTER TABLE identity_verifications ALTER COLUMN selfie_url DROP NOT NULL;"))
            conn.commit()
            logger.info("Successfully removed NOT NULL constraints.")
        except Exception as e:
            logger.error(f"Error dropping constraints: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate_kyc_columns()
    fix_not_null_constraints()
