"""Field detection API routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.models import Document, Field, User, get_db
from app.schemas import (
    BoundingBox,
    DetectedField,
    FieldDetectionResponse,
    FieldCreate,
    FieldResponse,
)
from app.services.detection.detector import field_detector

router = APIRouter(prefix="/documents/{document_id}", tags=["detection"])


@router.post("/detect", response_model=FieldDetectionResponse)
async def detect_fields(
    document_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Automatically detect form fields in a document.

    Uses a hybrid approach combining:
    - PDF text analysis
    - Vector graphics detection (underlines, checkboxes)
    - Keyword-based inference
    - Anchor tag detection [type|role]
    """
    user = await get_current_user(token, db)

    # Get document
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == user.id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Run detection
    file_path = Path(document.file_path)
    detection_result = await field_detector.detect_fields(
        document_id=document.id,
        file_path=file_path,
        text_layout=document.text_layout,
    )

    # Convert to response format
    detected_fields = [
        DetectedField(
            page_number=f.page_number,
            bbox=BoundingBox(**f.bbox.to_dict()),
            field_type=f.field_type,
            owner=f.owner,
            detection_confidence=f.detection_confidence,
            classification_confidence=f.classification_confidence,
            owner_confidence=f.owner_confidence,
            evidence=f.evidence,
            label=f.label,
            suggested_placeholder=f.nearby_text,
        )
        for f in detection_result.detected_fields
    ]

    return FieldDetectionResponse(
        document_id=document_id,
        detected_fields=detected_fields,
        detection_time_ms=detection_result.detection_time_ms,
        total_candidates=detection_result.total_candidates,
        filtered_candidates=detection_result.filtered_candidates,
    )


@router.post("/detect/apply", response_model=list[FieldResponse])
async def apply_detected_fields(
    document_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Detect fields and automatically create them on the document.

    This is a convenience endpoint that combines detection and field creation.
    """
    user = await get_current_user(token, db)

    # Get document
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == user.id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Run detection
    file_path = Path(document.file_path)
    detection_result = await field_detector.detect_fields(
        document_id=document.id,
        file_path=file_path,
        text_layout=document.text_layout,
    )

    # Create fields
    created_fields = []
    for detected in detection_result.detected_fields:
        field = Field(
            document_id=document.id,
            page_number=detected.page_number,
            bbox_x=detected.bbox.x,
            bbox_y=detected.bbox.y,
            bbox_width=detected.bbox.width,
            bbox_height=detected.bbox.height,
            field_type=detected.field_type,
            owner=detected.owner,
            required=True,
            label=detected.label,
            detection_confidence=detected.detection_confidence,
            classification_confidence=detected.classification_confidence,
            owner_confidence=detected.owner_confidence,
            evidence=detected.evidence,
        )
        db.add(field)
        created_fields.append(field)

    await db.commit()

    # Refresh and return
    for field in created_fields:
        await db.refresh(field)

    return [FieldResponse.from_orm_with_bbox(f) for f in created_fields]
