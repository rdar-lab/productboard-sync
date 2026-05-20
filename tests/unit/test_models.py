from productboard_sync.productboard.models import Entity, Note, NoteContentMessage, Member, Team, PaginatedResponse


def test_entity_parses_valid_payload():
    from tests.conftest import sample_entity_payload
    entity = Entity.model_validate(sample_entity_payload())
    assert entity.id == "abc-123"
    assert entity.type == "feature"
    assert entity.fields.name == "Test Feature"
    assert entity.fields.status.name == "In Progress"
    assert len(entity.fields.tags) == 2


def test_entity_optional_fields_default_to_none():
    entity = Entity.model_validate({"id": "x", "type": "feature", "fields": {}})
    assert entity.fields.name is None
    assert entity.fields.owner is None
    assert entity.fields.tags == []


def test_text_note_content_is_string():
    from tests.conftest import sample_text_note_payload
    note = Note.model_validate(sample_text_note_payload())
    assert isinstance(note.fields.content, str)
    assert note.fields.content == "App is slow on mobile"


def test_conversation_note_content_is_list():
    from tests.conftest import sample_conversation_note_payload
    note = Note.model_validate(sample_conversation_note_payload())
    assert isinstance(note.fields.content, list)
    assert len(note.fields.content) == 2
    assert isinstance(note.fields.content[0], NoteContentMessage)
    assert note.fields.content[0].authorName == "John"


def test_paginated_response_parses():
    from tests.conftest import sample_entity_payload
    data = {"data": [sample_entity_payload()], "links": {"next": "https://api.productboard.com/v2/entities?pageCursor=abc"}}
    resp = PaginatedResponse.model_validate(data)
    assert len(resp.data) == 1
    assert resp.links.next is not None


def test_paginated_response_null_next():
    resp = PaginatedResponse.model_validate({"data": [], "links": {"next": None}})
    assert resp.links.next is None
