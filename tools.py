"""Deterministic tools for building vulnerability scoring and retrofit cost estimation.

The logic here is derived from the provided "Assignment Final.xlsx" sheets:
- Score Table: maps zone / year / soft-story / structure type to points and risk tiers.
- Cost Table: provides PWD cost rates by zone and intervention method.

These functions are designed to be deterministic and usable as "tool" functions in an LLM tool-calling workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class VulnerabilityResult:
    zone: str
    zone_points: int
    year: int
    year_points: int
    soft_story: str
    soft_story_points: int
    structure_type: str
    structure_points: int
    total_score: int
    risk_tier: str


@dataclass
class RetrofitEstimate:
    intervention_type: str
    zone: str
    quantity: float
    unit: str
    num_floors: int
    unit_cost_description: str
    estimated_cost_tk: float
    details: str


# ----- Scoring rules (from Score Table sheet) -----
ZONE_POINTS = {
    "zone 1": 10,
    "zone1": 10,
    "zone 2": 25,
    "zone2": 25,
    "zone 3": 40,
    "zone3": 40,
}

YEAR_POINTS = [
    (1993, 20),  # < 1993
    (2007, 15),  # 1993-2006
    (2016, 10),  # 2007-2015
    (9999, 5),
]

SOFT_STORY_POINTS = {
    "open": 20,
    "piloti": 20,
    "open/piloti": 20,
    "open ground floor": 20,
    "piloti ground floor": 20,
    "solid": 0,
    "solid ground floor": 0,
    "no": 0,
    "none": 0,
}

STRUCTURE_TYPE_POINTS = {
    "urm": 20,
    "urm (old dhaka)": 20,
    "rc soft story": 10,
    "rc soft story (6-9 story)": 10,
    "rc infilled": 5,
    "rc infilled (engineered)": 5,
    "rc non-engineered": 8,
    "rc non-engineered (poor detailing)": 8,
    "high-rise": 5,
    "high-rise (deep pile)": 5,
}

RISK_TIERS = [
    (70, "Critical"),
    (45, "High"),
    (25, "Moderate"),
    (0, "Low"),
]


def _normalize_text(text: Optional[str]) -> str:
    if text is None:
        return ""
    return str(text).strip().lower()


def calculate_vulnerability_score(
    soil_type: str, construction_year: int, soft_story: str, structure_type: str
) -> VulnerabilityResult:
    """Calculate a deterministic vulnerability score based on the research tables.

    Args:
        soil_type: e.g. "Zone 1", "Zone 2", "Zone 3" (as per Dhaka zones).
        construction_year: The year the building was constructed.
        soft_story: A description indicating whether the ground floor is open/piloti.
        structure_type: Structural description, e.g. "RC Soft Story", "URM", etc.

    Returns:
        VulnerabilityResult containing component scores, total, and risk tier.
    """

    zone_norm = _normalize_text(soil_type)
    zone_points = ZONE_POINTS.get(zone_norm, 0)

    # Year points
    year_points = 0
    for ceiling_year, pts in YEAR_POINTS:
        if construction_year < ceiling_year:
            year_points = pts
            break

    soft_norm = _normalize_text(soft_story)
    soft_story_points = SOFT_STORY_POINTS.get(soft_norm, 0)

    struct_norm = _normalize_text(structure_type)
    structure_points = STRUCTURE_TYPE_POINTS.get(struct_norm, 0)

    total_score = zone_points + year_points + soft_story_points + structure_points

    risk_tier = "Unknown"
    for threshold, tier in RISK_TIERS:
        if total_score >= threshold:
            risk_tier = tier
            break

    return VulnerabilityResult(
        zone=soil_type,
        zone_points=zone_points,
        year=construction_year,
        year_points=year_points,
        soft_story=soft_story,
        soft_story_points=soft_story_points,
        structure_type=structure_type,
        structure_points=structure_points,
        total_score=total_score,
        risk_tier=risk_tier,
    )


# ----- Cost estimation rules (from Cost Table sheet) -----
# We keep a simplified cost database; the full table can be extended easily.
COST_RATES = {
    "zone 1": {
        "column jacketing (with footing)": {
            "ground": 94232.5,
            "first": 45595,
            "escalation": 1.015,
            "unit": "m",
        },
        "shear walls (with footing)": {
            "ground": 75766.25,
            "first": 23966,
            "escalation": 1.015,
            "unit": "m2",
        },
        "steel bracing work in-fill steel brace": {
            "ground": 126000,
            "first": 23966,
            "escalation": 1.015,
            "unit": "m2",
        },
    },
    "zone 2": {
        "column jacketing (with footing)": {
            "ground": 94232.5,
            "first": 45595,
            "escalation": 1.015,
            "unit": "m",
        },
        "shear walls (with footing)": {
            "ground": 75766.25,
            "first": 23966,
            "escalation": 1.015,
            "unit": "m2",
        },
        "steel bracing work in-fill steel brace": {
            "ground": 126000,
            "first": 23966,
            "escalation": 1.015,
            "unit": "m2",
        },
        "deep foundation retrofitting": {
            "ground": 0,  # Not in PWD, separate estimate
            "first": 0,
            "escalation": 1.0,
            "unit": "unit",
        },
    },
    "zone 3": {
        "shear walls (with footing)": {
            "ground": 75766.25,
            "first": 23966,
            "escalation": 1.015,
            "unit": "m2",
        },
        "deep foundation piles": {
            "ground": 0,  # Not in PWD, separate estimate
            "first": 0,
            "escalation": 1.0,
            "unit": "unit",
        },
        "soil stabilization": {
            "ground": 0,  # Not in PWD, separate estimate
            "first": 0,
            "escalation": 1.0,
            "unit": "unit",
        },
    },
}


def estimate_retrofit_cost(
    intervention_type: str,
    quantity: float,
    zone: str = "Zone 2",
    num_floors: int = 2,
) -> RetrofitEstimate:
    """Estimate retrofit cost based on the Excel cost table.

    Args:
        intervention_type: e.g. "Column Jacketing (with footing)" or "Shear Walls (with footing)".
        quantity: The quantity of the work (e.g., meters of column, sqm of wall/frame) per floor.
        zone: The seismic/soil zone (Zone 1/2/3) used to choose rate table.
        num_floors: Number of floors for escalation cost computation.

    Returns:
        RetrofitEstimate with a rough cost estimate in Bangladeshi Taka.
    """

    zone_norm = _normalize_text(zone)
    intervention_norm = _normalize_text(intervention_type)

    zone_rates = COST_RATES.get(zone_norm)
    if not zone_rates:
        raise ValueError(
            f"Unknown zone '{zone}'. Valid choices are: {', '.join(COST_RATES.keys())}."
        )

    rate_info = zone_rates.get(intervention_norm)
    if not rate_info:
        valid = ", ".join(zone_rates.keys())
        raise ValueError(
            f"Intervention '{intervention_type}' not found for zone '{zone}'. Valid options: {valid}."
        )

    ground = rate_info["ground"]
    first = rate_info["first"]
    escalation = rate_info.get("escalation", 1.0)
    unit = rate_info.get("unit", "unit")

    details: list[str] = []

    if ground == 0 and first == 0:
        # PWD does not provide a rate; require engineering estimate.
        details.append(
            "PWD does not provide a rate for this intervention. Please consult an experienced structural engineer and provide drawings for a reliable estimate."
        )
        return RetrofitEstimate(
            intervention_type=intervention_type,
            zone=zone,
            quantity=quantity,
            unit=unit,
            num_floors=num_floors,
            unit_cost_description=f"No PWD rate (consult engineer)",
            estimated_cost_tk=0.0,
            details="; ".join(details),
        )

    # Cost per unit (m or m2) per floor.
    total_cost = 0.0

    # Ground floor
    ground_cost = ground * quantity
    total_cost += ground_cost
    details.append(f"Ground floor: {ground:,.2f} Tk per {unit} => {ground_cost:,.2f} Tk")

    # First floor
    first_cost = first * quantity
    total_cost += first_cost
    details.append(f"First floor: {first:,.2f} Tk per {unit} => {first_cost:,.2f} Tk")

    # Additional floors (2nd above ground and beyond)
    for floor_index in range(2, num_floors):
        multiplier = escalation ** (floor_index - 1)
        floor_rate = first * multiplier
        floor_cost = floor_rate * quantity
        total_cost += floor_cost
        details.append(
            f"Floor {floor_index + 1} (escalation {escalation:.3f}): {floor_rate:,.2f} Tk per {unit} => {floor_cost:,.2f} Tk"
        )

    return RetrofitEstimate(
        intervention_type=intervention_type,
        zone=zone,
        quantity=quantity,
        unit=unit,
        num_floors=num_floors,
        unit_cost_description=f"Rates per {unit} (ground/first+escalation)",
        estimated_cost_tk=total_cost,
        details="; ".join(details),
    )
