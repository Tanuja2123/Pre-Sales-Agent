# Pre-Sales AI Agent

Enterprise pre-sales RFP pipeline — upload an RFP, run AI agents, generate a proposal draft, and receive timeline and deadline emails.

---

## Running the project (complete guide)

### At a glance

| Service | Command | URL |
|---------|---------|-----|
| **Backend API** | `uvicorn main:app --reload --host 127.0.0.1 --port 8000` (from `backend/`) | [http://127.0.0.1:8000](http://127.0.0.1:8000) |
| **API docs (Swagger)** | (same as backend) | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| **Frontend app** | `npm run dev` (from `frontend/`) | [http://127.0.0.1:5173](http://127.0.0.1:5173) |
| **Health check** | `GET /api/v1/health` | Returns `server_boot_id` (used for session refresh) |

The Vite dev server proxies **`/api`** → **`http://127.0.0.1:8000`**, so the browser always calls the backend through the frontend origin.

**Keep two terminals open** while developing: one for uvicorn, one for `npm run dev`.

---

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 18+ | Frontend build and dev server |
| **Groq API key** | — | [console.groq.com](https://console.groq.com) when `LLM_BACKEND=groq` (default) |
| **Microsoft Word** | Optional | Only if you regenerate PDFs locally via `docx2pdf` |

Optional alternatives (no Groq):

- **Ollama** — local LLM (`LLM_BACKEND=ollama`, run `ollama serve`)
- **ChromaDB** — persistent RAG (`VECTOR_STORE_BACKEND=chroma`, extra pip install)

---

### Step 1 — Clone and configure environment

From the **repository root** (folder containing this README):

```powershell
copy .env.example .env
```

Edit **`.env`** at the repo root. Minimum for a real run:

```env
LLM_BACKEND=groq
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.3-70b-versatile
LLM_ONLY_MODE=true
JWT_SECRET=change-this-in-production
```

Paths in `.env` (`DATA_DIR`, `RUN_DB_PATH`, `CHROMA_PERSIST_DIR`) resolve **relative to the repo root**, not your shell directory.

**Restart uvicorn** after any `.env` change.

See [Environment variables](#environment-variables) for the full list.

---

### Step 2 — Install and start the backend

**Terminal 1:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Optional (Chroma vector store):

```powershell
pip install -r requirements-chroma.txt
```

Start the API:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Expected output:** Uvicorn listening on `127.0.0.1:8000`, application startup complete.

On startup the backend:

- Loads **`.env`** from the repo root
- Creates **`data/`** if needed (`uploads/`, `runs.sqlite3`, `email_outbox/`)
- **Hydrates** prior run history from SQLite into memory
- Starts the **reminder scheduler** (deadline emails)

**Verify:** open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) or:

```powershell
curl http://127.0.0.1:8000/api/v1/health
```

---

### Step 3 — Install and start the frontend

**Terminal 2:**

```powershell
cd frontend
npm install
npm run dev
```

**Expected output:** Local URL [http://127.0.0.1:5173](http://127.0.0.1:5173).

Production build (optional):

```powershell
npm run build
npm run preview
```

Serve `frontend/dist/` behind nginx or similar; proxy `/api` to the backend.

---

### Step 4 — Log in or register

| Action | URL |
|--------|-----|
| Login | [http://127.0.0.1:5173/login](http://127.0.0.1:5173/login) |
| Register | [http://127.0.0.1:5173/register](http://127.0.0.1:5173/register) |

**Default test account** (if already seeded in your database):

| Email | Password |
|-------|----------|
| `tanuja.sharma@maqsoftware.com` | `test1234` |

**Optional demo personas** (run once from `backend/`):

```powershell
python scripts/seed_demo_users.py
```

| Persona | Email | Password |
|---------|-------|----------|
| Presales Lead | `presales.lead@example.com` | `DemoPass1` |
| Solution Architect | `solution.architect@example.com` | `DemoPass1` |
| Bid Manager | `bid.manager@example.com` | `DemoPass1` |

- Auth uses **JWT Bearer** tokens (stored in the browser).
- All **`/api/v1/rfp/*`** routes require login.
- **Restarting the backend** changes `server_boot_id`; the UI may ask you to **sign in again**.
- Each user only sees **their own** RFP runs.

---

### Step 5 — Run an RFP through the pipeline

#### 5.1 Upload (Phase 1 — automatic)

1. Open **[http://127.0.0.1:5173/intake](http://127.0.0.1:5173/intake)** (New intake).
2. Upload **TXT**, **PDF**, or **DOCX** (e.g. `samples/sample-rfp-it-services.txt`).
3. The UI navigates to **`/analysis/{runId}`** and polls status until complete.

**Backend:** `POST /api/v1/rfp/analyze` saves the file under `data/uploads/` and starts the pipeline asynchronously.

#### 5.2 Phase 1 pipeline (no proposal draft yet)

| Progress | Step | Output |
|----------|------|--------|
| 20% | Ingestion | Parsed text, chunks, vector index |
| 40% | Understanding | Requirements (`REQ-###`), **strict timeline** (6 milestones) |
| 60% | Summarization | Executive summary |
| 70% | Scope gathering | Business requirements, user stories |
| 80% | Clarification | Clarifying questions |
| 100% | Complete | Results ready; clarification chat opened |

**Status values:** `pending` → `running` → `complete` | `failed` | `aborted`.

Groq free tier: the backend inserts **cooldown delays** between LLM steps (`GROQ_INTER_REQUEST_DELAY_SECONDS`, default 55s for 70B models). A full run can take **several minutes**.

#### 5.3 Review results (Phase 1 outputs)

Open **`/results/{runId}`** or use the app navigation after analysis completes.

| Tab | Content |
|-----|---------|
| **Summary & scope** | Executive summary, scope document |
| **Timeline** | Strict 6-milestone table (submission → go-live) |
| **Requirements** | Extracted requirements with MAF and ambiguity |
| **Questions** | Clarifying questions + answer fields |
| **Chat** | Interactive clarification assistant |
| **Proposal draft** | Empty until Phase 2 |

Other pages:

| Route | Purpose |
|-------|---------|
| `/dashboard` | Overview |
| `/history` | Past runs for the logged-in user |
| `/agents`, `/run/{runId}/agents/{agentId}` | Per-agent workspace |

#### 5.4 Submit clarifications (Phase 2 — final draft)

1. On **Results → Questions**, fill answers (and optional file uploads).
2. Click **Submit all answers and create new draft**.
3. Backend: `POST /api/v1/rfp/{runId}/clarifications/resolve` → **ResponseDraftAgent** builds the 15-section proposal using RAG + your answers.
4. Review **Proposal draft** and **Timeline** tabs.
5. A **timeline email** is sent to your registered email when SMTP is configured (otherwise saved under `data/email_outbox/`).

---

### Runtime data (created automatically)

| Path | Purpose | Submit to git? |
|------|---------|----------------|
| `data/uploads/` | Uploaded RFP files (UUID names) | **No** |
| `data/runs.sqlite3` | Users, runs, outputs, chat, reminders | **No** |
| `data/chroma/` | Vector DB when using Chroma | **No** |
| `data/email_outbox/` | `.eml` copies when SMTP is off | **No** |
| `.env` | Secrets and local config | **No** (use `.env.example`) |
| `backend/.venv/`, `frontend/node_modules/` | Dependencies | **No** |

---

### Running tests

**Backend** (from `backend/`, venv active):

```powershell
pytest tests/ -q
```

**Frontend** (from `frontend/`):

```powershell
npm test
npm run lint
```

**Spec validation** (repo root):

```powershell
python scripts/validate_specs.py
```

---

### Alternative run configurations

#### Ollama (local LLM, no Groq key)

```env
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT_SECONDS=600
```

```powershell
ollama serve
ollama pull llama3.2
```

#### Chroma (persistent RAG)

```env
VECTOR_STORE_BACKEND=chroma
CHROMA_PERSIST_DIR=./data/chroma
```

```powershell
pip install -r requirements-chroma.txt
```

#### Mock LLM (CI / offline, no API calls)

```env
LLM_BACKEND=mock
LLM_ONLY_MODE=false
```

Upload will be rejected if `LLM_ONLY_MODE=true` and backend is `mock`.

#### Azure OpenAI

```env
LLM_BACKEND=azure_openai
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

---

### Email notifications (optional)

| Event | When |
|-------|------|
| Project timeline email | After **final draft** (Phase 2) |
| Deadline reminder | **3 days before** each milestone (`REMINDER_DAYS_BEFORE`) |

**Gmail example** in `.env`:

```env
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your@gmail.com
SMTP_PASSWORD="your-16-char-app-password"
SMTP_FROM_EMAIL=your@gmail.com
```

Use a [Google App Password](https://myaccount.google.com/apppasswords). Quote passwords that contain spaces.

Without SMTP, emails are written to **`data/email_outbox/`**.

---

### Troubleshooting while running

| Symptom | What to do |
|---------|------------|
| `Cannot reach the API at /api` | Start backend on port **8000**; keep frontend dev server running |
| `LLM-only mode` / 400 on upload | Set `GROQ_API_KEY` or change `LLM_BACKEND`; do not use `mock` with `LLM_ONLY_MODE=true` |
| Pipeline stuck / slow | Groq rate limits — wait 1–2 min; increase `GROQ_INTER_REQUEST_DELAY_SECONDS` |
| `LLMError` or JSON errors | Use `GROQ_MODEL=llama-3.3-70b-versatile`; check backend terminal logs |
| Empty **Timeline** tab | Refresh Results; timeline is rebuilt from RFP if missing |
| No **draft** until submit | Expected — complete Phase 2 (clarifications resolve) |
| 404 on run after restart | Re-login; run must exist in `data/runs.sqlite3` for your user |
| Session lost after backend restart | Log in again (`server_boot_id` changed) |
| Chroma import error on Windows | `pip install -r requirements-chroma.txt` |

**Logs:** watch the **uvicorn** terminal for `pipeline.failed`, `groq.cooldown`, `LLMError`.

---

### What not to submit with your code

Do **not** commit: **`.env`**, **`data/`**, **`.venv/`**, **`node_modules/`**, caches (`__pycache__/`, `.pytest_cache/`), or generated secrets.  
**Do** commit: source code, `README.md`, `PROJECT_GUIDE.md`, `.env.example`, `requirements.txt`, `package.json`.

---

## Reference

- **Technical Implementation (concise)** — [PDF](docs/TECHNICAL_IMPLEMENTATION.pdf) · [Word](docs/TECHNICAL_IMPLEMENTATION.docx) · [Markdown](docs/TECHNICAL_IMPLEMENTATION.md) — regenerate: `python scripts/generate_technical_docs.py`
- **Full technical reference** — [TECHNICAL_IMPLEMENTATION_FULL.md](docs/TECHNICAL_IMPLEMENTATION_FULL.md)
- **Project guide** — [PROJECT_GUIDE.md](PROJECT_GUIDE.md) (structure, API, persistence)
- **[Data Flow Diagrams](docs/DATA_FLOW_DIAGRAM.md)** — pipeline data movement

### Project layout

| Path | Role |
|------|------|
| `backend/` | FastAPI API, agents, orchestrator |
| `frontend/` | React + TypeScript + Fluent UI |
| `samples/` | Example RFP files |
| `data/` | SQLite DB, uploads, email outbox (created at runtime) |
| `specs/` | Versioned YAML specs |
| `scripts/` | `validate_specs.py`, `generate_technical_docs.py`, `generate_data_flow_docx.py` |
| `backend/scripts/seed_demo_users.py` | Seed demo login personas |

### Environment variables

Copy `.env.example` → `.env` at the repo root. Restart uvicorn after any change.

| Variable | Purpose | Typical value |
|----------|---------|---------------|
| `LLM_BACKEND` | LLM provider | `groq` |
| `GROQ_API_KEY` | Groq API key | from console.groq.com |
| `GROQ_MODEL` | Groq model | `llama-3.3-70b-versatile` |
| `GROQ_INTER_REQUEST_DELAY_SECONDS` | Delay between agent LLM calls | `55` |
| `LLM_ONLY_MODE` | Require real LLM | `true` |
| `VECTOR_STORE_BACKEND` | RAG store | `memory` |
| `JWT_SECRET` | Auth signing key | change in production |
| `JWT_EXPIRES_MINUTES` | Token lifetime | `10080` (7 days) |
| `EMAIL_ENABLED` | Send real emails | `true` / `false` |
| `SMTP_*` | Mail server settings | Gmail or other |
| `REMINDER_DAYS_BEFORE` | Days before deadline reminders | `3` |
| `SCHEDULER_INTERVAL_SECONDS` | Reminder job interval | `3600` |
| `DATA_DIR` | Upload folder | `./data/uploads` |
| `RUN_DB_PATH` | SQLite database | `./data/runs.sqlite3` |

Full list: `backend/core/config.py`

**Groq:** set `GROQ_API_KEY` in `.env`. For `llama-3.1-8b-instant` (6000 TPM limit), the backend auto-truncates prompts; for large RFPs prefer `llama-3.3-70b-versatile`.  
**Ollama:** set `LLM_BACKEND=ollama`, run `ollama serve`, pull your model.  
**Chroma:** set `VECTOR_STORE_BACKEND=chroma`, then `pip install -r backend/requirements-chroma.txt`.

### Authentication

- JWT Bearer tokens; passwords stored as bcrypt hashes in `data/runs.sqlite3`
- All `/api/v1/rfp/*` routes require login
- Auth API: [http://127.0.0.1:8000/docs#/Auth](http://127.0.0.1:8000/docs#/Auth)

### LLM backends

| Backend | Use case |
|---------|----------|
| `groq` | Fast cloud inference (default) |
| `ollama` | Local models |
| `azure_openai` | Enterprise Azure deployment |
| `mock` | CI / offline demos |

### Architecture

Microsoft Agent Framework + specialist agents:

- **Orchestrator** — two-phase pipeline (analysis → clarification → final draft)
- **Specialists** — ingestion, understanding, summarization, scope, clarification, draft, evaluation, chat
- **Agent Framework tools** — ingest, retrieve, audit, revise

Aligned with [Spec Kit](https://github.com/github/spec-kit) workflows (`specs/`, `.specify/memory/constitution.md`).
