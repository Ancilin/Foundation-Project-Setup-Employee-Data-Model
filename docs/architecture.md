# LedgerForge System Architecture

This document illustrates the final production architecture of **LedgerForge** (Phases 1–4, `v1.0.0-rc1`), including client entry points, the layered FastAPI backend, asynchronous Celery/Redis workers, PostgreSQL storage, observability, and data export pipelines.

## 1. High-Level Deployment & Runtime Architecture

```mermaid
flowchart TD
    subgraph Clients["Clients & Consumers"]
        WEB["Browser / Mobile Web UI\n(/ui)"]
        SWAGGER["Swagger / OpenAPI Docs\n(/docs)"]
        INTEGRATION["External Scripts / BI Tools\n(CSV & Excel Exports)"]
    end

    subgraph Edge["Render Cloud / Docker Compose Stack"]
        subgraph APIContainer["FastAPI Service (Uvicorn)"]
            MW["Middleware Layer\n(JSON Logging + JWT RBAC + Error Handler)"]
            ROUTES["API v1 Routers\n(/api/v1/* — 90 Operations)"]
            SERVICES["Domain Service Layer\n(Payroll, Ledger, Tax, Reports, Exports, Jobs)"]
            CACHE["In-Memory TTL Cache\n(Trial Balance Hot Cache)"]
            ORM["SQLAlchemy 2.0 ORM\n(29 Tables + Alembic Migrations)"]
        end

        REDIS[("Redis Broker &\nResult Backend")]
        CELERY["Celery Worker\n(Bulk Payroll & Async Jobs)"]
        PG[("PostgreSQL 16\n(Hosted DB / Local Volume)")]
    end

    WEB --> MW
    SWAGGER --> MW
    INTEGRATION --> MW

    MW --> ROUTES
    ROUTES --> SERVICES
    SERVICES --> CACHE
    SERVICES --> ORM
    SERVICES -- "Enqueue Async Job" --> REDIS
    REDIS --> CELERY
    CELERY --> PG
    ORM --> PG
```

## 2. Layered Request & Data Flow

Every HTTP request follows a strict one-way layered architecture (`Route → Service → ORM/Database`) so business rules remain completely decoupled from HTTP transport concerns:

```mermaid
sequenceDiagram
    actor User as HR / Admin User
    participant API as FastAPI Route (/api/v1)
    participant Auth as JWT RBAC Guard
    participant Svc as Domain Service
    participant DB as PostgreSQL / SQLite
    participant Log as JSON Structured Logger

    User->>API: HTTP Request + Bearer JWT
    API->>Auth: Verify Token & Role (ADMIN / HR / EMPLOYEE)
    Auth-->>API: Authenticated User Context
    API->>Svc: Execute Business Rule (e.g. Payroll / Export / Report)
    Svc->>DB: Indexed SQLAlchemy Query (Composite Indexes)
    DB-->>Svc: Result Rows / Stream Chunks
    Svc-->>API: Pydantic Schema or StreamingResponse (CSV/XLSX)
    API->>Log: Emit Structured JSON Log (method, path, status, duration_ms)
    API-->>User: HTTP 200 Response
```

## 3. Core Domain Modules

| Layer | Directory | Responsibility |
| :--- | :--- | :--- |
| **HTTP Routes** | `app/api/routes/` | Request parsing, role guards, pagination, streaming responses (`employees`, `salaries`, `attendance`, `leave`, `payroll`, `ledger`, `invoices`, `expenses`, `tax`, `reports`, `jobs`, `exports`, `health`, `ui`) |
| **Business Services** | `app/services/` | Payroll engine, double-entry journal posting, Indian statutory tax engine (EPF/ESI/PT/TDS), financial reports + TTL cache, streaming CSV/Excel exports, background job orchestration |
| **ORM Models** | `app/models/` | 29 normalized tables with natural business keys, `CHECK` constraints, soft-delete flags (`is_active`), audit timestamps, and composite indexes |
| **Migrations** | `migrations/versions/` | Versioned Alembic migrations (`0001` through `0011`) for schema creation and performance indexing |
| **Core Infrastructure** | `app/core/` | Environment config (`config.py`), JWT/bcrypt security (`security.py`), structured JSON logs (`logging.py`), OpenAPI enrichment (`openapi.py`), report cache (`cache.py`) |
| **Operations & QA** | `scripts/` & `tests/` | Master dataset seeder, official verifier (`verify_ledgerforge.py`), backup/restore proof (`backup_restore.py`), live smoke tests (`smoke_test.py`), 128 automated pytest tests |
