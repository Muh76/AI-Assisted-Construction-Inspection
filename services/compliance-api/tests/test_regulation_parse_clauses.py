from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models import RegulationClause, RegulationDocument, RegulationText


@pytest.fixture
def sample_clause_text() -> str:
    return (
        "3.4.7.1 Door clear width\n"
        "Doors shall have a minimum clear width of 860 mm.\n"
        "\n"
        "3.4.7.2 Exit clear width\n"
        "Exits shall have a minimum clear width of 900 mm."
    )


@pytest.fixture
def regulation_document_with_text(
    db_session,
    sample_clause_text: str,
) -> RegulationDocument:
    document = RegulationDocument(
        code="OBC",
        edition="2024",
        file_path="data/regulations/obc-2024.pdf",
        uploaded_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(document)
    db_session.flush()

    db_session.add(
        RegulationText(
            document_id=document.id,
            page_number=1,
            raw_text=sample_clause_text,
        )
    )
    db_session.commit()
    db_session.refresh(document)
    return document


def test_preview_parsed_clauses(
    client,
    regulation_document_with_text: RegulationDocument,
    auth_headers,
):
    document_id = regulation_document_with_text.id

    response = client.post(
        f"/api/v1/regulations/documents/{document_id}/parse-clauses",
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["preview"] is True
    assert len(body["clauses"]) == 2
    assert body["clauses"][0]["section"] == "3.4.7.1"
    assert "Door clear width" in body["clauses"][0]["text"]
    assert body["clauses"][0]["page_number"] == 1
    assert body["clauses"][1]["section"] == "3.4.7.2"


def test_preview_parsed_clauses_document_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/regulations/documents/99999/parse-clauses",
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Regulation document not found"


def test_confirm_parsed_clauses_updates_existing(
    client,
    db_session,
    regulation_document_with_text: RegulationDocument,
    auth_headers,
):
    document_id = regulation_document_with_text.id
    placeholder = RegulationClause(
        code="OBC",
        section="3.4.7.1",
        title="Minimum door clear width",
        description="Placeholder seeded description.",
        threshold_value=800.0,
        threshold_unit="mm",
    )
    db_session.add(placeholder)
    db_session.commit()

    response = client.post(
        f"/api/v1/regulations/documents/{document_id}/parse-clauses/confirm",
        json={
            "clauses": [
                {
                    "section": "3.4.7.1",
                    "text": (
                        "Door clear width\n"
                        "Doors shall have a minimum clear width of 860 mm."
                    ),
                    "threshold_value": 860.0,
                    "threshold_unit": "mm",
                }
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["document_id"] == document_id
    assert body["created"] == []
    assert len(body["updated"]) == 1
    assert body["updated"][0]["section"] == "3.4.7.1"
    assert body["updated"][0]["title"] == "Door clear width"
    assert "860 mm" in body["updated"][0]["description"]
    assert body["updated"][0]["threshold_value"] == 860.0
    assert body["updated"][0]["threshold_unit"] == "mm"

    stored = db_session.scalar(
        select(RegulationClause).where(
            RegulationClause.code == "OBC",
            RegulationClause.section == "3.4.7.1",
        )
    )
    assert stored is not None
    assert stored.id == placeholder.id
    assert stored.title == "Door clear width"
    assert stored.threshold_value == 860.0


def test_confirm_parsed_clauses_creates_new(
    client,
    db_session,
    regulation_document_with_text: RegulationDocument,
    auth_headers,
):
    document_id = regulation_document_with_text.id

    response = client.post(
        f"/api/v1/regulations/documents/{document_id}/parse-clauses/confirm",
        json={
            "clauses": [
                {
                    "section": "3.4.7.2",
                    "text": (
                        "Exit clear width\n"
                        "Exits shall have a minimum clear width of 900 mm."
                    ),
                    "threshold_value": 900.0,
                    "threshold_unit": "mm",
                }
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["document_id"] == document_id
    assert len(body["created"]) == 1
    assert body["updated"] == []
    assert body["created"][0]["section"] == "3.4.7.2"
    assert body["created"][0]["threshold_value"] == 900.0

    stored = db_session.scalar(
        select(RegulationClause).where(
            RegulationClause.code == "OBC",
            RegulationClause.section == "3.4.7.2",
        )
    )
    assert stored is not None
    assert stored.threshold_unit == "mm"
