"""Signing API routes for recipient signing flow."""

import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import base64

from app.core.security import verify_signing_token
from app.models import (
    AssigneeType,
    AuditEventType,
    Document,
    Envelope,
    EnvelopeStatus,
    Field,
    FieldOwner,
    FieldType,
    FieldValue,
    Recipient,
    RecipientStatus,
    Role,
    get_db,
)
from app.schemas import (
    FieldResponse,
    FieldValueCreate,
    FieldValueResponse,
    RoleResponse,
    SigningComplete,
    SigningSessionResponse,
)
from app.services.audit import audit_service
from app.services.storage import storage_service

router = APIRouter(prefix="/signing", tags=["signing"])


async def get_recipient_from_token(
    signing_token: str,
    db: AsyncSession,
    check_signing_order: bool = True,
) -> tuple[Recipient, Envelope]:
    """Verify signing token and return recipient and envelope."""
    payload = verify_signing_token(signing_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired signing link",
        )

    recipient_id = payload.get("sub")
    envelope_id = payload.get("envelope_id")

    if not recipient_id or not envelope_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signing token",
        )

    # Get recipient with role info
    result = await db.execute(
        select(Recipient)
        .options(
            selectinload(Recipient.role_ref),
            selectinload(Recipient.envelope)
            .selectinload(Envelope.document)
            .selectinload(Document.fields)
            .selectinload(Field.role),
        )
        .where(
            Recipient.id == recipient_id,
            Recipient.signing_token == signing_token,
        )
    )
    recipient = result.scalar_one_or_none()

    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signing link is no longer valid",
        )

    envelope = recipient.envelope

    if envelope.status == EnvelopeStatus.VOIDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This envelope has been voided",
        )

    if envelope.status == EnvelopeStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This envelope has already been completed",
        )

    if recipient.status == RecipientStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already completed signing",
        )

    # Check signing order enforcement
    if check_signing_order:
        await _check_signing_order(recipient, envelope, db)

    return recipient, envelope


async def _check_signing_order(
    recipient: Recipient,
    envelope: Envelope,
    db: AsyncSession,
) -> None:
    """
    Check if signing order allows this recipient to sign.

    If signing_order is set on roles, earlier signers must complete
    before later signers can sign.
    """
    # Get recipient's role and signing order
    if not recipient.role_ref or recipient.role_ref.signing_order is None:
        # No signing order enforcement for this recipient
        return

    my_order = recipient.role_ref.signing_order

    # Get all roles with signing_order < my_order
    result = await db.execute(
        select(Role)
        .where(
            Role.envelope_id == envelope.id,
            Role.signing_order.isnot(None),
            Role.signing_order < my_order,
        )
    )
    earlier_roles = result.scalars().all()

    if not earlier_roles:
        # No earlier signers to wait for
        return

    # Get all recipients for earlier roles
    earlier_role_ids = [r.id for r in earlier_roles]
    result = await db.execute(
        select(Recipient)
        .where(
            Recipient.envelope_id == envelope.id,
            Recipient.role_id.in_(earlier_role_ids),
        )
    )
    earlier_recipients = result.scalars().all()

    # Check if all earlier recipients have completed
    incomplete_signers = [
        r for r in earlier_recipients
        if r.status != RecipientStatus.COMPLETED
    ]

    if incomplete_signers:
        # Build message about who needs to sign first
        waiting_for = ", ".join([r.name for r in incomplete_signers])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Signing order required. Waiting for: {waiting_for}",
        )


def _field_belongs_to_recipient(field: Field, recipient: Recipient) -> bool:
    """Check if a field belongs to this recipient's role."""
    # New role-based matching
    if recipient.role_id and field.role_id:
        return field.role_id == recipient.role_id

    # Legacy matching using owner enum
    if recipient.role and field.owner:
        return field.owner == recipient.role

    return False


def _field_is_sender(field: Field) -> bool:
    """Check if field is a sender field."""
    return field.assignee_type == AssigneeType.SENDER or field.owner == FieldOwner.SENDER


