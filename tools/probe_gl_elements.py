"""
GL LOB discovery probe.

Navigates every GL screen (Risk Address, Basic Policy Information, Coverage and
Limits, Liability Location List, Rating Basis and Classification), snapshots all
visible interactive controls, collects every dropdown option list, and probes
conditional fields (ForeignSales Yes path, DeductibleType / DeductibleApplies
dependencies, GL class-code drill-down).  Does NOT rate or bind.

Usage:
    python tools/probe_gl_elements.py [--headed] [--slow-mo 100]
"""

import json
import re
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.pages.common.customer_page import CustomerPage
from ui.pages.common.login_page import LoginPage
from ui.pages.common.new_quote_page import NewQuotePage
from ui.pages.common.quote_registration_page import QuoteRegistrationPage
from ui.pages.gl.gl_coverages_and_limits_page import GeneralLiabilityCoverageAndLimitsPage
from ui.pages.gl.gl_liability_location_list_page import GeneralLiabilityLiabilityLocationListPage
from ui.pages.gl.gl_policy_information_page import GeneralLiabilityBasicPolicyInformationPage
from ui.pages.gl.gl_rating_page import GeneralLiabilityRatingBasisAndClassificationPage
from ui.pages.gl.gl_risk_address_page import GeneralLiabilityRiskAddressPage

OUTPUT_DIR = ROOT / "reports" / "lob-discovery" / "gl"

# ── helpers ──────────────────────────────────────────────────────────────────

def load_case(tc_id="GL_001"):
    data_path = ROOT / "testdata" / "static" / "gl" / "GLData.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    data = next(
        (deepcopy(case) for case in payload["testCases"] if case["TC_ID"] == tc_id),
        None,
    )
    if data is None:
        raise ValueError(f"Unknown GL TC_ID: {tc_id}")
    ts = datetime.now().strftime("%H%M%S")
    data["Email"] = f"gl_probe_{ts}_{{timestamp}}@example.com"
    data["FirstName"] = "GL"
    data["LastName"] = f"Probe{ts}"
    return data


def visible_controls(page):
    """Return all visible interactive elements with metadata."""
    return page.evaluate(
        """() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = window.getComputedStyle(el);
                return r.width > 0 && r.height > 0
                    && s.display !== 'none'
                    && s.visibility !== 'hidden';
            };
            const norm = v => (v || '').replace(/\\s+/g, ' ').trim();
            return [...document.querySelectorAll(
                'input, textarea, select, button, [role="combobox"], '
                + '[role="checkbox"], [role="radio"], [role="button"], a'
            )]
            .filter(visible)
            .map(el => {
                const id = el.id || '';
                const explicitLabel = id
                    ? document.querySelector('label[for="' + CSS.escape(id) + '"]')
                    : null;
                const container = el.closest(
                    '.x-field, .x-form-item, li, td, div[class*="field"]'
                );
                const nearbyLabel = container
                    ? container.querySelector('label, .x-form-item-label, .x-form-cb-label')
                    : null;
                return {
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type'),
                    role: el.getAttribute('role'),
                    label: norm(
                        el.getAttribute('aria-label')
                        || (explicitLabel && explicitLabel.textContent)
                        || (nearbyLabel && nearbyLabel.textContent)
                    ),
                    text: norm(el.textContent),
                    value: 'value' in el ? norm(el.value) : '',
                    required: el.required || el.getAttribute('aria-required') === 'true',
                    disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
                    osviewid: el.getAttribute('osviewid'),
                    name: el.getAttribute('name'),
                };
            })
            .filter(item => item.label || item.text || item.value);
        }"""
    )


