# ER Diagram – Employee, Department & Role data model

Source of truth: [`app/models/`](../app/models) and migration
[`0001_create_employee_tables.py`](../migrations/versions/0001_create_employee_tables.py).
Column names follow the `01_LedgerForge_Python_Master_Dataset` workbook (`employees`, `departments`, `roles` sheets).

```mermaid
erDiagram
    DEPARTMENTS ||--o{ ROLES : "defines"
    DEPARTMENTS ||--o{ EMPLOYEES : "has"
    ROLES ||--o{ EMPLOYEES : "held by"
    EMPLOYEES |o--o{ EMPLOYEES : "manages (manager_id)"

    DEPARTMENTS {
        string department_id PK "D00..D10"
        string department_name UK
        string cost_center UK
        string description
        bool is_active "soft delete"
        timestamptz created_at
        timestamptz updated_at
    }

    ROLES {
        string role_id PK "R001.."
        string department_id FK
        string role_title "UK with department_id"
        smallint level "CHECK 1..7"
        string grade
        numeric band_min_annual "CHECK min<=mid<=max"
        numeric band_mid_annual
        numeric band_max_annual
        bool overtime_eligible
        bool is_active "soft delete"
        timestamptz created_at
        timestamptz updated_at
    }

    EMPLOYEES {
        string employee_id PK "EMP-0001.."
        string first_name
        string last_name
        string work_email UK
        string gender "CHECK Male/Female/Other"
        date date_of_birth
        date hire_date "CHECK > date_of_birth"
        date exit_date "nullable, CHECK >= hire_date"
        string employment_status "CHECK Active/Resigned/Terminated/Contract Ended"
        string employment_type "CHECK Permanent/Fixed-Term Contract"
        string work_location
        string work_mode "CHECK Onsite/Hybrid/Remote"
        string department_id FK
        string role_id FK
        string manager_id FK "self-reference, nullable"
        bool is_active "soft delete"
        timestamptz created_at
        timestamptz updated_at
    }
```

## Relationships

| Relationship | Type | Delete behaviour |
|---|---|---|
| department → roles | one-to-many | blocked while roles exist (no cascade) |
| department → employees | one-to-many | blocked while employees exist |
| role → employees | one-to-many | blocked while employees hold it |
| employee → manager (employee) | many-to-one, **self-reference** | blocked while the manager has reports |

Nothing cascades: rows are never hard-deleted in normal use. Set `is_active = false` instead (soft delete),
so payroll, leave and reports can still resolve old IDs.

## Constraints

| Table | Constraint | Why |
|---|---|---|
| employees | `UNIQUE(work_email)` | one login/identity per person |
| employees | `CHECK exit_date IS NULL OR exit_date >= hire_date` | no leaving before joining |
| employees | `CHECK hire_date > date_of_birth` | sanity |
| employees | `CHECK manager_id IS NULL OR manager_id <> employee_id` | nobody manages themselves |
| employees | `CHECK` on gender / status / type / work mode | allowed values enforced by the DB |
| roles | `UNIQUE(department_id, role_title)` | no duplicate titles within a department |
| roles | `CHECK level BETWEEN 1 AND 7`, band order | matches dataset rules |
| departments | `UNIQUE(department_name)`, `UNIQUE(cost_center)` | |

## Indexes (for searching)

| Index | Columns | Serves |
|---|---|---|
| `ix_employees_name` | `last_name, first_name` | name search / sorted lists |
| `ix_employees_department_id` | `department_id` | "all employees in department X" |
| `ix_employees_role_id` | `role_id` | "who holds role X" |
| `ix_employees_manager_id` | `manager_id` | "show my team" (hierarchy lookups) |
| `ix_employees_employment_status` | `employment_status` | active/leaver filters |
| `ix_roles_department_id` | `department_id` | roles per department |
| (automatic) | `work_email` unique index | login / duplicate check |

## Known limits

- Cycles longer than one step (A manages B, B manages A) are not blocked by the database; the
  service layer in Task 3 must reject them when a manager is changed.
- Only the *current* role/manager/department is stored. Dataset sheets such as `employee_assignments`
  (history) are a later addition.
