"""Fields API routes for managing document fields."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.models import Document, Field, User, get_db
from app.schemas import FieldCreate, FieldResponse, FieldUpdate

router = APIRouter(prefix="/documents/{document_id}/fields", tags=["fields"])


async def get_document_or_404(
    document_id: str,
    user: User,
    db: AsyncSession,
) -> Document:
    """Get document or raise 404."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.owner_id == user.id
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document


@router.post("", response_model=FieldResponse)
async def create_field(
    document_id: str,
    field_data: FieldCreate,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Create a new field on a document."""
    user = await get_current_user(token, db)
    document = await get_document_or_404(document_id, user, db)

    # Validate page number
    if field_data.page_number < 1 or field_data.page_number > document.page_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid page number. Document has {document.page_count} pages",
        )

    # Create field
    field = Field(
        document_id=document.id,
        page_number=field_data.page_number,
        bbox_x=field_data.bbox.x,
        bbox_y=field_data.bbox.y,
        bbox_width=field_data.bbox.width,
        bbox_height=field_data.bbox.height,
        field_type=field_data.field_type,
        owner=field_data.owner,
        required=field_data.required,
        label=field_data.label,
        placeholder=field_data.placeholder,
        default_value=field_data.default_value,
        sender_variable_key=field_data.sender_variable_key,
        anchor_text=field_data.anchor_text,
        # Manual fields have confidence of 1.0
        detection_confidence=1.0,
        classification_confidence=1.0,
        owner_confidence=1.0,
        evidence="Manually created field",
    )

    db.add(field)
    await db.commit()
    await db.refresh(field)

    return FieldResponse.from_orm_with_bbox(field)


@router.get("", response_model=list[FieldResponse])
async def list_fields(
    document_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """List all fields for a document."""
    user = await get_current_user(token, db)
    await get_document_or_404(document_id, user, db)

    result = await db.execute(
        select(Field)
        .where(Field.document_id == document_id)
        .order_by(Field.page_number, Field.bbox_y)
    )
    fields = result.scalars().all()

    return [FieldResponse.from_orm_with_bbox(f) for f in fields]


@router.get("/{field_id}", response_model=FieldResponse)
async def get_field(
    document_id: str,
    field_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific field."""
    user = await get_current_user(token, db)
    await get_document_or_404(document_id, user, db)

    result = await db.execute(
        select(Field).where(Field.id == field_id, Field.document_id == document_id)
    )
    field = result.scalar_one_or_none()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found",
        )

    return FieldResponse.from_orm_with_bbox(field)


@router.patch("/{field_id}", response_model=FieldResponse)
async def update_field(
    document_id: str,
    field_id: str,
    field_data: FieldUpdate,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Update a field."""
    user = await get_current_user(token, db)
    document = await get_document_or_404(document_id, user, db)

    result = await db.execute(
        select(Field).where(Field.id == field_id, Field.document_id == document_id)
    )
    field = result.scalar_one_or_none()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found",
        )

    # Update fields
    if field_data.page_number is not None:
        if field_data.page_number < 1 or field_data.page_number > document.page_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid page number. Document has {document.page_count} pages",
            )
        field.page_number = field_data.page_number

    if field_data.bbox is not None:
        field.bbox_x = field_data.bbox.x
        field.bbox_y = field_data.bbox.y
        field.bbox_width = field_data.bbox.width
        field.bbox_height = field_data.bbox.height

    if field_data.field_type is not None:
        field.field_type = field_data.field_type

    if field_data.owner is not None:
        field.owner = field_data.owner

    if field_data.required is not None:
        field.required = field_data.required

    if field_data.label is not None:
        field.label = field_data.label

    if field_data.placeholder is not None:
        field.placeholder = field_data.placeholder

    if field_data.default_value is not None:
        field.default_value = field_data.default_value

    if field_data.sender_variable_key is not None:
        field.sender_variable_key = field_data.sender_variable_key

    await db.commit()
    await db.refresh(field)

    return FieldResponse.from_orm_with_bbox(field)


@router.delete("/{field_id}")
async def delete_field(
    document_id: str,
    field_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a field."""
    user = await get_current_user(token, db)
    await get_document_or_404(document_id, user, db)

    result = await db.execute(
        select(Field).where(Field.id == field_id, Field.document_id == document_id)
    )
    field = result.scalar_one_or_none()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found",
        )

    await db.delete(field)
    await db.commit()

    return {"message": "Field deleted successfully"}


@router.post("/bulk", response_model=list[FieldResponse])
async def create_fields_bulk(
    document_id: str,
    fields_data: list[FieldCreate],
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple fields at once."""
    user = await get_current_user(token, db)
    document = await get_document_or_404(document_id, user, db)

    created_fields = []
    for field_data in fields_data:
        # Validate page number
        if field_data.page_number < 1 or field_data.page_number > document.page_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid page number {field_data.page_number}. "
                f"Document has {document.page_count} pages",
            )

        field = Field(
            document_id=document.id,
            page_number=field_data.page_number,
            bbox_x=field_data.bbox.x,
            bbox_y=field_data.bbox.y,
            bbox_width=field_data.bbox.width,
            bbox_height=field_data.bbox.height,
            field_type=field_data.field_type,
            owner=field_data.owner,
            required=field_data.required,
            label=field_data.label,
            placeholder=field_data.placeholder,
            default_value=field_data.default_value,
            sender_variable_key=field_data.sender_variable_key,
            anchor_text=field_data.anchor_text,
            detection_confidence=1.0,
            classification_confidence=1.0,
            owner_confidence=1.0,
            evidence="Manually created field",
        )
        db.add(field)
        created_fields.append(field)

    await db.commit()

    # Refresh all fields
    for field in created_fields:
        await db.refresh(field)

    return [FieldResponse.from_orm_with_bbox(f) for f in created_fields]


@router.delete("")
async def delete_all_fields(
    document_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete all fields from a document."""
    user = await get_current_user(token, db)
    await get_document_or_404(document_id, user, db)

    result = await db.execute(
        select(Field).where(Field.document_id == document_id)
    )
    fields = result.scalars().all()

    for field in fields:
        await db.delete(field)

    await db.commit()

    return {"message": f"Deleted {len(fields)} fields"}
