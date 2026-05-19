from pytest_bdd import scenario


@scenario(
    "../features/general_liability/general_liability_dropdown_options.feature",
    "Exercise the General Liability dropdown option matrix",
)
def test_general_liability_dropdown_options():
    pass