@router.get("/session/{signing_token}", response_model=SigningSessionResponse)
async def get_signing_session(
    signing_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get signing session data for a recipient."""
    recipient, envelope = await get_recipient_from_token(signing_token, db)
    document = envelope.document

    # Determine role key for audit logging
    role_key = (
        recipient.role_ref.key if recipient.role_ref
        else (recipient.role.value if recipient.role else "unknown")
    )

    # Mark as viewed if first time
    if recipient.status == RecipientStatus.SENT:
        recipient.status = RecipientStatus.VIEWED
        recipient.viewed_at = datetime.now(timezone.utc)
        await db.commit()

        # Log view event
        await audit_service.log_event(
            db=db,
            envelope_id=envelope.id,
            event_type=AuditEventType.RECIPIENT_VIEWED,
            actor_email=recipient.email,
            actor_role=role_key,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            data={"recipient_id": recipient.id},
        )

    # Get fields for this recipient's role
    recipient_fields = [
        FieldResponse.from_orm_with_bbox(f)
        for f in document.fields
        if _field_belongs_to_recipient(f, recipient)
    ]

    # Get sender fields (visible but not editable)
    sender_fields = [
        FieldResponse.from_orm_with_bbox(f)
        for f in document.fields
        if _field_is_sender(f)
    ]

    # Get existing field values
    result = await db.execute(
        select(FieldValue).where(FieldValue.envelope_id == envelope.id)
    )
    field_values = result.scalars().all()

    # Build role response if available
    role_response = None
    if recipient.role_ref:
        role_response = RoleResponse(
            id=recipient.role_ref.id,
            envelope_id=recipient.role_ref.envelope_id,
            key=recipient.role_ref.key,
            display_name=recipient.role_ref.display_name,
            color=recipient.role_ref.color,
            signing_order=recipient.role_ref.signing_order,
            created_at=recipient.role_ref.created_at,
        )

    return SigningSessionResponse(
        envelope_id=envelope.id,
        document_name=document.name,
        recipient_name=recipient.name,
        recipient_role=recipient.role,  # Legacy
        recipient_role_id=recipient.role_id,
        recipient_role_info=role_response,
        fields=recipient_fields + sender_fields,
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
            for fv in field_values
        ],
        sender_variables=envelope.sender_variables,
        page_images=document.page_images or [],
        page_count=document.page_count,
    )


@router.post("/session/{signing_token}/field")
async def save_field_value(
    signing_token: str,
    field_value: FieldValueCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Save a field value during signing."""
    recipient, envelope = await get_recipient_from_token(signing_token, db)

    # Verify field belongs to document
    result = await db.execute(
        select(Field).where(
            Field.id == field_value.field_id,
            Field.document_id == envelope.document_id,
        )
    )
    field = result.scalar_one_or_none()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found",
        )

    # Verify field belongs to this recipient using role-based matching
    if not _field_belongs_to_recipient(field, recipient):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot fill this field",
        )

    # Determine role key for audit logging
    role_key = (
        recipient.role_ref.key if recipient.role_ref
        else (recipient.role.value if recipient.role else "unknown")
    )

    # Update recipient status to signing
    if recipient.status == RecipientStatus.VIEWED:
        recipient.status = RecipientStatus.SIGNING

    # Check if value already exists
    result = await db.execute(
        select(FieldValue).where(
            FieldValue.envelope_id == envelope.id,
            FieldValue.field_id == field.id,
        )
    )
    existing_value = result.scalar_one_or_none()

    if existing_value:
        existing_value.value = field_value.value
        existing_value.signature_data = field_value.signature_data
        existing_value.filled_at = datetime.now(timezone.utc)
        fv = existing_value
    else:
        fv = FieldValue(
            envelope_id=envelope.id,
            field_id=field.id,
            value=field_value.value,
            signature_data=field_value.signature_data,
            filled_by_role=recipient.role,  # Legacy
            filled_by_role_id=recipient.role_id,  # New
            filled_at=datetime.now(timezone.utc),
        )
        db.add(fv)

    await db.commit()
    await db.refresh(fv)

    # Log field completion
    await audit_service.log_event(
        db=db,
        envelope_id=envelope.id,
        event_type=AuditEventType.FIELD_COMPLETED,
        actor_email=recipient.email,
        actor_role=role_key,
        ip_address=request.client.host if request.client else None,
        data={
            "field_id": field.id,
            "field_type": field.field_type.value,
        },
    )

    return FieldValueResponse(
        id=fv.id,
        envelope_id=fv.envelope_id,
        field_id=fv.field_id,
        value=fv.value,
        signature_data=fv.signature_data,
        filled_by_role=fv.filled_by_role,
        filled_by_role_id=fv.filled_by_role_id,
        filled_at=fv.filled_at,
    )


