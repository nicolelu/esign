"""Envelopes API routes for sending documents for signature."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.core.config import get_settings
from app.core.security import create_signing_token
from app.models import (
    AssigneeType,
    AuditEventType,
    Document,
    DocumentStatus,
    Envelope,
    EnvelopeStatus,
    Field,
    FieldOwner,
    Recipient,
    RecipientStatus,
    Role,
    User,
    get_db,
)
from app.schemas import (
    EnvelopeCreate,
    EnvelopeDetailResponse,
    EnvelopeResponse,
    EnvelopeSend,
    MessageResponse,
    RecipientResponse,
    RoleResponse,
)
from app.services.audit import audit_service

settings = get_settings()
router = APIRouter(prefix="/envelopes", tags=["envelopes"])


# Default colors for roles
DEFAULT_ROLE_COLORS = {
    "client": "#3B82F6",  # Blue
    "contractor": "#10B981",  # Green
    "company": "#8B5CF6",  # Purple
    "landlord": "#F59E0B",  # Amber
    "tenant": "#EC4899",  # Pink
    "witness": "#6B7280",  # Gray
    "signer_1": "#3B82F6",  # Blue
    "signer_2": "#10B981",  # Green
}


def _get_role_color(key: str) -> str:
    """Get default color for a role key."""
    return DEFAULT_ROLE_COLORS.get(key.lower(), "#3B82F6")


@router.post("", response_model=EnvelopeResponse)
async def create_envelope(
    envelope_data: EnvelopeCreate,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Create a new envelope (document package for signing)."""
    user = await get_current_user(token, db)

    # Verify document exists and belongs to user
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.fields))
        .where(Document.id == envelope_data.document_id, Document.owner_id == user.id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Validate sender variables are provided for all sender fields
    sender_fields = [
        f for f in document.fields
        if f.assignee_type == AssigneeType.SENDER or f.owner == FieldOwner.SENDER
    ]
    sender_var_keys = {
        f.sender_variable_key
        for f in sender_fields
        if f.sender_variable_key
    }
    provided_keys = set(envelope_data.sender_variables.keys()) if envelope_data.sender_variables else set()

    missing_keys = sender_var_keys - provided_keys
    if missing_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing sender variable values: {missing_keys}",
        )

    # Create envelope
    envelope = Envelope(
        sender_id=user.id,
        document_id=document.id,
        name=envelope_data.name,
        message=envelope_data.message,
        status=EnvelopeStatus.DRAFT,
        sender_variables=envelope_data.sender_variables,
        expires_at=datetime.now(timezone.utc)
        + timedelta(hours=settings.signing_link_expiry_hours),
    )
    db.add(envelope)
    await db.flush()

    # Create roles for this envelope
    role_map: dict[str, Role] = {}  # key -> Role

    if envelope_data.roles:
        # Use explicitly provided roles
        for i, role_data in enumerate(envelope_data.roles):
            role = Role(
                envelope_id=envelope.id,
                key=role_data.key,
                display_name=role_data.display_name,
                color=role_data.color or _get_role_color(role_data.key),
                signing_order=role_data.signing_order,
            )
            db.add(role)
            await db.flush()
            role_map[role_data.key] = role
    else:
        # Auto-create roles based on recipient role_key or legacy role
        for recipient_data in envelope_data.recipients:
            role_key = recipient_data.role_key or (
                recipient_data.role.value.lower() if recipient_data.role else "signer_1"
            )
            if role_key not in role_map:
                # Determine display name
                if recipient_data.role:
                    display_name = recipient_data.role.value.replace("_", " ").title()
                else:
                    display_name = role_key.replace("_", " ").title()

                role = Role(
                    envelope_id=envelope.id,
                    key=role_key,
                    display_name=display_name,
                    color=_get_role_color(role_key),
                )
                db.add(role)
                await db.flush()
                role_map[role_key] = role

    # Create recipients linked to roles
    for i, recipient_data in enumerate(envelope_data.recipients):
        # Determine which role this recipient belongs to
        role_key = recipient_data.role_key or (
            recipient_data.role.value.lower() if recipient_data.role else "signer_1"
        )

        if role_key not in role_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_key}' not defined. "
                f"Available roles: {list(role_map.keys())}",
            )

        role = role_map[role_key]

        recipient = Recipient(
            envelope_id=envelope.id,
            email=recipient_data.email,
            name=recipient_data.name,
            role=recipient_data.role,  # Keep for backward compatibility
            role_id=role.id,
            order=i + 1,
            status=RecipientStatus.PENDING,
        )
        db.add(recipient)

    await db.commit()
    await db.refresh(envelope)

    # Log creation event
    await audit_service.log_event(
        db=db,
        envelope_id=envelope.id,
        event_type=AuditEventType.ENVELOPE_CREATED,
        actor_id=user.id,
        actor_email=user.email,
        actor_role="sender",
        data={
            "document_id": document.id,
            "document_name": document.name,
            "roles": [{"key": r.key, "display_name": r.display_name} for r in role_map.values()],
            "recipients": [
                {"email": r.email, "name": r.name, "role_key": r.role_key or (r.role.value if r.role else None)}
                for r in envelope_data.recipients
            ],
        },
    )

    # Load recipients and roles for response
    result = await db.execute(
        select(Envelope)
        .options(
            selectinload(Envelope.recipients).selectinload(Recipient.role_ref),
            selectinload(Envelope.roles),
        )
        .where(Envelope.id == envelope.id)
    )
    envelope = result.scalar_one()

    return EnvelopeResponse(
        id=envelope.id,
        sender_id=envelope.sender_id,
        document_id=envelope.document_id,
        name=envelope.name,
        message=envelope.message,
        status=envelope.status,
        sender_variables=envelope.sender_variables,
        sent_at=envelope.sent_at,
        completed_at=envelope.completed_at,
        created_at=envelope.created_at,
        roles=[
            RoleResponse(
                id=role.id,
                envelope_id=role.envelope_id,
                key=role.key,
                display_name=role.display_name,
                color=role.color,
                signing_order=role.signing_order,
                created_at=role.created_at,
            )
            for role in envelope.roles
        ],
        recipients=[
            RecipientResponse(
                id=r.id,
                email=r.email,
                name=r.name,
                role=r.role,
                role_id=r.role_id,
                role_info=RoleResponse(
                    id=r.role_ref.id,
                    envelope_id=r.role_ref.envelope_id,
                    key=r.role_ref.key,
                    display_name=r.role_ref.display_name,
                    color=r.role_ref.color,
                    signing_order=r.role_ref.signing_order,
                    created_at=r.role_ref.created_at,
                ) if r.role_ref else None,
                order=r.order,
                status=r.status,
                sent_at=r.sent_at,
                viewed_at=r.viewed_at,
                completed_at=r.completed_at,
            )
            for r in envelope.recipients
        ],
    )


