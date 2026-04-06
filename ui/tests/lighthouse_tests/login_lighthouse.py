"""
Lighthouse performance & accessibility audit on the Login page.

How it works
────────────
1. Chromium is launched with --remote-debugging-port=9222 so Lighthouse
   can attach to the already-loaded browser session.
2. Playwright navigates to the splash page, clicks the Employee Portal button,
   and waits for the login form to appear.
3. The globally-installed `lighthouse` CLI connects on port 9222, audits the
   live login page, and writes an HTML report.
4. The report is attached to the Allure run for easy inspection.

Run locally
───────────
    pytest ui/tests/lighthouse_tests/login_lighthouse.py -v -s

Run in Docker
─────────────
    docker run --rm --env-file .env \\
        -v ./reports:/app/reports \\
        -v ./allure-results:/app/allure-results \\
        playwright-tests-lighthouse:latest \\
        pytest ui/tests/lighthouse_tests/login_lighthouse.py -m lighthouse -v -s
"""

import os
import shutil
import subprocess
import tempfile

import allure
import pytest
from playwright.sync_api import sync_playwright


@pytest.mark.lighthouse
@allure.epic("Performance")
@allure.feature("Lighthouse Audits")
@allure.story("Login Page")
@allure.title("Lighthouse audit - Login page")
def test_login_page_lighthouse():
    """
    Full Lighthouse audit (performance + accessibility + best-practices)
    executed against the Login page.

    Navigates to https://inforcedev.oneshield.com/oneshield, follows the
    splash → Employee Portal flow, and audits the resulting login form URL.
    """
    report_dir = os.path.abspath("reports/lighthouse")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "login_audit.html")

    # ── Verify lighthouse is on PATH ─────────────────────────────────────────
    lh_bin = str(shutil.which("lighthouse") or "")
    print(f"\n[Lighthouse] Binary resolved to: {lh_bin or '(not found)'}")
    if not lh_bin:
        pytest.fail(
            "'lighthouse' binary not found in PATH.\n"
            "Make sure the Dockerfile contains: RUN npm install -g lighthouse"
        )

    user_data_dir = tempfile.mkdtemp(prefix="pw-lh-login-")
    current_url: str | None = None
    lh_result = None

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            args=[
                "--remote-debugging-port=9222",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
            ],
        )
        page = context.new_page()

        try:
            # ── 1. Navigate to the app entry point ────────────────────────────
            with allure.step("Navigate to https://inforcedev.oneshield.com/oneshield"):
                print("[Lighthouse] Navigating to https://inforcedev.oneshield.com/oneshield")
                page.goto("https://inforcedev.oneshield.com/oneshield", wait_until="load", timeout=60_000)
                page.wait_for_load_state("networkidle", timeout=30_000)

            # ── 2. Click Employee Portal (splash screen) if present ───────────
            with allure.step("Click Employee Portal button (splash screen)"):
                splash_btn = page.locator("#employeePortal")
                if splash_btn.is_visible(timeout=5_000):
                    print("[Lighthouse] Splash screen detected — clicking Employee Portal")
                    splash_btn.click()
                    page.wait_for_load_state("networkidle", timeout=30_000)
                else:
                    print("[Lighthouse] No splash screen detected, continuing")

            # ── 3. Wait for login form ────────────────────────────────────────
            with allure.step("Wait for login form to be ready"):
                login_field = page.get_by_role("textbox", name="PARTNER NUMBER*")
                login_field.wait_for(state="visible", timeout=30_000)
                current_url = page.url
                print(f"[Lighthouse] Login page URL: {current_url}")

            # ── 4. Run Lighthouse ─────────────────────────────────────────────
            with allure.step(f"Run Lighthouse audit on: {current_url}"):
                command = [
                    lh_bin,
                    current_url,
                    "--port=9222",
                    "--output=html",
                    f"--output-path={report_path}",
                    "--only-categories=performance,accessibility,best-practices",
                    "--preset=desktop",
                    "--form-factor=desktop",
                    "--screenEmulation.disabled=true",
                    "--no-enable-error-reporting",
                ]
                print(f"[Lighthouse] Running: {' '.join(command)}")
                lh_result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                print(f"[Lighthouse] Exit code: {lh_result.returncode}")
                if lh_result.stdout:
                    print(f"[Lighthouse] STDOUT:\n{lh_result.stdout}")
                if lh_result.stderr:
                    print(f"[Lighthouse] STDERR:\n{lh_result.stderr}")

                if lh_result.returncode > 1:
                    pytest.fail(
                        f"Lighthouse exited with fatal error code "
                        f"{lh_result.returncode}.\n"
                        f"STDERR: {lh_result.stderr}\n"
                        f"STDOUT: {lh_result.stdout}"
                    )
        finally:
            context.close()

    shutil.rmtree(user_data_dir, ignore_errors=True)

    # ── 5. Validate & attach report ──────────────────────────────────────────
    if not os.path.exists(report_path):
        lh_debug = (
            f"\nExit code : {lh_result.returncode if lh_result else 'N/A'}"
            f"\nSTDOUT    : {lh_result.stdout if lh_result else ''}"
            f"\nSTDERR    : {lh_result.stderr if lh_result else ''}"
            f"\nTarget URL: {current_url}"
        )
        pytest.fail(
            f"Lighthouse HTML report was not created at: {report_path}"
            f"{lh_debug}"
        )

    with open(report_path, "r", encoding="utf-8") as fh:
        allure.attach(
            fh.read(),
            name="Lighthouse Report - Login Page",
            attachment_type=allure.attachment_type.HTML,
        )

    print(f"[Lighthouse] Report saved → {report_path}")
