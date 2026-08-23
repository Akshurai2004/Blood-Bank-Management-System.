# Blood Bank Management & Emergency Allocation System

An enterprise-grade, full-stack Healthcare and Blood Inventory Management platform built with **FastAPI**, **React 18**, **MySQL 8.0**, **Redis 7.0**, **Nginx**, and **Docker Compose**. Features Role-Based Access Control (RBAC), real Email OTP authentication via SMTP, JWT route guards, an asynchronous emergency message queue, real-time donor eligibility computation, live OpenStreetMap geolocation matching, and multi-hospital emergency blood allocation workflows.

---

## 🌐 1-Click Live Public Deployment & Mobile Access

You can make your entire local Docker stack accessible over a secure **HTTPS public link** on mobile phones, tablets, or computers anywhere in the world.

### How to Launch:
1. Double-click **`start_public.bat`** (or run `python tunnel_launcher.py`).
2. The script will:
   * Spin up all Docker containers (`db`, `redis`, `backend`, `frontend`).
   * Provision a secure Cloudflare HTTPS tunnel.
   * **Automatically copy the live public link to your Windows clipboard**.
   * Render an **ASCII QR Code** directly in the terminal for instant phone camera scanning.
3. Keep the terminal window open in the background while using the system.

> [!NOTE]
> **Understanding Public URLs**:
> * **During the active session:** The generated URL remains active continuously as long as the terminal window stays open.
> * **On fresh restarts:** The free anonymous quick tunnel generates a new unique domain (`https://*.trycloudflare.com`) on each launch to prevent naming collisions and abuse. Simply scan the freshly rendered QR code or paste the auto-copied link from your clipboard.

---

## 🏛️ Architecture and Microservices

```
                           +-------------------------------------+
                           |         Cloudflare Public SSL       |
                           |   (HTTPS Tunnel / Mobile / Web)     |
                           +------------------+------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |            Nginx (Port 3000)        |
                           |  - Serves React 18 Single Page App  |
                           |  - Reverse-proxies /api to FastAPI  |
                           +------------------+------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |        FastAPI Backend (Port 8000)  |
                           |  - RESTful APIs & Pydantic Schemas  |
                           |  - JWT Auth Guard & RBAC Middleware |
                           |  - Haversine Geospatial Matcher     |
                           +--------+------------------+---------+
                                    |                  |
                   +----------------+                  +----------------+
                   |                                                    |
                   v                                                    v
+------------------------------------+               +------------------------------------+
|         MySQL 8.0 (Port 3307)      |               |          Redis 7.0 (Port 6379)     |
| - 3NF Relational Database Schema   |               | - Emergency Message Queue          |
| - Stored Procedures & Triggers     |               | - OTP Verification Store with TTL  |
| - Stored Functions & Views         |               | - Real-Time Event Dispatch Broker  |
+------------------------------------+               +------------------------------------+
```

---

## ✨ Key Features

### 1. Live Geolocation & Network Map
* **Interactive Map Visualization:** OpenStreetMap Leaflet canvas rendering registered donors, emergency blood requests, and regional blood bank repositories.
* **Proximity & Compatibility Match Engine:** Clicking any emergency blood request computes Haversine geographic distances (in kilometers) to compatible donors based on the standard ABO/Rh blood compatibility matrix, calculates estimated travel times, and draws proximity routes.
* **Filter and Search:** Filter by entity layers, blood groups (A+, A-, B+, B-, AB+, AB-, O+, O-), request urgency, and text search.
* **GPS Device Locator:** Real-time device geolocation via the HTML5 Geolocation API.

### 2. Email OTP Authentication and Role-Based Access Control
* **Email OTP Verification:** Secure 6-digit numeric OTP delivered directly to user inboxes via SMTP. OTPs expire after 10 minutes with rate limiting and TTL in Redis.
* **Password & OTP Sign-In:** Users can sign in using password authentication or request single-use email verification codes.
* **Role-Based Authorization:** Strict route guards and session management for four distinct roles:
  * **Donor:** Personal dashboard, digital donor pass, donation history, and automated 56-day cooldown eligibility checker.
  * **Hospital:** Emergency blood request creation, patient registry, and real-time fulfillment tracking.
  * **Blood Bank Admin:** Inventory telemetry across all 8 blood groups and 4 components (Whole Blood, RBC, Plasma, Platelets), stored-procedure-driven donation intake (`RecordBloodDonation`), and unit-level allocation engine.
  * **SuperAdmin:** System-wide management, hospital/bank onboarding, and operational statistics.

### 3. Asynchronous Emergency Message Queue
* **Decoupled Notification Pipeline:** Emergency requests are enqueued into Redis (`bb:emergency_queue`) and processed asynchronously without blocking HTTP client response times.
* **Eligibility Matching:** Automatically matches emergency requests with active, eligible donors within geographic proximity.
* **Queue Telemetry:** Live queue health and broadcast status accessible at `/api/notifications/queue-status`.

