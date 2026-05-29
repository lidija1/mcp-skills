Feature: Cyber Insurance Creation

  Background:
    Given The user is logged in with valid credentials

  @smoke @cyber
  Scenario Outline: Create a new cyber policy
    Given the data is loaded "testdata/static/cyber/CyberData.json", "<TC_ID>"

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

    # ── Cyber Quote Details ───────────────────────────────────────────────────
    When I provide Cyber quote details
        * I set cyber billing method
        * I enter business start date
        * I enter total employees
        * I select nature of business
        * I enter percentage of online sales
        * I select aggregate limit
        * I select per claim limit
        * I select per claim deductible
        * I answer cyber training question
        * I answer prior cyber situations question
        * I answer cyber regulations question

    # ── Rating & Issuance ─────────────────────────────────────────────────────
    When I rate the Cyber quote
    When I request issue for the Cyber quote

    # ── Policy Binding ────────────────────────────────────────────────────────
    When I complete delivery preferences
    When I complete billing plan
    When I bind the Cyber policy

    # ── Policy Summary ────────────────────────────────────────────────────────
    Then I read and extract policy summary page details

    Examples:
      | TC_ID      |
      | TC_ID_0001 |
#      | TC_ID_0002 |
#      | TC_ID_0003 |