def collect_options(page, locator):
    """Open an ExtJS combobox and collect all visible option texts."""
    try:
        locator.scroll_into_view_if_needed()
        locator.click()
        page.wait_for_function(
            """() => [...document.querySelectorAll('.x-boundlist')]
                .some(l => {
                    const r = l.getBoundingClientRect();
                    const s = window.getComputedStyle(l);
                    return r.width > 0 && r.height > 0
                        && s.display !== 'none' && s.visibility !== 'hidden';
                })""",
            timeout=5000,
        )
        options = page.evaluate(
            """() => {
                const lists = [...document.querySelectorAll('.x-boundlist')]
                    .filter(l => {
                        const r = l.getBoundingClientRect();
                        const s = window.getComputedStyle(l);
                        return r.width > 0 && r.height > 0
                            && s.display !== 'none' && s.visibility !== 'hidden';
                    });
                const active = lists[lists.length - 1];
                return [...active.querySelectorAll('.x-boundlist-item')]
                    .filter(i => {
                        const r = i.getBoundingClientRect();
                        return r.width > 0 && r.height > 0;
                    })
                    .map(i => (i.textContent || '').replace(/\\s+/g, ' ').trim())
                    .filter(Boolean);
            }"""
        )
        page.keyboard.press("Escape")
        return options
    except Exception as exc:
        page.keyboard.press("Escape")
        return {"error": str(exc)}


def collect_radio_options(page, question_text):
    """Collect radio-button labels for a given question group."""
    try:
        return page.evaluate(
            """(q) => {
                const norm = v => (v || '').replace(/\\s+/g, ' ').trim();
                return [...document.querySelectorAll('.x-form-check-group, fieldset')]
                    .filter(g => norm(g.textContent).toLowerCase().includes(q.toLowerCase()))
                    .flatMap(g => [...g.querySelectorAll('[role="radio"], input[type="radio"]')]
                        .map(el => {
                            const container = el.closest('.x-form-cb-wrap, label, td, .x-form-item');
                            const label = container
                                ? container.querySelector('.x-form-cb-label, label')
                                : null;
                            return norm(
                                el.getAttribute('aria-label')
                                || (label && label.textContent)
                                || el.value
                            );
                        }).filter(Boolean)
                    );
            }""",
            question_text,
        )
    except Exception as exc:
        return {"error": str(exc)}


# ── screen helpers ────────────────────────────────────────────────────────────

def snap_risk_address(page, data):
    risk = GeneralLiabilityRiskAddressPage(page)
    risk.risk_address_steps(data)
    return {
        "screen": "RiskAddress",
        "controls": visible_controls(page),
    }


def snap_policy_info(page, data):
    po = GeneralLiabilityBasicPolicyInformationPage(page)
    po.wait_for_loader_to_disappear()
    snap = {
        "screen": "BasicPolicyInformation",
        "controls": visible_controls(page),
        "dropdownOptions": {
            "BillingMethod": collect_options(page, po.billing_method),
            "AuditFrequency": collect_options(page, po.audit_frequency),
            "LossHistory": collect_options(page, po.loss_history),
        },
    }
    po.basic_policy_information_steps(data)
    return snap


