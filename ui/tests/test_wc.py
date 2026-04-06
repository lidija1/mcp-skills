import pytest
from pytest_bdd import scenario


@scenario('../features/wc/wc_creation.feature', 'Create a new workers compensation policy')
def test_wc_workflow():
    pass
