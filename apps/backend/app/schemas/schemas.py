"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field as PydanticField

from app.models.models import (
    AssigneeType,
    AuditEventType,
    DocumentStatus,
    EnvelopeStatus,
    FieldOwner,
    FieldType,
    RecipientStatus,
)


# --- Base schemas ---


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    class Config:
        from_attributes = True


# --- User schemas ---


class UserCreate(BaseModel):
    """Schema for creating a user."""

    email: EmailStr
    name: str | None = None


class UserResponse(BaseSchema):
    """Schema for user response."""

    id: str
    email: str
    name: str | None
    is_active: bool
    created_at: datetime


class AuthRequest(BaseModel):
    """Schema for magic link auth request."""

    email: EmailStr


class AuthResponse(BaseModel):
    """Schema for auth response."""

    access_token: str
    token_type: str = "bearer"


# --- Document schemas ---


class DocumentCreate(BaseModel):
    """Schema for document metadata during upload."""

    name: str | None = None


class DocumentResponse(BaseSchema):
    """Schema for document response."""

    id: str
    owner_id: str
    name: str
    original_filename: str
    file_size: int
    mime_type: str
    page_count: int
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentResponse):
    """Schema for detailed document response with fields."""

    fields: list["FieldResponse"] = []
    page_images: list[str] | None = None


# --- Field schemas ---


class BoundingBox(BaseModel):
    """Schema for field bounding box."""

    x: float
    y: float
    width: float
    height: float


class FieldCreate(BaseModel):
    """Schema for creating a field."""

    page_number: int
    bbox: BoundingBox
    field_type: FieldType

    # DEPRECATED: Use assignee_type + role_key instead
    owner: FieldOwner | None = None

    # NEW: N-signer assignee model
    assignee_type: AssigneeType = AssigneeType.ROLE
    role_key: str | None = None  # Key to match envelope role
    detected_role_key: str | None = None

    required: bool = True
    label: str | None = None
    placeholder: str | None = None
    default_value: str | None = None
    sender_variable_key: str | None = None
    anchor_text: str | None = None


class FieldUpdate(BaseModel):
    """Schema for updating a field."""

    page_number: int | None = None
    bbox: BoundingBox | None = None
    field_type: FieldType | None = None

    # DEPRECATED: Use assignee_type + role_key instead
    owner: FieldOwner | None = None

    # NEW: N-signer assignee model
    assignee_type: AssigneeType | None = None
    role_key: str | None = None

    required: bool | None = None
    label: str | None = None
    placeholder: str | None = None
    default_value: str | None = None
    sender_variable_key: str | None = None


class FieldResponse(BaseSchema):
    """Schema for field response."""

    id: str
    document_id: str
    page_number: int
    bbox: BoundingBox
    field_type: FieldType

    # DEPRECATED: Use assignee_type + role_id instead
    owner: FieldOwner | None = None

    # NEW: N-signer assignee model
    assignee_type: AssigneeType
    role_id: str | None = None
    detected_role_key: str | None = None

    required: bool
    label: str | None
    placeholder: str | None
    default_value: str | None
    sender_variable_key: str | None
    detection_confidence: float | None
    classification_confidence: float | None
    owner_confidence: float | None
    role_confidence: float | None = None
    evidence: str | None
    created_at: datetime

    @classmethod
    def from_orm_with_bbox(cls, field) -> "FieldResponse":
        """Create response from ORM model with bbox conversion."""
        return cls(
            id=field.id,
            document_id=field.document_id,
            page_number=field.page_number,
            bbox=BoundingBox(
                x=field.bbox_x,
                y=field.bbox_y,
                width=field.bbox_width,
                height=field.bbox_height,
            ),
            field_type=field.field_type,
            owner=field.owner,
            assignee_type=field.assignee_type,
            role_id=field.role_id,
            detected_role_key=field.detected_role_key,
            required=field.required,
            label=field.label,
            placeholder=field.placeholder,
            default_value=field.default_value,
            sender_variable_key=field.sender_variable_key,
            detection_confidence=field.detection_confidence,
            classification_confidence=field.classification_confidence,
            owner_confidence=field.owner_confidence,
            role_confidence=field.role_confidence,
            evidence=field.evidence,
            created_at=field.created_at,
        )


class DetectedField(BaseModel):
    """Schema for a detected field candidate."""

    page_number: int
    bbox: BoundingBox
    field_type: FieldType

    # DEPRECATED: Use assignee_type + detected_role_key instead
    owner: FieldOwner | None = None

    # NEW: N-signer assignee model
    assignee_type: AssigneeType = AssigneeType.ROLE
    detected_role_key: str | None = None  # e.g., "client", "landlord"

    detection_confidence: float
    classification_confidence: float
    owner_confidence: float
    role_confidence: float = 0.5
    evidence: str
    label: str | None = None
    suggested_placeholder: str | None = None


