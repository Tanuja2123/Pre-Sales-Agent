# Pre-Sales AI Agent — Requirements

| Field | Value |
|-------|-------|
| **Project** | Pre-Sales AI Agent |
| **Organization** | MAQ Software |
| **Version** | 2.0 |
| **Last updated** | May 2026 |

---

## 1. Purpose

The Pre-Sales AI Agent automates the early stages of RFP (Request for Proposal) response work for enterprise presales teams. The system ingests client RFP documents, runs a multi-agent AI pipeline to extract requirements and generate intelligence, collects human clarifications, and produces a structured proposal draft and project timeline.

**Primary goal:** Reduce manual effort in RFP analysis, requirement mapping, and first-draft proposal creation while keeping presales experts in control through human-in-the-loop clarification.

**Related documents:** [README.md](README.md) · [PROJECT_GUIDE.md](PROJECT_GUIDE.md) · [docs/TECHNICAL_IMPLEMENTATION.md](docs/TECHNICAL_IMPLEMENTATION.md)

---

## 2. Scope

### In scope

- RFP upload (TXT, PDF, DOCX)
- Multi-agent automated analysis pipeline (Phase 1)
- Human clarification capture and final proposal generation (Phase 2)
- Web UI for upload, progress tracking, results review, and agent workspaces
- JWT-based authentication with per-user run isolation
- Optional email notifications (timeline and deadline reminders)
- Retrieval-augmented generation (RAG) for proposal drafting
- Configurable LLM backends (Groq, Ollama, Azure OpenAI, mock)

### Out of scope

- Full contract negotiation or e-signature workflows
- Automated submission to client procurement portals
- Real-time collaboration between multiple users on the same run
- Guaranteed legal or financial accuracy of pricing/commercial terms
- Production-grade multi-tenant SaaS billing and admin console

---

## 3. User roles

| Role | Description |
|------|-------------|
| **Presales user** | Uploads RFPs, reviews agent outputs, answers clarifying questions, downloads/reviews proposal draft |
| **Bid manager** | Same as presales user; uses history and timeline for pursuit tracking |
| **System administrator** | Configures `.env`, LLM keys, SMTP, and deployment (not a separate UI role) |

All authenticated users have equal application access. Each user sees only their own RFP runs.

---

## 4. Functional requirements

### 4.1 Authentication & account management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-AUTH-01 | Users shall register with email and password | Must |
| FR-AUTH-02 | Users shall log in and receive a JWT Bearer token | Must |
| FR-AUTH-03 | All `/api/v1/rfp/*` endpoints shall require a valid JWT | Must |
| FR-AUTH-04 | Passwords shall be stored as bcrypt hashes in SQLite | Must |
| FR-AUTH-05 | Users shall only access runs they own (`assert_run_access`) | Must |
| FR-AUTH-06 | UI shall detect backend restart and prompt re-login when session is invalid | Should |

### 4.2 RFP intake & document handling

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-INTAKE-01 | Users shall upload RFP files in TXT, PDF, or DOCX format | Must |
| FR-INTAKE-02 | System shall persist uploaded files under `data/uploads/` with UUID filenames | Must |
| FR-INTAKE-03 | System shall reject analysis when `LLM_ONLY_MODE=true` and backend is `mock` | Must |
| FR-INTAKE-04 | Upload shall return a unique `run_id` for tracking | Must |
| FR-INTAKE-05 | System shall parse PDF and DOCX content into plain text for agents | Must |

### 4.3 Phase 1 — Automated analysis pipeline

Phase 1 runs automatically after upload. No proposal draft is generated in this phase.

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-P1-01 | **Ingestion Agent** shall parse the document, chunk text, and index chunks for RAG | Must |
| FR-P1-02 | **Understanding Agent** shall extract structured requirements with unique IDs (`REQ-###`) | Must |
| FR-P1-03 | Requirements shall include priority, type, MAF classification, and ambiguity score | Must |
| FR-P1-04 | **Summarization Agent** shall produce an executive summary with client overview, objectives, risks, and bid strategy | Must |
| FR-P1-05 | **Scope Gathering Agent** shall produce a presales scope document (business requirements, user stories) | Must |
| FR-P1-06 | **Clarification Agent** shall generate client-ready clarifying questions tied to requirements | Must |
| FR-P1-07 | System shall expose pipeline progress (0–100%) and status (`pending`, `running`, `complete`, `failed`, `aborted`) | Must |
| FR-P1-08 | System shall build a strict 6-milestone project timeline from RFP content | Must |
| FR-P1-09 | Phase 1 shall complete at 100% with clarification chat available; proposal draft tab remains empty | Must |

**Phase 1 progress mapping:**

