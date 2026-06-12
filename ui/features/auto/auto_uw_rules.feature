Feature: Personal Auto Underwriting Rules
  Validate that specific UW rules are triggered and surfaced on the underwriting
  referral page during the Personal Auto quote workflow.

  The confirmed Personal Auto UW triggers are:
    - SR-22 required: "SR-22 / Certificate of Insurance Indicator is checked"
    - Suspended/Revoked license: "An operator of this policy has a driver license status that is revoked or suspended."
    - Driver under 25: "All drivers under 25 years of age."

  Background: Login as Claim Adjuster
    Given The user is logged in with valid credentials

  @uw_rules @auto
  Scenario Outline: Soft UW referral triggered at quote rating - <TC_ID>
    Given the data is loaded "testdata/static/auto/AutoUWRulesData.json", "<TC_ID>"

    # New Quote
    When i create a new quote
        * I click the Quotes button
        * I click New Quote
        * I select the Agent role
        * I proceed to customer setup

    # Customer Details
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

    # Quote Registration
    When I provide quote registration details
        * I enter producer
        * I select program
        * I set effective date

    # Quote Summary
    When I provide quote summary PA info
        * I set billing method
        * I answer false information question
        * I answer existing vehicle damage question

    # Driver Details
    When I provide Driver Details
        * I enter driver gender
        * I enter marital status
        * I enter driver status
        * I enter employment category
        * I enter occupation
        * I enter license status
        * I answer SR-22 requirement
        * I select SR-22 filing state when required

    # Vehicle Details
    When I provide Vehicle Details
        * I select vehicle year
        * I select vehicle make
        * I select vehicle model
        * I select vehicle specification
        * I select vehicle use
        * I select vehicle ownership

    # Coverage & Rating
    When I select coverage and rate the quote
        * I select coverage tier
        * I click rate quote

    # Underwriting Referral
    Then the UW referral page shows a "<UWType>" condition containing "<ExpectedCondition>"
        * I verify the expected underwriting condition

    Examples:
      | TC_ID     | UWType       | ExpectedCondition                                              |
      | UW_TC_001 | Underwriting | SR-22 / Certificate of Insurance Indicator is checked          |
      | UW_TC_002 | Underwriting | driver license status that is revoked or suspended             |
      | UW_TC_003 | Underwriting | All drivers under 25 years of age                              |
      | UW_TC_004 | Underwriting | driver license status that is revoked or suspended             |
      | UW_TC_005 | Underwriting | All drivers under 25 years of age                              |
      | UW_TC_006 | Underwriting | driver license status that is revoked or suspended             |
      | UW_TC_007 | Underwriting | SR-22 / Certificate of Insurance Indicator is checked          |
      | UW_TC_008 | Underwriting | All drivers under 25 years of age                              |
      | UW_TC_009 | Underwriting | driver license status that is revoked or suspended             |
      | UW_TC_010 | Underwriting | SR-22 / Certificate of Insurance Indicator is checked          |

  @uw_rules @auto
  Scenario Outline: Overridable Auto UW referral can continue to bind - <TC_ID>
    Given the data is loaded "testdata/static/auto/AutoUWRulesData.json", "<TC_ID>"

    # New Quote
    When i create a new quote
        * I click the Quotes button
        * I click New Quote
        * I select the Agent role
        * I proceed to customer setup

    # Customer Details
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

    # Quote Registration
    When I provide quote registration details
        * I enter producer
        * I select program
        * I set effective date

    # Quote Summary
    When I provide quote summary PA info
        * I set billing method
        * I answer false information question
        * I answer existing vehicle damage question

    # Driver Details
    When I provide Driver Details
        * I enter driver gender
        * I enter marital status
        * I enter driver status
        * I enter employment category
        * I enter occupation
        * I enter license status
        * I answer SR-22 requirement
        * I select SR-22 filing state when required

    # Vehicle Details
    When I provide Vehicle Details
        * I select vehicle year
        * I select vehicle make
        * I select vehicle model
        * I select vehicle specification
        * I select vehicle use
        * I select vehicle ownership

    # Coverage & Rating
    When I select coverage and rate the quote
        * I select coverage tier
        * I click rate quote

    # Underwriting Referral
    Then the UW referral page shows a "<UWType>" condition containing "<ExpectedCondition>"
        * I verify the expected underwriting condition

    # UW Override
    When I override all UW conditions and accept
        * I confirm every UW row is editable
        * I set all UW override flags to Yes
        * I enter underwriter comments
        * I accept the underwriting referral

    # Contact Information
    When I complete Contact Information with Email permission
        * I select Email contact permission
        * I save contact information
        * I continue past contact information

    # Re-Rate
    When I re-rate the quote after UW override
        * I click re-rate

    # Policy Creation
    When I create a policy from the quote
        * I request issue
        * I proceed through delivery preferences
        * I proceed through billing plan
        * I bind the policy

    # Policy Summary
    Then I read and extract policy summary page details

    Examples:
      | TC_ID     | UWType       | ExpectedCondition                                                                          |
      | UW_TC_001 | Underwriting | SR-22 / Certificate of Insurance Indicator is checked                                      |
      | UW_TC_003 | Underwriting | All drivers under 25 years of age                                                          |
      | UW_TC_005 | Underwriting | SR-22 / Certificate of Insurance Indicator is checked; All drivers under 25 years of age   |
