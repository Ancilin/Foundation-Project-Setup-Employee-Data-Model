"""Smoke test suite — run against the live deployment to verify core functionality.

Usage:
    python smoke_test.py https://your-app.onrender.com
    python smoke_test.py http://localhost:8000
"""

import sys
import time
from decimal import Decimal

import httpx


def main():
    if len(sys.argv) < 2:
        print("Usage: python smoke_test.py <BASE_URL>")
        print("Example: python smoke_test.py https://ledgerforge.onrender.com")
        sys.exit(1)

    base = sys.argv[1].rstrip("/")
    passed = 0
    failed = 0
    results = []

    def check(name: str, ok: bool, detail: str = ""):
        nonlocal passed, failed
        if ok:
            passed += 1
            results.append(f"  ✓ {name}")
        else:
            failed += 1
            results.append(f"  ✗ {name} — {detail}")

    client = httpx.Client(base_url=base, timeout=30.0, follow_redirects=True)

    # ── 1. Health endpoint ──
    print("1. Health check...")
    try:
        r = client.get("/api/v1/health")
        check("GET /api/v1/health returns 200", r.status_code == 200, f"status={r.status_code}")
        body = r.json()
        check("Health response has status field", "status" in body, f"body={body}")
    except Exception as e:
        check("Health endpoint reachable", False, str(e))

    # ── 2. Docs page loads ──
    print("2. Swagger docs...")
    try:
        r = client.get("/docs")
        check("GET /docs returns 200", r.status_code == 200, f"status={r.status_code}")
        check("Docs page contains swagger-ui", "swagger" in r.text.lower(), "swagger-ui not found in HTML")
    except Exception as e:
        check("Docs page reachable", False, str(e))

    # ── 3. Login ──
    print("3. Login as admin...")
    token = None
    try:
        r = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "LedgerForge2025!",
        })
        check("POST /api/v1/auth/login returns 200", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
        if r.status_code == 200:
            token = r.json().get("access_token")
            check("Login returns access_token", token is not None, f"body={r.json()}")
    except Exception as e:
        check("Login endpoint reachable", False, str(e))

    if not token:
        print("\n⚠ Cannot continue without a valid token. Stopping early.\n")
        for line in results:
            print(line)
        print(f"\nResult: {passed} passed, {failed} failed")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # ── 4. List employees ──
    print("4. List employees...")
    target_emp_id = "EMP-0002"
    try:
        r = client.get("/api/v1/employees", headers=headers)
        check("GET /api/v1/employees returns 200", r.status_code == 200, f"status={r.status_code}")
        emps_data = r.json()
        emp_list = emps_data.get("items", emps_data) if isinstance(emps_data, dict) else emps_data
        check("Employees list is non-empty", isinstance(emp_list, list) and len(emp_list) > 0, f"count={len(emp_list) if isinstance(emp_list, list) else 'N/A'}")
        if isinstance(emp_list, list) and len(emp_list) > 0:
            # Pick first active employee or fallback to EMP-0002
            for e in emp_list:
                if e.get("status") == "ACTIVE":
                    target_emp_id = e.get("employee_id", "EMP-0002")
                    break
    except Exception as e:
        check("Employees endpoint reachable", False, str(e))

    # ── 5. One payroll calculation (LF-07) ──
    print(f"5. Payroll calculation (for {target_emp_id}, 2025-04)...")
    try:
        calc_payload = {
            "employee_id": target_emp_id,
            "month": "2025-04",
            "variable_pay": "0.00",
            "other_deductions": "0.00"
        }
        r = client.post("/api/v1/payroll/calculate", headers=headers, json=calc_payload)
        check("POST /api/v1/payroll/calculate returns 200", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
        if r.status_code == 200:
            cdata = r.json()
            gross = Decimal(str(cdata.get("gross_pay", "0")))
            net = Decimal(str(cdata.get("net_pay", "0")))
            check("Calculated gross_pay > 0", gross > 0, f"gross_pay={gross}")
            check("Calculated net_pay > 0", net > 0, f"net_pay={net}")
            check("Gross pay >= Net pay (statutory deductions applied)", gross >= net, f"gross={gross}, net={net}")
    except Exception as e:
        check("Payroll calculate endpoint reachable", False, str(e))

    # ── 6. View Payslip ──
    print(f"6. View payslip (for {target_emp_id}, PR-2025-04)...")
    try:
        r = client.get(f"/api/v1/payslips/{target_emp_id}/PR-2025-04", headers=headers)
        check(f"GET /api/v1/payslips/{target_emp_id}/PR-2025-04 returns 200", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            pdata = r.json()
            check("Payslip has net_pay", "net_pay" in pdata, f"payslip={pdata}")
    except Exception as e:
        check("Payslip endpoint reachable", False, str(e))

    # ── 7. Web UI loads ──
    print("7. Web UX interface...")
    try:
        r = client.get("/ui")
        check("GET /ui returns 200", r.status_code == 200, f"status={r.status_code}")
        check("UI contains LedgerForge title", "LedgerForge" in r.text, "Title not found")
    except Exception as e:
        check("Web UI reachable", False, str(e))

    # ── 8. Payroll run list ──
    print("8. Payroll data...")
    try:
        r = client.get("/api/v1/payroll/runs", headers=headers)
        check("GET /api/v1/payroll/runs returns 200", r.status_code == 200, f"status={r.status_code}")
        runs = r.json()
        if isinstance(runs, list) and len(runs) > 0:
            check("Payroll runs exist", True)
            run_id = runs[0].get("run_id", runs[0].get("id"))
            if run_id:
                r2 = client.get(f"/api/v1/payroll/runs/{run_id}", headers=headers)
                check(f"GET payroll run {run_id} returns 200", r2.status_code == 200, f"status={r2.status_code}")
        else:
            check("Payroll runs exist", False, f"empty list or error: {runs}")
    except Exception as e:
        check("Payroll endpoint reachable", False, str(e))

    # ── 9. Ledger accounts ──
    print("9. Ledger / chart of accounts...")
    try:
        r = client.get("/api/v1/ledger/accounts", headers=headers)
        check("GET /api/v1/ledger/accounts returns 200", r.status_code == 200, f"status={r.status_code}")
        accounts = r.json()
        check("Chart of accounts is non-empty", isinstance(accounts, list) and len(accounts) > 0,
              f"count={len(accounts) if isinstance(accounts, list) else 'N/A'}")
    except Exception as e:
        check("Ledger endpoint reachable", False, str(e))

    # ── 10. Reports ──
    print("10. Financial reports...")
    try:
        r = client.get("/api/v1/reports/trial-balance", headers=headers, params={"as_of_date": "2025-04-30"})
        check("GET /api/v1/reports/trial-balance returns 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        check("Reports endpoint reachable", False, str(e))

    # ── Summary ──
    print("\n" + "=" * 50)
    print(f"SMOKE TEST RESULTS — {base}")
    print("=" * 50)
    for line in results:
        print(line)
    print(f"\n{'=' * 50}")
    print(f"Total: {passed} passed, {failed} failed")
    if failed == 0:
        print("✓ ALL SMOKE TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