| Progress | Agent / step |
|----------|----------------|
| 20% | Ingestion |
| 40% | Understanding |
| 60% | Summarization |
| 70% | Scope gathering |
| 80% | Clarification |
| 100% | Complete |

### 4.4 Phase 2 — Clarification & final proposal

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-P2-01 | Users shall answer clarifying questions in the Results UI | Must |
| FR-P2-02 | Users shall optionally upload supporting files with clarifications | Should |
| FR-P2-03 | Submitting answers shall call `POST /rfp/{run_id}/clarifications/resolve` | Must |
| FR-P2-04 | System shall build a clarification resolution document from user answers and assumptions | Must |
| FR-P2-05 | **Response Draft Agent** shall generate a 15-section enterprise proposal using RAG + clarifications | Must |
| FR-P2-06 | Proposal shall use **MAQ Software** as the responding company name | Must |
| FR-P2-07 | Proposal sections shall include: Cover Page, Executive Summary, About the Company, Understanding of Client Requirements, Proposed Solution, Scope of Work, Project Timeline & Implementation Plan, Team Structure, Commercial Proposal / Pricing, Risk Management, Support & Maintenance, Competitive Advantages, Compliance Matrix, Terms and Conditions, Conclusion | Must |
| FR-P2-08 | Draft shall address mandatory requirements by requirement ID in solution and compliance sections | Must |
| FR-P2-09 | System shall reject empty or title-only draft bodies and retry with JSON repair or prose fallback | Must |
| FR-P2-10 | A timeline email shall be sent to the registered user after final draft generation (when SMTP enabled) | Should |

### 4.5 Agent framework & orchestration

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-AGENT-01 | Pipeline shall be orchestrated sequentially via `PipelineOrchestrator` | Must |
| FR-AGENT-02 | System shall integrate **Microsoft Agent Framework** (`agent-framework-core`) | Must |
| FR-AGENT-03 | Agent Framework tools shall support ingest, retrieve, audit, and revise operations | Should |
| FR-AGENT-04 | **Evaluation Agent** shall score draft quality / MAF compliance (critic loop configurable) | Should |
| FR-PRESALES-01 | **Presales Chat Agent** shall assist users during clarification on the active run | Should |
| FR-AGENT-05 | Groq rate limits shall be handled with cooldown delays between agent LLM calls | Must |

### 4.6 Results & review UI

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-UI-01 | Dashboard shall show overview, pipeline flow, and recent runs | Must |
| FR-UI-02 | Analysis page shall poll run status until complete or failed | Must |
| FR-UI-03 | Results page shall provide tabs: Summary & scope, Timeline, Requirements, Questions, Proposal draft, Clarification chat | Must |
| FR-UI-04 | Agent Fleet page shall list all specialist agents with per-agent workspace views | Must |
| FR-UI-05 | History page shall list past runs for the logged-in user | Must |
| FR-UI-06 | Proposal draft shall render with formatted headings, paragraphs, lists, tables, and label rows | Must |
| FR-UI-07 | Users shall copy proposal draft text from the UI | Should |

### 4.7 Notifications

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-EMAIL-01 | System shall send a project timeline email after final draft generation | Should |
| FR-EMAIL-02 | System shall send reminder emails N days before milestone deadlines (`REMINDER_DAYS_BEFORE`) | Should |
| FR-EMAIL-03 | When SMTP is disabled, emails shall be saved to `data/email_outbox/` as `.eml` files | Must |

### 4.8 API

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-API-01 | REST API shall be exposed under `/api/v1` with OpenAPI docs at `/docs` | Must |
| FR-API-02 | Endpoints shall include: analyze, status, output, summary, questions, draft, scope, history, chat, clarifications/resolve | Must |
| FR-API-03 | Health endpoint shall return `server_boot_id` for session validation | Must |
| FR-API-04 | LLM failures during draft generation shall return HTTP 502 with actionable error detail | Must |

---

## 5. Non-functional requirements

### 5.1 Performance & reliability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-PERF-01 | Phase 1 pipeline shall complete for a typical sample RFP (≤50 pages) using Groq 70B within reasonable demo time (several minutes with rate-limit delays) | Should |
| NFR-PERF-02 | LLM client shall auto-truncate prompts and cap output tokens for Groq 8B models (6000 TPM limit) | Must |
| NFR-PERF-03 | LLM client shall retry on transient Groq 429/413 errors with backoff | Must |
| NFR-PERF-04 | Frontend shall poll status at ~500ms interval while pipeline is running | Should |

