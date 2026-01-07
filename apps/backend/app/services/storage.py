"""Storage service for file management."""

import hashlib
import os
import shutil
from pathlib import Path
from typing import BinaryIO

import aiofiles
import aiofiles.os

from app.core.config import get_settings

settings = get_settings()


class StorageService:
    """Service for managing file storage."""

    def __init__(self):
        """Initialize storage service."""
        self.storage_path = Path(settings.storage_path)
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        directories = [
            self.storage_path / "documents",
            self.storage_path / "page_images",
            self.storage_path / "signatures",
            self.storage_path / "final_documents",
            self.storage_path / "certificates",
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def get_document_path(self, document_id: str, filename: str) -> Path:
        """Get path for storing a document."""
        return self.storage_path / "documents" / document_id / filename

    def get_page_image_path(self, document_id: str, page_number: int) -> Path:
        """Get path for a page image."""
        return (
            self.storage_path / "page_images" / document_id / f"page_{page_number}.png"
        )

    def get_signature_path(self, envelope_id: str, field_id: str) -> Path:
        """Get path for a signature image."""
        return (
            self.storage_path / "signatures" / envelope_id / f"sig_{field_id}.png"
        )

    def get_final_document_path(self, envelope_id: str) -> Path:
        """Get path for final signed document."""
        return self.storage_path / "final_documents" / f"{envelope_id}_final.pdf"

    def get_certificate_path(self, envelope_id: str) -> Path:
        """Get path for completion certificate."""
        return self.storage_path / "certificates" / f"{envelope_id}_certificate.pdf"

    async def save_file(
        self,
        file_data: bytes | BinaryIO,
        dest_path: Path,
    ) -> tuple[str, int]:
        """
        Save a file and return its SHA-256 hash and size.

        Args:
            file_data: File content as bytes or file-like object
            dest_path: Destination path

        Returns:
            Tuple of (sha256_hash, file_size)
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if hasattr(file_data, "read"):
            # It's a file-like object
            content = file_data.read()
            if hasattr(file_data, "seek"):
                file_data.seek(0)
        else:
            content = file_data

        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(content)

        file_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        return file_hash, file_size

    async def read_file(self, file_path: Path) -> bytes:
        """Read file content."""
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def delete_file(self, file_path: Path) -> bool:
        """Delete a file if it exists."""
        try:
            if file_path.exists():
                await aiofiles.os.remove(file_path)
            return True
        except Exception:
            return False

    async def delete_directory(self, dir_path: Path) -> bool:
        """Delete a directory and its contents."""
        try:
            if dir_path.exists():
                shutil.rmtree(dir_path)
            return True
        except Exception:
            return False

    def file_exists(self, file_path: Path) -> bool:
        """Check if a file exists."""
        return file_path.exists()

    def get_file_url(self, file_path: Path) -> str:
        """
        Get the URL for accessing a file.

        For local storage, this returns a path relative to the storage root
        that can be served by the API.
        """
        try:
            relative_path = file_path.relative_to(self.storage_path)
            return f"/api/v1/files/{relative_path}"
        except ValueError:
            return str(file_path)

    def compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


# Singleton instance
storage_service = StorageService()