@router.get("", response_model=list[EnvelopeResponse])
async def list_envelopes(
    token: str,
    status_filter: EnvelopeStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all envelopes for the current user."""
    user = await get_current_user(token, db)

    query = (
        select(Envelope)
        .options(
            selectinload(Envelope.recipients).selectinload(Recipient.role_ref),
            selectinload(Envelope.roles),
        )
        .where(Envelope.sender_id == user.id)
    )
    if status_filter:
        query = query.where(Envelope.status == status_filter)

    query = query.order_by(Envelope.created_at.desc())
    result = await db.execute(query)
    envelopes = result.scalars().all()

    return [
        EnvelopeResponse(
            id=e.id,
            sender_id=e.sender_id,
            document_id=e.document_id,
            name=e.name,
            message=e.message,
            status=e.status,
            sender_variables=e.sender_variables,
            sent_at=e.sent_at,
            completed_at=e.completed_at,
            created_at=e.created_at,
            roles=[
                RoleResponse(
                    id=role.id,
                    envelope_id=role.envelope_id,
                    key=role.key,
                    display_name=role.display_name,
                    color=role.color,
                    signing_order=role.signing_order,
                    created_at=role.created_at,
                )
                for role in e.roles
            ],
            recipients=[
                RecipientResponse(
                    id=r.id,
                    email=r.email,
                    name=r.name,
                    role=r.role,
                    role_id=r.role_id,
                    role_info=RoleResponse(
                        id=r.role_ref.id,
                        envelope_id=r.role_ref.envelope_id,
                        key=r.role_ref.key,
                        display_name=r.role_ref.display_name,
                        color=r.role_ref.color,
                        signing_order=r.role_ref.signing_order,
                        created_at=r.role_ref.created_at,
                    ) if r.role_ref else None,
                    order=r.order,
                    status=r.status,
                    sent_at=r.sent_at,
                    viewed_at=r.viewed_at,
                    completed_at=r.completed_at,
                )
                for r in e.recipients
            ],
        )
        for e in envelopes
    ]


@router.get("/{envelope_id}", response_model=EnvelopeDetailResponse)
async def get_envelope(
    envelope_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get envelope details."""
    user = await get_current_user(token, db)

    result = await db.execute(
        select(Envelope)
        .options(
            selectinload(Envelope.recipients).selectinload(Recipient.role_ref),
            selectinload(Envelope.roles),
            selectinload(Envelope.document),
            selectinload(Envelope.field_values),
        )
        .where(Envelope.id == envelope_id, Envelope.sender_id == user.id)
    )
    envelope = result.scalar_one_or_none()

    if not envelope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Envelope not found",
        )

    from app.schemas import DocumentResponse, FieldValueResponse

    return EnvelopeDetailResponse(
        id=envelope.id,
        sender_id=envelope.sender_id,
        document_id=envelope.document_id,
        name=envelope.name,
        message=envelope.message,
        status=envelope.status,
        sender_variables=envelope.sender_variables,
        sent_at=envelope.sent_at,
        completed_at=envelope.completed_at,
        created_at=envelope.created_at,
        roles=[
            RoleResponse(
                id=role.id,
                envelope_id=role.envelope_id,
                key=role.key,
                display_name=role.display_name,
                color=role.color,
                signing_order=role.signing_order,
                created_at=role.created_at,
            )
            for role in envelope.roles
        ],
        recipients=[
            RecipientResponse(
                id=r.id,
                email=r.email,
                name=r.name,
                role=r.role,
                role_id=r.role_id,
                role_info=RoleResponse(
                    id=r.role_ref.id,
                    envelope_id=r.role_ref.envelope_id,
                    key=r.role_ref.key,
                    display_name=r.role_ref.display_name,
                    color=r.role_ref.color,
                    signing_order=r.role_ref.signing_order,
                    created_at=r.role_ref.created_at,
                ) if r.role_ref else None,
                order=r.order,
                status=r.status,
                sent_at=r.sent_at,
                viewed_at=r.viewed_at,
                completed_at=r.completed_at,
            )
            for r in envelope.recipients
        ],
        document=DocumentResponse(
            id=envelope.document.id,
            owner_id=envelope.document.owner_id,
            name=envelope.document.name,
            original_filename=envelope.document.original_filename,
            file_size=envelope.document.file_size,
            mime_type=envelope.document.mime_type,
            page_count=envelope.document.page_count,
            status=envelope.document.status,
            created_at=envelope.document.created_at,
            updated_at=envelope.document.updated_at,
        ),
        field_values=[
            FieldValueResponse(
                id=fv.id,
                envelope_id=fv.envelope_id,
                field_id=fv.field_id,
                value=fv.value,
                signature_data=fv.signature_data,
                filled_by_role=fv.filled_by_role,
                filled_by_role_id=fv.filled_by_role_id,
                filled_at=fv.filled_at,
            )
            for fv in envelope.field_values
        ],
    )


