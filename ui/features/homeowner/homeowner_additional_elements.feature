Feature: Homeowner Discovered Elements

  Background:
    Given The user is logged in with valid credentials

  @homeowner @additional_elements
  Scenario Outline: Exercise discovered Homeowner controls without binding
    Given the data is loaded "testdata/static/homeowner/HomeownerDiscoveryData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I exercise the configured Homeowner discovered-element flow
    Then the Homeowner discovery flow stops before rating and binding

    Examples:
      | TC_ID      | Description                                                                  |
      | HO_DISC_001 | Verify every discovered Homeowner dropdown and selectable option           |
      | HO_DISC_002 | Verify prior-address fields appear when residence history is under three years |
      | HO_DISC_003 | Verify all discovered Homeowner optional coverage checkboxes               |
      | HO_DISC_004 | Open Reinsurance Add flow and verify hidden detail fields                  |
      | HO_DISC_005 | Open Inspection Add flow and exercise request fields and dropdowns         |
      | HO_DISC_006 | Open Manuscripts Add flow and verify search and manuscript controls        |
      | HO_DISC_007 | Open Additional Interests and verify all Add entry actions                 |
