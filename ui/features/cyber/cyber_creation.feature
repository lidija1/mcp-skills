Feature: Cyber Insurance Creation

  Background:
    Given The user is logged in with valid credentials

  @smoke @cyber
  Scenario Outline: Create a new cyber policy
    Given the data is loaded "testdata/static/CyberData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide Cyber quote details
    When I rate the Cyber quote
    When I request issue for the Cyber quote
    When I complete delivery preferences
    When I complete billing plan
    When I bind the Cyber policy

    Examples:
      | TC_ID      |
      | TC_ID_0001 |
      | TC_ID_0002 |
