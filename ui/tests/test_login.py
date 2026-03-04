from pytest_bdd import scenario


@scenario('../features/common/login.feature', 'Successfully login with valid credentials on OneShield')
def test_login_process(login_page):
    pass