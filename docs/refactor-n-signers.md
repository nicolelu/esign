# N-Signer Refactor Plan

## Overview

This document outlines the refactor from hardcoded SIGNER_1/SIGNER_2 to support an arbitrary number of signers (N recipients).

## Current State Analysis

### Files Containing SIGNER_1/SIGNER_2/FieldOwner

| File | Usage |
|------|-------|
| `apps/backend/app/models/models.py` | FieldOwner enum (SENDER, SIGNER_1, SIGNER_2) |
| `apps/backend/app/schemas/schemas.py` | FieldOwner in Pydantic schemas |
| `apps/backend/app/api/envelopes.py` | Validation: `signer_roles = {FieldOwner.SIGNER_1, FieldOwner.SIGNER_2}` |
| `apps/backend/app/api/signing.py` | Filters by `FieldOwner.SENDER` |
| `apps/backend/app/services/detection/detector.py` | SIGNER_1_KEYWORDS, SIGNER_2_KEYWORDS lists |
| `apps/web/src/types/index.ts` | FieldOwner enum |
| `apps/web/src/lib/utils.ts` | `getOwnerLabel`, `getOwnerColor` hardcoded maps |
| `apps/web/src/components/SendModal.tsx` | Hardcoded SIGNER_1/SIGNER_2 options |
| `apps/web/src/components/FieldPropertiesPanel.tsx` | FieldOwner dropdown |
| `apps/backend/tests/test_detection.py` | Tests use FieldOwner.SIGNER_1/SIGNER_2 |
| `scripts/evaluate_field_detection.py` | Ground truth uses SIGNER_1/SIGNER_2 |

---

## Target Data Model

### New Enums

```python
class AssigneeType(str, enum.Enum):
    """Field assignee type."""
    SENDER = "SENDER"  # Filled by sender at send time
    ROLE = "ROLE"       # Filled by a signer role
```

### New Table: Role

```python
class Role(Base, TimestampMixin):
    """Role model for envelope signer roles."""
    __tablename__ = "roles"

    id: Mapped[uuid_pk]
    envelope_id: Mapped[str]  # FK to envelopes.id

    # Role identification
    key: Mapped[str]           # e.g., "client", "contractor", "witness_1"
    display_name: Mapped[str]  # e.g., "Client", "Contractor", "Witness 1"
    color: Mapped[str]         # Hex color for UI

    # Signing order (1-indexed, null = no order enforcement)
    signing_order: Mapped[int | None]

    # Relationships
    envelope: Mapped["Envelope"]
    recipient: Mapped["Recipient | None"]  # One-to-one with Recipient
    fields: Mapped[list["Field"]]          # Fields assigned to this role
```

### Updated Field Model

```python
class Field(Base, TimestampMixin):
    # ... existing fields ...

    # REMOVE: owner: Mapped[FieldOwner]

    # NEW: Assignee model
    assignee_type: Mapped[AssigneeType]  # SENDER or ROLE
    role_id: Mapped[str | None]          # FK to roles.id (null if SENDER)

    # NEW: Detection outputs
    detected_role_key: Mapped[str | None]  # e.g., "client", "landlord"

    # Relationships
    role: Mapped["Role | None"]  # Only set if assignee_type == ROLE
```

### Updated Recipient Model

```python
class Recipient(Base, TimestampMixin):
    # ... existing fields ...

    # REMOVE: role: Mapped[FieldOwner]

    # NEW: Link to role
    role_id: Mapped[str]  # FK to roles.id (required)

    # Relationships
    role: Mapped["Role"]
```

### Updated FieldValue Model

```python
class FieldValue(Base, TimestampMixin):
    # ... existing fields ...

    # REMOVE: filled_by_role: Mapped[FieldOwner | None]

    # NEW: Reference role
    filled_by_role_id: Mapped[str | None]  # FK to roles.id

    # Relationships
    filled_by_role: Mapped["Role | None"]
```

---

## Detection Pipeline Changes

### Current Keywords (to be replaced)

```python
SIGNER_1_KEYWORDS = ["client", "employee", "contractor", "tenant", "buyer", ...]
SIGNER_2_KEYWORDS = ["company", "employer", "landlord", "seller", ...]
```

### New Role Keywords

