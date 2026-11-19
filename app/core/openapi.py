"""OpenAPI schema enrichment with real examples for every endpoint (Task 19)."""

from typing import Any

# Realistic request body examples keyed by path substring
REQUEST_EXAMPLES: dict[str, dict[str, Any]] = {
    "/auth/login": {
        "username": "admin",
        "password": "LedgerForge2025!",
    },
    "/payroll/calculate": {
        "employee_id": "EMP-0002",
        "month": "2025-04",
        "variable_pay": "0.00",
        "variable_pay_type": "PERFORMANCE_BONUS",
        "other_deductions": "0.00",
    },
    "/payroll/runs": {
        "month": "2025-05",
        "run_by": "U-0099",
    },
    "/jobs/payroll/bulk-run": {
        "months": ["2025-04", "2025-05", "2025-06"],
        "auto_approve": True,
        "run_by": "U-0099",
    },
    "/ledger/entries": {
        "entry_date": "2025-04-30",
        "posting_period": "2025-04",
        "financial_year": "FY2025-26",
        "description": "Office supplies monthly accrual",
        "source_type": "MANUAL",
        "source_id": "M-2025-001",
        "lines": [
            {"account_code": 5100, "debit": "15000.00", "credit": "0.00", "cost_center_department_id": "D-ENG"},
            {"account_code": 2100, "debit": "0.00", "credit": "15000.00", "cost_center_department_id": "D-ENG"},
        ],
    },
    "/employees": {
        "employee_id": "EMP-0999",
        "first_name": "Arun",
        "last_name": "Kumar",
        "work_email": "arun.kumar@znova-demo.example",
        "gender": "Male",
        "date_of_birth": "1994-05-15",
        "hire_date": "2024-01-10",
        "department_id": "D-ENG",
        "role_id": "R-SWE1",
        "employment_status": "Active",
        "employment_type": "Permanent",
        "work_location": "Bengaluru",
        "work_mode": "Hybrid",
    },
    "/expenses": {
        "vendor_id": "V-0001",
        "expense_date": "2025-04-15",
        "amount_excl_gst": "45000.00",
        "gst_rate": "0.18",
        "department_id": "D-ENG",
        "description": "Q1 Cloud hosting and server fees",
    },
    "/invoices": {
        "client_id": "C-0001",
        "invoice_date": "2025-04-20",
        "due_date": "2025-05-20",
        "currency": "INR",
        "items": [
            {"description": "Backend API Architecture Consulting", "quantity": 1, "unit_price": "250000.00", "gst_rate": "0.18"}
        ],
    },
    "/attendance": {
        "employee_id": "EMP-0002",
        "attendance_date": "2025-04-01",
        "check_in": "09:00:00",
        "check_out": "18:00:00",
        "status": "PRESENT",
    },
    "/leave/requests": {
        "employee_id": "EMP-0002",
        "leave_type": "CASUAL",
        "start_date": "2025-04-10",
        "end_date": "2025-04-11",
        "reason": "Family function",
    },
    "/tax/slabs/rerun-demo": {
        "employee_id": "EMP-0002",
        "month": "2025-04",
        "regime": "NEW",
    },
    "/tax/slabs": {
        "financial_year": "FY2025-26",
        "regime": "NEW",
        "slab_order": 2,
        "income_from": "400001.00",
        "income_to": "800000.00",
        "rate_percent": "5.00",
    },
    "/tax/parameters": {
        "value": "75000.00",
        "notes": "Updated standard deduction for FY2025-26",
    },
    "/tax/statutory-rates": {
        "value": "0.12",
        "notes": "Standard EPF employee contribution rate",
    },
}

# Realistic parameter examples by parameter name
PARAMETER_EXAMPLES: dict[str, Any] = {
    "employee_id": "EMP-0002",
    "emp_id": "EMP-0002",
    "user_id": "U-0001",
    "run_id": "PR-2025-04",
    "payroll_run_id": "PR-2025-04",
    "job_id": "JOB-20261118-001",
    "entry_id": "JE-000105",
    "invoice_id": "INV-2025-0001",
    "expense_id": "EXP-2025-0001",
    "vendor_id": "V-0001",
    "client_id": "C-0001",
    "slab_id": "SLAB-NEW-02",
    "parameter": "STANDARD_DEDUCTION",
    "leave_id": "LR-0001",
    "month": "2025-04",
    "department_id": "D-ENG",
    "dept_id": "D-ENG",
    "department": "D01",
    "account_code": 5001,
    "financial_year": "FY2025-26",
    "start_date": "2025-04-01",
    "end_date": "2025-04-30",
    "as_of": "2025-09-30",
    "since": "2025-04-01T00:00:00",
    "limit": 50,
    "offset": 0,
    "page": 1,
    "size": 20,
    "status": "Active",
    "q": "jatin",
    "format": "csv",
}

