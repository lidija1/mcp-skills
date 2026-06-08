from pytest_bdd import scenario


@scenario(
    "../features/cyber/cyber_creation.feature",
    "Create a new cyber policy",
)
def test_cyber_workflow():
    pass


@scenario(
    "../features/cyber/cyber_creation.feature",
    "Discover Cyber policy information elements",
)
def test_cyber_element_discovery():
    pass


@scenario(
    "../features/cyber/cyber_creation.feature",
    "Discover Cyber Reinsurance and Inspection elements",
)
def test_cyber_reinsurance_inspection_discovery():
    pass


@scenario(
    "../features/cyber/cyber_creation.feature",
    "Exercise Cyber optional fields",
)
def test_cyber_optional_fields():
    pass
