# PharmMedian — Closed-Loop Drug Return Platform

PharmMedian is an enterprise-grade, closed-loop pharmaceutical return and destruction platform designed to enforce regulatory compliance, eliminate supply chain leakages, detect re-entry fraud, and provide tamper-evident cryptographic auditability.

---

## 🏗 Repository Structure

```plaintext
pharmamedian/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── batches.py
│   │   │   ├── returns.py
│   │   │   ├── disputes.py
│   │   │   ├── destruction.py
│   │   │   ├── certificates.py
│   │   │   └── audit.py
│   │   ├── models/
│   │   │   └── schemas.py
│   │   ├── services/
│   │   │   ├── workflow_service.py
│   │   │   ├── fraud_service.py
│   │   │   ├── notification_service.py
│   │   │   └── audit_service.py
│   │   ├── moderator/
│   │   │   ├── agent.py
│   │   │   ├── risk_engine.py
│   │   │   └── prompts.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── auth.py
│   │   └── main.py
│   ├── seed.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AppLayout.jsx
│   │   │   ├── Navbar.jsx
│   │   │   ├── ProtectedRoute.jsx
│   │   │   ├── StatusBadge.jsx
│   │   │   ├── ProgressTracker.jsx
│   │   │   ├── TimelineEvent.jsx
│   │   │   ├── AlertCard.jsx
│   │   │   └── ModeratorPanel.jsx
│   │   ├── pages/
│   │   │   ├── LandingPage.jsx
│   │   │   ├── PharmacyDashboard.jsx
│   │   │   ├── DistributorDashboard.jsx
│   │   │   ├── ManufacturerDashboard.jsx
│   │   │   ├── FacilityDashboard.jsx
│   │   │   └── RegulatorDashboard.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
└── README.md
```

---

## 🚀 Key Features

1. **Authoritative State Machine**:
   `ACTIVE → EXPIRED → RETURN_REQUESTED → PICKUP_CONFIRMED → RECEIVED_BY_DISTRIBUTOR → DISPUTED (if discrepancy) → RECEIVED_BY_MANUFACTURER → DESTRUCTION_SCHEDULED → DESTROYED → CERTIFICATE_VERIFIED → CLOSED`
2. **Cryptographic SHA-256 Audit Chain**:
   Tamper-evident hash chaining with `POST /audit/verify` verification endpoint.
3. **Re-Entry Fraud Engine**:
   Detects unauthorized scans of destroyed/closed batches without resetting state.
4. **Gemini AI Moderator**:
   Real-time autonomous compliance risk analysis with fallback to rule engine.
5. **5 Persona Dashboards**:
   Role-specific views for Pharmacy, Distributor, Manufacturer, Facility, and Regulator.

---

## ⚡ Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Configure PostgreSQL DATABASE_URL and GEMINI_API_KEY in .env

# Seed database with initial dataset
python seed.py

# Run FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173) in your browser.
