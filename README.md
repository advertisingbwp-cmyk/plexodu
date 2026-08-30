# SMTAS — Social Media Trend Analysis System

Final Year Project — Software Design based on `SDD_Social_media_trend_analysis__final.pdf`
and `SRS_Document_Social_media_trend_analysis__final.pdf`.

This is a **complete, runnable** implementation: Flask backend + HTML/CSS/JS dashboard +
SQLite database + NLP sentiment engine + PDF report generator.

## Live YouTube Data (Real API Key Setup)

YouTube now uses the **real YouTube Data API v3** (`backend/services/real_api.py`).
TikTok still uses mock data (`backend/services/mock_api.py`) until a TikTok
Research API key is available — swapping it in later is the same one-line-import
process described below, which matches the "Modular Connector" rationale in
SDD Section 3.3.

### ⚠️ Important security note
Never paste an API key directly into a chat, screenshot, or commit it to GitHub.
If a key has ever been shared in plaintext anywhere, treat it as compromised and
regenerate a new one from Google Cloud Console
(APIs & Services → Credentials → your key → Regenerate Key).

### Setup
1. Copy the template file and rename it:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and paste your (regenerated) key:
   ```
   YOUTUBE_API_KEY=your_real_key_here
   ```
3. That's it — `app.py` loads this automatically on startup via `python-dotenv`.
   `.env` is already listed in `.gitignore`, so it will never be pushed to GitHub.

### Deploying with the real key (Render.com)
Do **not** put the real key inside `render.yaml` (that file is meant to be public
in your repo). Instead add it in the Render dashboard:
your service → **Environment** tab → **Add Environment Variable** →
Key: `YOUTUBE_API_KEY`, Value: your real key → Save.

### A note on the growth chart with real data
The YouTube API only returns a video's *current* total views/likes/comments — it
doesn't give a historical day-by-day breakdown for free. `real_api.py` estimates a
realistic daily growth curve from the real current totals (clearly commented in
the code as an estimate). For a true historical record, the system would need a
scheduled background job that snapshots each tracked video daily (matches the
"unattended mode" in SRS Section 2.1.1) — a good "Future Enhancement" point for
your report/viva if asked.

