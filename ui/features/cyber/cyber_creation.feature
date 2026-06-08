Feature: Cyber Insurance Creation

  Background:
    Given The user is logged in with valid credentials

  @smoke @cyber
  Scenario Outline: Create a new cyber policy
    Given the data is loaded "testdata/static/cyber/CyberData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide Cyber policy information
    When I rate and issue the Cyber quote
    When I complete Cyber policy binding
    Then I read and extract policy summary page details

    Examples:
      | TC_ID                |
      | CYBER_USUAL_001      |
      | CYBER_USUAL_002      |
      | CYBER_USUAL_003      |
      | CYBER_USUAL_004      |
      | CYBER_USUAL_005      |
      | CYBER_USUAL_006      |
      | CYBER_USUAL_007      |
      | CYBER_USUAL_008      |
      | CYBER_USUAL_009      |
      | CYBER_USUAL_010      |
      | CYBER_USUAL_011      |
      | CYBER_USUAL_012      |
      | CYBER_USUAL_013      |
      | CYBER_USUAL_014      |
      | CYBER_USUAL_015      |
      | CYBER_USUAL_016      |
      | CYBER_USUAL_017      |
      | CYBER_USUAL_018      |
      | CYBER_USUAL_019      |
      | CYBER_USUAL_020      |

  @cyber
  Scenario Outline: Discover Cyber policy information elements
    Given the data is loaded "testdata/static/cyber/CyberDiscoveryData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I review discovered Cyber policy information elements

    Examples:
      | TC_ID                     |
      | TC_ID_CYBER_DISCOVERY_001 |

  @cyber
  Scenario Outline: Exercise Cyber optional fields
    Given the data is loaded "testdata/static/cyber/CyberOptionalData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I exercise configured Cyber optional fields

    Examples:
      | TC_ID                   |
      | CYBER_OPTIONAL_001      |
      | CYBER_OPTIONAL_002      |
      | CYBER_OPTIONAL_003      |
      | CYBER_OPTIONAL_004      |
      | CYBER_OPTIONAL_005      |
      | CYBER_OPTIONAL_006      |
      | CYBER_OPTIONAL_007      |
      | CYBER_OPTIONAL_008      |
      | CYBER_OPTIONAL_009      |
      | CYBER_OPTIONAL_010      |
      | CYBER_OPTIONAL_011      |
      | CYBER_OPTIONAL_012      |
      | CYBER_OPTIONAL_013      |
      | CYBER_OPTIONAL_014      |
      | CYBER_OPTIONAL_015      |
      | CYBER_OPTIONAL_016      |
      | CYBER_OPTIONAL_017      |
      | CYBER_OPTIONAL_018      |

  @cyber
  Scenario Outline: Discover Cyber Reinsurance and Inspection elements
    Given the data is loaded "testdata/static/cyber/CyberDiscoveryData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I review Cyber Reinsurance and Inspection elements

    Examples:
      | TC_ID                     |
      | TC_ID_CYBER_DISCOVERY_001 |
