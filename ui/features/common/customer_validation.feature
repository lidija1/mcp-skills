Feature: Customer Page Field Validation

  Background: Login as User
    Given The user is logged in with valid credentials

  @smoke @validation
  Scenario Outline: Validate invalid email format on customer search
    Given the data is loaded "testdata/static/common/CustomerValidationData.json", "<TC_ID>"
    When i create a new quote
    When I fill all customer fields with test data
    When I click search for customer
    Then I should see email validation error message

    Examples:
      | TC_ID                    |
      | TC_INVALID_EMAIL_NO_AT   |
      | TC_INVALID_EMAIL_NO_USER |
      | TC_INVALID_EMAIL_NO_DOMAIN |
      | TC_INVALID_EMAIL_SPECIAL_CHARS |
      | TC_INVALID_EMAIL_SPACES |

  @smoke @validation
  Scenario Outline: Validate invalid date of birth on customer search
    Given the data is loaded "testdata/static/common/CustomerValidationData.json", "<TC_ID>"
    When i create a new quote
    When I fill all customer fields with test data
    When I click search for customer
    Then I should see date of birth validation error message

    Examples:
      | TC_ID                    |
      | TC_INVALID_DOB_FUTURE    |
      | TC_INVALID_DOB_FORMAT    |
      | TC_INVALID_DOB_TOO_OLD   |
      | TC_INVALID_DOB_INVALID_DATE |
      | TC_INVALID_DOB_INCOMPLETE |

  @smoke @validation
  Scenario Outline: Validate valid email formats are accepted
    Given the data is loaded "testdata/static/common/CustomerValidationData.json", "<TC_ID>"
    When i create a new quote
    When I fill all customer fields with test data
    When I click search for customer
    Then I should not see any email validation errors

    Examples:
      | TC_ID              |
      | TC_VALID_EMAIL_001 |
      | TC_VALID_EMAIL_002 |
      | TC_VALID_EMAIL_003 |

  @smoke @validation
  Scenario Outline: Validate valid date of birth formats are accepted
    Given the data is loaded "testdata/static/common/CustomerValidationData.json", "<TC_ID>"
    When i create a new quote
    When I fill all customer fields with test data
    When I click search for customer
    Then I should not see any date of birth validation errors

    Examples:
      | TC_ID            |
      | TC_VALID_DOB_001 |
      | TC_VALID_DOB_002 |
      | TC_VALID_DOB_003 |

  @smoke @validation
  Scenario Outline: Validate required fields are filled before search
    Given the data is loaded "testdata/static/common/CustomerValidationData.json", "<TC_ID>"
    When i create a new quote
    When I fill all customer fields with test data
    When I click search for customer
    Then I should see all required field validation errors

    Examples:
      | TC_ID                      |
      | TC_MISSING_FIRST_NAME      |
      | TC_MISSING_LAST_NAME       |
      | TC_MISSING_DOB             |
      | TC_MISSING_EMAIL           |
      | TC_MISSING_MULTIPLE_FIELDS |

