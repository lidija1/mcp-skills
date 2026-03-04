from pytest_bdd import scenario


@scenario('../features/homeowner/homeowner_creation.feature', 'Create a new homeowner policy')
def test_homeowner_workflow():
    """
    This test runs the 'Homeowner Creation' feature.
    All step definitions are imported via conftest.py's pytest_plugins.
    """
    pass