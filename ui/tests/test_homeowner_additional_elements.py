"""BDD wrapper for the homeowner additional elements flow."""
from pytest_bdd import scenario


@scenario(
    "../features/homeowner/homeowner_additional_elements.feature",
    "Exercise additional homeowner page elements",
)
def test_homeowner_additional_elements():
    """Run homeowner flow with additional page elements exercised."""
