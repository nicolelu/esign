# Data Model and Audit Trail

This document describes the data model and audit trail implementation in AI E-Sign.

## Core Data Model

### Entity Relationship Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    User     │────<│  Document   │────<│    Field    │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │                   │                   │
       ▼                   ▼                   │
┌─────────────┐     ┌─────────────┐           │
│  Envelope   │────<│  Recipient  │           │
└─────────────┘     └─────────────┘           │
       │                                       │
       │                                       │
       ├──────────────────────────────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│ FieldValue  │     │ AuditEvent  │
└─────────────┘     └─────────────┘
```

### User

Represents a sender who can upload documents and create envelopes.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| email | String | Unique email address |
| name | String? | Display name |
| is_active | Boolean | Account status |
| created_at | DateTime | Account creation time |

### Document

Represents an uploaded PDF document.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| owner_id | UUID | Foreign key to User |
| name | String | Document name |
| original_filename | String | Original upload filename |
| file_path | String | Storage path |
| file_hash | String? | SHA-256 of original file |
| file_size | Integer | File size in bytes |
| mime_type | String | MIME type (application/pdf) |
| page_count | Integer | Number of pages |
| status | Enum | DRAFT, TEMPLATE, SENT, COMPLETED, VOIDED |
| page_images | JSON? | Array of page image URLs |
| extracted_text | Text? | Full text content |
| text_layout | JSON? | Text positions and layout |

### Field

Represents a form field on a document.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| document_id | UUID | Foreign key to Document |
| page_number | Integer | Page (1-indexed) |
| bbox_x, bbox_y | Float | Position in PDF coordinates |
| bbox_width, bbox_height | Float | Size in PDF coordinates |
| field_type | Enum | TEXT, NAME, EMAIL, DATE_SIGNED, CHECKBOX, SIGNATURE, INITIALS |
| owner | Enum | SENDER, SIGNER_1, SIGNER_2 |
| required | Boolean | Must be filled |
| label | String? | Internal label |
| placeholder | String? | Placeholder text |
| default_value | String? | Default value |
| sender_variable_key | String? | Variable key for sender fields |
| detection_confidence | Float? | 0.0-1.0 detection confidence |
| classification_confidence | Float? | 0.0-1.0 type confidence |
| owner_confidence | Float? | 0.0-1.0 owner confidence |
| evidence | String? | Explanation of classification |
| anchor_text | String? | Anchor tag if used |

### Envelope

Represents a document package sent for signing.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| sender_id | UUID | Foreign key to User |
| document_id | UUID | Foreign key to Document |
| name | String | Envelope name |
| message | String? | Message to recipients |
| status | Enum | DRAFT, SENT, IN_PROGRESS, COMPLETED, VOIDED, EXPIRED |
| sender_variables | JSON? | Key-value pairs for sender fields |
| sent_at | DateTime? | When sent |
| completed_at | DateTime? | When all signed |
| expires_at | DateTime? | Link expiration |
| final_document_path | String? | Path to signed PDF |
| final_document_hash | String? | SHA-256 of final PDF |
| completion_certificate_path | String? | Path to certificate |

### Recipient

Represents a signing party.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| envelope_id | UUID | Foreign key to Envelope |
| email | String | Recipient email |
| name | String | Recipient name |
| role | Enum | SIGNER_1, SIGNER_2 |
| order | Integer | Signing order |
| status | Enum | PENDING, SENT, VIEWED, SIGNING, COMPLETED, DECLINED |
| signing_token | String? | Unique signing link token |
| sent_at | DateTime? | When email sent |
| viewed_at | DateTime? | First view time |
| completed_at | DateTime? | Signing completion time |

### FieldValue

Stores filled field values for an envelope.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| envelope_id | UUID | Foreign key to Envelope |
| field_id | UUID | Foreign key to Field |
| value | String? | Text value |
| signature_data | String? | Base64 signature image |
| filled_by_role | Enum? | Who filled it |
| filled_at | DateTime? | When filled |

## Audit Trail

### Purpose

The audit trail provides:
1. **Compliance:** Legal record of all signing activities
2. **Non-repudiation:** Evidence of who did what and when
3. **Tamper detection:** Hash chain reveals any modifications

### AuditEvent Model

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| envelope_id | UUID | Foreign key to Envelope |
| event_type | Enum | Event category |
| timestamp | DateTime | When event occurred |
| actor_id | UUID? | User ID if sender |
| actor_email | String? | Actor's email |
| actor_role | String? | Role (sender, signer1, signer2) |
| ip_address | String? | Client IP |
| user_agent | String? | Browser/client info |
| data | JSON? | Event-specific data |
| previous_event_hash | String? | Hash of previous event |
| event_hash | String? | SHA-256 of this event |

### Event Types

| Event Type | Description | Logged Data |
|------------|-------------|-------------|
| DOCUMENT_CREATED | Document uploaded | document_id, filename |
| DOCUMENT_UPLOADED | File stored | file_hash, file_size |
| FIELDS_DETECTED | Auto-detection run | field_count, detection_time |
| FIELDS_MODIFIED | Fields added/edited | field_ids, changes |
| ENVELOPE_CREATED | Envelope created | recipients, document_id |
| ENVELOPE_SENT | Envelope sent | recipient_emails |
| RECIPIENT_VIEWED | Signer opened link | recipient_id |
| FIELD_COMPLETED | Field filled | field_id, field_type |
| SIGNATURE_APPLIED | Signature drawn | recipient_id |
| RECIPIENT_COMPLETED | Signer finished | recipient_id |
| ENVELOPE_COMPLETED | All signed | document_hash |
| DOCUMENT_DOWNLOADED | Final PDF downloaded | user_id |
| ENVELOPE_VOIDED | Envelope cancelled | reason |

### Hash Chain

Each event includes:
- `previous_event_hash`: SHA-256 of the previous event
- `event_hash`: SHA-256 of current event data + previous hash

This creates a blockchain-like chain where modifying any event would break the chain.

**Hash calculation:**
```python
hash_data = {
    "envelope_id": event.envelope_id,
    "event_type": event.event_type.value,
    "timestamp": event.timestamp.isoformat(),
    "actor_id": event.actor_id,
    "actor_email": event.actor_email,
    "actor_role": event.actor_role,
    "ip_address": event.ip_address,
    "data": event.data,
    "previous_event_hash": event.previous_event_hash,
}
hash_string = json.dumps(hash_data, sort_keys=True, default=str)
event_hash = hashlib.sha256(hash_string.encode()).hexdigest()
```

### Verification

The audit trail can be verified:

```python
async def verify_audit_trail(db, envelope_id):
    events = await get_audit_trail(db, envelope_id)
    errors = []

    for i, event in enumerate(events):
        # Check chain continuity
        if i > 0:
            expected = events[i-1].event_hash
            if event.previous_event_hash != expected:
                errors.append(f"Event {event.id}: chain broken")

        # Verify event hash
        computed = compute_event_hash(event)
        if event.event_hash != computed:
            errors.append(f"Event {event.id}: hash mismatch")

    return len(errors) == 0, errors
