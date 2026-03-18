Feature: Login Validation

  Background: Navigate to Login Page
    Given The user navigates to the OneShield login page

  @login @smoke @validation
  Scenario: Successfully login with valid credentials
    When The user fills valid credentials
    And The user clicks the login button
    Then The user should be logged in successfully

  @login @validation @empty-fields
  Scenario: Login attempt with empty partner number
    When The user leaves partner number empty
    And The user fills valid username from environment
    And The user fills valid password from environment
    And The user clicks the login button
    Then The user should be logged in successfully

  @login @validation @empty-fields
  Scenario: Login attempt with empty username
    When The user fills partner number "0"
    And The user leaves username empty
    And The user fills valid password from environment
    And The user clicks the login button
    Then The login should fail with validation error

  @login @validation @empty-fields
  Scenario: Login attempt with empty password
    When The user fills partner number "0"
    And The user fills valid username from environment
    And The user leaves password empty
    And The user clicks the login button
    Then The login should fail with validation error

  @login @validation @empty-fields
  Scenario: Login attempt with all fields empty
    When The user leaves all fields empty
    And The user clicks the login button
    Then The login should fail with validation error

  @login @validation @invalid-credentials
  Scenario: Login with invalid partner number
    When The user fills partner number "99999"
    And The user fills username "testuser"
    And The user fills password "ValidPassword123!"
    And The user clicks the login button
    Then The login should fail

  @login @validation @invalid-credentials
  Scenario: Login with invalid username
    When The user fills valid partner number
    And The user fills username "invaliduser@nonexistent.com"
    And The user fills valid password from environment
    And The user clicks the login button
    Then The login should fail

  @login @validation @invalid-credentials
  Scenario: Login with invalid password
    When The user fills valid partner number
    And The user fills valid username from environment
    And The user fills password "WrongPassword123!"
    And The user clicks the login button
    Then The login should fail

  @login @validation @format-validation
  Scenario: Partner number with special characters
    When The user fills partner number "0@#$%"
    And The user fills valid username from environment
    And The user fills valid password from environment
    And The user clicks the login button
    Then The login should fail

  @login @validation @format-validation
  Scenario: Partner number with negative value
    When The user fills partner number "-1"
    And The user fills valid username from environment
    And The user fills valid password from environment
    And The user clicks the login button
    Then The login should fail

  @login @validation @format-validation
  Scenario: Partner number with decimal value
    When The user fills partner number "0.5"
    And The user fills valid username from environment
    And The user fills valid password from environment
    And The user clicks the login button
    Then The login should fail

  @login @validation @whitespace
  Scenario: Username with leading and trailing whitespace
    When The user fills partner number "0"
    And The user fills username "  testuser  "
    And The user fills valid password from environment
    And The user clicks the login button
    Then The system should handle the login properly

  @login @validation @case-sensitivity
  Scenario: Password is case sensitive
    When The user fills partner number "0"
    And The user fills valid username from environment
    And The user fills password "validpassword123!"
    And The user clicks the login button
    Then The login should fail

  @login @validation @length
  Scenario: Partner number exceeding maximum length
    When The user fills partner number "123456789012345678901234567890"
    And The user fills valid username from environment
    And The user fills valid password from environment
    And The user clicks the login button
    Then The login should fail or show validation error

  @login @validation @length
  Scenario: Username exceeding maximum length
    When The user fills partner number "0"
    And The user fills username with 500 characters
    And The user fills valid password from environment
    And The user clicks the login button
    Then The login should fail or show validation error

  @login @validation @security
  Scenario: SQL injection attempt in username
    When The user fills partner number "0"
    And The user fills username "' OR '1'='1"
    And The user fills valid password from environment
    And The user clicks the login button
    Then The login should fail

  @login @validation @security
  Scenario: SQL injection attempt in password
    When The user fills partner number "0"
    And The user fills valid username from environment
    And The user fills password "' OR '1'='1"
    And The user clicks the login button
    Then The login should fail

  @login @validation @security
  Scenario: XSS attempt in username
    When The user fills partner number "0"
    And The user fills username "<script>alert('xss')</script>"
    And The user fills valid password from environment
    And The user clicks the login button
    Then The login should fail

  @login @validation @ui
  Scenario: Verify password field type
    Given The user navigates to the OneShield login page
    Then The password field should be of type password

  @login @validation @ui
  Scenario: Verify all required fields have indicators
    Given The user navigates to the OneShield login page
    Then All required fields should have visual indicators

  @login @validation @ui
  Scenario: Verify login form elements are visible
    Given The user navigates to the OneShield login page
    Then The partner number field should be visible
    And The username field should be visible
    And The password field should be visible
    And The login button should be visible

  @login @validation @navigation
  Scenario: Verify login page layout
    Given The user navigates to the OneShield login page
    Then The login page should display the OneShield branding
    And The login form should contain all required input fields

  @login @validation @error-messages
  Scenario: Verify error message displayed on invalid credentials
    When The user fills valid partner number
    And The user fills username "testuser"
    And The user fills password "WrongPassword123!"
    And The user clicks the login button
    Then An error message should be displayed

  @login @validation @error-messages
  Scenario: Verify error message cleared when field is corrected
    When The user fills partner number "0"
    And The user leaves username empty
    And The user fills password "ValidPassword123!"
    And The user clicks the login button
    Then A validation error should be displayed
    When The user fills valid username from environment
    Then The error message should be cleared or updated

  @login @validation @special-chars
  Scenario: Username with special characters
    When The user fills partner number "0"
    And The user fills username "test@user#123"
    And The user fills valid password from environment
    And The user clicks the login button
    Then The system should process the login

  @login @validation @special-chars
  Scenario: Password with special characters
    When The user fills partner number "0"
    And The user fills valid username from environment
    And The user fills password "P@ssw0rd!#$%^&*()"
    And The user clicks the login button
    Then The system should process the login

  @login @validation @format
  Scenario: Partner number with leading zeros
    When The user fills partner number "0000000"
    And The user fills valid username from environment
    And The user fills valid password from environment
    And The user clicks the login button
    Then The system should process the login

  @login @validation @edge-case
  Scenario: User clicks login button twice rapidly
    When The user fills valid credentials
    And The user clicks the login button twice rapidly
    Then Only one login attempt should be processed

  @login @validation @edge-case
  Scenario: Page refresh during login
    When The user fills valid credentials
    And The page is refreshed
    Then The user should be returned to the login page

  @login @validation @accessibility
  Scenario: Tab navigation through login fields
    Given The user navigates to the OneShield login page
    When The user navigates through fields using Tab key
    Then The focus order should be correct

  @login @validation @post-login
  Scenario: User can logout after successful login
    When The user fills valid credentials
    And The user clicks the login button
    Then The user should be logged in successfully
    When The user clicks the logout button
    Then The user should be returned to the login page

  @login @smoke
  Scenario Outline: Login with various invalid credentials
    When The user fills partner number "<partner>"
    And The user fills username "<username>"
    And The user fills password "<password>"
    And The user clicks the login button
    Then The login should <result>

    Examples:
      | partner | username | password | result |
      | 0       | invalid  | valid    | fail   |
      | invalid | valid    | valid    | fail   |
      | 0       | valid    | invalid  | fail   |
      | ""      | valid    | valid    | fail   |
      | 0       | ""       | valid    | fail   |
      | 0       | valid    | ""       | fail   |

