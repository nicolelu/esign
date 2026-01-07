"""API endpoint tests."""

import pytest
from httpx import AsyncClient
from pathlib import Path


pytestmark = pytest.mark.asyncio


class TestHealth:
    """Health check endpoint tests."""

    async def test_health_check(self, client: AsyncClient):
        """Test health check returns healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns app info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "version" in data


class TestAuth:
    """Authentication endpoint tests."""

    async def test_request_magic_link(self, client: AsyncClient):
        """Test requesting a magic link."""
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "magic_link" in data

    async def test_verify_magic_link(self, client: AsyncClient):
        """Test verifying a magic link."""
        # First request a magic link
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "test@example.com"},
        )
        token = response.json()["token"]

        # Verify the token
        response = await client.post(f"/api/v1/auth/verify?token={token}")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_get_me(self, client: AsyncClient):
        """Test getting current user info."""
        # Get auth token
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "test@example.com"},
        )
        magic_token = response.json()["token"]

        response = await client.post(f"/api/v1/auth/verify?token={magic_token}")
        access_token = response.json()["access_token"]

        # Get user info
        response = await client.get(f"/api/v1/auth/me?token={access_token}")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"


class TestDocuments:
    """Document endpoint tests."""

    async def test_upload_document(self, client: AsyncClient, sample_pdf_path: Path):
        """Test uploading a document."""
        # Get auth token
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "test@example.com"},
        )
        magic_token = response.json()["token"]
        response = await client.post(f"/api/v1/auth/verify?token={magic_token}")
        access_token = response.json()["access_token"]

        # Upload document
        with open(sample_pdf_path, "rb") as f:
            response = await client.post(
                f"/api/v1/documents?token={access_token}&name=Test%20Document",
                files={"file": ("test.pdf", f, "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Document"
        assert data["mime_type"] == "application/pdf"
        assert data["page_count"] >= 1

    async def test_list_documents(self, client: AsyncClient, sample_pdf_path: Path):
        """Test listing documents."""
        # Get auth token
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "test@example.com"},
        )
        magic_token = response.json()["token"]
        response = await client.post(f"/api/v1/auth/verify?token={magic_token}")
        access_token = response.json()["access_token"]

        # Upload a document first
        with open(sample_pdf_path, "rb") as f:
            await client.post(
                f"/api/v1/documents?token={access_token}",
                files={"file": ("test.pdf", f, "application/pdf")},
            )

        # List documents
        response = await client.get(f"/api/v1/documents?token={access_token}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestFields:
    """Field endpoint tests."""

    async def test_create_field(self, client: AsyncClient, sample_pdf_path: Path):
        """Test creating a field."""
        # Get auth token
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "test@example.com"},
        )
        magic_token = response.json()["token"]
        response = await client.post(f"/api/v1/auth/verify?token={magic_token}")
        access_token = response.json()["access_token"]

        # Upload document
        with open(sample_pdf_path, "rb") as f:
            response = await client.post(
                f"/api/v1/documents?token={access_token}",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        doc_id = response.json()["id"]

        # Create field
        response = await client.post(
            f"/api/v1/documents/{doc_id}/fields?token={access_token}",
            json={
                "page_number": 1,
                "bbox": {"x": 100, "y": 100, "width": 200, "height": 30},
                "field_type": "TEXT",
                "owner": "SIGNER_1",
                "required": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["field_type"] == "TEXT"
        assert data["owner"] == "SIGNER_1"

    async def test_update_field(self, client: AsyncClient, sample_pdf_path: Path):
        """Test updating a field."""
        # Get auth token
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "test@example.com"},
        )
        magic_token = response.json()["token"]
        response = await client.post(f"/api/v1/auth/verify?token={magic_token}")
        access_token = response.json()["access_token"]

        # Upload document
        with open(sample_pdf_path, "rb") as f:
            response = await client.post(
                f"/api/v1/documents?token={access_token}",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        doc_id = response.json()["id"]

        # Create field
        response = await client.post(
            f"/api/v1/documents/{doc_id}/fields?token={access_token}",
            json={
                "page_number": 1,
                "bbox": {"x": 100, "y": 100, "width": 200, "height": 30},
                "field_type": "TEXT",
                "owner": "SIGNER_1",
            },
        )
        field_id = response.json()["id"]

        # Update field
        response = await client.patch(
            f"/api/v1/documents/{doc_id}/fields/{field_id}?token={access_token}",
            json={"field_type": "SIGNATURE"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["field_type"] == "SIGNATURE"


class TestEnvelopes:
    """Envelope endpoint tests."""

    async def test_create_envelope(self, client: AsyncClient, sample_pdf_path: Path):
        """Test creating an envelope."""
        # Get auth token
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "sender@example.com"},
        )
        magic_token = response.json()["token"]
        response = await client.post(f"/api/v1/auth/verify?token={magic_token}")
        access_token = response.json()["access_token"]

        # Upload document
        with open(sample_pdf_path, "rb") as f:
            response = await client.post(
                f"/api/v1/documents?token={access_token}",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        doc_id = response.json()["id"]

        # Create envelope
        response = await client.post(
            f"/api/v1/envelopes?token={access_token}",
            json={
                "document_id": doc_id,
                "name": "Test Envelope",
                "recipients": [
                    {"email": "signer@example.com", "name": "Test Signer", "role": "SIGNER_1"}
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Envelope"
        assert data["status"] == "DRAFT"
        assert len(data["recipients"]) == 1

    async def test_send_envelope(self, client: AsyncClient, sample_pdf_path: Path):
        """Test sending an envelope."""
        # Get auth token
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "sender@example.com"},
        )
        magic_token = response.json()["token"]
        response = await client.post(f"/api/v1/auth/verify?token={magic_token}")
        access_token = response.json()["access_token"]

        # Upload document
        with open(sample_pdf_path, "rb") as f:
            response = await client.post(
                f"/api/v1/documents?token={access_token}",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        doc_id = response.json()["id"]

        # Create envelope
        response = await client.post(
            f"/api/v1/envelopes?token={access_token}",
            json={
                "document_id": doc_id,
                "name": "Test Envelope",
                "recipients": [
                    {"email": "signer@example.com", "name": "Test Signer", "role": "SIGNER_1"}
                ],
            },
        )
        envelope_id = response.json()["id"]

        # Send envelope
        response = await client.post(
            f"/api/v1/envelopes/{envelope_id}/send?token={access_token}",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SENT"

    async def test_get_signing_links(self, client: AsyncClient, sample_pdf_path: Path):
        """Test getting signing links."""
        # Get auth token
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "sender@example.com"},
        )
        magic_token = response.json()["token"]
        response = await client.post(f"/api/v1/auth/verify?token={magic_token}")
        access_token = response.json()["access_token"]

        # Upload document
        with open(sample_pdf_path, "rb") as f:
            response = await client.post(
                f"/api/v1/documents?token={access_token}",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        doc_id = response.json()["id"]

        # Create and send envelope
        response = await client.post(
            f"/api/v1/envelopes?token={access_token}",
            json={
                "document_id": doc_id,
                "name": "Test Envelope",
                "recipients": [
                    {"email": "signer@example.com", "name": "Test Signer", "role": "SIGNER_1"}
                ],
            },
        )
        envelope_id = response.json()["id"]

        await client.post(
            f"/api/v1/envelopes/{envelope_id}/send?token={access_token}",
            json={},
        )

        # Get signing links
        response = await client.get(
            f"/api/v1/envelopes/{envelope_id}/signing-links?token={access_token}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["signing_links"]) == 1
        assert "signing_url" in data["signing_links"][0]