@router.post("/session/{signing_token}/complete")
async def complete_signing(
    signing_token: str,
    signing_data: SigningComplete,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Complete signing for a recipient."""
    recipient, envelope = await get_recipient_from_token(signing_token, db)
    document = envelope.document

    # Determine role key for audit logging
    role_key = (
        recipient.role_ref.key if recipient.role_ref
        else (recipient.role.value if recipient.role else "unknown")
    )

    # Save all field values
    for fv_data in signing_data.field_values:
        result = await db.execute(
            select(Field).where(
                Field.id == fv_data.field_id,
                Field.document_id == document.id,
            )
        )
        field = result.scalar_one_or_none()

        if not field:
            continue

        # Use role-based matching
        if not _field_belongs_to_recipient(field, recipient):
            continue

        # Check if value exists
        result = await db.execute(
            select(FieldValue).where(
                FieldValue.envelope_id == envelope.id,
                FieldValue.field_id == field.id,
            )
        )
        existing_value = result.scalar_one_or_none()

        if existing_value:
            existing_value.value = fv_data.value
            existing_value.signature_data = fv_data.signature_data
            existing_value.filled_at = datetime.now(timezone.utc)
        else:
            fv = FieldValue(
                envelope_id=envelope.id,
                field_id=field.id,
                value=fv_data.value,
                signature_data=fv_data.signature_data,
                filled_by_role=recipient.role,  # Legacy
                filled_by_role_id=recipient.role_id,  # New
                filled_at=datetime.now(timezone.utc),
            )
            db.add(fv)

    # Validate all required fields are filled using role-based matching
    required_fields = [
        f for f in document.fields
        if _field_belongs_to_recipient(f, recipient) and f.required
    ]

    result = await db.execute(
        select(FieldValue).where(FieldValue.envelope_id == envelope.id)
    )
    field_values = {fv.field_id: fv for fv in result.scalars().all()}

    missing_fields = []
    for field in required_fields:
        fv = field_values.get(field.id)
        if not fv or (not fv.value and not fv.signature_data):
            missing_fields.append(field.id)

    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Required fields not filled: {missing_fields}",
        )

    # Mark recipient as completed
    recipient.status = RecipientStatus.COMPLETED
    recipient.completed_at = datetime.now(timezone.utc)
    recipient.signing_token = None  # Invalidate token

    await db.commit()

    # Log signature applied
    await audit_service.log_event(
        db=db,
        envelope_id=envelope.id,
        event_type=AuditEventType.SIGNATURE_APPLIED,
        actor_email=recipient.email,
        actor_role=role_key,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        data={"recipient_id": recipient.id},
    )

    # Log recipient completed
    await audit_service.log_event(
        db=db,
        envelope_id=envelope.id,
        event_type=AuditEventType.RECIPIENT_COMPLETED,
        actor_email=recipient.email,
        actor_role=role_key,
        ip_address=request.client.host if request.client else None,
        data={"recipient_id": recipient.id},
    )

    # Check if all recipients have completed
    result = await db.execute(
        select(Recipient).where(Recipient.envelope_id == envelope.id)
    )
    all_recipients = result.scalars().all()
    all_completed = all(r.status == RecipientStatus.COMPLETED for r in all_recipients)

    if all_completed:
        await _finalize_envelope(envelope, document, db)

    return {"message": "Signing completed successfully", "all_completed": all_completed}


async def _finalize_envelope(
    envelope: Envelope,
    document: Document,
    db: AsyncSession,
):
    """Finalize an envelope after all recipients have signed."""
    # Get all field values
    result = await db.execute(
        select(FieldValue)
        .options(selectinload(FieldValue.field))
        .where(FieldValue.envelope_id == envelope.id)
    )
    field_values = list(result.scalars().all())

    # Create final PDF with filled values
    final_pdf_path = await _create_final_pdf(
        document,
        field_values,
        envelope.sender_variables or {},
    )

    # Compute hash
    final_hash = storage_service.compute_hash(final_pdf_path)

    # Create completion certificate
    certificate_path = await _create_completion_certificate(
        envelope, document, field_values, final_hash, db
    )

    # Update envelope
    envelope.status = EnvelopeStatus.COMPLETED
    envelope.completed_at = datetime.now(timezone.utc)
    envelope.final_document_path = str(final_pdf_path)
    envelope.final_document_hash = final_hash
    envelope.completion_certificate_path = str(certificate_path)

    await db.commit()

    # Log completion
    await audit_service.log_event(
        db=db,
        envelope_id=envelope.id,
        event_type=AuditEventType.ENVELOPE_COMPLETED,
        data={
            "document_hash": final_hash,
            "certificate_path": str(certificate_path),
        },
    )


async def _create_final_pdf(
    document: Document,
    field_values: list[FieldValue],
    sender_variables: dict[str, str],
) -> Path:
    """Create final PDF with all field values rendered."""
    # Open original PDF
    source_path = Path(document.file_path)
    doc = fitz.open(source_path)

    # Create a mapping of field_id to value
    value_map = {fv.field_id: fv for fv in field_values}

    # Get all fields
    result_fields = document.fields if hasattr(document, 'fields') else []

    for field in result_fields:
        fv = value_map.get(field.id)

        # Get the value to render
        if field.owner == FieldOwner.SENDER and field.sender_variable_key:
            value = sender_variables.get(field.sender_variable_key, "")
        elif fv:
            value = fv.value or ""
        else:
            continue

        if not value and not (fv and fv.signature_data):
            continue

        page = doc[field.page_number - 1]

        # Handle signature fields
        if field.field_type in [FieldType.SIGNATURE, FieldType.INITIALS]:
            if fv and fv.signature_data:
                try:
                    # Decode base64 signature data
                    if fv.signature_data.startswith("data:"):
                        # Remove data URL prefix
                        sig_data = fv.signature_data.split(",", 1)[1]
                    else:
                        sig_data = fv.signature_data

                    sig_bytes = base64.b64decode(sig_data)

                    # Create image from bytes
                    sig_img = Image.open(io.BytesIO(sig_bytes))
                    sig_img = sig_img.convert("RGBA")

                    # Convert to PNG bytes
                    img_buffer = io.BytesIO()
                    sig_img.save(img_buffer, format="PNG")
                    img_buffer.seek(0)

                    # Insert image into PDF
                    rect = fitz.Rect(
                        field.bbox_x,
                        field.bbox_y,
                        field.bbox_x + field.bbox_width,
                        field.bbox_y + field.bbox_height,
                    )
                    page.insert_image(rect, stream=img_buffer.read())
                except Exception as e:
                    # If signature rendering fails, add text fallback
                    print(f"Error rendering signature: {e}")
        else:
            # Text fields
            rect = fitz.Rect(
                field.bbox_x,
                field.bbox_y,
                field.bbox_x + field.bbox_width,
                field.bbox_y + field.bbox_height,
            )

            # Determine font size based on field height
            font_size = min(field.bbox_height * 0.7, 12)

            # Insert text
            page.insert_textbox(
                rect,
                value,
                fontsize=font_size,
                align=0,  # Left align
            )

    # Save final PDF
    final_path = storage_service.get_final_document_path(document.id)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(final_path)
    doc.close()

    return final_path


async def _create_completion_certificate(
    envelope: Envelope,
    document: Document,
    field_values: list[FieldValue],
    document_hash: str,
    db: AsyncSession,
) -> Path:
    """Create a completion certificate PDF."""
    certificate_path = storage_service.get_certificate_path(envelope.id)
    certificate_path.parent.mkdir(parents=True, exist_ok=True)

    # Get audit trail
    audit_events = await audit_service.get_audit_trail(db, envelope.id)

    # Get recipients
    result = await db.execute(
        select(Recipient).where(Recipient.envelope_id == envelope.id)
    )
    recipients = list(result.scalars().all())

    # Create PDF
    doc = SimpleDocTemplate(
        str(certificate_path),
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=1,  # Center
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
    )
    normal_style = styles['Normal']

    story = []

    # Title
    story.append(Paragraph("Certificate of Completion", title_style))
    story.append(Spacer(1, 20))

    # Document info
    story.append(Paragraph("Document Information", heading_style))
    doc_info = [
        ["Document Name:", document.name],
        ["Envelope ID:", envelope.id],
        ["Completed At:", envelope.completed_at.strftime("%Y-%m-%d %H:%M:%S UTC") if envelope.completed_at else "N/A"],
        ["Document Hash (SHA-256):", document_hash[:32] + "..."],
    ]
    t = Table(doc_info, colWidths=[2 * inch, 4 * inch])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # Signers
    story.append(Paragraph("Signers", heading_style))
    signer_data = [["Name", "Email", "Role", "Signed At"]]
    for r in recipients:
        signer_data.append([
            r.name,
            r.email,
            r.role.value,
            r.completed_at.strftime("%Y-%m-%d %H:%M:%S UTC") if r.completed_at else "N/A",
        ])
    t = Table(signer_data, colWidths=[1.5 * inch, 2 * inch, 1 * inch, 1.5 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # Audit Trail
    story.append(Paragraph("Audit Trail", heading_style))
    audit_data = [["Timestamp", "Event", "Actor", "Details"]]
    for event in audit_events:
        audit_data.append([
            event.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            event.event_type.value,
            event.actor_email or "System",
            str(event.data)[:50] + "..." if event.data and len(str(event.data)) > 50 else str(event.data or ""),
        ])
    t = Table(audit_data, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t)
    story.append(Spacer(1, 30))

    # Verification note
    story.append(Paragraph(
        f"This certificate verifies that the document with SHA-256 hash "
        f"<b>{document_hash}</b> was signed by all parties listed above. "
        f"The audit trail above provides a tamper-evident record of all "
        f"signing activities.",
        normal_style,
    ))

    doc.build(story)

    return certificate_path


@router.get("/download/{envelope_id}/final")
async def download_final_document(
    envelope_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Download the final signed document."""
    from app.api.auth import get_current_user

    user = await get_current_user(token, db)

    result = await db.execute(
        select(Envelope).where(
            Envelope.id == envelope_id,
            Envelope.sender_id == user.id,
        )
    )
    envelope = result.scalar_one_or_none()

    if not envelope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Envelope not found",
        )

    if envelope.status != EnvelopeStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envelope is not completed",
        )

    if not envelope.final_document_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Final document not found",
        )

    # Log download
    await audit_service.log_event(
        db=db,
        envelope_id=envelope.id,
        event_type=AuditEventType.DOCUMENT_DOWNLOADED,
        actor_id=user.id,
        actor_email=user.email,
        actor_role="sender",
    )

    return FileResponse(
        envelope.final_document_path,
        media_type="application/pdf",
        filename=f"signed_{envelope.name}.pdf",
    )


@router.get("/download/{envelope_id}/certificate")
async def download_certificate(
    envelope_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Download the completion certificate."""
    from app.api.auth import get_current_user

    user = await get_current_user(token, db)

    result = await db.execute(
        select(Envelope).where(
            Envelope.id == envelope_id,
            Envelope.sender_id == user.id,
        )
    )
    envelope = result.scalar_one_or_none()

    if not envelope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Envelope not found",
        )

    if envelope.status != EnvelopeStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envelope is not completed",
        )

    if not envelope.completion_certificate_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found",
        )

    return FileResponse(
        envelope.completion_certificate_path,
        media_type="application/pdf",
        filename=f"certificate_{envelope.name}.pdf",
    )
