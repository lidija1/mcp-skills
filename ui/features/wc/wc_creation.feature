Feature: Workers Compensation Creation

  Background:
    Given The user is logged in with valid credentials

  @smoke @wc
  Scenario Outline: Create a new workers compensation policy
    Given the data is loaded "testdata/static/WCData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I explore the WC quote page

    Examples:
      | TC_ID      |
      | TC_ID_0001 |
