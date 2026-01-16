Feature: Personal Auto Creation

  Background: Login as Claim Adjuster
    Given The user is logged in with valid credentials

  @auto
  Scenario Outline: Create a new personal auto policy
    Given the data is loaded "<ExcelData>", "<SHEET>", "<TC_ID>"
    When I create a new quote
#    And I create a new customer
#    And I provide PA information
#    And I provide Driver Details
#    Then I provide Vehicle Details
#    And I provide policy term details
#    And I extract and write the PA policy cost to Results sheet
#    And I extract and write the policy number to Results sheet

    Examples:
      | ExcelData                     | SHEET       | TC_ID      |
#      | testdata/static/AutoData.xlsx | Policy_Data | TC_ID_0001 |
      | testdata/static/AutoData.xlsx | Policy_Data | TC_ID_0003 |
#      | testdata/static/AutoData.xlsx | Policy_Data | TC_ID_0004 |
#      | testdata/static/AutoData.xlsx | Policy_Data | TC_ID_0005 |
#
#    @TC_0003
#    Examples:
#      | ExcelData                     | SHEET       | TC_ID      |
#      | testdata/static/AutoData.xlsx | Policy_Data | TC_ID_0003 |