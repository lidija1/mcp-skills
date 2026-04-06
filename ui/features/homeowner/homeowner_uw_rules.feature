Feature: Homeowner Underwriting Rules
  Validate that UW rules are triggered and surfaced on the underwriting
  referral page during the Homeowner quote workflow.

  UW trigger points:
    - Page 1 save (Quote Summary) : eligibility radios — ResidenceVacant, DayCare, Animals
    - Page 2 save (Location Coverage) : Renovation=Yes fires a hard-stop before Rate Quote
    - After Rate Quote : old Frame construction, high-risk roof types, Refused/Declined

  Confirmed condition text (substring match, case-sensitive):
    Renovation hard-stop  : "Property is under construction"
    Old Frame (>10 yrs)   : "Building construction type is 'Frame'. It is also more than 10 years old."

  Note on unconfirmed conditions (HO_UW_004 – HO_UW_009):
    These cases are expected to trigger a UW referral. The condition text substrings
    used below are initial guesses based on the trigger field names. Run with --headed -s
    to observe the actual gridcell text, then update the Examples table as needed.

  Background:
    Given The user is logged in with valid credentials

  @uw_rules @homeowner
  Scenario Outline: UW referral triggered during homeowner quote — <TC_ID>
    Given the data is loaded "testdata/static/HomeownerUWRulesData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide quote summary HO info for UW testing
    When I provide location coverage info for UW testing
    Then the UW referral page shows a "<UWType>" condition containing "<ExpectedCondition>"

    Examples:
      | TC_ID     | UWType       | ExpectedCondition                                                             |
      # ── Renovation hard-stop (fires on Location Coverage save) ──────────────────
      | HO_UW_002 | Hard-Stop    | Property is under construction                                                |
      | HO_UW_003 | Hard-Stop    | Property is under construction                                                |
      # ── Old Frame construction alone (fires after Rate Quote) ────────────────────
      | HO_UW_004 | Underwriting | Building construction type is 'Frame'                                         |
      # ── Bind Information flags (fires at Rate Quote) ─────────────────────────────
      | HO_UW_005 | Underwriting | cancelled or refused to insure                                                |
      # ── Page 1 eligibility hard-stops (fire on Quote Summary save) ───────────────
      | HO_UW_006 | Hard-Stop    | vacant                                                                        |
      | HO_UW_007 | Hard-Stop    | Day Care                                                                      |
      # ── High-risk roof types (fire after Rate Quote) ─────────────────────────────
      | HO_UW_008 | Hard-Stop    | Flat                                                                          |
      | HO_UW_009 | Hard-Stop    | Asbestos                                                                      |
