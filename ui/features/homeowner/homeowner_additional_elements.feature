Feature: Homeowner Additional Elements

  Background: Login as Claim Adjuster
    Given The user is logged in with valid credentials

  @homeowner @additional_elements
  Scenario Outline: Exercise additional homeowner page elements
    Given the data is loaded "testdata/static/homeowner/HomeData.json", "<TC_ID>"

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

    # Homeowner Quote Summary
    When I review homeowner quote summary additional elements
        * I review quote summary identity fields

    When I complete homeowner quote summary details
        * I select program type
        * I set billing method
        * I answer day care question
        * I answer underground oil tank question
        * I answer residence rented question
        * I answer residence vacant question
        * I answer animals question

    # Homeowner City Information
    When I review homeowner city information elements
        * I review city information display fields

    # Homeowner Location Coverage
    When I provide homeowner location coverage additional elements
        * I select residence type
        * I select homeowner coverage option
        * I set replacement cost
        * I set contents limit
        * I set loss of use limit
        * I review other structures limit
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
        * I review mitigation dropdowns
        * I review security protection checkboxes

    # Homeowner Bind Information
    When I provide homeowner bind information
        * I answer existing agency client question
        * I answer refused to insure question
        * I answer coverage declined question

    # Homeowner Premium Summary
    When I review homeowner premium summary elements
        * I review premium summary actions

    # Homeowner Delivery Preferences
    When I review homeowner delivery preference elements
        * I review delivery preference controls

    # Homeowner Billing Plan
    When I review homeowner billing plan elements
        * I review billing plan controls

    # Homeowner Verify Billing
    When I review homeowner verify billing elements and bind
        * I review verify billing actions

    Then I read and extract policy summary page details

    Examples:
      | TC_ID      |
      | TC_ID_0001 |
      | TC_ID_0011 |
      | TC_ID_0012 |
