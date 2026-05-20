# Productboard Public REST API — Reference

> Researched from the Productboard OpenAPI v2 specs (OpenAPI 3.1.1, version `2.0.0`).  
> Source: https://developer.productboard.com

---

## Summary

The Productboard API is a **v2 REST API** served from `https://api.productboard.com/v2`. It is organized into 8 OpenAPI spec modules: entities, notes, members, teams, analytics, webhooks, jira-integrations, and plugin-integrations. All endpoints use cursor-based pagination via `pageCursor`, Bearer token auth, and return standardized JSON envelopes with `{data, links}`. Incremental sync is well-supported for notes via `updatedFrom`/`updatedTo` query params, and for entities via the search endpoint's `filter.updatedAt` range. Webhooks support 23 event types covering all major entity changes.

---

## 1. Authentication

### Bearer Token (API Key — for sync tools)
```http
Authorization: Bearer <your_api_token>
```
The token is a static API access token generated in the Productboard workspace settings. It is long-lived. Set it as the `Authorization` header on every request.

```python
headers = {
    "Authorization": "Bearer <token>",
    "Content-Type": "application/json",
}
```

### OAuth 2.0 (Authorization Code — for multi-tenant apps)
- **Authorize URL:** `https://app.productboard.com/oauth/authorize`
- **Token URL:** `https://app.productboard.com/oauth/token`

**Relevant read scopes for a sync tool:**

| Scope | Access |
|---|---|
| `entities:read` | Read features, components, products, initiatives, etc. |
| `notes:read` | Read notes/insights |
| `members:read` | Read workspace members |
| `members:pii:read` | Unredact emails/names (without this, returns `"[redacted]"`) |
| `teams:read` | Read teams |
| `analytics:read` | Read member activity data |
| `webhooks:read` | Read webhook subscriptions |

---

## 2. Base URL and Versioning

**Production Base URL:** `https://api.productboard.com/v2`

Versioning is in the **URL path**. There is **no `X-Version` header** in the v2 API — that was a concept from the deprecated v1 API (`https://api.productboard.com/features`, etc.).

---

## 3. Available Read Endpoints

### 3a. Entities (Features, Components, Products, etc.)

Entity types: `product`, `component`, `feature`, `subfeature`, `initiative`, `objective`, `keyResult`, `release`, `releaseGroup`, `company`, `user`

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/entities/configurations` | Introspect all entity types, fields, and filters available in the workspace |
| `GET` | `/entities/configurations/{type}` | Introspect a single type (e.g. `feature`) — get exact field definitions |
| `GET` | `/entities` | List entities — paginated, filterable by type, name, owner, status, parent, archived |
| `GET` | `/entities/{id}` | Get single entity by UUID |
| `POST` | `/entities/search` | Advanced search — filter by updatedAt/createdAt ranges, custom fields, relationships |
| `GET` | `/entities/{id}/relationships` | List parent/child/linked entities for one entity |
| `GET` | `/entities/fields/{id}/values` | List allowed values for a select/status field |

**GET /entities query params:**
```
type[]           = feature | component | product | etc. (repeatable)
name             = exact string match
owner[id]        = UUID
owner[email]     = email (requires members:pii:read scope)
status[id]       = UUID
status[name]     = string
archived         = true | false
parent[id]       = UUID
pageCursor       = opaque cursor from links.next
fields           = all | default | name,status,owner (comma-separated)
```

**POST /entities/search body** (required for date-range / incremental sync):
```json
{
  "data": {
    "filter": {
      "type": ["feature"],
      "updatedAt": { "from": "2024-01-01T00:00:00Z", "to": "2024-12-31T23:59:59Z" },
      "createdAt": { "from": "...", "to": "..." },
      "fields": {
        "archived": false,
        "status": [{"name": "In Progress"}],
        "owner": [{"id": "uuid-of-member"}]
      },
      "relationships": {
        "parent": [{"id": "uuid-of-parent"}]
      }
    },
    "return": {
      "fields": ["name", "status", "owner", "tags"]
    }
  }
}
```

> ⚠️ `GET /entities` does **not** support `updatedAt` filtering. For incremental sync by date, you **must** use `POST /entities/search`. Pass `?pageCursor=` as a query param on subsequent pages (not in the body).

### 3b. Notes / Insights

Note types: `textNote`, `conversationNote`, `opportunityNote` (opportunityNote is read-only)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/notes/configurations` | Introspect note field definitions |
| `GET` | `/notes` | List notes — paginated, supports date range filters |
| `GET` | `/notes/{id}` | Get single note |
| `POST` | `/notes/search` | Advanced search — filter by customers, linked features, etc. |
| `GET` | `/notes/{id}/relationships` | Get customer and product-link relationships for a note |

