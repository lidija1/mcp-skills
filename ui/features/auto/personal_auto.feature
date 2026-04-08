Feature: Personal Auto Creation

  Background: Login as Claim Adjuster
    Given The user is logged in with valid credentials

  @smoke @auto
  Scenario Outline: Create a new personal auto policy
    Given the data is loaded "testdata/static/AutoData.json", "<TC_ID>"

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
    When I provide quote summary PA info
        * I set billing method
        * I answer false information question
        * I answer existing vehicle damage question

    # ── Driver Details ────────────────────────────────────────────────────────
    When I provide Driver Details
        * I enter driver gender
        * I enter marital status
        * I enter driver status
        * I enter employment category
        * I enter occupation
        * I enter license status
        * I answer SR-22 requirement

    # ── Vehicle Details ───────────────────────────────────────────────────────
    When I provide Vehicle Details
        * I select vehicle year
        * I select vehicle make
        * I select vehicle model
        * I select vehicle specification
        * I select vehicle use
        * I select vehicle ownership

    # ── Coverage & Rating ─────────────────────────────────────────────────────
    Given I provide policy term details
        * I select coverage tier
        * I click rate quote

    # ── Policy Creation ───────────────────────────────────────────────────────
    When I create a policy from the quote
        * I request issue
        * I proceed through delivery preferences
        * I proceed through billing plan
        * I bind the policy

    Examples:
      | TC_ID      |
      | TC_ID_0001 |
      | TC_ID_0011 |
#      | TC_ID_0002 |
#      | TC_ID_0003 |
#      | TC_ID_0004 |
#      | TC_ID_0005 |
#      | TC_ID_0006 |
#      | TC_ID_0007 |
#      | TC_ID_0008 |
#      | TC_ID_0009 |
#      | TC_ID_0010 |
