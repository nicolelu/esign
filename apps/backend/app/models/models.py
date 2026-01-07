"""Core database models for the AI E-Sign application."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk


class FieldType(str, enum.Enum):
    """Field type enumeration."""

    TEXT = "TEXT"
    NAME = "NAME"
    EMAIL = "EMAIL"
    DATE_SIGNED = "DATE_SIGNED"
    CHECKBOX = "CHECKBOX"
    SIGNATURE = "SIGNATURE"
    INITIALS = "INITIALS"


class FieldOwner(str, enum.Enum):
    """Field owner enumeration - DEPRECATED, use AssigneeType + Role instead."""

    SENDER = "SENDER"
    SIGNER_1 = "SIGNER_1"
    SIGNER_2 = "SIGNER_2"


class AssigneeType(str, enum.Enum):
    """Field assignee type enumeration."""

    SENDER = "SENDER"  # Filled by sender at send time
    ROLE = "ROLE"  # Filled by a signer role


class DocumentStatus(str, enum.Enum):
    """Document status enumeration."""

    DRAFT = "DRAFT"
    TEMPLATE = "TEMPLATE"
    SENT = "SENT"
    COMPLETED = "COMPLETED"
    VOIDED = "VOIDED"


class EnvelopeStatus(str, enum.Enum):
    """Envelope status enumeration."""

    DRAFT = "DRAFT"
    SENT = "SENT"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VOIDED = "VOIDED"
    EXPIRED = "EXPIRED"


class RecipientStatus(str, enum.Enum):
    """Recipient status enumeration."""

    PENDING = "PENDING"
    SENT = "SENT"
    VIEWED = "VIEWED"
    SIGNING = "SIGNING"
    COMPLETED = "COMPLETED"
    DECLINED = "DECLINED"


class AuditEventType(str, enum.Enum):
    """Audit event types."""

    DOCUMENT_CREATED = "DOCUMENT_CREATED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    FIELDS_DETECTED = "FIELDS_DETECTED"
    FIELDS_MODIFIED = "FIELDS_MODIFIED"
    ENVELOPE_CREATED = "ENVELOPE_CREATED"
    ENVELOPE_SENT = "ENVELOPE_SENT"
    RECIPIENT_VIEWED = "RECIPIENT_VIEWED"
    FIELD_COMPLETED = "FIELD_COMPLETED"
    SIGNATURE_APPLIED = "SIGNATURE_APPLIED"
    RECIPIENT_COMPLETED = "RECIPIENT_COMPLETED"
    ENVELOPE_COMPLETED = "ENVELOPE_COMPLETED"
    DOCUMENT_DOWNLOADED = "DOCUMENT_DOWNLOADED"
    ENVELOPE_VOIDED = "ENVELOPE_VOIDED"


class User(Base, TimestampMixin):
    """User model for senders."""

    __tablename__ = "users"

    id: Mapped[uuid_pk]
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    documents: Mapped[list["Document"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    envelopes: Mapped[list["Envelope"]] = relationship(
        back_populates="sender", cascade="all, delete-orphan"
    )


class Document(Base, TimestampMixin):
    """Document model for uploaded files."""

    __tablename__ = "documents"

    id: Mapped[uuid_pk]
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_hash: Mapped[str | None] = mapped_column(String(64))  # SHA-256
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.DRAFT
    )

    # Page images stored as JSON array of paths
    page_images: Mapped[dict | None] = mapped_column(JSON, default=None)

    # Extracted text and layout (for detection)
    extracted_text: Mapped[str | None] = mapped_column(Text, default=None)
    text_layout: Mapped[dict | None] = mapped_column(JSON, default=None)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="documents")
    fields: Mapped[list["Field"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    envelopes: Mapped[list["Envelope"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Field(Base, TimestampMixin):
    """Field model for document fields."""

    __tablename__ = "fields"

    id: Mapped[uuid_pk]
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), index=True
    )

    # Position
    page_number: Mapped[int] = mapped_column(Integer)
    bbox_x: Mapped[float] = mapped_column(Float)
    bbox_y: Mapped[float] = mapped_column(Float)
    bbox_width: Mapped[float] = mapped_column(Float)
    bbox_height: Mapped[float] = mapped_column(Float)

    # Field properties
    field_type: Mapped[FieldType] = mapped_column(Enum(FieldType))

    # DEPRECATED: Use assignee_type + role_id instead
    owner: Mapped[FieldOwner | None] = mapped_column(Enum(FieldOwner), nullable=True)

    # NEW: N-signer assignee model
    assignee_type: Mapped[AssigneeType] = mapped_column(
        Enum(AssigneeType), default=AssigneeType.ROLE
    )
    role_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("roles.id"), index=True, nullable=True
    )
    # Detected role key from detection pipeline (e.g., "client", "landlord")
    detected_role_key: Mapped[str | None] = mapped_column(String(100), default=None)

    required: Mapped[bool] = mapped_column(Boolean, default=True)
    label: Mapped[str | None] = mapped_column(String(255), default=None)
    placeholder: Mapped[str | None] = mapped_column(String(255), default=None)
    default_value: Mapped[str | None] = mapped_column(Text, default=None)

    # Sender variable support
    sender_variable_key: Mapped[str | None] = mapped_column(String(100), default=None)

    # Confidence scores (0.0 - 1.0)
    detection_confidence: Mapped[float | None] = mapped_column(Float, default=None)
    classification_confidence: Mapped[float | None] = mapped_column(Float, default=None)
    owner_confidence: Mapped[float | None] = mapped_column(Float, default=None)
    # NEW: Role inference confidence
    role_confidence: Mapped[float | None] = mapped_column(Float, default=None)

    # Evidence for why this classification/owner was chosen
    evidence: Mapped[str | None] = mapped_column(Text, default=None)

    # Anchor text support (for tag-based placement)
    anchor_text: Mapped[str | None] = mapped_column(String(255), default=None)
    anchor_offset_x: Mapped[float | None] = mapped_column(Float, default=None)
    anchor_offset_y: Mapped[float | None] = mapped_column(Float, default=None)

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="fields")
    role: Mapped["Role | None"] = relationship(back_populates="fields")
    values: Mapped[list["FieldValue"]] = relationship(
        back_populates="field", cascade="all, delete-orphan"
    )


class Envelope(Base, TimestampMixin):
    """Envelope model for sending documents."""

    __tablename__ = "envelopes"

    id: Mapped[uuid_pk]
    sender_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), index=True
    )

    name: Mapped[str] = mapped_column(String(255))
    message: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[EnvelopeStatus] = mapped_column(
        Enum(EnvelopeStatus), default=EnvelopeStatus.DRAFT
    )

    # Sender variables values (key -> value)
    sender_variables: Mapped[dict | None] = mapped_column(JSON, default=None)

    # Final document after completion
    final_document_path: Mapped[str | None] = mapped_column(String(500), default=None)
    final_document_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    completion_certificate_path: Mapped[str | None] = mapped_column(
        String(500), default=None
    )

    # Timestamps
    sent_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)

    # Relationships
    sender: Mapped["User"] = relationship(back_populates="envelopes")
    document: Mapped["Document"] = relationship(back_populates="envelopes")
    roles: Mapped[list["Role"]] = relationship(
        back_populates="envelope", cascade="all, delete-orphan"
    )
    recipients: Mapped[list["Recipient"]] = relationship(
        back_populates="envelope", cascade="all, delete-orphan"
    )
    field_values: Mapped[list["FieldValue"]] = relationship(
        back_populates="envelope", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="envelope", cascade="all, delete-orphan"
    )


class Role(Base, TimestampMixin):
    """Role model for envelope signer roles (N-signer support)."""

    __tablename__ = "roles"

    id: Mapped[uuid_pk]
    envelope_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("envelopes.id"), index=True
    )

    # Role identification
    key: Mapped[str] = mapped_column(String(100))  # e.g., "client", "contractor"
    display_name: Mapped[str] = mapped_column(String(255))  # e.g., "Client"
    color: Mapped[str] = mapped_column(String(20), default="#3B82F6")  # Hex color

    # Signing order (1-indexed, null = no order enforcement)
    signing_order: Mapped[int | None] = mapped_column(Integer, default=None)

    # Relationships
    envelope: Mapped["Envelope"] = relationship(back_populates="roles")
    recipient: Mapped["Recipient | None"] = relationship(
        back_populates="role_ref", uselist=False
    )
    fields: Mapped[list["Field"]] = relationship(back_populates="role")


class Recipient(Base, TimestampMixin):
    """Recipient model for envelope recipients."""

    __tablename__ = "recipients"

    id: Mapped[uuid_pk]
    envelope_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("envelopes.id"), index=True
    )

    email: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))

    # DEPRECATED: Use role_id instead
    role: Mapped[FieldOwner | None] = mapped_column(Enum(FieldOwner), nullable=True)

    # NEW: Reference to Role table
    role_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("roles.id"), index=True, nullable=True
    )

    order: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[RecipientStatus] = mapped_column(
        Enum(RecipientStatus), default=RecipientStatus.PENDING
    )

    # Signing token (unique, unguessable)
    signing_token: Mapped[str | None] = mapped_column(
        String(500), unique=True, index=True, default=None
    )

    # Timestamps
    sent_at: Mapped[datetime | None] = mapped_column(default=None)
    viewed_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    # Relationships
    envelope: Mapped["Envelope"] = relationship(back_populates="recipients")
    role_ref: Mapped["Role | None"] = relationship(back_populates="recipient")


class FieldValue(Base, TimestampMixin):
    """Field value model for filled field values in an envelope."""

    __tablename__ = "field_values"

    id: Mapped[uuid_pk]
    envelope_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("envelopes.id"), index=True
    )
    field_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fields.id"), index=True
    )

    # The actual value
    value: Mapped[str | None] = mapped_column(Text, default=None)

    # For signature/initials, store the image data
    signature_data: Mapped[str | None] = mapped_column(Text, default=None)

    # DEPRECATED: Who filled it (old enum)
    filled_by_role: Mapped[FieldOwner | None] = mapped_column(
        Enum(FieldOwner), default=None, nullable=True
    )

    # NEW: Reference to role that filled this
    filled_by_role_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("roles.id"), index=True, nullable=True
    )

    filled_at: Mapped[datetime | None] = mapped_column(default=None)

    # Relationships
    envelope: Mapped["Envelope"] = relationship(back_populates="field_values")
    field: Mapped["Field"] = relationship(back_populates="values")
    filled_by: Mapped["Role | None"] = relationship()


class AuditEvent(Base):
    """Audit event model for tamper-evident logging."""

    __tablename__ = "audit_events"

    id: Mapped[uuid_pk]
    envelope_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("envelopes.id"), index=True
    )

    event_type: Mapped[AuditEventType] = mapped_column(Enum(AuditEventType))
    timestamp: Mapped[datetime] = mapped_column()
    actor_id: Mapped[str | None] = mapped_column(String(36), default=None)
    actor_email: Mapped[str | None] = mapped_column(String(255), default=None)
    actor_role: Mapped[str | None] = mapped_column(String(50), default=None)
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(500), default=None)

    # Event-specific data
    data: Mapped[dict | None] = mapped_column(JSON, default=None)

    # For tamper evidence, store hash of previous event
    previous_event_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    event_hash: Mapped[str | None] = mapped_column(String(64), default=None)

    # Relationships
    envelope: Mapped["Envelope"] = relationship(back_populates="audit_events")
