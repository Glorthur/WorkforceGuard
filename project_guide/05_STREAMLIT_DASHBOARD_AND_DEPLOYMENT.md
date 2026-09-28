# Step 5: Streamlit Dashboard & Deployment Guide

This guide covers running your dashboard locally and deploying it for free via GitHub.

---

## 1. Running the Dashboard Locally

Make sure you are in the project directory when running the command:

```powershell
cd C:\Users\maame\.gemini\antigravity\scratch\workforce-ai-governance; python -m streamlit run app.py
```

By default the app uses **SQLite** at `data/workforce_ai.db`, built automatically from `data/raw/` on first run. To use MySQL instead, set the environment variable first (never write a real password into code or docs):

```powershell
$env:MYSQL_DATABASE_URL = "mysql+pymysql://<user>:<password>@localhost:3306/workforce_ai_governance"
```

If the variable is unset or MySQL is unreachable, the app falls back to SQLite.

### What You Will See:
Your browser opens to `http://localhost:8501`. `app.py` renders one editorial HTML page (`src/ui/editorial_renderer.py`) via `components.html(..., scrolling=True)`; the Streamlit sidebar and chrome are hidden. The page has four tabs:
* **01 · Exposure**:
  Live SQL Query 1: sector exposure ranking for 20 NAICS sectors (chart / table toggle), workforce by exposure tier (High ≥ 7.5, Moderate 5.5-7.5, Low < 5.5), and the most exposed large industries (250,000+ workers). The exposure score is an industry AI task-exposure score (0-10) whose source is not yet documented.
* **02 · Workforce trust**:
  Real Pew ATP Wave 119 microdata. KPIs for the final-hiring-decision item (7.1% favor, 70.9% oppose) and net skepticism (−31.4 pp); the cohort chart shows whether AI would do **better or worse than humans at treating all applicants the same way**, with ±MOE and n per cohort; and favor / oppose for the five use cases.
* **03 · EU AI Act**:
  Statutory classification of the five use cases (Annex III, point 4(a)/(b) and Art. 5(1)(f)) against public support, and the **"Obligations to evidence"** panel with PROVIDER / DEPLOYER badges. The dashboard reports no conformity status of its own.
* **04 · Provenance**:
  The 6-table 3NF directory with live row counts and the active database engine, the BLS hierarchy double-counting trap (180.5M every row summed vs **104.1M** each worker counted once), and the data quality gates.

---

## 2. Deploying on the Web (Free via GitHub)

### Why GitHub Pages (`glorthur.github.io`) cannot run Streamlit directly:
GitHub Pages only hosts static HTML/CSS files. Streamlit needs an active Python runtime to execute SQL queries.

### The Solution: Streamlit Community Cloud (Free)

1. **Push your code to GitHub**:
   ```powershell
   git add .
   git commit -m "WorkforceGuard: 2-dataset MySQL & Python edition"
   git push origin main
   ```
2. **Go to [share.streamlit.io](https://share.streamlit.io/)**:
   * Sign in with your GitHub account.
   * Click **New App**.
   * Select your repository and choose `app.py`.
   * Click **Deploy**!
3. **Your Live URL**:
   Streamlit will give you a free, public URL:
   `https://workforceguard-glorthur.streamlit.app`

### How It Handles the Database in the Cloud:
In the cloud, Streamlit cannot reach `localhost:3306` on your personal laptop.
Because of the **dual-mode design** in `connection.py`, the cloud app automatically falls back to **SQLite**: `*.db` files are git-ignored, so on first run the app builds `data/workforce_ai.db` from the CSVs in `data/raw/` — so those CSVs, including the two `pew_w119_*.csv` files, must be committed. No configuration is needed. Only if you want the cloud app to use a hosted MySQL server do you add a `MYSQL_DATABASE_URL` secret in the app's settings.

### Embedding on Your Portfolio (`glorthur.github.io`):
You can embed your live dashboard directly into your GitHub Pages website by adding this HTML snippet:

```html
<iframe 
    src="https://workforceguard-glorthur.streamlit.app" 
    width="100%" 
    height="850px" 
    style="border: none; border-radius: 8px;">
</iframe>
```

The page scrolls inside Streamlit's component iframe (`scrolling=True`). The old `postMessage` height-sync script was removed, because Streamlit only honours it for registered custom components.
