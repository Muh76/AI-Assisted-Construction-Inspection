"""Interactively verify TODO placeholder regulation clauses against uploaded PDFs.

For each seed clause still marked with a `# TODO:` section comment in
`seed_regulations.py`, prompts for a regulation document and page range, runs
text extract + Claude-assisted parse-clauses on that range, prints candidates,
and lets you confirm one — replacing the guessed section with a verified one.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import RegulationClause, RegulationDocument, RegulationText
from app.parsing.clause_extract import (
    extract_candidate_clauses,
    refine_candidate_clauses,
)
from app.parsing.regulation_text import extract_regulation_pages
from scripts.audit_rules import _load_seed_todo_sections
from scripts.seed_regulations import REGULATION_CLAUSE_SEEDS, RegulationClauseSeed

# Guessed seed sections → rule modules that hardcode the same citation.
SEED_SECTION_TO_RULE_FILE: dict[str, Path] = {
    "3.3.2.4": Path("app/rules/corridor_width.py"),
    "3.4.7.1": Path("app/rules/door_width.py"),
    "3.4.7.2": Path("app/rules/exit_width.py"),
    "3.4.2.7": Path("app/rules/travel_distance.py"),
    "3.4.2.1": Path("app/rules/required_exits.py"),
    "3.2.2.1": Path("app/rules/sprinkler_coverage.py"),
    "3.2.5.1": Path("app/rules/fire_extinguisher.py"),
    "3.1.9.4": Path("app/rules/penetrations.py"),
    "3.1.3.2": Path("app/rules/fire_separation.py"),
    "3.1.2.1": Path("app/rules/occupant_load.py"),
}

SCRIPTS_DIR = Path(__file__).resolve().parent
API_ROOT = SCRIPTS_DIR.parent
SEED_PATH = SCRIPTS_DIR / "seed_regulations.py"


def _todo_placeholder_seeds() -> list[RegulationClauseSeed]:
    todo_sections = _load_seed_todo_sections()
    return [seed for seed in REGULATION_CLAUSE_SEEDS if seed.section in todo_sections]


def _prompt(message: str) -> str:
    try:
        return input(message).strip()
    except EOFError:
        print()
        raise SystemExit("Aborted.") from None


def _prompt_int(message: str, *, minimum: int | None = None) -> int:
    while True:
        raw = _prompt(message)
        try:
            value = int(raw)
        except ValueError:
            print("Enter an integer.")
            continue
        if minimum is not None and value < minimum:
            print(f"Value must be >= {minimum}.")
            continue
        return value


def _title_and_description(text: str, preferred_title: str | None) -> tuple[str, str]:
    stripped = text.strip()
    if not stripped:
        return preferred_title or "", ""

    first_line = stripped.splitlines()[0].strip()
    title = (preferred_title or "").strip() or first_line
    return title, stripped


def _list_documents(db: Session) -> list[RegulationDocument]:
    return list(
        db.scalars(
            select(RegulationDocument).order_by(RegulationDocument.uploaded_at.desc())
        ).all()
    )


def _print_documents(documents: list[RegulationDocument]) -> None:
    print()
    print("Available regulation documents")
    print("-" * 40)
    if not documents:
        print("(none uploaded yet — upload a PDF via the API first)")
        return
    for document in documents:
        print(
            f"  id={document.id}  {document.code} {document.edition}  "
            f"{document.file_path}"
        )


def _print_seed(seed: RegulationClauseSeed, index: int, total: int) -> None:
    print()
    print("=" * 72)
    print(f"Placeholder {index}/{total}: {seed.code} {seed.section}")
    print(f"  title:       {seed.title}")
    print(f"  threshold:   {seed.threshold_value} {seed.threshold_unit or ''}".rstrip())
    print(f"  description: {seed.description}")
    print("=" * 72)


def _print_candidates(candidates: list[dict]) -> None:
    print()
    print(f"Candidates ({len(candidates)})")
    print("-" * 72)
    if not candidates:
        print("(no section candidates found in this page range)")
        return

    for index, candidate in enumerate(candidates, start=1):
        is_clause = candidate.get("is_regulation_clause")
        title = candidate.get("title") or "—"
        threshold_value = candidate.get("threshold_value")
        threshold_unit = candidate.get("threshold_unit") or ""
        note = candidate.get("claude_confidence_note") or "—"
        text = str(candidate.get("text") or "").replace("\n", " ").strip()
        if len(text) > 160:
            text = text[:157] + "..."

        print(
            f"[{index}] section={candidate.get('section')}  "
            f"page={candidate.get('page_number')}  "
            f"is_clause={is_clause}"
        )
        print(f"     title={title}")
        print(f"     threshold={threshold_value} {threshold_unit}".rstrip())
        print(f"     note={note}")
        print(f"     text={text}")
        print()


def _pages_in_range(
    db: Session,
    document_id: int,
    start_page: int,
    end_page: int,
) -> list[RegulationText]:
    return list(
        db.scalars(
            select(RegulationText)
            .where(
                RegulationText.document_id == document_id,
                RegulationText.page_number >= start_page,
                RegulationText.page_number <= end_page,
            )
            .order_by(RegulationText.page_number)
        ).all()
    )


def _update_seed_file(old_section: str, new_section: str) -> None:
    source = SEED_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(^[ \t]*# TODO:.*\n)([ \t]*section=\"{re.escape(old_section)}\")",
        re.MULTILINE,
    )

    def _replacer(match: re.Match[str]) -> str:
        return match.group(2).replace(
            f'section="{old_section}"',
            f'section="{new_section}"',
            1,
        )

    updated, count = pattern.subn(_replacer, source)
    if count != 1:
        print(
            f"  Warning: could not uniquely update TODO section "
            f'"{old_section}" in seed_regulations.py (matches={count}).'
        )
        return
    SEED_PATH.write_text(updated, encoding="utf-8")
    print(f"  Updated seed_regulations.py: {old_section} -> {new_section} (TODO removed)")


def _update_rule_section_constant(old_section: str, new_section: str) -> None:
    relative = SEED_SECTION_TO_RULE_FILE.get(old_section)
    if relative is None:
        print(f"  Warning: no rule module mapped for seed section {old_section}")
        return

    path = API_ROOT / relative
    source = path.read_text(encoding="utf-8")
    needle = f'REGULATION_CLAUSE_SECTION = "{old_section}"'
    replacement = f'REGULATION_CLAUSE_SECTION = "{new_section}"'
    if needle not in source:
        print(f"  Warning: {relative} does not contain {needle}")
        return
    path.write_text(source.replace(needle, replacement, 1), encoding="utf-8")
    print(f"  Updated {relative}: {old_section} -> {new_section}")


def _confirm_candidate(
    db: Session,
    seed: RegulationClauseSeed,
    candidate: dict,
) -> None:
    new_section = str(candidate.get("section") or "").strip()
    if not new_section:
        raise ValueError("Selected candidate has no section")

    title, description = _title_and_description(
        str(candidate.get("text") or ""),
        candidate.get("title"),
    )
    threshold_value = candidate.get("threshold_value")
    threshold_unit = candidate.get("threshold_unit")
    if threshold_value is None:
        threshold_value = seed.threshold_value
        threshold_unit = seed.threshold_unit

    placeholder = db.scalar(
        select(RegulationClause).where(
            RegulationClause.code == seed.code,
            RegulationClause.section == seed.section,
        )
    )
    existing_new = db.scalar(
        select(RegulationClause).where(
            RegulationClause.code == seed.code,
            RegulationClause.section == new_section,
        )
    )

    if placeholder is None and existing_new is None:
        clause = RegulationClause(
            code=seed.code,
            section=new_section,
            title=title,
            description=description,
            threshold_value=threshold_value,
            threshold_unit=threshold_unit,
        )
        db.add(clause)
        action = "created"
    elif placeholder is not None and (existing_new is None or existing_new.id == placeholder.id):
        placeholder.section = new_section
        placeholder.title = title
        placeholder.description = description
        placeholder.threshold_value = threshold_value
        placeholder.threshold_unit = threshold_unit
        action = "updated placeholder"
    elif placeholder is not None and existing_new is not None:
        existing_new.title = title
        existing_new.description = description
        existing_new.threshold_value = threshold_value
        existing_new.threshold_unit = threshold_unit
        db.delete(placeholder)
        action = "merged into existing section row; deleted guessed placeholder"
    else:
        assert existing_new is not None
        existing_new.title = title
        existing_new.description = description
        existing_new.threshold_value = threshold_value
        existing_new.threshold_unit = threshold_unit
        action = "updated existing section row"

    db.commit()
    print(f"  Database: {action} ({seed.code} {seed.section} -> {new_section})")

    if new_section != seed.section:
        _update_seed_file(seed.section, new_section)
        _update_rule_section_constant(seed.section, new_section)
    else:
        # Guessed section was already correct — still drop the TODO marker.
        _update_seed_file(seed.section, new_section)
        print("  Section number unchanged; TODO comment removed from seed file.")


def _handle_placeholder(db: Session, seed: RegulationClauseSeed, index: int, total: int) -> str:
    """Return 'confirmed', 'skipped', or 'quit'."""
    _print_seed(seed, index, total)

    while True:
        documents = _list_documents(db)
        _print_documents(documents)

        choice = _prompt(
            "Enter document id (or 's' to skip this placeholder, 'q' to quit): "
        ).lower()
        if choice in {"q", "quit"}:
            return "quit"
        if choice in {"s", "skip"}:
            print("Skipped.")
            return "skipped"

        try:
            document_id = int(choice)
        except ValueError:
            print("Enter a document id, s, or q.")
            continue

        document = db.get(RegulationDocument, document_id)
        if document is None:
            print(f"Document {document_id} not found.")
            continue

        start_page = _prompt_int("Start page (1-based): ", minimum=1)
        end_page = _prompt_int("End page (1-based): ", minimum=1)
        if end_page < start_page:
            print("end page must be >= start page.")
            continue

        print(
            f"Extracting text from {document.code} {document.edition} "
            f"pages {start_page}-{end_page}..."
        )
        try:
            pages_processed = extract_regulation_pages(
                document_id,
                start_page,
                end_page,
                db,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"Extract failed: {exc}")
            continue

        print(f"Extracted {pages_processed} page(s). Parsing clauses with Claude...")
        text_pages = _pages_in_range(db, document_id, start_page, end_page)
        regex_candidates = extract_candidate_clauses(text_pages)
        try:
            candidates = refine_candidate_clauses(regex_candidates)
        except RuntimeError as exc:
            print(f"Claude refinement failed: {exc}")
            print("Showing regex-only candidates instead.")
            candidates = [
                {
                    **row,
                    "is_regulation_clause": None,
                    "title": None,
                    "threshold_value": None,
                    "threshold_unit": None,
                    "claude_confidence_note": str(exc),
                }
                for row in regex_candidates
            ]

        _print_candidates(candidates)
        if not candidates:
            retry = _prompt("No candidates. Retry with another range? [Y/n]: ").lower()
            if retry in {"", "y", "yes"}:
                continue
            print("Skipped.")
            return "skipped"

        pick = _prompt(
            "Pick candidate number to confirm "
            "(or 'r' retry range, 's' skip, 'q' quit): "
        ).lower()
        if pick in {"q", "quit"}:
            return "quit"
        if pick in {"s", "skip"}:
            print("Skipped.")
            return "skipped"
        if pick in {"r", "retry"}:
            continue

        try:
            selected_index = int(pick)
        except ValueError:
            print("Enter a candidate number, r, s, or q.")
            continue
        if selected_index < 1 or selected_index > len(candidates):
            print("Candidate number out of range.")
            continue

        selected = candidates[selected_index - 1]
        confirm = _prompt(
            f"Confirm replace {seed.code} {seed.section} -> "
            f"{selected.get('section')}? [y/N]: "
        ).lower()
        if confirm not in {"y", "yes"}:
            print("Not confirmed; choose again or retry.")
            continue

        _confirm_candidate(db, seed, selected)
        return "confirmed"


def run() -> int:
    placeholders = _todo_placeholder_seeds()
    if not placeholders:
        print("No TODO-marked placeholder clauses remain in seed_regulations.py.")
        return 0

    print(
        f"Found {len(placeholders)} TODO placeholder clause(s) to verify.\n"
        "For each one you will extract a page range, review Claude-refined "
        "candidates, and optionally confirm a replacement section."
    )

    confirmed = 0
    skipped = 0
    db = SessionLocal()
    try:
        for index, seed in enumerate(placeholders, start=1):
            result = _handle_placeholder(db, seed, index, len(placeholders))
            if result == "confirmed":
                confirmed += 1
            elif result == "skipped":
                skipped += 1
            else:
                print("Quit.")
                break
    finally:
        db.close()

    print()
    print("=" * 72)
    print(f"Done. confirmed={confirmed} skipped={skipped}")
    return 0


def main() -> None:
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