**GET /notes query params** (ideal for incremental sync):
```
pageCursor                   = cursor
archived                     = true | false
processed                    = true | false
owner[id]                    = UUID
owner[email]                 = email
creator[id]                  = UUID
creator[email]               = email
metadata[source][system]     = e.g. "intercom"
metadata[source][recordId]   = e.g. "ticket-12345"
createdFrom                  = ISO-8601 datetime (inclusive)
createdTo                    = ISO-8601 datetime (inclusive)
updatedFrom                  = ISO-8601 datetime (inclusive)  ← key for incremental sync
updatedTo                    = ISO-8601 datetime (inclusive)
fields                       = all | default | name,content,tags
```

**archived/processed filter matrix:**

| `archived` | `processed` | Result |
|---|---|---|
| — | — | All notes |
| `false` | — | Processed + Unprocessed (non-archived) |
| — | `true` | Processed only |
| `true` | `false` | Archived only |
| `false` | `true` | Processed, non-archived |

### 3c. Members

| Method | Path | Filters |
|---|---|---|
| `GET` | `/members` | `query` (partial name/email), `roles[]` (admin/maker/viewer/contributor), `includeDisabled`, `includeInvitationPending` |
| `POST` | `/members/search` | Batch by IDs, emails, roles |
| `GET` | `/members/{id}` | Single member |

**Member fields** (requires `members:pii:read` for non-redacted values): `name`, `username`, `email`, `role`, `disabled`, `invitationPending`, `teams[]`

### 3d. Teams

| Method | Path | Filters |
|---|---|---|
| `GET` | `/teams` | `name` (exact), `handle` (exact), `query` (partial) |
| `POST` | `/teams/search` | Batch by IDs, names, handles |
| `GET` | `/teams/{id}` | Single team |
| `GET` | `/teams/{id}/members` | Members of a team |

**Team fields:** `name`, `handle`, `description`, `avatarUrl`, `createdAt`, `updatedAt`

### 3e. Analytics

| Method | Path | Filters |
|---|---|---|
| `GET` | `/analytics/member-activities` | `dateFrom` (ISO date), `dateTo` (ISO date) |

**Activity record fields:** `date`, `domain`, `memberId`, `role`, `activeFlag`, plus daily counts for boards, features, components, notes, and insights created/opened.

---

## 4. Response Shapes

### Entity / Feature Response
```json
{
  "data": {
    "id": "195a1cb2-728f-4be8-900f-aebbd84d7944",
    "type": "feature",
    "fields": {
      "name": "Awesome Public API",
      "owner": { "id": "56caede9-...", "email": "john@doe.com" },
      "tags": [
        { "id": "95db5914-...", "name": "api" },
        { "id": "a1b2c3d4-...", "name": "enterprise" }
      ],
      "timeframe": { "startDate": "2023-10-01", "endDate": "2023-10-31" },
      "status": { "id": "uuid", "name": "In Progress" }
    },
    "metadata": {
      "source": { "system": "Jira", "recordId": "API-100" }
    },
    "relationships": {
      "data": [
        {
          "type": "parent",
          "target": {
            "id": "318de52f-...",
            "type": "component",
            "links": { "self": "https://api.productboard.com/v2/entities/...", "html": "..." }
          }
        }
      ],
      "links": { "next": null }
    },
    "links": {
      "self": "https://api.productboard.com/v2/entities/195a1cb2-...",
      "html": "https://example.productboard.com/detail/..."
    },
    "createdAt": "2023-10-01T00:00:00Z",
    "updatedAt": "2023-10-01T00:00:00Z"
  }
}
```

