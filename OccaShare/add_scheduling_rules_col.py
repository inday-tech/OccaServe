import logging
from sqlalchemy import text
from app.db.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_scheduling_rules():
    logger.info("Adding scheduling_rules to caterer_profiles...")
    try:
        with engine.begin() as conn:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='caterer_profiles' AND column_name='scheduling_rules';
            """))
            if not result.scalar():
                conn.execute(text("""
                    ALTER TABLE caterer_profiles 
                    ADD COLUMN scheduling_rules JSONB DEFAULT '{
                        "business_hours": {"open_time": "08:00", "close_time": "20:00"},
                        "food_rules": {"delivery_available": true, "pickup_available": true, "delivery_start": "09:00", "delivery_end": "19:00", "lead_time_hours": 24, "allow_same_day": false},
                        "equipment_rules": {"pickup_start": "08:00", "pickup_end": "18:00", "return_start": "08:00", "return_end": "18:00", "min_rental_hours": 24, "max_rental_hours": 72},
                        "service_rules": {"min_duration_hours": 3, "max_duration_hours": 8, "earliest_start": "08:00", "latest_end": "22:00"},
                        "package_rules": {"min_event_duration": 4, "max_event_duration": 6, "setup_time_hours": 2, "cleanup_time_hours": 1}
                    }'::jsonb;
                """))
                logger.info("Successfully added scheduling_rules column!")
            else:
                logger.info("scheduling_rules column already exists.")
    except Exception as e:
        logger.error(f"Migration error: {e}")

if __name__ == "__main__":
    add_scheduling_rules()
