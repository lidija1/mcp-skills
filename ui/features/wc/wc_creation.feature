Feature: Workers Compensation Creation

  Background:
    Given The user is logged in with valid credentials

  @smoke @wc
  Scenario Outline: Create a new workers compensation policy
    Given the data is loaded "testdata/static/wc/WCData.json", "<TC_ID>"

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

    # ── WC Quote Details ──────────────────────────────────────────────────────
    When I explore the WC quote page

    # ── Policy Summary ────────────────────────────────────────────────────────
    Then I read and extract policy summary page details

    Examples:
      | TC_ID      |
      | TC_ID_0001 |