```

## Completion Certificate

When an envelope is completed, a PDF certificate is generated containing:

1. **Document Information**
   - Document name
   - Envelope ID
   - Completion timestamp
   - Final document SHA-256 hash

2. **Signer Information**
   - Name and email of each signer
   - Role assignment
   - Signing timestamp

3. **Audit Trail**
   - Chronological list of all events
   - Timestamps and actors
   - IP addresses (when available)

4. **Verification Statement**
   - Hash verification result
   - Legal compliance notice

## Security Considerations

### Data Protection

- Passwords are not stored (magic link auth)
- Signing tokens expire after 72 hours (configurable)
- Tokens invalidated after use
- Minimal PII stored

### Access Control

- Documents accessible only by owner
- Signing sessions scoped to specific recipient
- API uses token authentication

### Secrets

- Secret key must be changed in production
- Use environment variables for sensitive config
- Never log document contents

## Storage

### File Storage Structure

```
storage/
├── documents/
│   └── {document_id}/
│       └── {original_filename}
├── page_images/
│   └── {document_id}/
│       ├── page_1.png
│       ├── page_2.png
│       └── ...
├── signatures/
│   └── {envelope_id}/
│       └── sig_{field_id}.png
├── final_documents/
│   └── {envelope_id}_final.pdf
└── certificates/
    └── {envelope_id}_certificate.pdf
```

### Database Schema

The complete schema is defined in SQLAlchemy models:
- `apps/backend/app/models/models.py`

Migrations are managed with Alembic (when using PostgreSQL).

## API Reference

See the auto-generated OpenAPI documentation at `/docs` when running the backend.

Key endpoints:
- `POST /api/v1/documents` - Upload document
- `POST /api/v1/documents/{id}/detect` - Run field detection
- `POST /api/v1/envelopes` - Create envelope
- `POST /api/v1/envelopes/{id}/send` - Send for signing
- `GET /api/v1/signing/session/{token}` - Get signing session
- `POST /api/v1/signing/session/{token}/complete` - Complete signing
