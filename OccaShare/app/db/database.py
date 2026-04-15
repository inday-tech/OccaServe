import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# load_dotenv() will NOT overwrite existing environment variables by default
load_dotenv(override=True)

# Check for various cloud environment indicators
IS_CLOUD = any(os.getenv(key) for key in ["RAILWAY_PROJECT_ID", "RENDER", "PORT"])

# Primary connection string
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    if IS_CLOUD:
        print("CRITICAL: Running in a cloud environment but DATABASE_URL is missing!")
        print("Please ensure you have set the DATABASE_URL variable in your Dashboard.")
    
    # Fallback to local development components
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"
else:
    # Ensure compatible prefix
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Summary of target (redacted password)
target_log = SQLALCHEMY_DATABASE_URL.split("@")[-1] if "@" in SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL
print(f"DATABASE CONNECTION TARGET: {target_log}")

# Create engine with connection pooling for production stability
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