> The `fields` object is **dynamic and workspace-specific**. Use `GET /v2/entities/configurations/feature` to discover all fields available in a given workspace. Standard fields: `name`, `owner`, `tags`, `status`, `timeframe`, `archived`. Custom fields appear as UUID-keyed entries.

**Available field value types:** `boolean`, `date`, `datetime`, `health`, `member`, `multi_select`, `name (string)`, `number`, `number_with_mode`, `progress`, `rich_text`, `single_select`, `status`, `teams`, `text`, `timeframe`, `url`, `uuid`, `work_progress`

**Relationship types:** `parent`, `child`, `link`, `isBlockedBy`, `isBlocking`

**Valid entity hierarchy:** `product → component → feature → subfeature`

### Note Response (textNote)
```json
{
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "type": "textNote",
    "createdAt": "2023-10-01T10:00:00Z",
    "updatedAt": "2023-10-15T14:30:00Z",
    "fields": {
      "name": "Customer feedback",
      "content": "Customer reported slow loading times on mobile app",
      "tags": [{ "name": "feedback" }, { "name": "q1" }],
      "owner": { "id": "923e4567-...", "email": "john.doe@example.com" },
      "creator": { "id": "e23e4567-...", "email": "creator@example.com" },
      "processed": true,
      "archived": false
    },
    "relationships": [
      {
        "type": "customer",
        "target": { "id": "f23e4567-...", "type": "user", "links": { "self": "..." } }
      },
      {
        "type": "link",
        "target": { "id": "g23e4567-...", "type": "feature", "links": { "self": "..." } }
      }
    ]
  }
}
```

### conversationNote
The `fields.content` is an **array of message objects** instead of a string:
```json
"content": [
  {
    "externalId": "b23e4567-...",
    "content": "Hello, I need help with the app",
    "authorName": "John Customer",
    "authorType": "customer",
    "timestamp": "2023-10-01T10:00:00Z"
  },
  {
    "externalId": "c23e4567-...",
    "content": "Hi John, how can I help?",
    "authorName": "Support Agent",
    "authorType": "agent",
    "timestamp": "2023-10-01T10:05:00Z"
  }
]
```

### Note relationships
A note's `relationships` array contains:
- `"type": "customer"` → `target.type` is `"user"` or `"company"`
- `"type": "link"` → `target.type` is `"feature"`, `"subfeature"`, `"product"`, or `"component"`

Use `GET /v2/notes/{id}/relationships?type=customer` or `?type=link&target[type]=feature` to filter.

---

## 5. Pagination

All list endpoints use **cursor-based pagination** — no page numbers or offsets.

