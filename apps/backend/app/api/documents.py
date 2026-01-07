"""Documents API routes."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.models import Document, DocumentStatus, Field, User, get_db
from app.schemas import (
    DocumentCreate,
    DocumentDetailResponse,
    DocumentResponse,
    FieldResponse,
)
from app.services.document import document_service
from app.services.storage import storage_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse)
async def upload_document(
    token: str,
    file: UploadFile = File(...),
    name: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new document."""
    user = await get_current_user(token, db)

    # Validate file type
    allowed_types = ["application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {allowed_types}",
        )

    # Create document record first to get ID
    doc_name = name or file.filename or "Untitled Document"
    document = Document(
        owner_id=user.id,
        name=doc_name,
        original_filename=file.filename or "document.pdf",
        file_path="",  # Will update after saving
        file_size=0,
        mime_type=file.content_type,
        status=DocumentStatus.DRAFT,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Save file
    file_content = await file.read()
    file_path = storage_service.get_document_path(document.id, document.original_filename)
    file_hash, file_size = await storage_service.save_file(file_content, file_path)

    # Process document (render pages, extract text)
    processing_result = await document_service.process_document(document.id, file_path)

    # Update document with file info and processing results
    document.file_path = str(file_path)
    document.file_hash = file_hash
    document.file_size = file_size
    document.page_count = processing_result["page_count"]
    document.page_images = processing_result["page_images"]
    document.extracted_text = processing_result["extracted_text"]
    document.text_layout = processing_result["text_layout"]

    await db.commit()
    await db.refresh(document)

    return document


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    token: str,
    status_filter: DocumentStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """List all documents for the current user."""
    user = await get_current_user(token, db)

    query = select(Document).where(Document.owner_id == user.id)
    if status_filter:
        query = query.where(Document.status == status_filter)

    query = query.order_by(Document.created_at.desc())
    result = await db.execute(query)
    documents = result.scalars().all()

    return documents


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a document by ID with its fields."""
    user = await get_current_user(token, db)

    result = await db.execute(
        select(Document)
        .options(selectinload(Document.fields))
        .where(Document.id == document_id, Document.owner_id == user.id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Convert fields to response format
    fields_response = [
        FieldResponse.from_orm_with_bbox(field) for field in document.fields
    ]

    return DocumentDetailResponse(
        id=document.id,
        owner_id=document.owner_id,
        name=document.name,
        original_filename=document.original_filename,
        file_size=document.file_size,
        mime_type=document.mime_type,
        page_count=document.page_count,
        status=document.status,
        created_at=document.created_at,
        updated_at=document.updated_at,
        fields=fields_response,
        page_images=document.page_images,
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document."""
    user = await get_current_user(token, db)

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

    # Don't allow deletion of sent/completed documents
    if document.status in [DocumentStatus.SENT, DocumentStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a document that has been sent or completed",
        )

    # Delete file and images
    from pathlib import Path

    await storage_service.delete_file(Path(document.file_path))
    await storage_service.delete_directory(
        storage_service.storage_path / "page_images" / document.id
    )

    # Delete from database
    await db.delete(document)
    await db.commit()

    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/page/{page_number}")
async def get_page_image(
    document_id: str,
    page_number: int,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific page image."""
    user = await get_current_user(token, db)

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

    if page_number < 1 or page_number > document.page_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid page number. Document has {document.page_count} pages",
        )

    image_path = storage_service.get_page_image_path(document_id, page_number)
    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page image not found",
        )

    from fastapi.responses import FileResponse

    return FileResponse(image_path, media_type="image/png")
