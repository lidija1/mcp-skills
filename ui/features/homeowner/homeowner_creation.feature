Feature: Homeowner Creation

  Background: Login as Claim Adjuster
    Given The user is logged in with valid credentials

  @smoke @homeowner
  Scenario Outline: Create a new homeowner policy
    Given the data is loaded "testdata/static/HomeData.json", "<TC_ID>"

    # ── New Quote ─────────────────────────────────────────────────────────────
    When i create a new quote
        * I click the Quotes button
        * I click New Quote
        * I select the Agent role
        * I proceed to customer setup

    # ── Customer Details ──────────────────────────────────────────────────────
    When i create a new customer
        * I enter first name
        * I enter last name
        * I enter ZIP code
        * I select customer type
        * I enter address
        * I enter city
        * I enter date of birth
        * I enter phone number
        * I enter email address
        * I search for existing customer
        * I create a new customer record
        * I confirm and proceed past customer setup

    # ── Quote Registration ────────────────────────────────────────────────────
    When I provide quote registration details
        * I enter producer
        * I select program
        * I set effective date

    # ── Quote Summary ─────────────────────────────────────────────────────────
    When I provide quote summary HO info
        * I select program type
        * I set billing method
        * I answer day care question
        * I answer underground oil tank question
        * I answer residence rented question
        * I answer residence vacant question
        * I answer animals question

    # ── Location Coverage ─────────────────────────────────────────────────────
    When I provide location coverage info
        * I select residence type
        * I select homeowner coverage option
        * I set replacement cost
        * I set all perils deductible
        * I set windstorm deductible
        * I set liability limit
        * I set medical payments limit
        * I enter year built
        * I select construction type
        * I enter roof type
        * I answer renovation question
        * I answer lived here question
        * I answer any losses question
        * I answer existing agency client question
        * I answer refused to insure question
        * I answer coverage declined question

    # ── Policy Creation ───────────────────────────────────────────────────────
    When I create a policy from the quote
        * I request issue
        * I proceed through delivery preferences
        * I proceed through billing plan
        * I bind the policy

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
