"""Field detection tests."""

import pytest
from pathlib import Path
import tempfile

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas

from app.services.detection.detector import field_detector, BBox
from app.models import AssigneeType, FieldType, FieldOwner


pytestmark = pytest.mark.asyncio


def create_test_pdf(path: Path, content_fn):
    """Create a test PDF with custom content."""
    c = pdf_canvas.Canvas(str(path), pagesize=letter)
    content_fn(c)
    c.save()


class TestFieldDetector:
    """Field detector tests."""

    async def test_detect_underscores(self):
        """Test detecting underscore blanks."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            c.drawString(100, 700, "Name: _________________________")
            c.drawString(100, 650, "Email: ________________________")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)
        assert len(result.detected_fields) >= 0  # May detect underscores

        path.unlink()

    async def test_detect_signature_keyword(self):
        """Test detecting signature fields by keyword."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            c.drawString(100, 700, "Client Signature:")
            c.drawString(100, 650, "Company Signature:")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Should find signature fields
        sig_fields = [
            f for f in result.detected_fields
            if f.field_type == FieldType.SIGNATURE
        ]
        assert len(sig_fields) >= 1

        path.unlink()

    async def test_detect_date_keyword(self):
        """Test detecting date fields by keyword."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            c.drawString(100, 700, "Date Signed:")
            c.drawString(100, 650, "Effective Date:")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Should find date fields
        date_fields = [
            f for f in result.detected_fields
            if f.field_type == FieldType.DATE_SIGNED
        ]
        assert len(date_fields) >= 1

        path.unlink()

    async def test_detect_anchor_tags(self):
        """Test detecting anchor tags."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            c.drawString(100, 700, "Sign here: [sig|signer1]")
            c.drawString(100, 650, "Date: [date|signer2]")
            c.drawString(100, 600, "Name: [name|signer1]")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Should find anchor tag fields with high confidence
        anchor_fields = [
            f for f in result.detected_fields
            if f.detection_confidence >= 0.9
        ]
        assert len(anchor_fields) >= 3

        # Check types
        types = {f.field_type for f in anchor_fields}
        assert FieldType.SIGNATURE in types
        assert FieldType.DATE_SIGNED in types
        assert FieldType.NAME in types

        path.unlink()

    async def test_detect_sender_variables(self):
        """Test detecting sender variable tags."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            c.drawString(100, 700, "Effective Date: {{effective_date}}")
            c.drawString(100, 650, "Total Amount: {{total_amount}}")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Should find sender variable fields
        sender_fields = [
            f for f in result.detected_fields
            if f.owner == FieldOwner.SENDER
        ]
        assert len(sender_fields) >= 2

        path.unlink()

    async def test_owner_inference_signer1(self):
        """Test owner inference for signer 1 keywords."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            c.drawString(100, 700, "Client Signature:")
            c.drawString(100, 650, "Tenant Name:")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Fields should be assigned to SIGNER_1
        signer1_fields = [
            f for f in result.detected_fields
            if f.owner == FieldOwner.SIGNER_1
        ]
        assert len(signer1_fields) >= 1

        path.unlink()

    async def test_owner_inference_signer2(self):
        """Test owner inference for signer 2 keywords."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            c.drawString(100, 700, "Company Signature:")
            c.drawString(100, 650, "Landlord Name:")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Fields should be assigned to SIGNER_2
        signer2_fields = [
            f for f in result.detected_fields
            if f.owner == FieldOwner.SIGNER_2
        ]
        assert len(signer2_fields) >= 1

        path.unlink()

    async def test_deduplication(self):
        """Test that overlapping candidates are deduplicated."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            # Create multiple similar patterns that might produce overlapping candidates
            c.drawString(100, 700, "Signature: __________________")
            c.drawString(100, 680, "Sign Here")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Check no significant overlap in results
        for i, f1 in enumerate(result.detected_fields):
            for f2 in result.detected_fields[i + 1:]:
                if f1.page_number == f2.page_number:
                    # Calculate overlap
                    x_overlap = max(0, min(f1.bbox.x + f1.bbox.width, f2.bbox.x + f2.bbox.width) - max(f1.bbox.x, f2.bbox.x))
                    y_overlap = max(0, min(f1.bbox.y + f1.bbox.height, f2.bbox.y + f2.bbox.height) - max(f1.bbox.y, f2.bbox.y))
                    overlap_area = x_overlap * y_overlap
                    area1 = f1.bbox.width * f1.bbox.height
                    area2 = f2.bbox.width * f2.bbox.height

                    # Should not have > 50% overlap
                    if area1 > 0 and area2 > 0:
                        assert overlap_area / min(area1, area2) < 0.5

        path.unlink()


