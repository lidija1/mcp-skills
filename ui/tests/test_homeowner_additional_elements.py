"""BDD wrapper for the homeowner additional elements flow."""
from pytest_bdd import scenario


@scenario(
    "../features/homeowner/homeowner_additional_elements.feature",
    "Exercise discovered Homeowner controls without binding",
)
def test_homeowner_additional_elements():
    """Run homeowner flow with additional page elements exercised."""
