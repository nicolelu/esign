# Architecture Decisions Log

This document records key architectural decisions made during the development of AI E-Sign.

## ADR-001: Hybrid Field Detection Approach

**Status:** Accepted

**Context:**
We need to automatically detect form fields (blanks, signatures, checkboxes, dates) in PDF documents. Options include:
1. Pure OCR/ML approach
2. Pure PDF structure analysis
3. Hybrid approach combining both

**Decision:**
Use a hybrid approach combining:
- PDF text extraction and layout analysis
- Vector graphics detection (underlines, rectangles)
- Keyword-based heuristics
- Anchor tag support ([type|role] format)

**Consequences:**
- More robust detection across different PDF generation methods
- Lower latency than pure ML approaches
- May miss some edge cases that ML would catch
- Requires maintaining heuristic rules

---

## ADR-002: SQLite for MVP, Postgres for Production

**Status:** Accepted

**Context:**
Need a database that works for local development and can scale to production.

**Decision:**
- Use SQLite with aiosqlite for local development (zero configuration)
- Use PostgreSQL for production deployments
- Use SQLAlchemy 2.0 async API for database abstraction

**Consequences:**
- Easy local setup without external dependencies
- Same codebase works with both databases
- Some SQLite-specific limitations (no concurrent writes in heavy load)

---

## ADR-003: Token-based Authentication for MVP

**Status:** Accepted

**Context:**
Need authentication for senders. Options:
1. Full OAuth2/OIDC
2. Magic link emails
3. Password-based

**Decision:**
Implement magic link authentication:
- Sender requests magic link with email
- Token generated and (in production) sent via email
- Token exchanged for JWT session token

**Consequences:**
- No password storage complexity
- Simple user experience
- Requires reliable email delivery in production
- For MVP, token returned directly (skip email)

---

## ADR-004: Signing Token Security

**Status:** Accepted

**Context:**
Signing links must be secure, unguessable, and scoped to specific recipients.

**Decision:**
- Use JWT tokens containing recipient ID, envelope ID, and email
- Set expiration (default 72 hours)
- Invalidate token after signing completion
- Store hashed token in database for verification

**Consequences:**
- Tokens are self-contained (include necessary claims)
- Expiration enforced cryptographically
- Can revoke by removing from database
- Token in URL (can be logged) - acceptable for MVP

---

## ADR-005: PDF Rendering with PyMuPDF

**Status:** Accepted

**Context:**
Need to render PDF pages as images for the web viewer and extract text/layout.

**Decision:**
Use PyMuPDF (fitz) for:
- Page rendering to PNG at configurable DPI
- Text and layout extraction
- Vector graphics (drawings) extraction
- Final PDF generation with filled fields

**Consequences:**
- Fast, native PDF processing
- Rich API for both reading and writing
- Single library for all PDF operations
- AGPL license (acceptable for our use)

---

## ADR-006: Append-Only Audit Log with Hash Chain

**Status:** Accepted

**Context:**
Need tamper-evident audit trail for legal compliance.

**Decision:**
Implement blockchain-like hash chain:
- Each audit event includes hash of previous event
- Event hash computed from event data + previous hash
- Verification function can detect tampering

**Consequences:**
- Any modification to historical events detectable
- Provides strong evidence of integrity
- Slightly more complex event insertion
- Cannot delete or modify historical events

---

## ADR-007: Field Owner Model (Sender + 2 Signers) - SUPERSEDED

**Status:** Superseded by ADR-011

**Context:**
Need to assign fields to different parties. Many real contracts have multiple signers.

**Decision:**
MVP supports three owner types:
- SENDER: Values set at send-time, visible but not editable by signers
- SIGNER_1: First signing party
- SIGNER_2: Second signing party

Design allows extension to N signers in future.

**Consequences:**
- Covers most common contract scenarios
- Sender variables enable dynamic content without templates
- Owner inference more challenging with multiple parties

**Note:** This ADR has been superseded by ADR-011 which introduces N-signer support.

---

## ADR-008: Frontend State Management with Zustand

**Status:** Accepted

**Context:**
Need state management for document editor (fields, selection, zoom, etc.).

**Decision:**
Use Zustand for:
- Auth state (persisted)
- Editor state (document, fields, selection)
- Light-weight, TypeScript-friendly

**Consequences:**
- Simpler than Redux
- Built-in persistence support
- Minimal boilerplate
- Good React 18 compatibility

---

## ADR-009: Confidence Scores for Detection

**Status:** Accepted

**Context:**
Auto-detection isn't perfect. Users need to understand reliability.

**Decision:**
Include three confidence scores per field:
- `detection_confidence`: How sure we found something
- `classification_confidence`: How sure about the type
- `owner_confidence`: How sure about who fills it

Plus `evidence` string explaining the reasoning.

**Consequences:**
- Users can prioritize reviewing low-confidence fields
- Enables filtering by confidence threshold
- Provides transparency ("why did it choose this?")
- Slightly more complex UI to display

---

## ADR-010: Sender Variables for Dynamic Content

**Status:** Accepted

**Context:**
Need to include dynamic values (effective date, amounts) set at send-time without creating new document versions.

**Decision:**
- Any field with `owner=SENDER` can have a `sender_variable_key`
- At send-time, sender provides values for all keys
- Values rendered into final PDF
- Signers see values but cannot edit

**Consequences:**
- Single template can be reused with different values
- No document cloning needed
- Clear separation of sender-provided vs signer-provided data
- Requires validation that all keys are provided

---

## ADR-011: N-Signer Support with Role-Based Field Assignment

**Status:** Accepted

**Context:**
The original MVP was limited to 2 signers (SIGNER_1, SIGNER_2). Real-world contracts often require more signers (e.g., buyer, seller, agent, witness, guarantor). The hardcoded enum was a limitation.

**Decision:**
Implement a generalized role-based system:

1. **New Data Model:**
   - `AssigneeType` enum: SENDER or ROLE
   - `Role` table: (id, envelope_id, key, display_name, color, signing_order)
   - Fields reference roles via `role_id` instead of hardcoded owner enum
   - Recipients link to roles via `role_id`

2. **Detection Pipeline Changes:**
   - Replace SIGNER_1_KEYWORDS/SIGNER_2_KEYWORDS with ROLE_KEYWORDS dict
   - Output `detected_role_key` (e.g., "client", "landlord", "guarantor")
   - New anchor tag format: `[sig|role:client]`
   - Maintain backward compatibility for `[sig|signer1]` format

3. **Signing Order Enforcement:**
   - `signing_order` on roles (nullable, 1-indexed)
   - Earlier signers must complete before later signers can sign
   - No enforcement when signing_order is null

4. **API Changes:**
   - Envelopes accept `roles[]` array at creation
   - Recipients reference roles via `role_key`
   - Signing session includes role info

**Consequences:**
- Supports arbitrary number of signers (tested with 1, 2, 5)
- Semantic role keys improve document understanding
- Signing order enables sequential workflows
- Backward compatible with existing documents
- Role mapping UI needed at send time
- More flexible field-recipient matching

**Migration:**
- Old `owner` field kept for backward compatibility
- SIGNER_1 → signer_1 role, SIGNER_2 → signer_2 role
- New documents use role_id exclusively

---

## Future Considerations

### Potential ADRs for Next Phase:
- ADR-012: LLM Integration for Classification
- ADR-013: Queue/Worker Architecture for Heavy Processing
- ADR-014: S3/Cloud Storage Backend
- ADR-015: Webhook Notifications
- ADR-016: Multi-tenancy and Organizations
