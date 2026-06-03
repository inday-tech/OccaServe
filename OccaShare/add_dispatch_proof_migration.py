import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

async def add_dispatch_proof():
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
            # Check if column exists first to avoid errors
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='bookings' AND column_name='dispatch_proof_url'")
            )
            exists = result.scalar()
            
            if exists:
                print("Column 'dispatch_proof_url' already exists in 'bookings'.")
            else:
                print("Adding 'dispatch_proof_url' column to 'bookings'...")
                await conn.execute(text("ALTER TABLE bookings ADD COLUMN dispatch_proof_url VARCHAR"))
                print("Successfully added 'dispatch_proof_url' column.")
    except Exception as e:
        print(f"Error executing migration: {e}")
    finally:
        await engine.dispose()
        print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(add_dispatch_proof())
