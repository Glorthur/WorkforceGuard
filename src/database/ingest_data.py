"""
Database Ingestion Pipeline for WorkforceGuard (Two-Dataset Edition).
Loads cleaned 3NF tables from the TWO real empirical datasets into MySQL or SQLite fallback.
Enforces dependency ordering: dimensions first, facts second.
"""
from pathlib import Path
from sqlalchemy import text
from src.database.connection import get_engine, get_db_type
from src.data_pipeline.cleaner import clean_and_normalize_datasets

SCHEMA_PATH = Path(__file__).resolve().parents[0] / "schema_3nf.sql"

def create_schema(engine):
    """(Re)creates the 3NF schema in the target database from the canonical DDL."""
    ddl_content = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [stmt.strip() for stmt in ddl_content.split(";") if stmt.strip()]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

def ingest_all_data(engine=None):
    """
    Performs full 3NF ingestion of the TWO real datasets and returns row counts.
    Ensures referential integrity by clearing and loading in strict dependency order.
    """
    if engine is None:
        engine = get_engine()

    create_schema(engine)

    # Always rebuild processed tables from raw (milliseconds), so they never go stale.
    # The dict is in dependency order: each dimension precedes the facts that reference it.
    tables = clean_and_normalize_datasets()

    # Tables are freshly created above; load in one transaction so a failure never
    # leaves a half-loaded database.
    with engine.begin() as conn:
        for name, table in tables.items():
            table.to_sql(name, conn, if_exists="append", index=False)

    # Verify row counts and referential integrity
    with engine.connect() as conn:
        counts = {name: conn.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar() for name in tables}

        # Verify zero orphaned foreign keys
        orphan_industries = conn.execute(text("""
            SELECT COUNT(*) FROM fact_industry_exposure f
            LEFT JOIN dim_naics_sectors d ON f.parent_sector_code = d.sector_code
            WHERE d.sector_code IS NULL
        """)).scalar()
        if orphan_industries > 0:
            raise ValueError(f"Referential integrity failure: {orphan_industries} orphaned industry records.")

        orphan_survey_cases = conn.execute(text("""
            SELECT COUNT(*) FROM fact_pew_survey_responses f
            LEFT JOIN dim_ai_use_cases d ON f.use_case_id = d.use_case_id
            WHERE d.use_case_id IS NULL
        """)).scalar()
        if orphan_survey_cases > 0:
            raise ValueError(f"Referential integrity failure: {orphan_survey_cases} orphaned survey use-cases.")

        orphan_survey_demos = conn.execute(text("""
            SELECT COUNT(*) FROM fact_pew_survey_responses f
            LEFT JOIN dim_demographics d ON f.demographic_id = d.demographic_id
            WHERE d.demographic_id IS NULL
        """)).scalar()
        if orphan_survey_demos > 0:
            raise ValueError(f"Referential integrity failure: {orphan_survey_demos} orphaned survey demographics.")

    return counts

if __name__ == "__main__":
    eng = get_engine()
    print(f"Ingesting into {get_db_type().upper()}...")
    results = ingest_all_data(eng)
    print("Ingestion complete! Verified row counts for the TWO real datasets:")
    for tbl, count in results.items():
        print(f"  - {tbl}: {count} rows")
