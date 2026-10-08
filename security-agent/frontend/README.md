# BizIQ Security & Compliance — Streamlit Dashboard Frontend

The **BizIQ Security Dashboard** is a standalone Python Streamlit frontend for the Security & Compliance Agent. It communicates exclusively through the backend's REST APIs to visualize security telemetry, summarize deterministic signals, display recent audit events, and trigger AI-assisted behavioral security analyses.

---

## 🏗️ Architecture

```
Streamlit Frontend (Port 8501)
          │
          │ HTTP / REST (Bearer JWT)
          ▼
FastAPI Security Backend (Port 8003)
          │
          ├── SQLite / SQLAlchemy (RBAC, Audit Logs, Login Attempts)
          └── Groq AI Service (openai/gpt-oss-20b)
```

- **Separation of Concerns**: The frontend contains zero direct database queries and zero direct LLM calls.
- **Authorization**: Backend RBAC is the single source of truth. The frontend enforces role-appropriate navigation while the backend guarantees permission checks.
- **Session Management**: JWT access tokens are stored securely in memory within Streamlit's `st.session_state` and never persisted to local storage or disk.

---

## 🚀 Getting Started

### 1. Backend Server Setup

In a dedicated terminal, launch the FastAPI Security backend:

```powershell
cd security-agent
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8003
```

Verify backend health at: [http://localhost:8003/health](http://localhost:8003/health)

---

### 2. Frontend Configuration & Setup

In a separate terminal, navigate to the `frontend` folder:

```powershell
cd security-agent\frontend
```

Install frontend dependencies:

```powershell
pip install -r requirements.txt
```

Create your local `.env` configuration file:

```powershell
copy .env.example .env
```

Ensure `API_BASE_URL` points to your running FastAPI server:

```ini
API_BASE_URL=http://localhost:8003
```

---

### 3. Launching the Streamlit Application

Run Streamlit from the `security-agent/frontend` directory:

```powershell
streamlit run app.py
```

The application will open in your default browser at: [http://localhost:8501](http://localhost:8501)

---

## 🛡️ Features & Capabilities

1. **Authentication & Session UX**:
   - Secure sign-in using email/username and password via `POST /api/v1/auth/login`.
   - Dynamic user badge display for `ADMIN`, `ANALYST`, and `USER` roles.
   - Clean session teardown upon sign-out.

2. **Access Control & RBAC Enforcement**:
   - `ADMIN` & `ANALYST`: Granted full access to Security Dashboard metrics, signal visualizations, audit logs, and AI analysis.
   - `USER`: Blocked with a friendly Access Denied banner.

3. **Overview Metrics**:
   - Total Users & Active Users
   - Login Attempts, Successful Logins & Failed Logins
   - Access Denied Events
   - Invalid & Expired JWT Token Events

4. **Deterministic Security Signals & Plotly Visualization**:
   - Summarizes Phase 7 deterministic security rules across all users:
     - Repeated Failed Logins
     - Multiple IP Addresses
     - Repeated Access Denied
     - Invalid Token Activity
     - Expired Token Activity
     - Unusual Login Frequency
   - Interactive Plotly chart with responsive hover tooltips.

5. **Recent Security Events**:
   - Chronological audit table displaying event action, user ID, status, client IP address, UTC timestamp, and sanitized details.

6. **UTC Time Window Filtering**:
   - Quick presets: *Last 24 hours*, *Last 7 days*, *Last 30 days*, and *Custom Range*.
   - Strictly converts all datetime inputs to UTC before transmitting to FastAPI.

7. **AI Security Analysis**:
   - Trigger deep-dive behavioral analysis for any user via `POST /api/v1/security/analyze`.
   - Displays Risk Level (`LOW`, `MEDIUM`, `HIGH`, `UNKNOWN`), Suspicious activity flag, Confidence percentage, Findings, Security Evidence, and Mitigation Recommendations.
   - Includes standard advisory disclaimer.
