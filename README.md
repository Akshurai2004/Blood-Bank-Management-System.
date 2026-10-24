# Blood Bank Management System

## Local start

Requirements:

- Docker Desktop
- Python 3.11+
- Node.js

### 1. Start PostgreSQL and Redis

```powershell
docker start bloodbank-postgres bloodbank-redis
```

If the containers do not exist yet:

```powershell
docker volume create bloodbank-postgres-data
docker run -d --name bloodbank-postgres `
  -e POSTGRES_USER=bloodbank_app `
  -e POSTGRES_PASSWORD=bloodbank_dev_password `
  -e POSTGRES_DB=bloodbank `
  -p 5432:5432 `
  -v bloodbank-postgres-data:/var/lib/postgresql/data `
  -v "${PWD}\render.sql:/docker-entrypoint-initdb.d/01-schema.sql:ro" `
  postgres:16-alpine

docker run -d --name bloodbank-redis -p 6379:6379 redis:7-alpine
```

### 2. Start the backend

```powershell
python -m uvicorn backend.blood_bank_fastapi:app --host 127.0.0.1 --port 8000
```

Backend:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/api/health
```

### 3. Start the frontend

Open another terminal:

```powershell
Set-Location frontend
npm start
```

Frontend:

```text
http://localhost:3000
```

## Demo login

```text
Email: admin@bloodbank.org
Password: Admin@123
```

## Stop local services

```powershell
docker stop bloodbank-postgres bloodbank-redis
```
