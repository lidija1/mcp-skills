"""
Lighthouse performance & accessibility audit on the Create Customer page.

How it works
────────────
1. Chromium is launched with --remote-debugging-port=9222 so that Lighthouse
   can attach to the *already-authenticated* browser session instead of
   opening a fresh, unauthenticated instance.
2. Playwright drives the full login → Create Customer navigation flow using the
   existing page-object classes (LoginPage, NewQuotePage).
3. The globally-installed `lighthouse` CLI (added in the Dockerfile via
   `npm install -g lighthouse`) connects on port 9222, audits the live page,
   and writes an HTML report.
4. The report is attached to the Allure run for easy inspection.

Run locally
───────────
    pytest ui/tests/lighthouse_tests/create_customer_lighthouse.py -v -s

Run in Docker (see docker-compose.yml → tests-lighthouse)
──────────────────────────────────────────────────────────
    docker-compose run --rm tests-lighthouse
"""

import os
import shutil
import subprocess
import tempfile

import allure
import pytest
from playwright.sync_api import sync_playwright

from ui.pages.common.login_page import LoginPage
from ui.pages.common.new_quote_page import NewQuotePage


@pytest.mark.lighthouse
@allure.epic("Performance")
@allure.feature("Lighthouse Audits")
@allure.story("Create Customer Page")
@allure.title("Lighthouse audit - Create Customer page (post-login)")
def test_create_customer_page_lighthouse():
    """
    Full Lighthouse audit (performance + accessibility + best-practices)
    executed against the Create Customer page after a real authenticated login.

    Why launch_persistent_context?
    ───────────────────────────────
    browser.new_context() creates an *isolated* context whose cookies are NOT
    visible to Lighthouse when it opens a new tab via --port=9222.
    launch_persistent_context() writes the profile to a real on-disk directory
    that is shared with the same Chrome process, so Lighthouse inherits the
    authenticated session automatically.
    """
    report_dir = os.path.abspath("reports/lighthouse")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "create_customer_audit.html")

    # ── Verify lighthouse is on PATH before launching the browser ────────────
    lh_bin = str(shutil.which("lighthouse") or "")
    print(f"\n[Lighthouse] Binary resolved to: {lh_bin or '(not found)'}")
    if not lh_bin:
        pytest.fail(
            "'lighthouse' binary not found in PATH.\n"
            "Make sure the Dockerfile contains: RUN npm install -g lighthouse"
        )

    # Temporary user-data-dir shared between Playwright and Lighthouse
    user_data_dir = tempfile.mkdtemp(prefix="pw-lh-")
    current_url: str | None = None
    lh_result = None

    with sync_playwright() as p:
        # ── Launch with a persistent profile so cookies are on disk ──────────
        # Lighthouse will open a new tab in the DEFAULT context of this same
        # Chrome process and will automatically have access to the cookies that
        # Playwright sets during the login / navigation steps below.
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
            # ── 1. Login ──────────────────────────────────────────────────────
            with allure.step("Login to OneShield"):
                login = LoginPage(page)
                login.navigate()
                login.click_splash_button()
                login.fill_credentials_from_env()
                login.click_login()

            # ── 2. Navigate to Create Customer page ───────────────────────────
            with allure.step("Navigate to Create Customer page"):
                create_customer = NewQuotePage(page)
                create_customer.click_quotes_button()
                create_customer.click_new_quote_button()
                create_customer.click_agent_radio_button()
                create_customer.click_next_button()

            page.wait_for_load_state("networkidle", timeout=30_000)
            current_url = page.url
            print(f"[Lighthouse] Target URL: {current_url}")

            # ── 3. Run Lighthouse ─────────────────────────────────────────────
            # --port=9222 attaches to the already-running Chrome process.
            # Because we used a persistent context the session cookies are
            # available on disk and Lighthouse's new tab will be authenticated.
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
                    # NOTE: --quiet is intentionally omitted so all output is
                    # captured and visible on failure for easier diagnosis.
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

                # 0 = success, 1 = audit warnings (report still written)
                # >1 = fatal error (lighthouse could not run at all)
                if lh_result.returncode > 1:
                    pytest.fail(
                        f"Lighthouse exited with fatal error code "
                        f"{lh_result.returncode}.\n"
                        f"STDERR: {lh_result.stderr}\n"
                        f"STDOUT: {lh_result.stdout}"
                    )
        finally:
            context.close()

    # Clean up the temporary profile directory
    shutil.rmtree(user_data_dir, ignore_errors=True)

    # ── 4. Validate & attach report ──────────────────────────────────────────
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
            name="Lighthouse Report - Create Customer Page",
            attachment_type=allure.attachment_type.HTML,
        )

    print(f"[Lighthouse] Report saved → {report_path}")
