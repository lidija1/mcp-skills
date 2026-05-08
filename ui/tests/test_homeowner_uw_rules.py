from pytest_bdd import scenario


@scenario(
    'homeowner/homeowner_uw_rules.feature',
    'Homeowner UW Hard-Stop fires on trigger field',
)
def test_homeowner_uw_hard_stop():
    pass


@scenario(
    'homeowner/homeowner_uw_rules.feature',
    'Clean homeowner profile does not trigger UW referral',
)
def test_homeowner_clean_profile():
    pass
