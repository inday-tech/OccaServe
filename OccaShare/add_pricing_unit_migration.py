import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

async def add_pricing_unit():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set.")
        return

    # Adjust for SQLAlchemy async driver
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    print(f"Connecting to database...")
    engine = create_async_engine(database_url, echo=True)

    try:
        async with engine.begin() as conn:
            # Check if column exists first to avoid errors if it was already added
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='menu_items' AND column_name='pricing_unit'")
            )
            exists = result.scalar()
            
            if exists:
                print("Column 'pricing_unit' already exists in 'menu_items'.")
            else:
                print("Adding 'pricing_unit' column to 'menu_items'...")
                await conn.execute(text("ALTER TABLE menu_items ADD COLUMN pricing_unit VARCHAR DEFAULT 'pax'"))
                print("Successfully added 'pricing_unit' column.")
    except Exception as e:
        print(f"Error executing migration: {e}")
    finally:
        await engine.dispose()
        print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(add_pricing_unit())
