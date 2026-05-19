import pytest
from pytest_bdd import scenario


@scenario('../features/cyber/cyber_creation.feature', 'Create a new cyber policy')
def test_cyber_workflow():
    pass
