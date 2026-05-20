import pytest

from productboard_sync.storage.local import LocalStorageBackend


def sample_entity_payload(entity_type="feature"):
    return {
        "id": "abc-123",
        "type": entity_type,
        "fields": {
            "name": "Test Feature",
            "owner": {"id": "user-1", "email": "owner@example.com"},
            "tags": [{"id": "t1", "name": "api"}, {"id": "t2", "name": "enterprise"}],
            "status": {"id": "s1", "name": "In Progress"},
            "timeframe": {"startDate": "2024-01-01", "endDate": "2024-03-31"},
            "archived": False,
        },
        "relationships": None,
        "links": {"self": "https://api.productboard.com/v2/entities/abc-123"},
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-06-01T00:00:00Z",
    }


def sample_text_note_payload():
    return {
        "id": "note-1",
        "type": "textNote",
        "fields": {
            "name": "Customer feedback",
            "content": "App is slow on mobile",
            "tags": [{"name": "feedback"}],
            "owner": {"id": "user-1", "email": "pm@example.com"},
            "creator": {"id": "user-2", "email": "cs@example.com"},
            "processed": True,
            "archived": False,
        },
        "relationships": [{"type": "link", "target": {"id": "abc-123", "type": "feature"}}],
        "createdAt": "2024-01-15T10:00:00Z",
        "updatedAt": "2024-01-16T08:00:00Z",
    }


def sample_conversation_note_payload():
    return {
        "id": "note-2",
        "type": "conversationNote",
        "fields": {
            "name": "Support chat",
            "content": [
                {
                    "externalId": "m1",
                    "content": "Hello I need help",
                    "authorName": "John",
                    "authorType": "customer",
                    "timestamp": "2024-01-15T10:00:00Z",
                },
                {
                    "externalId": "m2",
                    "content": "How can I help?",
                    "authorName": "Agent",
                    "authorType": "agent",
                    "timestamp": "2024-01-15T10:01:00Z",
                },
            ],
            "tags": [],
            "owner": {"id": "user-1", "email": "pm@example.com"},
            "creator": None,
            "processed": False,
            "archived": False,
        },
        "relationships": [],
        "createdAt": "2024-01-15T10:00:00Z",
        "updatedAt": "2024-01-15T10:05:00Z",
    }


def sample_member_payload():
    return {
        "id": "user-1",
        "name": "Alice Smith",
        "email": "alice@example.com",
        "role": "admin",
        "disabled": False,
    }


def sample_team_payload():
    return {
        "id": "team-1",
        "name": "Product Team",
        "handle": "product",
        "description": "Core product team",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-06-01T00:00:00Z",
    }


@pytest.fixture
def tmp_local_backend(tmp_path):
    return LocalStorageBackend(tmp_path)


@pytest.fixture(autouse=True)
def clear_settings_cache():
    yield
    from productboard_sync.config import get_settings
    get_settings.cache_clear()
