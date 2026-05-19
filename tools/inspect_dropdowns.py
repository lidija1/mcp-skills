"""
Inspect all dropdown options on the auto LOB pages by navigating the full
workflow up to each page and reading every combobox.
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

RESULTS = {}


def read_options(page, locator, label):
    try:
        locator.scroll_into_view_if_needed()
        locator.click()
        page.wait_for_timeout(700)
        items = page.locator(".x-boundlist-item").all()
        opts = [i.text_content().strip() for i in items if i.is_visible()]
        RESULTS[label] = opts if opts else ["(no items visible)"]
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    except Exception as exc:
        RESULTS[label] = f"ERROR: {exc}"


def ext_btn(page, label):
    page.evaluate(
        """(lbl) => {
            const btn = [...document.querySelectorAll('.x-btn-inner')]
                .find(el => el.textContent.trim().toLowerCase() === lbl.toLowerCase());
            if (btn) { let el = btn; while (el && !el.classList.contains('x-btn')) el = el.parentElement; if (el) el.click(); }
        }""",
        label,
    )


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Login via splash
    page.goto("https://inforcedev.oneshield.com/splash.html")
    page.wait_for_timeout(2000)
    page.locator("#employeePortal").click()
    page.wait_for_timeout(1500)
    page.get_by_role("textbox", name="PARTNER NUMBER*").fill(os.getenv("PARTNER_NUM", "0"))
    page.get_by_role("textbox", name="USERNAME*").fill(os.getenv("USERNAMEE", ""))
    page.get_by_role("textbox", name="PASSWORD*").fill(os.getenv("PASSWORD", ""))
    page.wait_for_timeout(500)
    page.get_by_role("button", name="login").click()
    page.wait_for_timeout(5000)
    print("Logged in:", "Goran" in page.inner_text("body"))

    # New Quote
    ext_btn(page, "quotes")
    page.wait_for_timeout(1000)
    ext_btn(page, ">>> new quote")
    page.wait_for_timeout(1500)
    print("After new quote click:", page.inner_text("body")[150:300])
    # Agent radio — use XPath as the framework does
    page.locator("//span[@osviewid='PAI_304805_OT_63_OI_2_BI_381805_RS']").click()
    page.wait_for_timeout(300)
    ext_btn(page, ">>> next")
    page.wait_for_timeout(2500)
    print("After next click (should be Producing Agency):", page.inner_text("body")[150:300])

    # Select agency — click entire row (not just radio) then use Direct Business path if needed
    page.evaluate(
        """() => {
        const rows = [...document.querySelectorAll('.x-grid-row')];
        if (rows.length > 0) {
            // Click the row itself which should select it in ExtJS single-select grid
            rows[0].click();
        }
    }"""
    )
    page.wait_for_timeout(600)
    print("Page after row click:", page.inner_text("body")[200:300])
    # Use Direct Business button which doesn't require agency selection
    ext_btn(page, "direct business")
    page.wait_for_timeout(3000)
    print("Page after Direct Business:", page.inner_text("body")[150:280])

    # Customer page — CustomerType
    print("Customer page:", "Search for a customer" in page.inner_text("body"))
    read_options(page, page.get_by_role("combobox", name="Customer Type"), "CustomerType")

    # Fill minimal customer and proceed
    ts = int(datetime.now().timestamp() * 1000)
    page.get_by_role("textbox", name="First Name").fill("Drop")
    page.get_by_role("textbox", name="Last Name").fill("Inspector")
    page.get_by_role("textbox", name="ZIP Code").fill("01101")
    page.expect_response("**/FieldProcessorServlet*")
    page.get_by_role("combobox", name="Date of Birth").fill("06/15/1981")
    page.get_by_role("textbox", name="Phone").fill("413-555-0001")
    page.get_by_role("textbox", name="Email").fill(f"drop_{ts}@inspect.com")
    page.get_by_role("textbox", name="City").fill("Springfield")
    page.get_by_role("textbox", name="Address Line 1").fill("1 Inspector Lane")
    page.evaluate(
        """() => {
        const btn = [...document.querySelectorAll('.x-btn-inner')]
            .find(el => el.textContent.trim() === '>>> Search');
        if (btn) { let el = btn; while (el && !el.classList.contains('x-btn')) el = el.parentElement; if (el) el.click(); }
    }"""
    )
    page.wait_for_timeout(2500)
    page.get_by_role("button", name=">>> Create A New Customer").click()
    page.wait_for_timeout(2500)
    page.get_by_role("button", name=">>> next").click()
    page.wait_for_timeout(3500)
    page.wait_for_selector("role=button[name='>>> skip']", timeout=15000)
    page.get_by_role("button", name=">>> skip").click()
    page.wait_for_timeout(3000)

    # Quote Registration — Program
    print("Quote reg:", "Producer" in page.inner_text("body"))
    read_options(page, page.get_by_role("combobox", name="Program*"), "Program")

    page.get_by_role("combobox", name="Producer*").fill("Janis Irey")
    page.wait_for_timeout(300)
    eff = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
    page.get_by_role("combobox", name="Effective Date*").fill(eff)
    page.get_by_role("combobox", name="Program*").click()
    page.wait_for_timeout(400)
    page.get_by_role("option", name="Personal Auto", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Next").click()
    page.wait_for_timeout(3000)

    # Quote Summary — BillingMethod
    print("Quote summary:", "Billing Method" in page.inner_text("body"))
    read_options(page, page.get_by_role("combobox", name="Billing Method*"), "BillingMethod")

    page.get_by_role("combobox", name="Billing Method*").fill("Direct Billed")
    page.wait_for_timeout(800)
    for text, ans in [
        ("Has anyone knowingly provided material, false, or misleading information", "No"),
        ("Does any vehicle have any existing damage?", "No"),
    ]:
        try:
            grp = page.get_by_role("radiogroup").filter(has_text=text).first
            grp.get_by_label(ans).dispatch_event("click")
        except Exception:
            pass
    page.get_by_role("button", name="save changes").click()
    page.wait_for_timeout(2000)
    page.get_by_role("link", name="Drop").first.click()
    page.wait_for_timeout(2000)

    # Driver Info
    print("Driver info:", "Gender" in page.inner_text("body"))
    for combo_name, key in [
        ("Gender*", "Gender"),
        ("Marital Status*", "MaritalStatus"),
        ("Driver Status*", "DriverStatus"),
        ("Employment Category", "EmploymentCategory"),
        ("License Status*", "LicenseStatus"),
    ]:
        read_options(page, page.get_by_role("combobox", name=combo_name), key)

    # Occupation (depends on Employment Category — set Employed first)
    page.get_by_role("combobox", name="Employment Category").fill("Employed")
    page.wait_for_timeout(700)
    read_options(page, page.get_by_role("combobox", name="Occupation"), "Occupation")

    # Fill driver info and go to vehicle
    page.get_by_role("combobox", name="Gender*").fill("Male")
    page.wait_for_timeout(300)
    page.get_by_role("combobox", name="Marital Status*").fill("Single")
    page.wait_for_timeout(300)
    page.get_by_role("combobox", name="Driver Status*").fill("Active (rated)")
    page.wait_for_timeout(300)
    page.get_by_role("combobox", name="Occupation").fill("Day Care")
    page.wait_for_timeout(300)
    page.get_by_role("combobox", name="License Status*").fill("Active License")
    page.wait_for_timeout(300)
    try:
        grp = page.get_by_role("radiogroup").filter(has_text="Certificate of Insurance Required").first
        grp.get_by_label("No").dispatch_event("click")
    except Exception:
        pass
    page.get_by_role("button", name="save changes").click()
    page.wait_for_timeout(1500)
    page.get_by_role("link", name="Vehicle_1").click()
    page.wait_for_timeout(2000)

    # Vehicle Info — VehicleUse and Ownership
    print("Vehicle info:", "Vehicle Type" in page.inner_text("body"))
    for combo_name, key in [
        ("Vehicle Use*", "VehicleUse"),
        ("Ownership", "Ownership"),
    ]:
        read_options(page, page.get_by_role("combobox", name=combo_name), key)

    # Fill vehicle and go to coverages
    page.get_by_role("combobox", name="Year*").click()
    page.wait_for_timeout(400)
    page.locator("//li[text()='2018']").click()
    page.wait_for_timeout(600)
    page.get_by_role("combobox", name="Make*").click()
    page.wait_for_timeout(400)
    page.locator("//li[text()='BMW']").click()
    page.wait_for_timeout(600)
    page.get_by_role("combobox", name="Model*").click()
    page.wait_for_timeout(400)
    page.locator("//li[text()='M3']").click()
    page.wait_for_timeout(600)
    page.get_by_role("combobox", name="Specification*").click()
    page.wait_for_timeout(400)
    page.locator(".x-boundlist-item").first.click()
    page.wait_for_timeout(400)
    page.get_by_role("combobox", name="Vehicle Use*").click()
    page.wait_for_timeout(400)
    page.locator("//li[text()='Pleasure']").click()
    page.wait_for_timeout(400)
    page.get_by_role("combobox", name="Ownership").fill("Owned")
    page.wait_for_timeout(400)
    page.get_by_role("button", name="save changes").click()
    page.wait_for_timeout(1500)
    page.get_by_role("link", name="Coverages").click()
    page.wait_for_timeout(2000)

    # Policy Term — PolicyCoverage
    print("Coverages:", "Policy Coverage" in page.inner_text("body"))
    read_options(page, page.get_by_role("combobox", name="Policy Coverage Option*"), "PolicyCoverage")

    browser.close()

print("\n=== DROPDOWN OPTIONS FOUND IN APP ===")
for k, v in RESULTS.items():
    print(f"\n{k}:")
    if isinstance(v, list):
        for opt in v:
            print(f"  - {opt}")
    else:
        print(f"  {v}")
