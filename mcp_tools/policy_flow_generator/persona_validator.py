from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class PersonaValidationError(ValueError):
    def __init__(self, lob: str, errors: list[dict[str, Any]]):
        self.lob = lob
        self.errors = _json_safe_errors(errors)
        super().__init__(f"{lob} persona validation failed")


class _PersonaBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    TC_ID: str
    CustomerType: Literal["Individual"]
    FirstName: str
    LastName: str
    DOB: str
    PhoneNum: str
    Email: str
    Address: str
    ZIP: Literal["01101"]
    State: Literal["Massachusetts"] | None = None
    City: Literal["Springfield"]
    Producer: Literal["Janis Irey"]
    EffectiveDate: str
    BillingMethod: Literal["Direct Billed"]
    PaymentPlan: Literal["Pay In Full"]


class AutoPersona(_PersonaBase):
    State: Literal["Massachusetts"]
    Program: Literal["Personal Auto"]
    FalseInfo: Literal["No"]
    DamageInfo: Literal["Yes", "No"]
    DescribeDamage: str | None = None
    Gender: Literal["Male", "Female"]
    MaritalStatus: Literal["Single", "Married", "Divorced", "Widowed"]
    DriverStatus: Literal["Active (rated)"]
    EmploymentCategory: Literal["Employed", "Unemployed", "Retired", "Student"]
    SR22: Literal["Yes", "No"]
    SR22FilingState: Literal["Massachusetts"] | None = None
    Occupation: str
    LicenseStatus: Literal["Active License", "Suspended", "Revoked"]
    VehicleType: Literal["Private Passenger Auto"]
    Year: str
    Make: str
    Model: str
    Spec: str
    VehicleUse: Literal["Pleasure", "Commute", "Business"]
    Ownership: Literal["Owned", "Leased", "Financed"]
    LossPayeeType: Literal["Leased", "Financed"] | None = None
    LossPayeeName: str | None = None
    PolicyCoverage: Literal["Bronze", "Silver", "Gold", "Platinum"]

    @model_validator(mode="after")
    def _validate_conditional_fields(self):
        if self.DamageInfo == "Yes" and not self.DescribeDamage:
            raise ValueError("DescribeDamage is required when DamageInfo is Yes")
        if self.SR22 == "Yes" and self.SR22FilingState != "Massachusetts":
            raise ValueError("SR22FilingState must be Massachusetts when SR22 is Yes")
        if self.Ownership != "Owned":
            if self.LossPayeeType != self.Ownership:
                raise ValueError("LossPayeeType must match non-owned Ownership")
            if not self.LossPayeeName:
                raise ValueError("LossPayeeName is required when Ownership is not Owned")
        return self


class HomeownerPersona(_PersonaBase):
    State: Literal["Massachusetts"]
    Program: Literal["Homeowner"]
    ProgramType: Literal["Basic"]
    DayCare: Literal["Yes", "No"]
    UndergroundOil: Literal["Yes", "No"]
    ResidenceRented: Literal["Yes", "No"]
    ResidenceVacant: Literal["Yes", "No"]
    Animals: Literal["Yes", "No"]
    PolicyCoverageOption: Literal["Bronze", "Silver", "Gold", "Platinum"]
    ResidenceType: Literal["Homeowner"]
    ReplacementCost: str
    Contents: str
    AllPerilsDeductable: Literal["1,000", "2,500", "5,000", "10,000"]
    WindstormDeductable: Literal["1%", "2%", "5%"]
    Liability: Literal["100,000", "300,000", "500,000"]
    MedPayments: Literal["1,000", "2,000", "5,000"]
    Renovation: Literal["Yes", "No"]
    LivedHere: Literal["Yes", "No"]
    YearBuilt: str
    ConstructionType: Literal["Frame", "Masonry", "Superior"]
    RoofType: Literal["Concrete Tile", "Asphalt Shingle", "Metal", "Wood Shake"]
    Loses: Literal["Yes", "No"]
    ExistingClient: Literal["Yes", "No"]
    Refused: Literal["Yes", "No"]
    Declined: Literal["Yes", "No"]


class CyberPersona(_PersonaBase):
    Program: Literal["Cyber"]
    BusinessStartDate: str
    TotalEmployees: str
    NatureOfBusiness: Literal[
        "Office",
        "Retail",
        "Healthcare",
        "Technology",
        "Education",
        "Financial Services",
        "Manufacturing",
    ]
    PctOnlineSales: str
    AggregateLimit: Literal["500,000", "1,000,000", "2,000,000"]
    PerClaimLimit: Literal["500,000", "1,000,000", "2,000,000"]
    PerClaimDeductible: Literal["500", "1,000", "2,500", "5,000"]
    CyberTraining: Literal["Yes", "No"]
    SituationsLast3Years: Literal["None", "Data Breach", "Ransomware Attack", "Phishing Attack"]
    CyberRegulations: Literal["Yes", "No"]


_MODELS: dict[str, type[BaseModel]] = {
    "auto": AutoPersona,
    "homeowner": HomeownerPersona,
    "cyber": CyberPersona,
}


def _json_safe_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe = []
    for error in errors:
        cleaned = {}
        for key, value in error.items():
            if key == "ctx" and isinstance(value, dict):
                cleaned[key] = {ctx_key: str(ctx_value) for ctx_key, ctx_value in value.items()}
            else:
                cleaned[key] = value
        safe.append(cleaned)
    return safe


def validate_persona(lob: str, persona: dict[str, Any]) -> dict[str, Any]:
    model = _MODELS.get(lob)
    if not model:
        raise PersonaValidationError(lob, [{"loc": ("lob",), "msg": f"Unsupported LOB: {lob}"}])

    try:
        validated = model.model_validate(persona)
    except ValidationError as exc:
        raise PersonaValidationError(lob, exc.errors()) from exc

    return validated.model_dump(exclude_none=True)
