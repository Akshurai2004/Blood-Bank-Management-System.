## 🩸 Blood Bank Management System

A simple full-stack app using FastAPI (backend), React (frontend) and MySQL (database).

---

## Prerequisites

- Python 3.10+ with a virtual environment (recommended)
- Node.js and npm
- MySQL server (import the provided SQL file)

---

## 1. Initialize the database

Import the provided SQL to create the schema and seed data:

```bash
mysql -u root -p < database/blood_bank_management.sql
```

---

## 2. Backend

Install backend dependencies and set your DB credentials:

```powershell
cd backend
pip install -r requirements.txt
```

Edit `backend/blood_bank_fastapi.py` and set your MySQL password in DB_CONFIG or export the `DB_PASSWORD` environment variable before running. Example (PowerShell):

```powershell
$env:DB_PASSWORD = 'your_mysql_password'
```

To run the backend by itself:

```powershell
# (use your venv python if desired)
python -m uvicorn backend.blood_bank_fastapi:app --host 127.0.0.1 --port 8000 --reload
```

---

## 3. Frontend

Install and run the React app:

```bash
cd frontend
npm install
npm start
```

The frontend runs at http://localhost:3000 and proxies API calls to http://localhost:8000 by default.

---

## 4. Recommended: Run both with the launcher

Use the included `main.py` (project root) to start backend first, wait for the health check, then start the frontend so the React proxy won't fail:

```powershell
# Optional: activate your venv so the correct Python is used
# .\env\Scripts\Activate.ps1

python .\main.py
```

The launcher streams both processes' logs and exits if the backend fails to become healthy within 30 seconds.

---

## Troubleshooting

- Proxy ECONNREFUSED: means the frontend couldn't reach the backend. Use `python .\main.py` or start the backend before the frontend.
- npm not found: make sure Node.js/npm are installed and on PATH. Check with:

```powershell
where.exe npm
npm --version
node --version
```
- Port conflict: if port 8000 is in use, start the backend on another port and update `frontend/package.json`'s `proxy` accordingly.

---

## Tech stack

- Frontend: React
- Backend: FastAPI
- Database: MySQL


```
```