```python
ROLE_KEYWORDS = {
    "client": ["client", "customer", "buyer", "purchaser", "party a"],
    "contractor": ["contractor", "employee", "worker", "consultant"],
    "company": ["company", "employer", "seller", "vendor", "party b"],
    "landlord": ["landlord", "owner", "lessor"],
    "tenant": ["tenant", "renter", "lessee"],
    "witness": ["witness"],
    "guarantor": ["guarantor", "co-signer", "cosigner"],
}
```

### Updated Detection Output

```python
@dataclass
class DetectedField:
    # ... existing fields ...

    # REMOVE: owner: FieldOwner

    # NEW: Role-based assignment
    assignee_type: AssigneeType  # SENDER or ROLE
    detected_role_key: str | None  # e.g., "client", "landlord"
    role_confidence: float
```

### Anchor Tag Syntax

**New Format:** `[type|role:key]`
- `[sig|role:client]` - Signature for client role
- `[date|role:contractor]` - Date for contractor role
- `[text|sender]` - Text for sender (unchanged)

**Backward Compatibility:**
- `[sig|signer1]` → interpreted as `[sig|role:signer_1]`
- `[date|signer2]` → interpreted as `[date|role:signer_2]`

---

## API Changes

### Envelope Creation

```python
class RoleCreate(BaseModel):
    key: str           # Unique within envelope
    display_name: str
    color: str | None = None
    signing_order: int | None = None

class RecipientCreate(BaseModel):
    email: EmailStr
    name: str
    role_key: str  # References RoleCreate.key

class EnvelopeCreate(BaseModel):
    document_id: str
    name: str
    message: str | None = None
    roles: list[RoleCreate]        # NEW: Define roles first
    recipients: list[RecipientCreate]
    sender_variables: dict[str, str] | None = None
```

### Signing Session

```python
class SigningSessionResponse(BaseModel):
    envelope_id: str
    document_name: str
    recipient_name: str
    recipient_role: RoleResponse  # Full role info
    fields: list[FieldResponse]
    # ... etc
```

---

## Frontend Changes

### Types (types/index.ts)

```typescript
// REMOVE: FieldOwner enum

// NEW:
export enum AssigneeType {
    SENDER = 'SENDER',
    ROLE = 'ROLE',
}

export interface Role {
    id: string;
    envelope_id: string;
    key: string;
    display_name: string;
    color: string;
    signing_order: number | null;
}

export interface Field {
    // ... existing ...
    // REMOVE: owner: FieldOwner
    assignee_type: AssigneeType;
    role_id: string | null;
    detected_role_key: string | null;
}
```

### SendModal.tsx

- Replace hardcoded SIGNER_1/SIGNER_2 dropdown with dynamic role management
- Allow adding/removing roles with custom keys
- Color picker for role visualization
- Optional signing order

### Utils (utils.ts)

```typescript
// REMOVE: getOwnerLabel, getOwnerColor with hardcoded maps

// NEW: Dynamic functions
export function getRoleColor(role: Role): string {
    return role.color || getDefaultRoleColor(role.key);
}

export function getDefaultRoleColor(roleKey: string): string {
    const defaults: Record<string, string> = {
        'sender': 'purple',
        'client': 'blue',
        'company': 'green',
        // ... etc
    };
    return defaults[roleKey] || 'gray';
}
```

---

## Migration Strategy

### Database Migration

1. Add new `roles` table
2. Add new columns to `fields`: `assignee_type`, `role_id`, `detected_role_key`
3. Add new column to `recipients`: `role_id`
4. Add new column to `field_values`: `filled_by_role_id`
5. Migrate existing data:
   - For each envelope with SIGNER_1/SIGNER_2 recipients, create Role records
   - Update fields.role_id based on old owner value
   - Update recipients.role_id based on old role value
6. Drop old columns after migration verified

### Backward Compatibility

- API should accept both old format (with `owner`/`role`) and new format (with `role_id`)
- Detection should recognize both old anchor tags `[type|signer1]` and new `[type|role:key]`

---

## Implementation Order

### Phase 1: Database Models (models.py)
1. Add `AssigneeType` enum
2. Add `Role` model
3. Update `Field` model with new columns
4. Update `Recipient` model with role_id
5. Update `FieldValue` model with filled_by_role_id
6. Keep old columns temporarily for migration

