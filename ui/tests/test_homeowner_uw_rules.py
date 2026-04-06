from pytest_bdd import scenario


@scenario(
    'homeowner/homeowner_uw_rules.feature',
    'UW referral triggered during homeowner quote — <TC_ID>',
)
def test_homeowner_uw_referral():
    """
    Verifies that homeowner property risk factors trigger an Underwriting referral
    during the Homeowner quote workflow.

    Two confirmed hard-stop triggers:
      - Renovation=Yes  → "Property is under construction"
      - Frame + old     → "Building construction type is 'Frame'. It is also more than 10 years old."

    Both fire immediately on Location Coverage save, before Rate Quote is reached.
    """
    pass
