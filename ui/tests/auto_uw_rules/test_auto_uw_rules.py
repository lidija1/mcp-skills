from pytest_bdd import scenario


@scenario('auto/auto_uw_rules.feature', 'Soft UW referral triggered at quote rating — <TC_ID>')
def test_uw_soft_referral():
    """
    Verifies that driver/vehicle risk factors (SR-22, suspended/revoked license,
    age, business use, etc.) trigger an Underwriting referral after clicking
    Rate Quote on the coverages page.
    """
    pass
