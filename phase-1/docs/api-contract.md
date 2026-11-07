# LedgerForge – Draft API Contract (v0.1, DRAFT)

> **Status:** draft for review by other teams. Only `GET /health` exists today; everything else
> is *planned* and may change. Send feedback before Task 2 starts.
> Live docs once running: <http://localhost:8000/docs> (Swagger) and `/openapi.json`.
> Sample data: [`sample_employees.json`](sample_employees.json) / [`sample_employees.csv`](sample_employees.csv)
> (10 rows taken from the `employees` sheet of `01_LedgerForge_Python_Master_Dataset`).

## Conventions

- Base URL: `http://localhost:8000` (no version prefix yet; `/api/v1` may be added later).
- JSON in / JSON out. Dates are ISO‑8601 `YYYY-MM-DD`. Timestamps are ISO‑8601 UTC.
- IDs are strings with the dataset's codes: employees `EMP-0001`, departments `D01`, roles `R002`.
- List endpoints take `limit` (default 50, max 200) and `offset` (default 0) and return
  `{"items": [...], "total": <int>, "limit": <int>, "offset": <int>}`.
- Errors: `{"detail": "<message>"}` with the usual status code (`404` not found, `409` duplicate,
  `422` validation error – FastAPI's default validation body).
- Auth: not enforced yet. A bearer‑token scheme is planned (the app already has a `SECRET_KEY` setting).

## Endpoints

| # | Method | Path | Purpose | Request | Success response | Status |
|---|--------|------|---------|---------|------------------|--------|
| 1 | GET | `/health` | Liveness check | – | `200` `{"status": "ok"}` | **Implemented** |
| 2 | GET | `/employees` | List employees | query: `limit`, `offset`, `department_id`, `employment_status`, `q` (name/email search) | `200` paged list of `Employee` | Planned (Task 2) |
| 3 | POST | `/employees` | Create employee | `EmployeeCreate` | `201` `Employee` | Planned (Task 2) |
| 4 | GET | `/employees/{employee_id}` | Get one employee | – | `200` `Employee` / `404` | Planned (Task 2) |
| 5 | PUT | `/employees/{employee_id}` | Replace/update employee | `EmployeeCreate` | `200` `Employee` / `404` | Planned (Task 2) |
| 6 | DELETE | `/employees/{employee_id}` | Remove employee | – | `204` / `404` | Planned (Task 2) |
| 7 | GET | `/departments` | List departments | – | `200` list of `Department` | Planned (Task 2) |
| 8 | GET | `/roles` | List roles | query: `department_id` | `200` list of `Role` | Planned (Task 2) |

## Schemas

### `Employee` (response)

| Field | Type | Nullable | Example | Notes |
|-------|------|----------|---------|-------|
| `employee_id` | string | no | `EMP-0002` | Primary key, format `EMP-NNNN` |
| `first_name` | string | no | `Jatin` | |
| `last_name` | string | no | `Jayaraman` | |
| `work_email` | string (email) | no | `jatin.jayaraman@znova-demo.example` | Unique |
| `gender` | enum | no | `Male` | `Male` \| `Female` \| `Other` |
| `date_of_birth` | date | no | `1973-06-25` | |
| `hire_date` | date | no | `2012-01-31` | |
| `exit_date` | date | **yes** | `null` | Empty for active employees |
| `employment_status` | enum | no | `Active` | `Active` \| `Resigned` \| `Terminated` \| `Contract Ended` |
| `employment_type` | enum | no | `Permanent` | `Permanent` \| `Fixed-Term Contract` |
| `department_id` | string | no | `D08` | FK → `Department` |
| `role_id` | string | no | `R047` | FK → `Role` |
| `manager_id` | string | **yes** | `EMP-0361` | FK → `Employee`; null only for the top of the hierarchy |
| `work_location` | string | no | `Pune` | City |
| `work_mode` | enum | no | `Remote` | `Onsite` \| `Hybrid` \| `Remote` |

`full_name` is a derived read‑only convenience field (`first_name + " " + last_name`) that may be added to responses.

### `EmployeeCreate` (request)

Same fields as `Employee` except `employee_id` is optional (server assigns the next `EMP-NNNN` if omitted).
Validation: `exit_date >= hire_date`; `work_email` must be a valid email; enums as above.

### `Department` / `Role`

| Schema | Fields |
|--------|--------|
| `Department` | `department_id` (`D01`), `department_name` (`Engineering`), `cost_center` (`CC-100`), `description` |
| `Role` | `role_id` (`R002`), `department_id`, `role_title`, `level` (int 1–7), `grade` |

Salary bands (`band_min_annual` …) exist in the dataset but are **not** exposed yet – open question below.

## Example

```http
GET /employees/EMP-0002
```

```json
{
  "employee_id": "EMP-0002",
  "first_name": "Jatin",
  "last_name": "Jayaraman",
  "work_email": "jatin.jayaraman@znova-demo.example",
  "gender": "Male",
  "date_of_birth": "1973-06-25",
  "hire_date": "2012-01-31",
  "exit_date": null,
  "employment_status": "Active",
  "employment_type": "Permanent",
  "department_id": "D08",
  "role_id": "R047",
  "manager_id": "EMP-0361",
  "work_location": "Pune",
  "work_mode": "Remote"
}
```

## Open questions for other teams

1. Do you need salary / payroll fields on `Employee`, or a separate `/employees/{id}/salary` resource later?
2. Is offset pagination enough, or do you need cursor pagination?
3. Should `gender` be returned by default? (Dataset notes say it is for fairness testing only.)
4. Do you want a bulk import endpoint (`POST /employees/bulk`) fed by the dataset?
5. Auth: is a bearer token enough for your clients?
