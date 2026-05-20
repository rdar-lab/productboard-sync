from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from typing import Any

from productboard_sync.productboard.models import Entity, Member, Note, NoteContentMessage, Team


def _join_tags(tags: list) -> str:
    return " | ".join(tag.name for tag in tags if getattr(tag, "name", None))


def _format_owner(owner) -> str:
    if owner is None:
        return ""
    return owner.email or owner.id or ""


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " | ".join(_stringify_value(item) for item in value if item is not None)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)


def entities_to_csv(entities: Iterable[Entity], columns: list[tuple[str, str]]) -> tuple[str, int]:
    output = io.StringIO()
    header = ["id", "type", "createdAt", "updatedAt"] + [display for _, display in columns]
    writer = csv.DictWriter(output, fieldnames=header, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()

    count = 0
    for entity in entities:
        fields = entity.fields
        extra = fields.model_extra or {}

        row: dict[str, Any] = {
            "id": entity.id,
            "type": entity.type,
            "createdAt": entity.createdAt or "",
            "updatedAt": entity.updatedAt or "",
        }

        for field_id, display_name in columns:
            if field_id == "name":
                row[display_name] = fields.name or ""
            elif field_id == "status":
                row[display_name] = fields.status.name if fields.status else ""
            elif field_id == "owner":
                row[display_name] = _format_owner(fields.owner)
            elif field_id == "tags":
                row[display_name] = _join_tags(fields.tags)
            elif field_id == "timeframe":
                if fields.timeframe:
                    row[display_name] = f"{fields.timeframe.startDate or ''} - {fields.timeframe.endDate or ''}"
                else:
                    row[display_name] = ""
            elif field_id == "archived":
                row[display_name] = str(fields.archived) if fields.archived is not None else ""
            else:
                row[display_name] = _stringify_value(extra.get(field_id, ""))

        writer.writerow(row)
        count += 1

    return output.getvalue(), count


def notes_to_csv(notes: Iterable[Note]) -> tuple[str, int]:
    output = io.StringIO()
    fieldnames = [
        "id",
        "type",
        "name",
        "content",
        "owner",
        "creator",
        "tags",
        "processed",
        "archived",
        "linked_features",
        "createdAt",
        "updatedAt",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()

    count = 0
    for note in notes:
        fields = note.fields

        if isinstance(fields.content, list):
            content = " | ".join(
                f"{message.authorName}: {message.content}"
                for message in fields.content
                if isinstance(message, NoteContentMessage)
            )
        else:
            content = fields.content or ""

        relationships = note.relationships or []
        linked = [
            rel.target.id
            for rel in relationships
            if rel.type == "link" and rel.target and rel.target.id
        ]

        writer.writerow(
            {
                "id": note.id,
                "type": note.type,
                "name": fields.name or "",
                "content": content,
                "owner": _format_owner(fields.owner),
                "creator": _format_owner(fields.creator),
                "tags": _join_tags(fields.tags),
                "processed": str(fields.processed) if fields.processed is not None else "",
                "archived": str(fields.archived) if fields.archived is not None else "",
                "linked_features": " | ".join(linked),
                "createdAt": note.createdAt or "",
                "updatedAt": note.updatedAt or "",
            }
        )
        count += 1

    return output.getvalue(), count


def members_to_csv(members: Iterable[Member]) -> tuple[str, int]:
    output = io.StringIO()
    fieldnames = ["id", "name", "email", "role", "disabled"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    count = 0
    for member in members:
        f = member.fields
        writer.writerow(
            {
                "id": member.id,
                "name": f.name or "",
                "email": f.email or "",
                "role": f.role or "",
                "disabled": str(f.disabled) if f.disabled is not None else "",
            }
        )
        count += 1
    return output.getvalue(), count


def teams_to_csv(teams: Iterable[Team]) -> tuple[str, int]:
    output = io.StringIO()
    fieldnames = ["id", "name", "handle", "description", "createdAt", "updatedAt"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    count = 0
    for team in teams:
        f = team.fields
        writer.writerow(
            {
                "id": team.id,
                "name": f.name or "",
                "handle": f.handle or "",
                "description": f.description or "",
                "createdAt": team.createdAt or "",
                "updatedAt": team.updatedAt or "",
            }
        )
        count += 1
    return output.getvalue(), count
