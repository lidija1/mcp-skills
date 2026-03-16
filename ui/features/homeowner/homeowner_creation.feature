Feature: Homeowner Creation

  Background: Login as Claim Adjuster
    Given The user is logged in with valid credentials

  @smoke @homeowner
  Scenario Outline: Create a new homeowner policy
    Given the data is loaded "testdata/static/HomeData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide quote summary HO info
    When I provide location coverage info
    When I create a policy from the quote




    Examples:
      | TC_ID      |
      | TC_ID_0001 |
#      | TC_ID_0002 |
#      | TC_ID_0003 |
#      | TC_ID_0004 |
#      | TC_ID_0005 |
#      | TC_ID_0006 |
#      | TC_ID_0007 |
#      | TC_ID_0008 |
#      | TC_ID_0009 |
#      | TC_ID_0010 |