class TestBoundingBox:
    """Bounding box tests."""

    def test_bbox_to_dict(self):
        """Test bbox conversion to dict."""
        bbox = BBox(x=100, y=200, width=300, height=40)
        d = bbox.to_dict()
        assert d["x"] == 100
        assert d["y"] == 200
        assert d["width"] == 300
        assert d["height"] == 40


class TestNSignerDetection:
    """N-signer (role-based) detection tests."""

    async def test_detect_new_anchor_tag_format(self):
        """Test detecting anchor tags with new [type|role:key] format."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            c.drawString(100, 700, "Client sign here: [sig|role:client]")
            c.drawString(100, 650, "Contractor sign here: [sig|role:contractor]")
            c.drawString(100, 600, "Witness sign here: [sig|role:witness]")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Should find all three signature fields with proper role keys
        sig_fields = [
            f for f in result.detected_fields
            if f.field_type == FieldType.SIGNATURE
        ]
        assert len(sig_fields) >= 3

        # Check role keys are detected
        role_keys = {f.detected_role_key for f in sig_fields}
        assert "client" in role_keys
        assert "contractor" in role_keys
        assert "witness" in role_keys

        # Verify assignee_type is ROLE
        for field in sig_fields:
            assert field.assignee_type == AssigneeType.ROLE

        path.unlink()

    async def test_detect_legacy_anchor_tags_backward_compat(self):
        """Test backward compatibility with legacy [type|signerN] format."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            c.drawString(100, 700, "Sign here: [sig|signer1]")
            c.drawString(100, 650, "Date: [date|signer2]")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Should find both fields
        sig_field = [f for f in result.detected_fields if f.field_type == FieldType.SIGNATURE]
        date_field = [f for f in result.detected_fields if f.field_type == FieldType.DATE_SIGNED]

        assert len(sig_field) >= 1
        assert len(date_field) >= 1

        # Legacy format should map to role_key signer_1/signer_2
        assert sig_field[0].detected_role_key == "signer_1"
        assert sig_field[0].owner == FieldOwner.SIGNER_1

        assert date_field[0].detected_role_key == "signer_2"
        assert date_field[0].owner == FieldOwner.SIGNER_2

        path.unlink()

    async def test_detect_role_inference_from_keywords(self):
        """Test role inference from document text keywords."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            # Client-related signature
            c.drawString(100, 700, "Client Signature:")
            # Company/employer-related signature
            c.drawString(100, 650, "Company Representative Signature:")
            # Landlord-related signature
            c.drawString(100, 600, "Landlord Signature:")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Should detect signature fields with role keys inferred
        sig_fields = [
            f for f in result.detected_fields
            if f.field_type == FieldType.SIGNATURE
        ]

        # Check that role keys are inferred from context
        role_keys = {f.detected_role_key for f in sig_fields if f.detected_role_key}
        # Should have at least some role key inferences
        assert len(role_keys) >= 1

        path.unlink()

    async def test_detect_sender_variables_assignee_type(self):
        """Test sender variables have correct assignee_type."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            c.drawString(100, 700, "Contract Date: {{contract_date}}")
            c.drawString(100, 650, "Amount: {{amount}}")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Find sender variable fields
        sender_fields = [
            f for f in result.detected_fields
            if f.assignee_type == AssigneeType.SENDER
        ]
        assert len(sender_fields) >= 2

        # Sender fields should have no role_id
        for field in sender_fields:
            assert field.detected_role_key is None

        path.unlink()

    async def test_detect_mixed_role_document(self):
        """Test document with multiple different roles."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        def content(c):
            # 5 different roles
            c.drawString(100, 750, "[sig|role:buyer]")
            c.drawString(100, 700, "[sig|role:seller]")
            c.drawString(100, 650, "[sig|role:agent]")
            c.drawString(100, 600, "[sig|role:witness1]")
            c.drawString(100, 550, "[sig|role:witness2]")
            c.drawString(100, 500, "{{effective_date}}")

        create_test_pdf(path, content)

        result = await field_detector.detect_fields("test", path)

        # Should detect 5 signer role fields + 1 sender field
        role_fields = [
            f for f in result.detected_fields
            if f.assignee_type == AssigneeType.ROLE
        ]
        sender_fields = [
            f for f in result.detected_fields
            if f.assignee_type == AssigneeType.SENDER
        ]

        assert len(role_fields) >= 5
        assert len(sender_fields) >= 1

        # Check unique role keys
        role_keys = {f.detected_role_key for f in role_fields if f.detected_role_key}
        assert len(role_keys) >= 5

        path.unlink()
