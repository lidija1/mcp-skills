import pytest
from pytest_bdd import scenario


@pytest.mark.gl
@scenario(
    "../features/gl/gl_creation.feature",
    "Create a new General Liability policy",
)
def test_gl_workflow():
    pass


@pytest.mark.gl
@pytest.mark.optional_fields
@scenario(
    "../features/gl/gl_creation.feature",
    "Create a General Liability policy with optional endorsements and rating modifiers",
)
def test_gl_optional_fields_workflow():
    pass
