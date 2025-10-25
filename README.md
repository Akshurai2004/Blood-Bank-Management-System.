
## 🩸 Blood Bank Management System
### 1️⃣ Setup Database
````markdown

A full-stack Blood Bank Management System using **FastAPI**, **React**, and **MySQL**.

---
### ⚙️ Setup Instructions



Import the provided SQL file to initialize your database and tables:

```bash
mysql -u root -p < database/blood_bank_management.sql
````

---

### 2️⃣ Setup Backend

Navigate to the backend directory and install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Edit `blood_bank_fastapi.py` with your MySQL credentials.

Start the FastAPI backend server:

```bash
python blood_bank_fastapi.py &
```

---

### 3️⃣ Setup Frontend

Open a terminal, navigate to the frontend folder, install dependencies, and start the React app:

```bash
cd ../frontend
npm install
npm start
```

The app runs at [http://localhost:3000](http://localhost:3000).

---

## 🧩 Tech Stack

* **Frontend:** React.js
* **Backend:** FastAPI
* **Database:** MySQL

```
```
