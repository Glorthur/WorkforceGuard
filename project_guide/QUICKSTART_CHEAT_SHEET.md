# Quickstart Cheat Sheet

Keep this file handy whenever you want to test, run, or verify WorkforceGuard! Run every command from the project folder.

---

### 1. (Optional) Point the App at MySQL
Skip this step to use SQLite: `data/workforce_ai.db` is built automatically on first run.

To use MySQL, start the service (Administrator PowerShell) and set the connection string in the same terminal you will run the commands from:
```powershell
net start MySQL80
$env:MYSQL_DATABASE_URL = "mysql+pymysql://<user>:<password>@localhost:3306/workforce_ai_governance"
```
bash equivalent:
```bash
export MYSQL_DATABASE_URL="mysql+pymysql://<user>:<password>@localhost:3306/workforce_ai_governance"
```
Never put your real password in a file you commit.

---

### 2. (Only if the Pew zip changes) Rebuild the Pew Raw Files from W119 Microdata
Converts `data/W119_Dec22.zip` into `data/raw/pew_w119_workplace_ai.csv` (55 rows) and `data/raw/pew_w119_hiring_ai_vs_humans.csv` (11 rows). Needs `pyreadstat` for this step only:
```powershell
pip install pyreadstat
python -m src.data_pipeline.build_pew_w119
```

---

### 3. Run Data Cleaning & Normalization (Phase 0)
Decomposes the two datasets into 6 clean 3NF tables in `data/processed/` (ingestion also does this automatically):
```powershell
python -m src.data_pipeline.cleaner
```

---

### 4. Ingest Data into the Database (Phase 1)
Drops and recreates the 6 tables, foreign keys, and indexes, rebuilds the processed tables from raw, and loads them in one transaction (MySQL if configured, otherwise SQLite):
```powershell
python -m src.database.ingest_data
```

---

### 5. Run Educational SQL Queries from the Terminal (Phase 2)
Tests Query 1 (Sector exposure, counting only `counts_in_total = 1` rows), Query 2 (AI vs humans in hiring by cohort), and Query 4 (EU AI Act risk classifications):
```powershell
python -m src.database.queries
```

---

### 6. Run the Automated Test Suite (Phase 5)
Runs all 15 tests (analytics, data quality, database integrity, governance classifications, no-ML guard); `pytest.ini` points pytest at `tests/`:
```powershell
python -m pytest
```

---

### 7. Launch the Streamlit Interactive Dashboard (Phase 4)
Always run from inside the project folder:
```powershell
streamlit run app.py
```
Open your browser at: `http://localhost:8501`