# Realistic 200 response examples for GET/read endpoints without query/body params
RESPONSE_EXAMPLES: dict[str, Any] = {
    "/health": {
        "status": "ok",
        "service": "ledgerforge-api",
        "database": "connected",
        "latency_ms": 1.42,
    },
    "/auth/me": {
        "user_id": "U-0001",
        "username": "sanjay.kumar@znova-demo.example",
        "role": "ADMIN",
        "employee_id": "EMP-0001",
        "is_active": "Y",
    },
    "/auth/permissions": {
        "role": "ADMIN",
        "permissions": ["employees:read", "employees:write", "payroll:run", "ledger:post", "exports:read"],
    },
    "/auth/users": {
        "total": 745,
        "items": [{"user_id": "U-0001", "username": "sanjay.kumar@znova-demo.example", "role": "ADMIN", "is_active": "Y"}],
    },
    "/departments": [
        {"department_id": "D01", "department_name": "Engineering", "cost_center": "CC-ENG", "is_active": True}
    ],
    "/employees": {
        "total": 745,
        "page": 1,
        "size": 20,
        "items": [{"employee_id": "EMP-0002", "first_name": "Jatin", "last_name": "Jayaraman", "department_id": "D01"}],
    },
    "/leave/holidays": [
        {"holiday_date": "2025-01-26", "name": "Republic Day", "type": "NATIONAL"}
    ],
    "/leave/types": [
        {"code": "CASUAL", "name": "Casual Leave", "annual_quota": 12}
    ],
    "/payroll/runs/reconciliation": {
        "total_runs": 18,
        "matched_journal_entries": 18,
        "variance_total": "0.00",
    },
    "/invoices/clients": [
        {"client_id": "C-0001", "client_name": "Acme Corp India", "gstin": "29AABCU9603R1ZM"}
    ],
    "/invoices/receivables": {
        "total_billed": "48500000.00",
        "total_received": "42100000.00",
        "total_outstanding": "6400000.00",
    },
    "/expenses/vendors": [
        {"vendor_id": "V-0001", "vendor_name": "CloudInfra India Pvt Ltd", "category": "Infrastructure"}
    ],
    "/expenses/report": {
        "total_expenses": 501,
        "total_amount": "18450200.00",
        "by_department": [{"department_id": "D01", "total": "6420000.00"}],
    },
    "/expenses/reconciliation/monthly": [
        {"month": "2025-04", "expense_total": "1025000.00", "ledger_total": "1025000.00", "variance": "0.00"}
    ],
    "/expenses/duplicates": {
        "duplicate_groups": 0,
        "items": [],
    },
    "/tax/slabs": [
        {"slab_id": "SLAB-NEW-01", "financial_year": "FY2025-26", "regime": "NEW", "income_from": "0.00", "income_to": "400000.00", "rate_percent": "0.00"}
    ],
    "/tax/parameters": [
        {"parameter": "STANDARD_DEDUCTION", "value": "75000.00", "financial_year": "FY2025-26"}
    ],
    "/tax/statutory-rates": [
        {"parameter": "EPF_EMPLOYEE_RATE", "value": "0.12", "effective_from": "2024-04-01"}
    ],
    "/tax/reports/summary": {
        "financial_year": "FY2025-26",
        "total_pf_employee": "24850120.00",
        "total_esi_employee": "1240500.00",
        "total_professional_tax": "1468000.00",
        "total_tds": "38920450.00",
    },
    "/reports/trial-balance": {
        "as_of": "2025-09-30",
        "total_debit": "245819204.50",
        "total_credit": "245819204.50",
        "is_balanced": True,
        "accounts": [{"account_code": 5001, "account_name": "Basic Pay Expense", "debit": "45120000.00", "credit": "0.00"}],
    },
    "/reports/balance-sheet": {
        "as_of": "2025-09-30",
        "total_assets": "128450000.00",
        "total_liabilities": "42100000.00",
        "total_equity": "86350000.00",
        "is_balanced": True,
    },
    "/reports/department-payroll-cost": {
        "report_type": "DEPARTMENT_PAYROLL_COST",
        "run_id": "PR-2025-04",
        "departments_count": 11,
        "total_payroll_items": 412,
        "company_total_gross_pay": "52410000.00",
        "company_total_employer_cost": "55890000.00",
        "departments": [
            {
                "department_id": "D01",
                "department_name": "Engineering",
                "cost_center": "CC-ENG",
                "unique_employees": 145,
                "total_employer_cost": "24850000.00",
                "share_of_total_cost_percent": "44.46",
            }
        ],
    },
}


def enrich_openapi_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Inject real, copy-pasteable examples into every path and operation."""
    paths = schema.get("paths", {})
    for path_str, path_item in paths.items():
        for method, op in path_item.items():
            if not isinstance(op, dict):
                continue

            # 1. Enrich Request Body Examples (longest key match first so sub-paths win)
            if "requestBody" in op:
                rb = op["requestBody"]
                content = rb.get("content", {})
                json_content = content.get("application/json", {})
                if json_content and "example" not in json_content:
                    for key in sorted(REQUEST_EXAMPLES.keys(), key=len, reverse=True):
                        if key in path_str:
                            json_content["example"] = REQUEST_EXAMPLES[key]
                            break

            # 2. Enrich Query and Path Parameter Examples
            for param in op.get("parameters", []):
                p_name = param.get("name", "")
                if "example" not in param and "schema" in param:
                    if p_name in PARAMETER_EXAMPLES:
                        param["example"] = PARAMETER_EXAMPLES[p_name]

            # 3. Enrich 200/201 Response Examples so every single endpoint has a real example
            responses = op.get("responses", {})
            for status_code in ("200", "201"):
                resp = responses.get(status_code)
                if not isinstance(resp, dict):
                    continue
                json_resp = resp.get("content", {}).get("application/json")
                if isinstance(json_resp, dict) and "example" not in json_resp:
                    for key in sorted(RESPONSE_EXAMPLES.keys(), key=len, reverse=True):
                        if path_str.endswith(key):
                            json_resp["example"] = RESPONSE_EXAMPLES[key]
                            break

    return schema