- **Request:** pass `?pageCursor=<opaque_string>` (value from the previous response's `links.next`)
- **End of results:** `links.next` is `null`
- **Page size:** not user-configurable; assume ~100 items/page

```json
{
  "data": [...],
  "links": {
    "next": "https://api.productboard.com/v2/notes?pageCursor=next_cursor_value"
  }
}
```

```python
from urllib.parse import urlparse, parse_qs

cursor = None
while True:
    params = {"pageCursor": cursor} if cursor else {}
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    process(data["data"])
    next_url = data["links"]["next"]
    if next_url is None:
        break
    cursor = parse_qs(urlparse(next_url).query).get("pageCursor", [None])[0]
```

> For `POST /entities/search` (and other POST search endpoints), pass `?pageCursor=` as a **query parameter** on subsequent pages while repeating the full request body.

---

## 6. Rate Limits

- HTTP `429 Too Many Requests` is returned when the limit is exceeded
- **No `Retry-After` header** — only a description in the response body
- Specific numeric limits are not published; implement conservative exponential backoff

```json
{
  "errors": [{
    "code": "rate.limitExceeded",
    "title": "Rate limit exceeded",
    "detail": "You have exceeded the allowed number of API requests. Please wait before making additional requests."
  }]
}
```

```python
def api_call_with_retry(fn, max_retries=5):
    for attempt in range(max_retries):
        resp = fn()
        if resp.status_code == 429:
            time.sleep(2 ** attempt)  # 1s, 2s, 4s, 8s, 16s
            continue
        resp.raise_for_status()
        return resp
    raise Exception("Rate limit retries exhausted")
```

---

## 7. Incremental Sync

### Notes — use `updatedFrom` on the GET list endpoint
```
GET /v2/notes?updatedFrom=2024-06-01T00:00:00Z
```
`updatedFrom` / `updatedTo` / `createdFrom` / `createdTo` — all ISO-8601, inclusive bounds. Returns HTTP 400 if `from > to`.

### Features/Entities — must use POST search
`GET /v2/entities` does **not** support date filtering. Use:
```json
POST /v2/entities/search
{
  "data": {
    "filter": {
      "type": ["feature"],
      "updatedAt": { "from": "2024-06-01T00:00:00Z" }
    }
  }
}
```
Then paginate with `?pageCursor=` as a query param on subsequent POST requests.

### State tracking
Store `last_synced_at` per entity type in `sync_state.json`. Update it to `datetime.utcnow()` **after** a successful full sync pass.

---

## 8. Webhooks

Webhooks allow push-based sync (vs. polling). Create a subscription once and receive events at your HTTPS endpoint.

### Supported event types (23 total)

| Category | Events |
|---|---|
| Feature | `feature.created`, `feature.updated`, `feature.deleted` |
| Component | `component.created`, `component.updated` |
| Product | `product.created`, `product.updated` |
| Release | `release.created`, `release.updated`, `release.deleted` |
| Feature-Release | `feature-release-assignment.updated` |
| Custom Fields | `hierarchy-entity.custom-field-value.updated` |
| Notes | `note.created`, `note.updated`, `note.deleted` |
| Insights | `insight.created`, `insight.deleted` |
| Key Results | `key-result.created`, `key-result.updated`, `key-result.deleted` |
| Objectives | `objective.created`, `objective.updated`, `objective.deleted` |
| Initiatives | `initiative.created`, `initiative.updated`, `initiative.deleted` |

### Create subscription
```
POST https://api.productboard.com/v2/webhooks
```
```json
{
  "data": {
    "fields": {
      "name": "Feature changes",
      "events": [
        { "eventType": "feature.updated" },
        { "eventType": "note.created" }
      ],
      "notification": {
        "url": "https://your-server.com/webhooks-handler",
        "version": 1,
        "headers": { "authorization": "Bearer myWebhookSecret" }
      }
    }
  }
}
```

### Webhook payload delivered to your endpoint
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "eventType": "feature.updated",
    "updatedAttributes": ["status", "name"],
    "links": {
      "target": "https://api.productboard.com/features/550e8400-..."
    }
  }
}
```

### Delivery rules
- Your endpoint must return a `2XX` within **5 seconds** (prefer `204 No Content`)
- Retried with exponential backoff: up to **8 attempts** (~1m, 3m, 9m, 27m, 81m, …)
- Too many failures → Productboard **disables** the subscription automatically
- URL must be publicly-accessible HTTPS (no localhost, no private IPs)

---

## Known Gotchas

| # | Issue |
|---|---|
| 1 | Rate limit numbers are not published. Empirically, v1 allowed ~200 req/min — assume similar for v2. |
| 2 | `X-Version` header is a v1 concept only. v2 uses URL versioning (`/v2/`). |
| 3 | Entity `fields` are workspace-specific. Always call `GET /v2/entities/configurations/{type}` to discover them before assuming field names. |
| 4 | `GET /v2/entities` has no date filter. Use `POST /v2/entities/search` for incremental sync. |
| 5 | `opportunityNote` cannot be created via API — read-only. |
| 6 | Without `members:pii:read` scope, all `email`/`name`/`username` fields return `"[redacted]"`. |
| 7 | `entity.user` and `entity.company` are CRM-style customers in the data model, **not** workspace members. |
| 8 | POST search pagination: `pageCursor` is a **query param**, not a body field. |
