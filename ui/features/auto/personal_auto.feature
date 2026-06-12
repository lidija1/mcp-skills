Feature: Personal Auto Creation

  Background: Login as Claim Adjuster
    Given The user is logged in with valid credentials

  @smoke @auto
  Scenario Outline: Create a new personal auto policy
    Given the data is loaded "testdata/static/auto/AutoData.json", "<TC_ID>"

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

    # ── Policy Summary ────────────────────────────────────────────────────────
    Then I read and extract policy summary page details

    Examples:
      | TC_ID      | Description                                         |
      | TC_ID_0001 | Standard Auto flow 01: Pleasure, Owned, Gold        |
      | TC_ID_0002 | Standard Auto flow 02: Business, Owned, Silver      |
      | TC_ID_0003 | Standard Auto flow 03: Commute, Owned, Gold         |
      | TC_ID_0004 | Standard Auto flow 04: Farm, Owned, Bronze          |
      | TC_ID_0005 | Standard Auto flow 05: Business, Owned, Platinum    |
      | TC_ID_0006 | Standard Auto flow 06: Commute, Owned, Gold         |
      | TC_ID_0007 | Standard Auto flow 07: Farm, Owned, Silver          |
      | TC_ID_0008 | Standard Auto flow 08: Pleasure, Owned, Gold        |
      | TC_ID_0009 | Standard Auto flow 09: Business, Owned, Silver      |
      | TC_ID_0010 | Standard Auto flow 10: Pleasure, Owned, Platinum    |
      | TC_ID_0011 | Standard Auto flow 11: Pleasure, Leased, Gold       |
      | TC_ID_0012 | Standard Auto flow 12: Commute, Financed, Silver    |
      | TC_ID_0013 | Standard Auto flow 13: Business, Owned, Bronze      |
      | TC_ID_0014 | Standard Auto flow 14: Commute, Leased, Platinum    |
      | TC_ID_0015 | Standard Auto flow 15: Farm, Financed, Gold         |
      | TC_ID_0016 | Standard Auto flow 16: Pleasure, Owned, Silver      |
      | TC_ID_0017 | Standard Auto flow 17: Business, Leased, Bronze     |
      | TC_ID_0018 | Standard Auto flow 18: Commute, Owned, Platinum     |
      | TC_ID_0019 | Standard Auto flow 19: Pleasure, Financed, Gold     |
      | TC_ID_0020 | Standard Auto flow 20: Farm, Owned, Silver          |

  @auto @optional_fields
  Scenario Outline: Create a personal auto policy with optional driver and vehicle fields
    Given the data is loaded "testdata/static/auto/AutoData.json", "<TC_ID>"
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
      | TC_ID                 | Description                                                                                                  |
      | AUTO_OPT_DRIVER_0001  | Driver identity fields                                                                                       |
      | AUTO_OPT_VEHICLE_0001 | Leased vehicle, loss payee, and physical damage symbol                                                       |
      | AUTO_OPT_DRIVER_0002  | Driver suffix and retired employment                                                                         |
      | AUTO_OPT_DRIVER_0003  | Unemployed driver with prior-state license response                                                          |
      | AUTO_OPT_DRIVER_0004  | Disabled driver and defensive course                                                                         |
      | AUTO_OPT_QUOTE_0001   | Agency billing with commission fields                                                                        |
      | AUTO_OPT_QUOTE_0002   | Prior carrier and prior premium fields                                                                       |
      | AUTO_OPT_DAMAGE_0001  | Existing vehicle damage description                                                                          |
      | AUTO_OPT_VEHICLE_0002 | Financed vehicle with loss payee                                                                              |
      | AUTO_OPT_VEHICLE_0003 | Jointly owned vehicle title                                                                                   |
      | AUTO_OPT_VEHICLE_0004 | Business-use vehicle with physical damage override                                                           |
      | AUTO_OPT_VEHICLE_0005 | Commute vehicle with distance-to-work data                                                                   |
      | AUTO_OPT_VEHICLE_0006 | Confirms inherited garaging fields match the customer address and remain read-only                           |
      | AUTO_FLOW_E2E_0001    | Covers quote, driver, vehicle, loss-payee, commute, and package-derived coverage fields in one bindable E2E flow |
