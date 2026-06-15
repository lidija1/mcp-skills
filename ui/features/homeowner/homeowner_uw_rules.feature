Feature: Homeowner UW Rules Validation

  Validates the 6 confirmed Hard-Stop underwriting rules for the Generic Homeowners
  product. Each positive scenario isolates one trigger field; the negative scenario
  proves a clean profile reaches premium summary without referral.

  All 6 confirmed conditions are Hard-Stops (verified via live browser session).
  No soft referrals exist for this product configuration.

  Trigger field → condition text mapping (confirmed):
    RoofType=Flat          → "Roof type is flat, tin or rolled paper"          (Location Coverage, after Rate Quote)
    UndergroundOil=Yes     → "Any underground oil or storage tanks?"            (Quote Summary, after Rate Quote)
    Renovation=Yes         → "Property is under construction"                   (Location Coverage, after Rate Quote)
    DayCare=Yes            → "Child or Day Care run out of the home"            (Quote Summary, after Rate Quote)
    ResidenceRented=Yes    → "Property rented more than 10 weeks a year"        (Quote Summary, after Rate Quote)
    ResidenceVacant=Yes    → "Property is Vacant"                               (Quote Summary, after Rate Quote)

  Background:
    Given The user is logged in with valid credentials

  # ── Positive: each row isolates one Hard-Stop trigger ─────────────────────
  @uw @homeowner
  Scenario Outline: Homeowner UW Hard-Stop fires on trigger field
    Given the data is loaded "testdata/static/homeowner/HomeUWData.json", "<TC_ID>"

    When i create a new quote
        * I click the Quotes button
        * I click New Quote
        * I select the Agent role
        * I proceed to customer setup

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

    When I provide quote registration details
        * I enter producer
        * I select program
        * I set effective date

    When I provide quote summary HO info for UW testing
    When I provide location coverage info for UW testing

    Then the UW referral page shows a "<uw_type>" condition containing "<expected_condition>"

    Examples:
      | TC_ID  | Description                                      | uw_type   | expected_condition                        |
      | UW_001 | Flat roof triggers the roof-type hard stop       | Hard-Stop | Roof type is flat, tin or rolled paper    |
      | UW_002 | Underground oil tank triggers a hard stop        | Hard-Stop | Any underground oil or storage tanks?     |
      | UW_003 | Major renovation triggers a construction stop    | Hard-Stop | Property is under construction            |
      | UW_004 | Home day care triggers a business-use hard stop  | Hard-Stop | Child or Day Care run out of the home     |
      | UW_005 | Long-term rental triggers an occupancy hard stop | Hard-Stop | Property rented more than 10 weeks a year |
      | UW_006 | Vacant residence triggers a vacancy hard stop    | Hard-Stop | Property is Vacant                        |

  # ── Negative: clean profile reaches premium summary without referral ───────
  @uw @homeowner @smoke
  Scenario Outline: Clean homeowner profile does not trigger UW referral
    Given the data is loaded "testdata/static/homeowner/HomeUWData.json", "<TC_ID>"

    When i create a new quote
        * I click the Quotes button
        * I click New Quote
        * I select the Agent role
        * I proceed to customer setup

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

    When I provide quote registration details
        * I enter producer
        * I select program
        * I set effective date

    When I provide quote summary HO info for UW testing
    When I provide location coverage info for UW testing

    Then no active UW conditions are present

    Examples:
      | TC_ID  | Description                                           |
      | UW_007 | Clean Homeowner profile reaches rating without referral |
