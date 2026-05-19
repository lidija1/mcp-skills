Feature: Personal Auto Underwriting Rules
  Validate that specific UW rules are triggered and surfaced on the underwriting
  referral page during the Personal Auto quote workflow.

  All 12 scenarios trigger soft-referral rules that fire after clicking Rate Quote
  on the Coverages page. The three confirmed UW triggers are:
    - SR-22 required  : "SR-22 / Certificate of Insurance Indicator is checked"
    - Suspended/Revoked license : "An operator of this policy has a driver license status that is revoked or suspended."
    - Driver under 25 : "All drivers under 25 years of age."

  Background:
    Given The user is logged in with valid credentials

  @uw_rules @auto
  Scenario Outline: Soft UW referral triggered at quote rating — <TC_ID>
    Given the data is loaded "testdata/static/auto/AutoUWRulesData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide quote summary PA info
    When I provide Driver Details
    When I provide Vehicle Details
    When I select coverage and rate the quote
    Then the UW referral page shows a "<UWType>" condition containing "<ExpectedCondition>"

    Examples:
      | TC_ID     | UWType       | ExpectedCondition                                              |
      | UW_TC_001 | Underwriting | SR-22 / Certificate of Insurance Indicator is checked          |
      | UW_TC_002 | Underwriting | driver license status that is revoked or suspended             |
      | UW_TC_003 | Underwriting | All drivers under 25 years of age                              |
      | UW_TC_004 | Underwriting | driver license status that is revoked or suspended             |
      | UW_TC_005 | Underwriting | All drivers under 25 years of age                              |
      | UW_TC_006 | Underwriting | driver license status that is revoked or suspended             |
      | UW_TC_007 | Underwriting | SR-22 / Certificate of Insurance Indicator is checked          |
      | UW_TC_008 | Underwriting | All drivers under 25 years of age                              |
      | UW_TC_009 | Underwriting | driver license status that is revoked or suspended             |
      | UW_TC_010 | Underwriting | SR-22 / Certificate of Insurance Indicator is checked          |
      | UW_TC_011 | Underwriting | All drivers under 25 years of age                              |
      | UW_TC_012 | Underwriting | driver license status that is revoked or suspended             |
      | UW_TC_013 | Underwriting | SR-22 / Certificate of Insurance Indicator is checked          |
      | UW_TC_014 | Underwriting | All drivers under 25 years of age                              |