def snap_coverage_and_limits(page, data):
    co = GeneralLiabilityCoverageAndLimitsPage(page)
    co.open_coverage_and_limits()
    co.wait_for_loader_to_disappear()

    coverage_type_options = page.evaluate(
        """() => [...document.querySelectorAll('[role="option"]')]
            .filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0;
            })
            .map(el => (el.textContent || '').replace(/\\s+/g, ' ').trim())
            .filter(Boolean)"""
    )

    co.select_coverage_type(data)
    co.wait_for_loader_to_disappear()

    controls_after_coverage = visible_controls(page)

    dropdown_options = {
        "CoverageType": coverage_type_options,
        "PolicyType": collect_options(page, co.policy_type),
        "FormType": collect_options(page, co.form_type),
        "DefenseTreatment": collect_options(page, co.defense_treatment),
        "ForeignSales": collect_radio_options(page, "foreign sales"),
        "LimitVentilationRequired": collect_options(page, co.limit_ventilation_required),
        "EachOccurrenceLimit": collect_options(page, co.each_occurrence_limit),
        "GeneralAggregateLimit": collect_options(page, co.general_aggregate_limit),
        "PersonalAndAdvertisingInjuryLimit": collect_options(page, co.personal_and_advertising_injury),
        "ProductsAndCompletedOperationsAggregateLimit": collect_options(page, co.products_and_completed_operations),
        "FireDamageLegalLiabilityLimitAnyOneFire": collect_options(page, co.fire_damage_legal_liability),
        "MedicalExpenseLimitAnyOnePerson": collect_options(page, co.medical_expense_limit),
        "GeneralLiabilityDeductible": collect_options(page, co.general_liability_deductible),
        "DeductibleType": collect_options(page, co.deductible_type),
        "DeductibleApplies": collect_options(page, co.deductible_applies),
    }

    # Probe ForeignSales=Yes path — check for conditional fields
    co.set_foreign_sales({"ForeignSales": "Yes"})
    co.wait_for_loader_to_disappear()
    controls_foreign_sales_yes = visible_controls(page)
    co.set_foreign_sales({"ForeignSales": "No"})
    co.wait_for_loader_to_disappear()

    # Probe deductible conditional: set a deductible and capture deductible_type/applies options
    co.set_general_liability_deductible(data)
    co.wait_for_loader_to_disappear()
    controls_after_deductible = visible_controls(page)
    dropdown_options["DeductibleType_afterSet"] = collect_options(page, co.deductible_type)
    dropdown_options["DeductibleApplies_afterSet"] = collect_options(page, co.deductible_applies)

    # All fields already set above — just save
    co.set_policy_type(data)
    co.set_form_type(data)
    co.set_defense_treatment(data)
    co.set_foreign_sales(data)
    co.set_limit_ventilation_required(data)
    co.set_each_occurrence_limit(data)
    co.set_general_aggregate_limit(data)
    co.set_personal_and_advertising_injury(data)
    co.set_products_and_completed_operations(data)
    co.set_fire_damage_legal_liability(data)
    co.set_medical_expense_limit(data)
    co.set_deductible_type(data)
    co.set_deductible_applies(data)
    co.set_rating_modifiers(data)
    co.set_optional_endorsements(data)

    locator_validation = {}
    for key, locator in (
        ("HiredAutoCoverage", co.hired_auto_coverage),
        ("NonOwnedAutoCoverage", co.non_owned_auto_coverage),
        ("EmployeeBenefitsCoverage", co.employee_benefits_coverage),
        ("LiquorLiabilityCoverage", co.liquor_liability_coverage),
        ("GLEnhancementEndorsement", co.gl_enhancement_endorsement),
        ("GLManualCoverages", co.gl_manual_coverages),
        ("ContractualLiabilityExclusion", co.contractual_liability_exclusion),
        ("ExcludeEmployeesAsAdditionalInsureds", co.exclude_employees_additional_insureds),
        ("HazardsDesignatedPremises", co.hazards_designated_premises),
        ("ScheduleMod", co.schedule_mod),
        ("Judgment", co.judgment),
        ("CommissionMod", co.commission_mod),
        ("ExperienceMod", co.experience_mod),
    ):
        count = locator.count()
        locator_validation[key] = {
            "active": data.get(key) is True or bool(str(data.get(key, "")).strip()),
            "count": count,
            "visible": locator.is_visible() if count else False,
            "role": locator.get_attribute("role") if count else None,
            "type": locator.get_attribute("type") if count else None,
        }
    co.click_coverage_save()

    return {
        "screen": "CoverageAndLimits",
        "controlsAfterCoverageType": controls_after_coverage,
        "controlsForeignSalesYes": controls_foreign_sales_yes,
        "controlsAfterDeductible": controls_after_deductible,
        "dropdownOptions": dropdown_options,
        "locatorValidation": locator_validation,
    }


def snap_liability_location_list(page, data):
    ll = GeneralLiabilityLiabilityLocationListPage(page)
    controls_before = visible_controls(page)
    ll.open_liability_location_list(data)
    controls_after = visible_controls(page)
    ll.click_location_save()
    return {
        "screen": "LiabilityLocationList",
        "controlsBefore": controls_before,
        "controlsAfterStateClick": controls_after,
    }


