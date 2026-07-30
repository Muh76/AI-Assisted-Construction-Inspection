"""Seed regulation clauses matching hardcoded thresholds in app/rules/*.py."""

from dataclasses import dataclass

from sqlalchemy import select

from app.db import SessionLocal
from app.models import RegulationClause
from app.rules.corridor_width import MIN_CORRIDOR_CLEAR_WIDTH_MM
from app.rules.door_width import MIN_DOOR_CLEAR_WIDTH_MM
from app.rules.exit_width import MIN_EXIT_CLEAR_WIDTH_MM
from app.rules.fire_extinguisher import MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M
from app.rules.occupant_load import OCCUPANT_LOAD_FACTORS_SQM_PER_PERSON
from app.rules.required_exits import (
    MIN_EXITS_ABOVE_THRESHOLD,
    MIN_EXITS_AT_OR_BELOW_THRESHOLD,
    OCCUPANT_LOAD_EXIT_THRESHOLD,
)
from app.rules.travel_distance import MAX_TRAVEL_DISTANCE_SPRINKLERED_M

OFFICE_OCCUPANT_LOAD_FACTOR = OCCUPANT_LOAD_FACTORS_SQM_PER_PERSON["office"]


@dataclass(frozen=True)
class RegulationClauseSeed:
    code: str
    section: str
    title: str
    description: str
    threshold_value: float | None
    threshold_unit: str | None


# Sections marked with TODO below need manual verification against the current OBC.
REGULATION_CLAUSE_SEEDS: tuple[RegulationClauseSeed, ...] = (
    RegulationClauseSeed(
        code="OBC",
        # TODO: Verify exact OBC corridor clear-width citation.
        section="3.3.2.4",
        title="Minimum corridor clear width",
        description=(
            "Corridors serving as means of egress must provide a minimum clear "
            f"width of {MIN_CORRIDOR_CLEAR_WIDTH_MM:g} mm."
        ),
        threshold_value=MIN_CORRIDOR_CLEAR_WIDTH_MM,
        threshold_unit="mm",
    ),
    RegulationClauseSeed(
        code="OBC",
        # TODO: Verify exact OBC door clear-width citation.
        section="3.4.7.1",
        title="Minimum door clear width",
        description=(
            "Egress doors must provide a minimum clear width of "
            f"{MIN_DOOR_CLEAR_WIDTH_MM:g} mm."
        ),
        threshold_value=MIN_DOOR_CLEAR_WIDTH_MM,
        threshold_unit="mm",
    ),
    RegulationClauseSeed(
        code="OBC",
        # TODO: Verify exact OBC exit clear-width citation.
        section="3.4.7.2",
        title="Minimum exit clear width",
        description=(
            "Exits must provide a minimum clear width of "
            f"{MIN_EXIT_CLEAR_WIDTH_MM:g} mm."
        ),
        threshold_value=MIN_EXIT_CLEAR_WIDTH_MM,
        threshold_unit="mm",
    ),
    RegulationClauseSeed(
        code="OBC",
        # TODO: Verify exact OBC travel-distance citation for sprinklered buildings.
        section="3.4.2.7",
        title="Maximum travel distance (sprinklered)",
        description=(
            "In sprinklered buildings, the travel distance from any point to "
            f"an exit must not exceed {MAX_TRAVEL_DISTANCE_SPRINKLERED_M:g} m."
        ),
        threshold_value=MAX_TRAVEL_DISTANCE_SPRINKLERED_M,
        threshold_unit="m",
    ),
    RegulationClauseSeed(
        code="OBC",
        # TODO: Verify exact OBC required-exit count citation.
        section="3.4.2.1",
        title="Required number of exits",
        description=(
            "Projects with a total occupant load exceeding "
            f"{OCCUPANT_LOAD_EXIT_THRESHOLD} require at least "
            f"{MIN_EXITS_ABOVE_THRESHOLD} exits; otherwise at least "
            f"{MIN_EXITS_AT_OR_BELOW_THRESHOLD} exit is sufficient."
        ),
        threshold_value=float(OCCUPANT_LOAD_EXIT_THRESHOLD),
        threshold_unit="occupants",
    ),
    RegulationClauseSeed(
        code="OBC",
        # TODO: Verify exact OBC automatic sprinkler coverage citation.
        section="3.2.2.1",
        title="Automatic sprinkler coverage",
        description=(
            "All rooms in the project must be protected by an automatic "
            "sprinkler system."
        ),
        threshold_value=None,
        threshold_unit=None,
    ),
    RegulationClauseSeed(
        code="OBC",
        # TODO: Verify exact OBC/NFPA fire-extinguisher travel-distance citation.
        section="3.2.5.1",
        title="Maximum fire extinguisher travel distance",
        description=(
            "Portable fire extinguishers must be located so that the travel "
            f"distance to the nearest extinguisher does not exceed "
            f"{MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M:g} m."
        ),
        threshold_value=MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M,
        threshold_unit="m",
    ),
    RegulationClauseSeed(
        code="OBC",
        # TODO: Verify exact OBC penetration fire-stop rating citation.
        section="3.1.9.4",
        title="Penetration seal fire rating",
        description=(
            "Penetration seals must provide a fire-resistance rating equal to "
            "or greater than the rating required for the assembly penetrated."
        ),
        threshold_value=None,
        threshold_unit=None,
    ),
    RegulationClauseSeed(
        code="OBC",
        # TODO: Verify exact OBC fire-separation rating citation.
        section="3.1.3.2",
        title="Fire separation rating",
        description=(
            "Fire separations must provide a fire-resistance rating equal to "
            "or greater than the rating required for the separation."
        ),
        threshold_value=None,
        threshold_unit=None,
    ),
    RegulationClauseSeed(
        code="OBC",
        # TODO: Verify exact OBC occupant-load factor table citation.
        section="3.1.2.1",
        title="Occupant load factor (office / Group B)",
        description=(
            "Occupant load for office and Group B spaces must be calculated "
            f"using {OFFICE_OCCUPANT_LOAD_FACTOR:g} square metres of floor "
            "area per person."
        ),
        threshold_value=OFFICE_OCCUPANT_LOAD_FACTOR,
        threshold_unit="sqm/person",
    ),
)


def seed() -> None:
    db = SessionLocal()

    try:
        inserted = 0
        skipped = 0

        for clause_seed in REGULATION_CLAUSE_SEEDS:
            existing = db.scalar(
                select(RegulationClause).where(
                    RegulationClause.code == clause_seed.code,
                    RegulationClause.section == clause_seed.section,
                )
            )
            if existing is not None:
                skipped += 1
                continue

            db.add(
                RegulationClause(
                    code=clause_seed.code,
                    section=clause_seed.section,
                    title=clause_seed.title,
                    description=clause_seed.description,
                    threshold_value=clause_seed.threshold_value,
                    threshold_unit=clause_seed.threshold_unit,
                )
            )
            inserted += 1

        db.commit()
        print(
            f"Regulation clause seed complete: {inserted} inserted, {skipped} skipped."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    seed()


if __name__ == "__main__":
    main()
