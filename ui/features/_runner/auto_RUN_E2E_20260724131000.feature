Feature: Runner scratch - 28-year-old employed auto driver

  Background: Login as Claim Adjuster
    Given The user is logged in with valid credentials

  @auto @runner
  Scenario Outline: Runner scratch e2e
    Given the data is loaded "testdata/_runner/auto_RUN_E2E_20260724131000.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide quote summary PA info
    When I provide Driver Details
    When I provide Vehicle Details
    Given I provide policy term details
    When I create a policy from the quote
    Then I read and extract policy summary page details

    Examples:
      | TC_ID                   |
      | RUN_E2E_20260724131000  |