### 4. Relational Database Design & Integrity
* **3NF Normalized Schema:** Enforces strict referential integrity across Donors, Patients, Hospitals, Blood Banks, Blood Units, Requests, Allocations, and Users.
* **Stored Procedure (`RecordBloodDonation`):** Automates blood unit intake, calculates 42-day expiration dates, and links inventory records.
* **Stored Function (`CheckDonorEligibility`):** Dynamically computes whether a donor meets the mandatory 56-day interval between donations.
* **Triggers (`UpdateDonorStats`):** Automatically updates a donor's total donations and last donation date on new blood unit registration.
* **View (`AvailableBloodInventory`):** Aggregates unexpired, available blood units grouped by blood bank and blood group.

---

## 🔑 Default Pre-Seeded Accounts

| Role | Email | Password | Scope |
| :--- | :--- | :--- | :--- |
| **Blood Bank Admin** | `admin@bloodbank.org` | `Admin@123` | Full inventory, donor management, unit allocation |
| **Global Super Admin** | `superadmin@bloodbank.org` | `SuperAdmin@123` | System-wide audit, facility onboarding |
| **Donor** | `alice@example.com` | `Donor@123` | Donor portal, eligibility checker, donation history |
| **Hospital Staff** | `hospital@citycare.org` | `Hospital@123` | Emergency request creation, patient tracking |

*(You can also use the **Fast 1-Click Demo Sign-In** pills on the login screen for instant access).*

---

## 📧 SMTP Email Configuration

The system delivers real 6-digit OTP codes to user email addresses using standard SMTP (such as Gmail, Outlook, or Amazon SES).

### Gmail SMTP Setup:
1. Enable **2-Step Verification** on your Google Account.
2. Generate an **App Password** under Security > App Passwords.
3. Configure your `.env` file:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_character_app_password
SMTP_FROM=Blood Bank Management <your_email@gmail.com>
SMTP_USE_TLS=true
REQUIRE_REAL_EMAIL=true
```

### Test Email Delivery:
```powershell
python backend/email_service.py test your_email@gmail.com
```

---

## 🚀 Local Startup with Docker Compose

Run the entire multi-container stack with a single command:

```powershell
docker compose up --build -d
```

### Service Endpoints:
* **Frontend Web Application:** http://localhost:3000
* **Backend API & Interactive Swagger Docs:** http://localhost:8000/docs
* **Queue Telemetry Endpoint:** http://localhost:8000/api/notifications/queue-status

### Useful Docker Commands:
```powershell
# Check container health and status
docker compose ps

# Stream backend logs
docker compose logs -f backend

# Stream frontend/nginx logs
docker compose logs -f frontend

# Stop all services
docker compose down
```

---

## 🧪 Verification Test Suite

Run the automated end-to-end verification suite:

```powershell
python backend/verify_all.py
```

### Verified Test Cases:
* [x] MySQL Database Connection and Health
* [x] Real Email OTP Registration Lifecycle (Send > TTL Cache > Verify > JWT Issue)
* [x] Live Session Verification (`/api/auth/me`)
* [x] Email OTP Passwordless Login Lifecycle
* [x] Pre-Seeded Accounts Authentication
* [x] Donor Portal Data and 56-Day Cooldown Computation
* [x] Blood Bank Directory and Inventory Aggregation View
* [x] Stored Procedure Donation Intake (`RecordBloodDonation`) and Trigger Execution
* [x] Emergency Request Creation and Redis Message Queue Dispatch
* [x] Queue Telemetry and Broadcast Notification Status
* [x] Unit Allocation Engine and Compatibility Validation
* [x] Dashboard Operational Statistics and Analytics
* [x] Live Network Map Geolocation Data Payloads and Anchor Resolution

---

## 📁 Project Structure

```
bloodbank-management-system/
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules (protects secrets and binaries)
├── .dockerignore                    # Docker build ignore rules
├── docker-compose.yml               # Production multi-container definition
├── start_public.bat                 # 1-Click public HTTPS tunnel launcher with QR code
├── tunnel_launcher.py               # Tunnel manager, QR code generator & clipboard copier
├── main.py                          # Unified local runner
├── README.md                        # Project documentation
│
├── backend/
│   ├── blood_bank_backend.py        # MySQL database repository layer
│   ├── blood_bank_fastapi.py        # FastAPI REST API endpoints
│   ├── email_service.py             # SMTP email service & OTP handler
│   ├── queue_service.py             # Redis emergency message queue
│   ├── verify_all.py                # End-to-end verification test suite
│   ├── Dockerfile                   # Python 3.12 Slim Docker image
│   └── requirements.txt             # Backend dependencies
│
├── frontend/
│   ├── public/                      # Static assets and index.html
│   ├── src/
│   │   ├── App.js                   # Main application with dynamic tabs
│   │   ├── LiveNetworkMap.js        # Leaflet OpenStreetMap network component
│   │   ├── index.css                # Application styles and responsive design
│   │   └── index.js                 # React DOM entrypoint
│   ├── nginx.conf                   # Nginx reverse proxy configuration
│   ├── Dockerfile                   # Multi-stage frontend Docker build
│   └── package.json                 # Frontend dependencies
│
└── database/
    ├── blood_bank_management.sql     # Database schema, triggers, functions, procedures
    ├── seed_data.sql                # Initial seed data for facilities and inventory
    └── seed_auth.sql                # Pre-seeded test accounts
```

---

## 📜 License

Developed for the Blood Bank Management & Emergency Allocation System. Built with FastAPI, React, Leaflet, MySQL, Redis, and Docker.