@router.post("/{envelope_id}/send", response_model=EnvelopeResponse)
async def send_envelope(
    envelope_id: str,
    token: str,
    send_data: EnvelopeSend | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Send an envelope to recipients."""
    user = await get_current_user(token, db)

    result = await db.execute(
        select(Envelope)
        .options(
            selectinload(Envelope.recipients).selectinload(Recipient.role_ref),
            selectinload(Envelope.roles),
            selectinload(Envelope.document).selectinload(Document.fields),
        )
        .where(Envelope.id == envelope_id, Envelope.sender_id == user.id)
    )
    envelope = result.scalar_one_or_none()

    if not envelope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Envelope not found",
        )

    if envelope.status != EnvelopeStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envelope has already been sent",
        )

    # Update sender variables if provided
    if send_data and send_data.sender_variables:
        envelope.sender_variables = {
            **(envelope.sender_variables or {}),
            **send_data.sender_variables,
        }

    # Generate signing tokens for each recipient
    for recipient in envelope.recipients:
        signing_token = create_signing_token(
            envelope_id=envelope.id,
            recipient_id=recipient.id,
            recipient_email=recipient.email,
        )
        recipient.signing_token = signing_token
        recipient.status = RecipientStatus.SENT
        recipient.sent_at = datetime.now(timezone.utc)

    # Update envelope status
    envelope.status = EnvelopeStatus.SENT
    envelope.sent_at = datetime.now(timezone.utc)

    # Update document status
    envelope.document.status = DocumentStatus.SENT

    await db.commit()
    await db.refresh(envelope)

    # Log send event
    await audit_service.log_event(
        db=db,
        envelope_id=envelope.id,
        event_type=AuditEventType.ENVELOPE_SENT,
        actor_id=user.id,
        actor_email=user.email,
        actor_role="sender",
        data={
            "recipients": [
                {"email": r.email, "name": r.name}
                for r in envelope.recipients
            ],
        },
    )

    # In production, send emails here
    # For MVP, signing links are accessible via the API

    return EnvelopeResponse(
        id=envelope.id,
        sender_id=envelope.sender_id,
        document_id=envelope.document_id,
        name=envelope.name,
        message=envelope.message,
        status=envelope.status,
        sender_variables=envelope.sender_variables,
        sent_at=envelope.sent_at,
        completed_at=envelope.completed_at,
        created_at=envelope.created_at,
        roles=[
            RoleResponse(
                id=role.id,
                envelope_id=role.envelope_id,
                key=role.key,
                display_name=role.display_name,
                color=role.color,
                signing_order=role.signing_order,
                created_at=role.created_at,
            )
            for role in envelope.roles
        ],
        recipients=[
            RecipientResponse(
                id=r.id,
                email=r.email,
                name=r.name,
                role=r.role,
                role_id=r.role_id,
                role_info=RoleResponse(
                    id=r.role_ref.id,
                    envelope_id=r.role_ref.envelope_id,
                    key=r.role_ref.key,
                    display_name=r.role_ref.display_name,
                    color=r.role_ref.color,
                    signing_order=r.role_ref.signing_order,
                    created_at=r.role_ref.created_at,
                ) if r.role_ref else None,
                order=r.order,
                status=r.status,
                sent_at=r.sent_at,
                viewed_at=r.viewed_at,
                completed_at=r.completed_at,
            )
            for r in envelope.recipients
        ],
    )


@router.get("/{envelope_id}/signing-links")
async def get_signing_links(
    envelope_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get signing links for all recipients (for testing/demo purposes)."""
    user = await get_current_user(token, db)

    result = await db.execute(
        select(Envelope)
        .options(selectinload(Envelope.recipients))
        .where(Envelope.id == envelope_id, Envelope.sender_id == user.id)
    )
    envelope = result.scalar_one_or_none()

    if not envelope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Envelope not found",
        )

    if envelope.status == EnvelopeStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envelope has not been sent yet",
        )

    signing_links = []
    for recipient in envelope.recipients:
        if recipient.signing_token:
            signing_links.append(
                {
                    "recipient_id": recipient.id,
                    "email": recipient.email,
                    "name": recipient.name,
                    "role": recipient.role.value,
                    "status": recipient.status.value,
                    "signing_url": f"{settings.signing_link_base_url}/sign/{recipient.signing_token}",
                }
            )

    return {"envelope_id": envelope_id, "signing_links": signing_links}


@router.delete("/{envelope_id}")
async def void_envelope(
    envelope_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Void an envelope (cancel signing)."""
    user = await get_current_user(token, db)

    result = await db.execute(
        select(Envelope)
        .options(selectinload(Envelope.recipients))
        .where(Envelope.id == envelope_id, Envelope.sender_id == user.id)
    )
    envelope = result.scalar_one_or_none()

    if not envelope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Envelope not found",
        )

    if envelope.status == EnvelopeStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot void a completed envelope",
        )

    envelope.status = EnvelopeStatus.VOIDED
    for recipient in envelope.recipients:
        recipient.signing_token = None

    await db.commit()

    # Log void event
    await audit_service.log_event(
        db=db,
        envelope_id=envelope.id,
        event_type=AuditEventType.ENVELOPE_VOIDED,
        actor_id=user.id,
        actor_email=user.email,
        actor_role="sender",
    )

    return {"message": "Envelope voided successfully"}
