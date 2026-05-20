import csv
import io
from tests.conftest import (
    sample_entity_payload, sample_text_note_payload,
    sample_conversation_note_payload, sample_member_payload, sample_team_payload
)
from productboard_sync.productboard.models import Entity, Note, Member, Team
from productboard_sync.sync.transformers import entities_to_csv, notes_to_csv, members_to_csv, teams_to_csv
from productboard_sync.sync.fields import STANDARD_FIELD_IDS

STANDARD_COLUMNS = [(f, f) for f in STANDARD_FIELD_IDS]


def parse_csv(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def test_entities_csv_header_contains_display_names():
    columns = [("name", "Feature Name"), ("status", "Status")]
    csv_content, _ = entities_to_csv([], columns)
    first_line = csv_content.split("\n")[0]
    assert "Feature Name" in first_line
    assert "Status" in first_line


def test_entities_csv_includes_all_records():
    entities = [Entity.model_validate(sample_entity_payload()) for _ in range(3)]
    csv_content, count = entities_to_csv(entities, STANDARD_COLUMNS)
    rows = parse_csv(csv_content)
    assert len(rows) == 3
    assert count == 3


def test_entities_csv_tags_joined_with_pipe():
    entity = Entity.model_validate(sample_entity_payload())
    csv_content, _ = entities_to_csv([entity], STANDARD_COLUMNS)
    rows = parse_csv(csv_content)
    assert "api" in rows[0]["tags"]
    assert "|" in rows[0]["tags"]


def test_entities_csv_empty_returns_header_only():
    csv_content, count = entities_to_csv([], STANDARD_COLUMNS)
    rows = parse_csv(csv_content)
    assert rows == []
    assert count == 0
    assert "name" in csv_content  # header present


def test_notes_csv_has_row_per_note():
    notes = [
        Note.model_validate(sample_text_note_payload()),
        Note.model_validate(sample_conversation_note_payload()),
    ]
    csv_content, count = notes_to_csv(notes)
    rows = parse_csv(csv_content)
    assert len(rows) == 2
    assert count == 2


def test_conversation_note_content_joined():
    note = Note.model_validate(sample_conversation_note_payload())
    csv_content, _ = notes_to_csv([note])
    rows = parse_csv(csv_content)
    assert "John: Hello I need help" in rows[0]["content"]
    assert "Agent: How can I help?" in rows[0]["content"]


def test_notes_csv_redacted_owner_written_as_is():
    payload = sample_text_note_payload()
    payload["fields"]["owner"] = {"id": "u1", "email": "[redacted]"}
    note = Note.model_validate(payload)
    csv_content, _ = notes_to_csv([note])
    rows = parse_csv(csv_content)
    assert rows[0]["owner"] == "[redacted]"


def test_members_csv_correct_headers():
    member = Member.model_validate(sample_member_payload())
    csv_content, _ = members_to_csv([member])
    rows = parse_csv(csv_content)
    assert set(rows[0].keys()) == {"id", "name", "email", "role", "disabled"}


def test_teams_csv_correct_headers():
    team = Team.model_validate(sample_team_payload())
    csv_content, _ = teams_to_csv([team])
    rows = parse_csv(csv_content)
    assert set(rows[0].keys()) == {"id", "name", "handle", "description", "createdAt", "updatedAt"}