### 5.2 Security

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-SEC-01 | JWT secret shall be configurable and changed for production | Must |
| NFR-SEC-02 | `.env` and `data/` shall not be committed to source control | Must |
| NFR-SEC-03 | CORS shall restrict browser origins to configured frontend URLs | Must |
| NFR-SEC-04 | RFP content sent to external LLM providers shall be disclosed in deployment docs; Ollama option for on-premises | Must |

### 5.3 Maintainability & configurability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-CONFIG-01 | All runtime settings shall load from repo-root `.env` via `backend/core/config.py` | Must |
| NFR-CONFIG-02 | LLM backend shall be switchable without code changes (`groq`, `ollama`, `azure_openai`, `mock`) | Must |
| NFR-CONFIG-03 | Vector store shall be switchable between `memory` and `chroma` | Must |
| NFR-CONFIG-04 | Spec Kit YAML under `specs/` shall document agent contracts (validated by `scripts/validate_specs.py`) | Should |

### 5.4 Persistence

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-DATA-01 | Run outputs shall persist in SQLite (`data/runs.sqlite3`) | Must |
| NFR-DATA-02 | System shall hydrate in-memory caches from SQLite on backend startup | Must |
| NFR-DATA-03 | Uploaded RFP files shall survive server restart | Must |

### 5.5 Compatibility

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-COMPAT-01 | Backend shall run on Python 3.11+ | Must |
| NFR-COMPAT-02 | Frontend shall run on Node.js 18+ | Must |
| NFR-COMPAT-03 | UI shall support modern Chromium-based browsers | Must |

---

## 6. Technology requirements

| Layer | Required technology |
|-------|---------------------|
| Backend API | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 |
| Frontend | React 18, TypeScript, Vite, Fluent UI |
| AI orchestration | Microsoft Agent Framework (`agent-framework-core`) |
| LLM | Groq (default), Ollama, Azure OpenAI, or mock |
| RAG | In-memory vector store or ChromaDB |
| Auth | JWT (python-jose), bcrypt |
| Database | SQLite |
| Email | SMTP (optional), APScheduler for reminders |
| Document parsing | pypdf, python-docx |

---

## 7. Data requirements

### 7.1 Inputs

- RFP document (TXT, PDF, DOCX)
- User clarification answers (text, optional file attachments)
- Environment configuration (`.env`)

### 7.2 Outputs

| Output | Description |
|--------|-------------|
| Structured requirements | List with `REQ-###`, priority, MAF level, ambiguity |
| Executive summary | Client overview, objectives, evaluation criteria, bid strategy, go/no-go |
| Scope document | Business requirements and user stories |
| Clarifying questions | Question set with assumptions |
| Clarification resolution document | Merged Q&A for draft agent |
| Proposal draft | 15-section markdown proposal (MAQ Software) |
| Project timeline | 6 milestones with dates, deliverables, dependencies |
| MAF audit | Minimum / Acceptable / Full gate assessment |
| Email notifications | Timeline and reminder messages |

---

## 8. Constraints & assumptions

### Constraints

- Groq free tier has token-per-minute limits; pipeline includes intentional delays between agent calls.
- Proposal draft quality depends on LLM model capability; `llama-3.3-70b-versatile` is recommended for large RFPs.
- Commercial/pricing sections may contain assumptions when exact costs are not in the RFP.

### Assumptions

- Users have valid LLM API credentials (Groq) or a running Ollama instance for real runs.
- Users are presales professionals who review and edit AI-generated drafts before client submission.
- One primary user owns each RFP run; concurrent multi-user editing is not required.
- English-language RFP content is the primary use case.

---

## 9. Acceptance criteria

The system is considered acceptable for demo/submission when:

1. A user can register, log in, and upload a sample RFP (`samples/sample-rfp-it-services.txt`).
2. Phase 1 completes with requirements, summary, scope, questions, and timeline visible in Results.
3. User can submit clarification answers and trigger Phase 2 final draft generation.
4. Proposal draft displays all 15 sections with **MAQ Software** as company name and readable formatting.
5. Run history persists after backend restart for the same user account.
6. Backend tests (`pytest tests/ -q`) and frontend tests (`npm test`) pass.
7. Technical documentation (`README.md`, `PROJECT_GUIDE.md`, `docs/TECHNICAL_IMPLEMENTATION.md`) reflects implemented behavior.

---

## 10. Future enhancements (not in v2.0)

- Multi-user collaboration on a single RFP run
- Export proposal draft to DOCX/PDF from the UI
- Azure AD / SSO authentication
- Admin dashboard for org-wide run analytics
- Persistent critic loop with automatic draft revision until MAF threshold is met
- Integration with CRM or document management systems

---

*For setup and run instructions, see [README.md](README.md). For architecture details, see [PROJECT_GUIDE.md](PROJECT_GUIDE.md).*
