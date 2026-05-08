Feature: General Liability creation

  Background:
    Given The user is logged in with valid credentials

  @general_liability
  Scenario Outline: Exercise the General Liability creation flow
    Given the data is loaded "testdata/static/general_liability/GeneralLiabilityData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide general liability risk address details
    When I provide general liability basic policy information
    When I provide general liability coverage and limits
    When I provide general liability liability location list details
    When I provide general liability rating basis and classification details
    When I rate the general liability quote
    When I request issue for the general liability quote
    When I proceed to the general liability billing plan
    When I complete the general liability billing plan
    When I bind the general liability policy
    Then the general liability flow is complete
    # ── Policy Summary ────────────────────────────────────────────────────────
    Then I read and extract policy summary page details for general liability
    Examples:
      | TC_ID      |
      | TC_ID_0001 |