class FieldDetectionResponse(BaseModel):
    """Schema for field detection response."""

    document_id: str
    detected_fields: list[DetectedField]
    detection_time_ms: float
    total_candidates: int
    filtered_candidates: int


# --- Role schemas ---


class RoleCreate(BaseModel):
    """Schema for creating a role."""

    key: str  # Unique within envelope, e.g., "client", "contractor"
    display_name: str  # Human-readable, e.g., "Client"
    color: str | None = None  # Hex color, e.g., "#3B82F6"
    signing_order: int | None = None  # 1-indexed, null = no order


class RoleResponse(BaseSchema):
    """Schema for role response."""

    id: str
    envelope_id: str
    key: str
    display_name: str
    color: str
    signing_order: int | None
    created_at: datetime


# --- Envelope schemas ---


class RecipientCreate(BaseModel):
    """Schema for creating a recipient."""

    email: EmailStr
    name: str

    # DEPRECATED: Use role_key instead
    role: FieldOwner | None = None

    # NEW: Reference role by key
    role_key: str | None = None  # Key matching RoleCreate.key


class EnvelopeCreate(BaseModel):
    """Schema for creating an envelope."""

    document_id: str
    name: str
    message: str | None = None

    # NEW: Define roles for this envelope
    roles: list[RoleCreate] | None = None

    recipients: list[RecipientCreate]
    sender_variables: dict[str, str] | None = None


class EnvelopeSend(BaseModel):
    """Schema for sending an envelope."""

    sender_variables: dict[str, str] | None = None


class RecipientResponse(BaseSchema):
    """Schema for recipient response."""

    id: str
    email: str
    name: str

    # DEPRECATED: Use role_id and role_info instead
    role: FieldOwner | None = None

    # NEW: N-signer role reference
    role_id: str | None = None
    role_info: RoleResponse | None = None

    order: int
    status: RecipientStatus
    sent_at: datetime | None
    viewed_at: datetime | None
    completed_at: datetime | None


class EnvelopeResponse(BaseSchema):
    """Schema for envelope response."""

    id: str
    sender_id: str
    document_id: str
    name: str
    message: str | None
    status: EnvelopeStatus
    sender_variables: dict[str, str] | None
    sent_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    # NEW: Roles defined for this envelope
    roles: list[RoleResponse] = []

    recipients: list[RecipientResponse] = []


class EnvelopeDetailResponse(EnvelopeResponse):
    """Schema for detailed envelope response."""

    document: DocumentResponse
    field_values: list["FieldValueResponse"] = []


# --- Field Value schemas ---


class FieldValueCreate(BaseModel):
    """Schema for creating/updating a field value."""

    field_id: str
    value: str | None = None
    signature_data: str | None = None


class FieldValueResponse(BaseSchema):
    """Schema for field value response."""

    id: str
    envelope_id: str
    field_id: str
    value: str | None
    signature_data: str | None

    # DEPRECATED: Use filled_by_role_id instead
    filled_by_role: FieldOwner | None = None

    # NEW: Reference to role that filled this
    filled_by_role_id: str | None = None

    filled_at: datetime | None


# --- Signing schemas ---


class SigningSessionResponse(BaseModel):
    """Schema for signing session data."""

    envelope_id: str
    document_name: str
    recipient_name: str

    # DEPRECATED: Use recipient_role_info instead
    recipient_role: FieldOwner | None = None

    # NEW: Full role information
    recipient_role_id: str | None = None
    recipient_role_info: RoleResponse | None = None

    fields: list[FieldResponse]
    field_values: list[FieldValueResponse]
    sender_variables: dict[str, str] | None
    page_images: list[str]
    page_count: int


class SigningComplete(BaseModel):
    """Schema for completing signing."""

    field_values: list[FieldValueCreate]


# --- Audit schemas ---


class AuditEventResponse(BaseSchema):
    """Schema for audit event response."""

    id: str
    envelope_id: str
    event_type: AuditEventType
    timestamp: datetime
    actor_email: str | None
    actor_role: str | None
    data: dict | None


class CompletionCertificate(BaseModel):
    """Schema for completion certificate."""

    envelope_id: str
    document_name: str
    completed_at: datetime
    document_hash: str
    signers: list[dict[str, Any]]
    audit_trail: list[AuditEventResponse]


# --- Response helpers ---


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str
    error_code: str | None = None