def snap_rating(page, data):
    ra = GeneralLiabilityRatingBasisAndClassificationPage(page)
    ra.wait_for_loader_to_disappear()

    # Capture all visible GL class-code options (listbox)
    class_code_options = page.evaluate(
        """() => [...document.querySelectorAll('[role="option"], li.x-boundlist-item')]
            .filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0;
            })
            .map(el => (el.textContent || '').replace(/\\s+/g, ' ').trim())
            .filter(Boolean)"""
    )

    controls_before_class = visible_controls(page)

    # Select class code and probe description dropdown options
    ra.open_rating_basis_and_classification(data)
    ra.select_class_code(data)
    ra.wait_for_loader_to_disappear()
    controls_after_class = visible_controls(page)

    # Collect GL class description options by typing the code prefix
    gl_desc_options = []
    try:
        locator = ra.gl_class_description
        locator.scroll_into_view_if_needed()
        locator.click()
        locator.fill("")
        locator.fill(str(data["GLClassCode"]))
        page.wait_for_function(
            """(code) => [...document.querySelectorAll('.x-boundlist-item')]
                .some(el => {
                    const r = el.getBoundingClientRect();
                    const s = window.getComputedStyle(el);
                    const label = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
                    return r.width > 0 && r.height > 0
                        && s.visibility !== 'hidden' && s.display !== 'none'
                        && label.startsWith(code);
                })""",
            arg=str(data["GLClassCode"]),
            timeout=10000,
        )
        gl_desc_options = page.evaluate(
            """() => [...document.querySelectorAll('.x-boundlist-item')]
                .filter(el => {
                    const r = el.getBoundingClientRect();
                    const s = window.getComputedStyle(el);
                    return r.width > 0 && r.height > 0
                        && s.visibility !== 'hidden' && s.display !== 'none';
                })
                .map(el => (el.textContent || '').replace(/\\s+/g, ' ').trim())
                .filter(Boolean)"""
        )
        page.keyboard.press("Escape")
    except Exception as exc:
        page.keyboard.press("Escape")
        gl_desc_options = {"error": str(exc)}

    ra.set_gl_class_description(data)
    ra.set_exposure(data)
    ra.click_rating_save()
    controls_after_save = visible_controls(page)

    return {
        "screen": "RatingBasisAndClassification",
        "classCodeOptions": class_code_options,
        "controlsBeforeClassCode": controls_before_class,
        "controlsAfterClassCode": controls_after_class,
        "glClassDescriptionOptions": gl_desc_options,
        "controlsAfterSave": controls_after_save,
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--headed", action="store_true", default=True)
    parser.add_argument("--slow-mo", type=int, default=50)
    parser.add_argument("--tc-id", default="GL_001")
    parser.add_argument("--stop-after-coverage", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=True)
    data = load_case(args.tc_id)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed, slow_mo=args.slow_mo)
        context = browser.new_context(viewport=None)
        page = context.new_page()

        login = LoginPage(page)
        import os
        base_url = os.getenv("BASE_URL", "https://inforcedev.oneshield.com/oneshield/")
        login.navigate(base_url)
        if hasattr(login, "employee_portal") and page.locator(login.employee_portal).is_visible(timeout=3000):
            login.click_splash_button()
        login.wait_for_login_page()
        login.fill_credentials_from_env()
        login.click_login()

        NewQuotePage(page).new_quote_steps()
        CustomerPage(page).customer_steps(data)
        QuoteRegistrationPage(page).quote_registration_steps(data)

        screens = {}

        print("[1/5] Risk Address")
        screens["RiskAddress"] = snap_risk_address(page, data)

        print("[2/5] Basic Policy Information")
        screens["BasicPolicyInformation"] = snap_policy_info(page, data)

        print("[3/5] Coverage and Limits")
        screens["CoverageAndLimits"] = snap_coverage_and_limits(page, data)

        if not args.stop_after_coverage:
            print("[4/5] Liability Location List")
            screens["LiabilityLocationList"] = snap_liability_location_list(page, data)

            print("[5/5] Rating Basis and Classification")
            screens["RatingBasisAndClassification"] = snap_rating(page, data)

        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        result = {
            "schemaVersion": 1,
            "lob": "gl",
            "generatedAt": timestamp,
            "quotesCreated": 1,
            "rated": False,
            "boundPolicies": 0,
            "screens": screens,
        }

        ts_file = datetime.now().strftime("%Y%m%dT%H%M%S")
        history_dir = OUTPUT_DIR / "history"
        history_dir.mkdir(parents=True, exist_ok=True)

        latest_path = OUTPUT_DIR / "latest.json"
        latest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        (history_dir / f"{ts_file}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

        baseline_path = OUTPUT_DIR / "baseline.json"
        if not baseline_path.exists():
            baseline_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print("Baseline written.")

        print(f"\nResults saved to {latest_path}")
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
