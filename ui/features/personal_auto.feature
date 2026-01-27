Feature: Personal Auto Creation

  Background: Login as Claim Adjuster
    Given The user is logged in with valid credentials

  @smoke @auto
  Scenario Outline: Create a new personal auto policy
    Given the data is loaded "testdata/static/AutoData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide quote summary PA info
    When I provide Driver Details
    When I provide Vehicle Details
    Given I provide policy term details
    Then I create a policy from the quote

    Examples:
      | TC_ID      |
      | TC_ID_0003 |
      | TC_ID_0001 |
