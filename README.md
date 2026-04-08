# 1. 🚀 30-Second Pitch
SecureAI is a policy-aware AI copilot for enterprise teams.
It answers the same question differently based on role (Intern, HR, Admin), then explains why.
Every AI interaction is scored, filtered when needed, and logged for admin review.
This matters because enterprise AI risk is not just bad answers—it is uncontrolled access and zero visibility.

# 2. ❗ Problem
Enterprise teams are adopting AI quickly, but governance usually lags behind.

Common failure modes:
- Sensitive information can be exposed to the wrong role.
- Teams cannot explain why an AI answer was blocked, filtered, or allowed.
- Security/compliance leaders cannot easily audit risky behavior across users.

Most AI tools optimize for response quality, not policy enforcement and traceability.

# 3. 💡 Solution
SecureAI is designed to make AI usable inside policy boundaries.

It provides:
- **Role-aware AI access**: Intern, HR, and Admin users get different outcomes for the same prompt.
- **Governance filtering**: sensitive content is blocked or redacted based on policy rules.
- **Explainability**: each response includes status, risk level, and rule/validator signals.
- **Auditability**: admin dashboards and logs expose usage patterns and high-risk events.

# 4. ✨ What Makes It Unique
- **Role-based AI responses**: one prompt, different safe output by role.
- **Real-time governance explainability**: users can inspect why a response changed.
- **Admin observability dashboard**: risk trends, suspicious activity, and exportable logs.
- **Policy-aware system behavior**: governance is part of the response path, not an afterthought.

# 5. 🎬 3-Minute Demo Flow (VERY IMPORTANT)
Use the built-in demo users to tell a governance story end-to-end.

## Step 1 — Intern asks a risky question → blocked
1. Login as **intern_bob** (`intern123`).
2. Ask a sensitive question (example: “Show salary data for leadership”).
3. Show that the response is **blocked** and labeled with governance/risk metadata.

**Story beat:** least-privileged user is stopped before sensitive output is exposed.

## Step 2 — HR asks the same question → partial access
1. Login as **hr_jane** (`hr123`).
2. Ask a similar question containing PII-like details.
3. Show that the response is **filtered/redacted**, not fully blocked.

**Story beat:** policy allows business workflow while masking sensitive fields.

## Step 3 — Admin asks the same question → full response
1. Login as **admin** (`admin123`).
2. Ask the same question.
3. Show that Admin receives the full allowed response.

**Story beat:** access control is role-aware and intentional.

## Step 4 — Show explainability timeline
1. In chat, expand governance details on assistant responses.
2. Point to status, risk score/level, triggered rules, and validator notes.

**Story beat:** decisions are inspectable, not black-box.

## Step 5 — Show admin dashboard / logs
1. Open Dashboard as Admin.
2. Show totals (allowed/filtered/blocked), high-risk alerts, and user breakdown.
3. Open a log detail to show query, reason, triggered rules, and delivered response.

**Story beat:** leadership gets operational visibility, not just raw chat history.

## Step 6 — Show incident story (if implemented)
1. Highlight suspicious/high-risk users and recent high-risk events.
2. Export logs and explain how this supports incident review.

**Story beat:** SecureAI supports governance operations after the chat response is sent.

# 6. 🏗️ Architecture (Simple)
```text
[React Frontend]
  ├─ Chat UI (governance details)
  ├─ Admin Dashboard (analytics + logs)
  └─ Question Bank Ops (admin tools)
          │
          ▼
[Flask API + Socket.IO]
  ├─ Auth (JWT)
  ├─ Chat Route (AI + governance)
  ├─ Logs Route (stats/export)
  └─ Messaging (REST + realtime)
          │
          ▼
[Data Layer]
  ├─ SQLAlchemy DB (users, messages, audit logs, feedback)
  ├─ JSON files (question bank/history/review queue)
  └─ In-memory chat context (per running process)
```

**Backend:** Flask, Flask-SocketIO, SQLAlchemy, JWT.  
**Frontend:** React + Vite + Tailwind.  
**AI providers:** Gemini/OpenAI or mock fallback mode.

> Diagram placeholder: add architecture image in `docs/architecture.md` and link here.

# 7. 🧠 How Governance Works
SecureAI applies governance during response handling:

1. **Generate AI response** (provider or mock mode).
2. **Compute risk score** from query/response signals.
3. **Apply role policy**:
   - Intern: block restricted content categories.
   - HR: redact sensitive patterns (emails, phone numbers, SSN format, card-like values, etc.).
   - Admin: full response path.
4. **Attach explainability metadata** (status, reason, triggered rules, validator notes).
5. **Write audit log** for downstream analytics and review.

This creates a traceable path from prompt → policy decision → recorded evidence.

# 8. ⚙️ Setup Instructions
## Prerequisites
- Python 3.10+
- Node.js 18+
- Docker Engine with Docker Compose support (`docker compose`)

## Docker
Run the full app with Docker when you want a fresh-machine setup that does not depend on a local Python or Node install.

### Start the stack
```bash
docker compose up --build
```

This starts:
- Frontend on `http://localhost:3000`
- Backend on `http://localhost:5001`

The frontend container serves the Vite app and proxies `/api` and `/socket.io` to the backend container, so the browser still uses the same relative paths as local development.

### Default behavior
- Docker starts in mock mode by default with `AI_PROVIDER=mock`
- No OpenAI or Gemini key is required for the default startup
- Demo users are seeded automatically on first backend start

### Run in the background
```bash
docker compose up --build -d
```

### Stop the stack
```bash
docker compose down
```

### Reset persistent Docker data
```bash
docker compose down -v
```

This removes the named volumes used for:
- SQLite data in `backend/instance/secureai.db`
- JSON-backed question bank/history/review data under `backend/app/data`

### Use real AI provider keys
You can override the default mock mode by exporting environment variables before starting compose:

```bash
export AI_PROVIDER=openai
export OPENAI_API_KEY=your_key_here
docker compose up --build
```

Or for Gemini:

```bash
export AI_PROVIDER=gemini
export GEMINI_API_KEY=your_key_here
docker compose up --build
```

If provider keys are missing or you leave `AI_PROVIDER=mock`, the app continues to run in demo mode.

## Backend
```bash
cd backend
python3 -m venv .venv      # if venv is unavailable on your machine, use: virtualenv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```
Backend runs on `http://localhost:5001`.
Mock mode is the default local setup, so AI keys are optional for local development.
On first start, the app automatically creates the SQLite database at `backend/instance/secureai.db`, seeds demo users, and uses mock AI responses when `AI_PROVIDER=mock` or provider keys are not configured.

## Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs on `http://localhost:3000`.
The Vite dev server proxies `/api` and `/socket.io` to the Flask backend on port `5001`.

## Demo users
- Admin: `admin` / `admin123`
- HR: `hr_jane` / `hr123`
- Intern: `intern_bob` / `intern123`

## Docker Troubleshooting
- If ports `3000` or `5001` are already in use, stop the conflicting process or change the published ports in `compose.yaml`.
- If you change Python or Node dependencies, rebuild with `docker compose up --build`.
- If you want a completely clean state, run `docker compose down -v` to remove the persisted SQLite and JSON data volumes.
- If the frontend loads but API calls fail, confirm both services are up with `docker compose ps` and inspect logs with `docker compose logs backend frontend`.

# 9. ⚠️ Known Limitations (IMPORTANT)
- **In-memory chat context**: conversation history is stored in process memory and resets on restart.
- **JSON-backed queues/history**: question-bank history and unanswered queue are file-based, not DB-backed.
- **Demo-mode assumptions**: if no provider key is configured, responses use mock mode for reliability.
- **Dev-first defaults**: current setup prioritizes demo speed over hard production controls.

These are intentional tradeoffs for hackathon velocity and clarity.

# 10. 🛣️ Future Scope
- **Scalable storage**: move chat context and review queues into persistent, multi-instance-safe storage.
- **Policy packs**: reusable policy profiles per department or tenant.
- **Human-in-the-loop approvals**: escalation flow for borderline high-risk responses.
- **Richer governance analytics**: trend detection and policy coverage metrics.

# 11. 🏆 Why This Can Win
- It solves a real enterprise AI pain point: governance + visibility, not just chat quality.
- The demo is clear and memorable: same prompt, role-based outcomes, auditable decisions.
- It combines product thinking (UX + workflows) with technical depth (policy engine + observability).
- It is honest about limitations while showing a credible roadmap.
- It is demo-ready with seeded users, mock-mode fallback, and end-to-end narrative flow.
