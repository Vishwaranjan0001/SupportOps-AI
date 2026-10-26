# SupportOps AI — Customer Support Agent

**React → FastAPI → LangGraph → Groq → MCP Server → SQLite**, plus RAG, Agent Skills, human refund approval, local support tickets, and checkpoint memory.

A local customer-support demonstration using fictional store data. It combines tool-backed order lookups, policy retrieval, persistent conversations, support tickets, and a separate human refund-approval workflow.

**Personal project by [Vishwaranjan Singh](https://github.com/Vishwaranjan0001)** · [Portfolio](https://vishwaranjan0001.github.io/)

## Validation

The existing 14 offline tests pass, and the React frontend builds successfully. These checks do not exercise live Groq responses. Default retrieval uses keyword matching; semantic retrieval is an optional upgrade.

## 1. Requirements

- Windows 11, or macOS/Linux with equivalent commands.
- **Python 3.11 or 3.12** (recommended).
- Node.js 20.19+ or 22.12+ and npm.
- A Groq API key (`GROQ_API_KEY`).

## 2. Backend (VS Code Terminal 1 — PowerShell)

Open this folder in VS Code, then:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:GROQ_API_KEY="paste_your_groq_key_here"
python smoke_mcp.py
python -m uvicorn app:app --reload
```

If `py -3.11` is not recognized, use `python -m venv .venv` after checking `python --version`.
If activation is unavailable, run the virtual environment's Python executable directly.

- **MCP smoke test:** `python smoke_mcp.py` should discover 7 tools and show `ORD-1001` data.
- API: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- **No third terminal is required for the MCP server**; the LangChain MCP adapter starts `mcp_server.py` as a subprocess automatically.

## 3. Frontend (VS Code Terminal 2 — PowerShell)

From the project root in a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173**.

If you open Terminal 2 while still inside `backend`, use `cd ..\frontend` instead of `cd frontend`.

## 4. Demo walkthrough

Ask these messages **in one conversation**:

1. `Where is my order ORD-1001?` → calls an MCP order tool → SQLite says `SHIPPED`.
2. `Is that order eligible for refund?` → LangGraph remembers `ORD-1001` → tool reports no.
3. `What is the return policy for damaged items?` → RAG searches local policy docs; no fabricated policy.
4. `Please request a refund for ORD-1003 because I changed my mind.` → MCP creates **PENDING** refund request.
5. In right panel click **Manager approval → Open → Approve**. This is a **human action, not a tool accessible to Groq**. The state becomes `APPROVED` without moving money.
6. `What happened to my refund request?` → MCP reads its updated status.
7. `Create a support ticket for a delivery issue with ORD-1001.` → MCP writes ticket to SQLite.
8. Ask `Show my support tickets.` → MCP reads the tickets saved locally in SQLite. The live-data panel has **Orders** and **Refunds** tabs.
9. Refresh the page or restart backend, and ask `Which order were we discussing?` → SQLite checkpoint memory persists.
10. Try `Show the details of ORD-1002.` → it belongs to another fictional user, so tool denies access.

Orders in the seeded database:

| Order | Product | Status | Eligible for refund? |
| --- | --- | --- | --- |
| ORD-1001 | Wireless Headphones | SHIPPED | No |
| ORD-1003 | Laptop Stand | DELIVERED | Yes |
| ORD-1004 | Bluetooth Speaker | PROCESSING | No |
| ORD-1002 | Gaming Mouse | DELIVERED | Yes, **but belongs to someone else** |

## 5. What each file does

```text
supportops_interview_ready/
│
├── backend/
│   ├── app.py                 ← FastAPI endpoints + app startup
│   ├── agent.py               ← LangGraph LLM/ToolNode loop and skills
│   ├── mcp_server.py          ← Genuine MCP tools for SQLite
│   ├── db.py                  ← Database tables and SQL operations
│   ├── rag.py                 ← Policy retrieval tool, offline by default
│   ├── build_vectors.py       ← Optional Chroma vector embeddings
│   ├── smoke_mcp.py           ← Check MCP works before running UI
│   ├── docs/                  ← Refund, shipping, warranty policies
│   ├── skills/                ← Refund/order/ticket SKILL.md instructions
│   ├── tests/test_db.py       ← Offline unit tests
│   ├── requirements.txt
│   └── requirements-rag.txt  ← Only for semantic vector RAG
│
├── frontend/
│   ├── src/App.jsx            ← Chat, orders, refunds, manager UI
│   ├── src/api.js             ← fetch() HTTP helper
│   ├── src/styles.css         ← Design
│   └── vite.config.js         ← API proxy to FastAPI
│
└── README.md
```

### One picture of the flow

```text
CUSTOMER
  ↓
React App.jsx
  ↓ POST /api/chat
FastAPI app.py
  ↓ graph.ainvoke() (thread ID saved by SqliteSaver)
LangGraph agent.py ──→ Groq (understands the request)
  ↓ decides which tool
ToolNode ──→ MCPAdapter (client) ──→ mcp_server.py ──→ db.py ──→ SQLite
    │
    └──────→ search_company_policy() ──→ rag.py ──→ company docs / Chroma
  ↓ ToolMessage returned to LangGraph
Groq produces answer
  ↓
FastAPI JSON → React renders answer
```

## 6. RAG: Easy mode, plus a vector DB upgrade

The default app **already performs RAG**: `search_company_policy` retrieves relevant passages from `docs/*.txt`, and Groq answers using those passages. **Default retrieval uses basic keyword matching**, not semantic embeddings. It's fast, offline, and simple to learn.

For **real semantic embeddings + Chroma vector database**, optionally run in Backend Terminal 1 (you can do this after the basic app works):

```powershell
python -m pip install -r requirements-rag.txt
python build_vectors.py
```

The embedding model (`all-MiniLM-L6-v2`) downloads the first time. The app switches to Chroma when it sees the created `backend/data/chroma/` index. The RAG tool interface remains the same.

After editing company documents, rerun `python build_vectors.py` to reindex.

## 7. LangGraph Agent Skills

Skills are simple `SKILL.md` guides. `agent.py` reads one matching skill for the question and includes it in the system prompt. This helps guide decisions but **does not itself enforce permissions**.

## 8. Human approval gate

The AI may call MCP `submit_refund_request`, which creates a PENDING request. Approval is handled **only** by the `POST /api/manager/refunds/{id}` HTTP endpoint and dashboard click. The database checks ownership, eligibility, and duplicate requests. **There are no payment operations.**

The current manager UI has **NO manager authentication**. It's for a local interview demonstration and must not be exposed on the public internet as-is. The customer is also hardcoded as `cust-001`.

## 9. Unit tests — no Groq key needed

From the `backend` folder:

```powershell
python -m unittest discover -s tests -v
```

Tests cover SQLite records, customer isolation, refund approval, duplicate handling, tickets, and basic RAG retrieval.

## 10. Technical honesty / scope

- **Fictional demo customer** (`cust-001`); there is no login system. Do not claim this is production authentication.
- **Fictional orders and no payments**. Refund approval is just a record update.
- **Live Groq required** for AI responses; tests only cover database and basic retrieval unless you run the real app.
- **Single-process / local SQLite demo**; for production, use authentication, proper async concurrency controls, Postgres, secure MCP identity propagation, audit logs, and evaluation.
- **Default RAG is keyword search**; semantic vector retrieval is an optional installed upgrade.

The intent is a small project that is easy to run, demo, and explain. Every core component has its own simple file.
