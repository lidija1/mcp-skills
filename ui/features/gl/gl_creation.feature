Feature: General Liability Insurance Creation

  Background:
    Given The user is logged in with valid credentials

  @smoke @gl
  Scenario Outline: Create a new General Liability policy
    Given the data is loaded "testdata/static/gl/GLData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide general liability risk address details
    When I provide general liability basic policy information
    When I provide general liability coverage and limits
    When I provide general liability liability location list details
    When I provide general liability rating basis and classification details
    When I rate the general liability quote
    When I request issue for the general liability quote
    When I proceed to the general liability billing plan
    When I complete the general liability billing plan
    When I bind the general liability policy
    Then I read and extract policy summary page details for general liability

    Examples:
      | TC_ID  | Description                                                              |
      | GL_001 | Baseline Commercial GL — Quarterly Audit, Inside Defense, Standard Limits |
      | GL_002 | Baseline GL — Repeat Run 2                                                |
      | GL_003 | Baseline GL — Repeat Run 3                                                |
      | GL_004 | Baseline GL — Repeat Run 4                                                |
      | GL_005 | Baseline GL — Repeat Run 5                                                |
      | GL_006 | Claims Made Form Type — Discovery Policy for Late-Reported Claims         |
      | GL_007 | Outside Defense Treatment — Legal Costs Paid Outside Policy Limits        |
      | GL_008 | Foreign Sales Exposure — Business with International Revenue              |
      | GL_009 | Primary and Excess Policy Type — Layered Coverage Structure               |
      | GL_010 | Excess Only Policy — Umbrella Overlay with Underlying GL                  |
      | GL_011 | Agency Billed — Broker Handles Premium Collection                         |
      | GL_012 | Semi-Annual Audit Frequency — Mid-Year Premium Adjustment                 |
      | GL_013 | Prior Loss History — Business with Claims in Last 3 Years                 |
      | GL_014 | Maximum Aggregate Limits — High-Exposure Commercial Operation             |
      | GL_015 | Products and Completed Operations Excluded — Service-Only Business        |
      | GL_016 | Personal and Advertising Injury Excluded — No Media Exposure              |
      | GL_017 | Medical Expense Excluded — Insured Carries Separate Medical Coverage      |
      | GL_018 | High Deductible Per Occurrence — Large Self-Retention Program             |
      | GL_019 | Property Damage Only Deductible — Bodily Injury Covered in Full           |
      | GL_020 | Bodily Injury Only Deductible — Property Damage Covered in Full           |
      | GL_021 | Limit Ventilation Required — Building Has Active Ventilation Requirement  |
      | GL_022 | No Deductible — Full First-Dollar Coverage                                |

  @gl @optional_fields
  Scenario Outline: Create a General Liability policy with optional endorsements and rating modifiers
    Given the data is loaded "testdata/static/gl/GLData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide general liability risk address details
    When I provide general liability basic policy information
    When I provide general liability coverage and limits
    When I provide general liability liability location list details
    When I provide general liability rating basis and classification details
    When I rate the general liability quote
    When I request issue for the general liability quote
    When I proceed to the general liability billing plan
    When I complete the general liability billing plan
    When I bind the general liability policy
    Then I read and extract policy summary page details for general liability

    Examples:
      | TC_ID  | Description                                                                             |
      | GL_023 | Hired Auto Coverage Added — Business Rents Vehicles for Operations                      |
      | GL_024 | Non-Owned Auto Coverage Added — Employees Use Personal Vehicles for Work                |
      | GL_025 | Employee Benefits Coverage Added — Employer Liability for Benefits Administration       |
      | GL_026 | Liquor Liability Coverage Added — Restaurant or Bar Serving Alcohol                     |
      | GL_027 | GL Enhancement Endorsement — Broadened Coverage Package for Low-Risk Business           |
      | GL_028 | Contractual Liability Exclusion — Business Refuses Hold-Harmless Agreements             |
      | GL_029 | Exclude Employees as Additional Insureds — Subcontractor-Heavy Operations               |
      | GL_030 | Hazards in Connection with Designated Premises — Site-Specific Risk Carve-Out           |
      | GL_031 | Hired and Non-Owned Auto Combined — Delivery Business Using Rented and Personal Vehicles|
      | GL_032 | Hospitality Package — Liquor Liability, Hired Auto, Non-Owned Auto for Hotel Operation  |
      | GL_033 | GL Manual Coverages — Non-Standard Classification Requiring Manual Rating               |
      | GL_034 | Schedule Mod Credit — Risk Management Program Earns Pricing Credit                      |
      | GL_035 | Experience Mod Surcharge — Poor Loss History Triggers Premium Increase                  |
