from pytest_bdd import scenario

@scenario('../features/auto/personal_auto.feature', 'Create a new personal auto policy')
def test_personal_auto_workflow():
    """
    This test runs the 'Personal Auto Creation' feature.
    All step definitions are imported via conftest.py's pytest_plugins.
    """
    pass
