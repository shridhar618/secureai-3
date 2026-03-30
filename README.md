# 🛡️ SecureAI — Enterprise AI Governance & Communication Platform

A production-grade, hackathon-ready AI governance platform featuring role-based AI response filtering, real-time private messaging, and a full admin audit dashboard.

---

## 🎯 Features

| Feature | Description |
|---|---|
| 🤖 AI Chatbot | Governed GPT/Gemini chatbot with RBAC filtering |
| 🔐 RBAC Governance | Intern/HR/Admin role-based response policies |
| 🛡️ Response Filtering | Keyword blocking + PII masking engine |
| 📊 Risk Scoring | Heuristic risk scoring per query |
| 💬 Private Chat | Real-time Socket.IO encrypted messaging |
| 📋 Audit Logs | Full query/response audit trail |
| 📈 Dashboard | Admin analytics with charts + table |
| 🔑 JWT Auth | Secure token-based authentication |

---

## 🏗️ Architecture

```
secureai/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # App factory, extensions
│   │   ├── models/
│   │   │   ├── user.py          # User model
│   │   │   ├── audit_log.py     # Audit log model
│   │   │   └── message.py       # Private message model
│   │   ├── routes/
│   │   │   ├── auth.py          # Register/Login/Me
│   │   │   ├── chat.py          # AI chat endpoint
│   │   │   ├── logs.py          # Audit logs (admin)
│   │   │   ├── users.py         # User list
│   │   │   ├── messages.py      # REST messages
│   │   │   └── socket_events.py # Socket.IO events
│   │   └── services/
│   │       ├── ai_service.py    # OpenAI/Gemini/Mock
│   │       └── governance.py    # RBAC + NRL filtering
│   ├── app.py                   # Entry point
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── context/AuthContext.jsx
    │   ├── utils/api.js
    │   ├── utils/socket.js
    │   ├── components/Layout.jsx
    │   └── pages/
    │       ├── LoginPage.jsx
    │       ├── RegisterPage.jsx
    │       ├── ChatPage.jsx
    │       ├── PrivateChatPage.jsx
    │       └── DashboardPage.jsx
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── tailwind.config.js
```

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm / yarn

---

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your AI API key (optional - demo mode works without one)
```

### 2. Configure AI Provider (optional)

Edit `backend/.env`:

```env
# For Gemini (recommended, free tier available):
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key

# OR for OpenAI:
AI_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key

# Leave blank for demo mode (mock responses)
```

> **Demo mode**: If no API key is set, the chatbot uses smart mock responses. Perfect for demos!

### 3. Run Backend

```bash
cd backend
python app.py
# Server starts on http://localhost:5000
```

---

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
# App runs on http://localhost:3000
```

---

## 🎮 Demo Credentials

The app auto-creates these accounts on first run:

| Role | Username | Password | Access Level |
|------|----------|----------|-------------|
| Admin | `admin` | `admin123` | Full access + Dashboard |
| HR | `hr_jane` | `hr123` | PII data masked |
| Intern | `intern_bob` | `intern123` | Sensitive data blocked |

Click the **Quick Demo Access** buttons on the login page for one-click login!

---

## 🔐 Governance Rules

### Intern Role
- Queries containing: `salary`, `password`, `confidential`, `secret`, `api_key`, `ssn`, `credit card`, etc.
- **Result**: Entire response blocked → "Access Restricted" message

### HR Role  
- Emails, phone numbers, SSNs, credit cards, salary figures automatically **masked**
- **Result**: Response returned with sensitive patterns replaced by `[REDACTED]`

### Admin Role
- **Full access** to all AI responses
- Complete audit log visibility

---

## 📡 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | None | Create account |
| POST | `/api/auth/login` | None | Get JWT token |
| GET | `/api/auth/me` | JWT | Get current user |
| POST | `/api/chat` | JWT | Send AI message |
| POST | `/api/chat/clear` | JWT | Clear chat history |
| GET | `/api/users` | JWT | List users (for chat) |
| GET | `/api/messages/<id>` | JWT | Get conversation |
| POST | `/api/messages` | JWT | Send message |
| GET | `/api/logs` | Admin JWT | Get audit logs |
| GET | `/api/logs/stats` | Admin JWT | Get statistics |

---

## 🔌 Socket.IO Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `connect` | Client→Server | Auth with token query param |
| `private_message` | Client→Server | Send message `{token, receiver_id, content}` |
| `typing` | Client→Server | Typing indicator |
| `stop_typing` | Client→Server | Stop typing |
| `new_message` | Server→Client | Incoming message |
| `online_users` | Server→Client | List of online user IDs |
| `user_typing` | Server→Client | Someone is typing |

---

## 🎨 Tech Stack

**Backend**: Flask · Flask-SocketIO · Flask-JWT-Extended · SQLAlchemy · eventlet  
**Frontend**: React 18 · Vite · Tailwind CSS · Framer Motion · Recharts · Socket.IO Client  
**AI**: OpenAI GPT-3.5 / Google Gemini 1.5 Flash (configurable)  
**DB**: SQLite (dev) / PostgreSQL (prod via `DATABASE_URL`)  
**Auth**: JWT tokens

---

## 🚀 Production Deployment

### PostgreSQL

```env
DATABASE_URL=postgresql://user:password@localhost/secureai
```

### Build Frontend

```bash
cd frontend
npm run build
# Serve dist/ with nginx or copy to backend/static/
```

### Gunicorn

```bash
pip install gunicorn
cd backend
gunicorn --worker-class eventlet -w 1 app:app --bind 0.0.0.0:5000
```

---

## 🏆 Hackathon Highlights

1. **Governance Engine**: Novel RBAC+NRL hybrid filtering — not just keyword blocking, but semantic role logic
2. **Risk Scoring**: Lightweight heuristic risk engine (extensible to ML)
3. **Real-time**: Full Socket.IO integration with typing indicators
4. **Production Architecture**: Blueprints, services layer, proper models
5. **Demo-Ready**: Works out of the box without any API keys

---

## 📝 Optional Improvements

- [ ] Add ML-based anomaly detection (scikit-learn IsolationForest)
- [ ] PostgreSQL + Redis for production
- [ ] Email notifications for high-risk queries
- [ ] Export audit logs to CSV
- [ ] Fine-grained permission matrix (not just 3 roles)
- [ ] Message encryption at rest
- [ ] Rate limiting per role
