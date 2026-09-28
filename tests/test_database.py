"""
Phase 1 Database Architecture & Ingestion Test Suite (Two-Dataset Edition).
Tests schema creation, 3NF ingestion row counts for BLS and Pew datasets,
referential integrity, and ON DELETE RESTRICT foreign key enforcement.
"""
import unittest
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, text, event
from sqlalchemy.exc import IntegrityError

from src.database.ingest_data import create_schema, ingest_all_data

class TestDatabaseArchitecture(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()
        
        self.engine = create_engine(f"sqlite:///{self.temp_db_path}")
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    def tearDown(self):
        self.engine.dispose()
        Path(self.temp_db_path).unlink(missing_ok=True)

    def test_schema_creation_and_ingestion_counts(self):
        """Validates that schema creates cleanly and ingestion produces exact expected row counts."""
        counts = ingest_all_data(self.engine)
        self.assertEqual(counts["dim_naics_sectors"], 20)  # the 20 NAICS sectors
        self.assertEqual(counts["fact_industry_exposure"], 337)
        self.assertEqual(counts["dim_demographics"], 11)
        self.assertEqual(counts["dim_ai_use_cases"], 5)
        self.assertEqual(counts["fact_pew_survey_responses"], 55)  # 5 use cases x 11 cohorts
        self.assertEqual(counts["fact_pew_hiring_vs_humans"], 11)

    def test_referential_integrity_no_orphans(self):
        """Validates zero orphaned foreign keys across all fact tables."""
        ingest_all_data(self.engine)
        with self.engine.connect() as conn:
            # Check 1: industry exposure -> sector
            orphan_ind = conn.execute(text("""
                SELECT COUNT(*) FROM fact_industry_exposure f
                LEFT JOIN dim_naics_sectors d ON f.parent_sector_code = d.sector_code
                WHERE d.sector_code IS NULL
            """)).scalar()
            self.assertEqual(orphan_ind, 0, "Found orphaned parent_sector_code in fact_industry_exposure")

            # Check 2: pew survey -> use cases
            orphan_case = conn.execute(text("""
                SELECT COUNT(*) FROM fact_pew_survey_responses f
                LEFT JOIN dim_ai_use_cases d ON f.use_case_id = d.use_case_id
                WHERE d.use_case_id IS NULL
            """)).scalar()
            self.assertEqual(orphan_case, 0, "Found orphaned use_case_id in fact_pew_survey_responses")

            # Check 3: pew survey -> demographics
            orphan_demo = conn.execute(text("""
                SELECT COUNT(*) FROM fact_pew_survey_responses f
                LEFT JOIN dim_demographics d ON f.demographic_id = d.demographic_id
                WHERE d.demographic_id IS NULL
            """)).scalar()
            self.assertEqual(orphan_demo, 0, "Found orphaned demographic_id in fact_pew_survey_responses")

    def test_foreign_key_on_delete_restrict(self):
        """Validates that deleting a referenced parent record raises an IntegrityError under ON DELETE RESTRICT."""
        ingest_all_data(self.engine)
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as conn:
                conn.execute(text("DELETE FROM dim_naics_sectors WHERE sector_code = '11'"))

    def test_dashboard_renders_on_sqlite(self):
        """The full page must build on the SQLite fallback (guards against MySQL-only SQL)."""
        from src.database import connection
        from src.ui.editorial_renderer import build_editorial_html
        ingest_all_data(self.engine)
        saved = connection._ENGINE, connection._DB_TYPE
        connection._ENGINE, connection._DB_TYPE = self.engine, "sqlite"
        try:
            html = build_editorial_html()
        finally:
            connection._ENGINE, connection._DB_TYPE = saved
        self.assertIn("SQLITE", html)
        self.assertNotIn("Art. 50", html)
        self.assertNotIn("135.5M", html)

if __name__ == "__main__":
    unittest.main()
