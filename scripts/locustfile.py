"""Locust load test suite for LedgerForge (Task 18 Optional).

Usage:
    locust -f scripts/locustfile.py --host http://127.0.0.1:8000
    # Headless 15-second benchmark:
    locust -f scripts/locustfile.py --headless -u 20 -r 5 --run-time 15s --host http://127.0.0.1:8000
"""

from locust import HttpUser, between, task


class LedgerForgeUser(HttpUser):
    wait_time = between(0.1, 0.5)
    token = None

    def on_start(self):
        """Authenticate on user startup to obtain JWT."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "LedgerForge2025!"},
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")

    @task(5)
    def check_health(self):
        self.client.get("/api/v1/health")

    @task(4)
    def get_employees(self):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.get("/api/v1/employees?limit=20", headers=headers)

    @task(3)
    def view_payslip(self):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.get("/api/v1/payslips/EMP-0002/PR-2025-04", headers=headers)

    @task(2)
    def get_trial_balance(self):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.get("/api/v1/reports/trial-balance", headers=headers)

    @task(1)
    def view_web_ui(self):
        self.client.get("/ui")
