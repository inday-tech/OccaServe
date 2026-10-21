import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from app.db.database import engine

def migrate():
    with engine.connect() as conn:
        print("Migrating 'catering_packages': adding internal cost and expense breakdown columns...")

        # Columns introduced alongside internal_cost_per_pax that may not yet
        # exist in the database.  Each entry is (column_name, sql_type_with_default).
        columns = [
            ("internal_cost_per_pax",   "FLOAT DEFAULT 0.0"),
            ("base_pax",                "INTEGER DEFAULT 50"),
            ("labor_cost",              "FLOAT DEFAULT 0.0"),
            ("utility_cost",            "FLOAT DEFAULT 0.0"),
            ("equipment_cost",          "FLOAT DEFAULT 0.0"),
            ("ingredient_total_cost",   "FLOAT DEFAULT 0.0"),
            ("markup_type",             "VARCHAR DEFAULT 'percentage'"),
            ("markup_value",            "FLOAT DEFAULT 0.0"),
        ]

        for col_name, col_type in columns:
            try:
                conn.execute(
                    text(f"ALTER TABLE catering_packages ADD COLUMN {col_name} {col_type};")
                )
                conn.commit()
                print(f"  ✓ Added column: {col_name}")
            except Exception as e:
                conn.rollback()
                print(f"  – Skipped {col_name} (already exists or error): {e}")

        # Back-fill any NULLs that slipped through on pre-existing rows so that
        # application code relying on non-NULL defaults works correctly.
        backfill_statements = [
            "UPDATE catering_packages SET internal_cost_per_pax = 0.0  WHERE internal_cost_per_pax IS NULL;",
            "UPDATE catering_packages SET base_pax              = 50    WHERE base_pax              IS NULL;",
            "UPDATE catering_packages SET labor_cost            = 0.0   WHERE labor_cost            IS NULL;",
            "UPDATE catering_packages SET utility_cost          = 0.0   WHERE utility_cost          IS NULL;",
            "UPDATE catering_packages SET equipment_cost        = 0.0   WHERE equipment_cost        IS NULL;",
            "UPDATE catering_packages SET ingredient_total_cost = 0.0   WHERE ingredient_total_cost IS NULL;",
            "UPDATE catering_packages SET markup_type           = 'percentage' WHERE markup_type    IS NULL;",
            "UPDATE catering_packages SET markup_value          = 0.0   WHERE markup_value          IS NULL;",
        ]

        print("Back-filling NULL values for existing rows...")
        for stmt in backfill_statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"  – Back-fill warning: {e}")

        print("Migration complete.")

if __name__ == "__main__":
    migrate()