### Phase 2: Schemas (schemas.py)
1. Add `AssigneeType` to schemas
2. Add `RoleCreate`, `RoleResponse` schemas
3. Update `FieldCreate`, `FieldResponse`
4. Update `RecipientCreate`, `RecipientResponse`
5. Update `EnvelopeCreate` with roles list

### Phase 3: API Endpoints
1. Update `envelopes.py` to create roles
2. Update `signing.py` for role-based field matching
3. Update validation logic

### Phase 4: Detection Pipeline (detector.py)
1. Replace SIGNER_1_KEYWORDS/SIGNER_2_KEYWORDS with ROLE_KEYWORDS
2. Update `_infer_owner_from_text` to `_infer_role_from_text`
3. Update anchor tag parsing
4. Update `DetectedField` dataclass

### Phase 5: Frontend
1. Update types/index.ts
2. Update utils.ts
3. Update SendModal.tsx with dynamic roles
4. Update FieldPropertiesPanel.tsx
5. Update signing page

### Phase 6: Tests
1. Update existing tests
2. Add N-signer scenario tests (1, 2, 5 signers)
3. Add signing order tests

### Phase 7: Evaluation & Docs
1. Update sample documents
2. Update ground truth format
3. Update evaluation script
4. Update documentation

---

## Acceptance Criteria

1. N-recipient signing works end-to-end (tested with 1, 2, 5 signers)
2. No code path hardcodes SIGNER_1 or SIGNER_2
3. All existing tests pass
4. New tests cover N-signer scenarios
5. Evaluation script runs and produces report
6. Signing order enforcement works when configured
7. UI supports dynamic role creation and assignment
8. Detection infers role keys from document context

---

## Implementation Status: COMPLETED

### Changes Made

#### Backend Models (`apps/backend/app/models/models.py`)
- Added `AssigneeType` enum (SENDER, ROLE)
- Added `Role` model with (id, envelope_id, key, display_name, color, signing_order)
- Updated `Field` model with `assignee_type`, `role_id`, `detected_role_key`, `role_confidence`
- Updated `Recipient` model with `role_id` FK to Role
- Updated `FieldValue` model with `filled_by_role_id` FK to Role
- Kept old `owner` column for backward compatibility

#### Backend Schemas (`apps/backend/app/schemas/schemas.py`)
- Added `RoleCreate`, `RoleResponse` schemas
- Updated all field/recipient/envelope schemas with role support
- Added `assignee_type`, `role_id`, `detected_role_key` to field schemas
- Updated `SigningSessionResponse` with `recipient_role_id`, `recipient_role_info`

#### API Endpoints (`apps/backend/app/api/`)
- `envelopes.py`: Creates roles for envelope, links recipients to roles
- `signing.py`: Field matching uses `_field_belongs_to_recipient()` helper for role-based matching

#### Detection Pipeline (`apps/backend/app/services/detection/detector.py`)
- Replaced `SIGNER_1_KEYWORDS`/`SIGNER_2_KEYWORDS` with `ROLE_KEYWORDS` dict
- Added `_infer_role_from_text()` returning (role_key, confidence)
- Updated anchor tag detection for `[type|role:key]` syntax
- Maintained backward compatibility for `[type|signer1]` syntax
- All detected fields populate `assignee_type` and `detected_role_key`

#### Frontend Types (`apps/web/src/types/index.ts`)
- Added `AssigneeType` enum
- Added `Role`, `RoleCreate` interfaces
- Updated `Field`, `Recipient`, `Envelope`, `FieldValue`, `SigningSession`

#### Frontend UI
- `SendModal.tsx`: Dynamic role creation from detected fields
- `utils.ts`: Added `getRoleLabel()`, `getRoleColor()`, `getRoleColorStyle()`

#### Tests
- Added `TestNSignerDetection` class with 5 new test cases
- Updated utility tests for new role functions

### Backward Compatibility

The refactor maintains full backward compatibility:
- Old `owner` field still works alongside new `role_id`
- Legacy anchor tags `[sig|signer1]` still work
- API accepts both `role` and `role_key` in recipients
- Frontend gracefully handles missing role info
