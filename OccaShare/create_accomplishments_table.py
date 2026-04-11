from app.db.database import engine, Base
from app.db.models import Accomplishment, CatererProfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    logger.info("Starting migration: Creating 'accomplishments' table...")
    try:
        # Create all tables that don't exist yet
        Base.metadata.create_all(bind=engine)
        logger.info("Successfully created 'accomplishments' table (if it didn't exist).")
    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