### Getting a TikTok key later
Once you have TikTok Research API access, add a `fetch_tiktok_data(keyword)`
function to `real_api.py` (same JSON shape as `mock_api.py`'s version) and change
one import line in `app.py`:
```python
from services.mock_api import fetch_tiktok_data
# becomes
from services.real_api import fetch_tiktok_data
```

---

## Project Structure

```
SMTAS/
├── backend/
│   ├── app.py                  # Flask routes (Controller)
│   ├── models.py                # SQLAlchemy models (Model)
│   ├── services/
│   │   ├── mock_api.py          # Simulated YouTube/TikTok connector
│   │   ├── nlp_engine.py        # Sentiment analysis (TextBlob)
│   │   ├── trend_engine.py      # Virality Index + growth rate
│   │   └── report_generator.py  # PDF export (ReportLab)
│   ├── exports/                 # Generated PDF reports land here
│   └── smtas.db                 # Auto-created SQLite database
├── frontend/
│   ├── index.html                # Login / Register page
│   ├── dashboard.html             # Main analytical dashboard
│   ├── css/style.css
│   └── js/ (login.js, dashboard.js)
├── database/
│   └── schema.sql                # Reference MySQL-compatible schema
└── requirements.txt
```

## Requirements Traceability (matches SDD Section 7)

| SRS Req. | Feature                  | Where it's implemented                          |
|----------|---------------------------|--------------------------------------------------|
| FR-01    | User Authentication       | `app.py` → `/api/login`, `/api/register`         |
| FR-02    | Data Acquisition           | `services/mock_api.py` → `/api/search`           |
| FR-03    | Sentiment Analysis         | `services/nlp_engine.py`                         |
| FR-04    | Trend Ranking               | `services/trend_engine.py`                       |
| FR-05    | Data Visualization          | `dashboard.html` + Chart.js                       |
| FR-06    | Report Generation           | `services/report_generator.py` → `/api/report/<id>` |
| FR-07    | Historical Archiving         | SQLite tables: `trends`, `metrics`, `sentiment`   |

---

## How to Run (Step by Step)

### 1. Install Python 3.10+
Check with: `python3 --version`

### 2. Install dependencies
```bash
cd SMTAS
pip install -r requirements.txt
```

### 3. Run the backend
```bash
cd backend
python app.py
```
You should see:
```
SMTAS backend running at http://127.0.0.1:5000
```
The backend also **serves the frontend automatically** — you don't need a separate server.

### 4. Open the app
Go to: **http://127.0.0.1:5000/**

- Create an account (Register)
- Login
- Type a hashtag/keyword (e.g. `#ArtificialIntelligence`), pick YouTube/TikTok, click **Analyze**
- View sentiment pie chart, growth line chart, virality index
- Click **Export PDF** to download a formatted report
- Your searches are saved automatically — visible in "Recent Trend Searches"

### 5. Database
SQLite database (`backend/smtas.db`) is created automatically on first run — no manual
setup needed. If your supervisor requires MySQL specifically (as named in the SRS/SDD),
run `database/schema.sql` on a MySQL 8.0+ server and change one line in `app.py`:
```python
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://user:password@localhost/smtas"
```
(also add `pymysql` to requirements.txt)

---

## Deploying Online (Render.com — Free Tier)

Vercel and Netlify are serverless/static platforms — they don't support a stateful
Flask app with a persistent SQLite database and disk-saved PDF files well. This
project is pre-configured for **Render.com**, which runs Flask as a normal server
with a real persistent disk, so nothing above needs to change.

### Step 1 — Push this project to GitHub
```bash
cd SMTAS
git init
git add .
git commit -m "SMTAS - initial commit"
```
Create a new repository on GitHub (github.com → New Repository), then:
```bash
git remote add origin https://github.com/<your-username>/SMTAS.git
git branch -M main
git push -u origin main
```

### Step 2 — Create a Render account
Go to **https://render.com** → Sign up (free, can use GitHub login directly).

### Step 3 — Create a new "Blueprint" deployment
1. In the Render dashboard, click **New +** → **Blueprint**
2. Connect your GitHub account and select the `SMTAS` repository
3. Render will automatically detect the `render.yaml` file in this project and
   configure everything: build command, start command, environment variables,
   and the persistent disk — you don't need to type anything manually
4. Click **Apply** / **Create**

### Step 4 — Wait for the build
Render will:
- Install everything in `requirements.txt`
- Start the app with `gunicorn` (production-grade server, not Flask's dev server)
- Mount a persistent 1GB disk at `/var/data` so your SQLite database and
  exported PDFs survive restarts and redeploys

This takes about 2–4 minutes the first time.

### Step 5 — Open your live link
Render gives you a public URL like:
```
https://smtas.onrender.com
```
Open it — you'll see the same login page, and everything (register, search,
charts, PDF export) works exactly like it does locally.

### Notes on the Free Tier
- Free web services on Render **sleep after 15 minutes of inactivity** and take
  ~30–50 seconds to "wake up" on the next visit. This is fine for a demo/viva —
  just open the link a minute or two before you need it.
- The free persistent disk (1GB) is more than enough for this project.

### If you'd rather not use `render.yaml`
You can also set it up manually in the Render dashboard without Blueprints:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `cd backend && gunicorn app:app --bind 0.0.0.0:$PORT`
- **Environment Variables:** `SECRET_KEY` (any random string), `DATA_DIR=/var/data`
- **Add a Disk:** mount path `/var/data`, size 1GB

---

## Next Steps for Your FYP Submission

1. **Get real API access**: Apply for a YouTube Data API v3 key (Google Cloud Console —
   free tier) and TikTok Research API access (TikTok for Developers). YouTube's key is
   usually approved instantly; TikTok Research API requires an academic/research
   application form.
2. **Write `real_api.py`** once you have the keys (I can help you write this the moment
   you have them — the mock module is structured so it's a drop-in swap).
3. **Screenshots for your report**: run the app and take screenshots of the login page,
   dashboard, and PDF report — these can go directly into your SDD Section 6 (Human
   Interface Design) and your final defense slides.
4. **Deployment (optional)**: for demo day, this can be deployed on Render/PythonAnywhere
   for a live link, or just run locally during your viva.

If you'd like, next I can also generate the **presentation slides (PPTX)** for your
defense, or a **project report (DOCX)** combining the SRS + SDD + implementation
screenshots.
