"""No-op sub-step definitions for Gherkin '*' bullet steps.

These are documentation-only steps used beneath aggregate steps in feature
files to show what each aggregate does.  The real work is performed by the
aggregate step (e.g. ``When i create a new customer``); these steps just
*pass* so pytest-bdd does not report a missing-step error.
"""
from pytest_bdd import step


# ── New Quote ──────────────────────────────────────────────────────────────────

@step("I click the Quotes button")
def noop_click_quotes(): pass


@step("I click New Quote")
def noop_click_new_quote(): pass


@step("I select the Agent role")
def noop_select_agent(): pass


@step("I proceed to customer setup")
def noop_proceed_customer(): pass


# ── Customer Details ───────────────────────────────────────────────────────────

@step("I enter first name")
def noop_first_name(): pass


@step("I enter last name")
def noop_last_name(): pass


@step("I enter ZIP code")
def noop_zip(): pass


@step("I select customer type")
def noop_ctype(): pass


@step("I enter address")
def noop_address(): pass


@step("I enter city")
def noop_city(): pass


@step("I enter date of birth")
def noop_dob(): pass


@step("I enter phone number")
def noop_phone(): pass


@step("I enter email address")
def noop_email(): pass


@step("I search for existing customer")
def noop_search(): pass


@step("I create a new customer record")
def noop_create_customer(): pass


@step("I confirm and proceed past customer setup")
def noop_confirm_customer(): pass


# ── Quote Registration ─────────────────────────────────────────────────────────

@step("I enter producer")
def noop_producer(): pass


@step("I select program")
def noop_program(): pass


@step("I set effective date")
def noop_eff_date(): pass


# ── Auto Quote Summary ─────────────────────────────────────────────────────────

@step("I set billing method")
def noop_billing(): pass


@step("I answer false information question")
def noop_false_info(): pass


@step("I answer existing vehicle damage question")
def noop_damage(): pass


# ── Auto Driver Details ────────────────────────────────────────────────────────

@step("I enter driver gender")
def noop_gender(): pass


@step("I enter marital status")
def noop_marital(): pass


@step("I enter driver status")
def noop_driver_status(): pass


@step("I enter employment category")
def noop_employment(): pass


@step("I enter occupation")
def noop_occupation(): pass


@step("I enter license status")
def noop_license(): pass


@step("I answer SR-22 requirement")
def noop_sr22(): pass


# ── Auto Vehicle Details ───────────────────────────────────────────────────────

@step("I select vehicle year")
def noop_year(): pass


@step("I select vehicle make")
def noop_make(): pass


@step("I select vehicle model")
def noop_model(): pass


@step("I select vehicle specification")
def noop_spec(): pass


@step("I select vehicle use")
def noop_use(): pass


@step("I select vehicle ownership")
def noop_ownership(): pass


# ── Auto Coverage & Rating ─────────────────────────────────────────────────────

@step("I select coverage tier")
def noop_coverage(): pass


@step("I click rate quote")
def noop_rate(): pass


# ── Policy Creation (shared) ───────────────────────────────────────────────────

@step("I request issue")
def noop_issue(): pass


@step("I proceed through delivery preferences")
def noop_delivery(): pass


@step("I proceed through billing plan")
def noop_billing_plan(): pass


@step("I bind the policy")
def noop_bind(): pass


# ── HO Quote Summary ───────────────────────────────────────────────────────────

@step("I select program type")
def noop_ho_program(): pass


@step("I answer day care question")
def noop_day_care(): pass


@step("I answer underground oil tank question")
def noop_oil_tank(): pass


@step("I answer residence rented question")
def noop_rented(): pass


@step("I answer residence vacant question")
def noop_vacant(): pass


@step("I answer animals question")
def noop_animals(): pass


# ── HO Location Coverage ───────────────────────────────────────────────────────

@step("I select residence type")
def noop_residence(): pass


@step("I select homeowner coverage option")
def noop_ho_coverage(): pass


@step("I set replacement cost")
def noop_replacement(): pass


@step("I set all perils deductible")
def noop_perils(): pass


@step("I set windstorm deductible")
def noop_windstorm(): pass


@step("I set liability limit")
def noop_liability(): pass


@step("I set medical payments limit")
def noop_medical(): pass


@step("I enter year built")
def noop_year_built(): pass


@step("I select construction type")
def noop_construction(): pass


@step("I enter roof type")
def noop_roof(): pass


@step("I answer renovation question")
def noop_renovation(): pass


@step("I answer lived here question")
def noop_lived_here(): pass


@step("I answer any losses question")
def noop_losses(): pass


@step("I answer pool question")
def noop_pool(): pass


@step("I answer existing agency client question")
def noop_existing_client(): pass


@step("I answer refused to insure question")
def noop_refused(): pass


@step("I answer coverage declined question")
def noop_declined(): pass


# Additional HO Elements

@step("I review quote summary identity fields")
def noop_ho_review_quote_identity(): pass


@step("I review city information display fields")
def noop_ho_review_city_information(): pass


@step("I set contents limit")
def noop_ho_contents(): pass


@step("I set loss of use limit")
def noop_ho_loss_of_use(): pass


@step("I review other structures limit")
def noop_ho_other_structures(): pass


@step("I review mitigation dropdowns")
def noop_ho_mitigation_dropdowns(): pass


@step("I review security protection checkboxes")
def noop_ho_security_checkboxes(): pass


@step("I review premium summary actions")
def noop_ho_premium_actions(): pass


@step("I review delivery preference controls")
def noop_ho_delivery_controls(): pass


@step("I review billing plan controls")
def noop_ho_billing_controls(): pass


@step("I review verify billing actions")
def noop_ho_verify_billing(): pass


# Auto UW documentation steps

@step("I select SR-22 filing state when required")
def noop_sr22_filing_state(): pass


@step("I verify the expected underwriting condition")
def noop_verify_uw_condition(): pass


@step("I confirm every UW row is editable")
def noop_confirm_uw_editable(): pass


@step("I set all UW override flags to Yes")
def noop_set_uw_flags_yes(): pass


@step("I enter underwriter comments")
def noop_enter_uw_comments(): pass


@step("I accept the underwriting referral")
def noop_accept_uw_referral(): pass


@step("I select Email contact permission")
def noop_select_email_contact_permission(): pass


@step("I save contact information")
def noop_save_contact_information(): pass


@step("I continue past contact information")
def noop_continue_contact_information(): pass


@step("I click re-rate")
def noop_click_re_rate(): pass
