"""
Field detection service for identifying form fields in PDF documents.

This module implements a hybrid approach combining:
1. PDF text extraction and analysis
2. Computer vision on rendered page images
3. Heuristic rules for common patterns
"""

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.models import AssigneeType, FieldOwner, FieldType

settings = get_settings()


@dataclass
class BBox:
    """Bounding box in PDF coordinates."""
    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class DetectedField:
    """A detected field candidate."""
    page_number: int
    bbox: BBox
    field_type: FieldType

    # DEPRECATED: Use assignee_type + detected_role_key instead
    owner: FieldOwner | None = None

    # NEW: N-signer assignee model
    assignee_type: AssigneeType = AssigneeType.ROLE
    detected_role_key: str | None = None  # e.g., "client", "landlord"

    detection_confidence: float = 0.5
    classification_confidence: float = 0.5
    owner_confidence: float = 0.5
    role_confidence: float = 0.5
    evidence: str = ""
    label: str | None = None
    nearby_text: str | None = None


@dataclass
class DetectionResult:
    """Result of field detection."""
    document_id: str
    detected_fields: list[DetectedField]
    detection_time_ms: float
    total_candidates: int
    filtered_candidates: int


class FieldDetector:
    """
    Hybrid field detector combining text analysis and computer vision.

    Detection strategies:
    1. Underline detection: Find horizontal lines near text labels
    2. Checkbox detection: Find small square shapes
    3. Signature detection: Find "Signature" labels with adjacent blank space
    4. Date detection: Find "Date" labels with adjacent blank space
    5. Anchor text detection: Find [type|role] tags in text
    """

    # Keywords that suggest field types
    SIGNATURE_KEYWORDS = [
        "signature", "sign here", "authorized signature",
        "client signature", "employee signature", "contractor signature",
        "landlord signature", "tenant signature", "buyer signature",
        "seller signature", "witness signature"
    ]

    DATE_KEYWORDS = [
        "date", "dated", "date signed", "effective date",
        "start date", "end date", "as of"
    ]

    NAME_KEYWORDS = [
        "name", "print name", "printed name", "full name",
        "client name", "employee name", "contractor name",
        "landlord", "tenant", "buyer", "seller"
    ]

    EMAIL_KEYWORDS = ["email", "e-mail", "email address"]

    INITIALS_KEYWORDS = ["initials", "initial here", "initial"]

    # Role inference keywords - maps role_key to keywords that indicate it
    ROLE_KEYWORDS = {
        "client": ["client", "customer", "buyer", "purchaser", "party a", "first party"],
        "contractor": ["contractor", "consultant", "freelancer", "vendor"],
        "employee": ["employee", "worker", "staff", "team member"],
        "company": ["company", "employer", "corporation", "business", "party b", "second party"],
        "landlord": ["landlord", "lessor", "property owner", "owner"],
        "tenant": ["tenant", "renter", "lessee", "occupant"],
        "seller": ["seller", "vendor"],
        "borrower": ["borrower", "debtor"],
        "lender": ["lender", "creditor", "bank"],
        "witness": ["witness"],
        "guarantor": ["guarantor", "co-signer", "cosigner"],
    }

    # Legacy mapping for backward compatibility
    LEGACY_ROLE_MAP = {
        "client": FieldOwner.SIGNER_1,
        "employee": FieldOwner.SIGNER_1,
        "contractor": FieldOwner.SIGNER_1,
        "tenant": FieldOwner.SIGNER_1,
        "buyer": FieldOwner.SIGNER_1,
        "borrower": FieldOwner.SIGNER_1,
        "company": FieldOwner.SIGNER_2,
        "employer": FieldOwner.SIGNER_2,
        "landlord": FieldOwner.SIGNER_2,
        "seller": FieldOwner.SIGNER_2,
        "lender": FieldOwner.SIGNER_2,
        "witness": FieldOwner.SIGNER_2,
        "guarantor": FieldOwner.SIGNER_2,
    }

    def __init__(self, dpi: int = 150):
        self.dpi = dpi
        self.zoom = dpi / 72  # PDF default is 72 DPI

    async def detect_fields(
        self,
        document_id: str,
        file_path: Path,
        text_layout: dict[str, Any] | None = None,
    ) -> DetectionResult:
        """
        Detect form fields in a PDF document.

        Args:
            document_id: Document ID
            file_path: Path to PDF file
            text_layout: Pre-extracted text layout (optional)

        Returns:
            DetectionResult with detected fields
        """
        start_time = time.time()
        all_candidates: list[DetectedField] = []

        doc = fitz.open(file_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_number = page_num + 1

            # Get page dimensions
            page_rect = page.rect

            # Extract text and layout if not provided
            if text_layout:
                page_layout = text_layout.get("pages", [])[page_num] if page_num < len(text_layout.get("pages", [])) else None
            else:
                page_layout = self._extract_page_layout(page)

            # Strategy 1: Detect underlines and blank spaces
            underline_candidates = self._detect_underlines(page, page_number, page_layout)
            all_candidates.extend(underline_candidates)

            # Strategy 2: Detect checkboxes
            checkbox_candidates = self._detect_checkboxes(page, page_number)
            all_candidates.extend(checkbox_candidates)

            # Strategy 3: Detect signature areas based on keywords
            signature_candidates = self._detect_signature_areas(page, page_number, page_layout)
            all_candidates.extend(signature_candidates)

            # Strategy 4: Detect anchor text tags [type|role]
            anchor_candidates = self._detect_anchor_tags(page, page_number)
            all_candidates.extend(anchor_candidates)

        doc.close()

        # Deduplicate overlapping candidates
        deduplicated = self._deduplicate_candidates(all_candidates)

        # Filter by confidence threshold
        filtered = [
            c for c in deduplicated
            if c.detection_confidence >= settings.detection_confidence_threshold
        ]

        detection_time_ms = (time.time() - start_time) * 1000

        return DetectionResult(
            document_id=document_id,
            detected_fields=filtered,
            detection_time_ms=detection_time_ms,
            total_candidates=len(all_candidates),
            filtered_candidates=len(filtered),
        )

    def _extract_page_layout(self, page: fitz.Page) -> dict[str, Any]:
        """Extract text layout from a page."""
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        layout = {
            "page_number": page.number + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "lines": [],
            "words": [],
        }

        for block in blocks.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    line_text = ""
                    line_bbox = line.get("bbox", [0, 0, 0, 0])

                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        span_bbox = span.get("bbox", [0, 0, 0, 0])
                        line_text += span_text

                        if span_text.strip():
                            layout["words"].append({
                                "text": span_text,
                                "bbox": {
                                    "x": span_bbox[0],
                                    "y": span_bbox[1],
                                    "width": span_bbox[2] - span_bbox[0],
                                    "height": span_bbox[3] - span_bbox[1],
                                },
                            })

                    layout["lines"].append({
                        "text": line_text,
                        "bbox": {
                            "x": line_bbox[0],
                            "y": line_bbox[1],
                            "width": line_bbox[2] - line_bbox[0],
                            "height": line_bbox[3] - line_bbox[1],
                        },
                    })

        return layout

    def _detect_underlines(
        self,
        page: fitz.Page,
        page_number: int,
        page_layout: dict | None,
    ) -> list[DetectedField]:
        """
        Detect underlines that indicate form fields.

        Looks for:
        - Horizontal lines in the drawing layer
        - Repeated underscores in text
        - Blank spaces after labels
        """
        candidates = []

        # Get drawings (vector graphics)
        drawings = page.get_drawings()

        for path in drawings:
            for item in path.get("items", []):
                if item[0] == "l":  # Line
                    start, end = item[1], item[2]

                    # Check if horizontal (y values similar)
                    if abs(start.y - end.y) < 2:
                        line_width = abs(end.x - start.x)
                        line_y = start.y

                        # Minimum width for a form field
                        if line_width > 50:
                            # Look for nearby text above the line
                            nearby_text, field_type, owner = self._find_nearby_label(
                                page_layout, start.x, line_y, line_width
                            )

                            confidence = 0.7 if nearby_text else 0.5

                            candidates.append(DetectedField(
                                page_number=page_number,
                                bbox=BBox(
                                    x=min(start.x, end.x),
                                    y=line_y - 15,  # Position above line
                                    width=line_width,
                                    height=20,
                                ),
                                field_type=field_type,
                                owner=owner,
                                detection_confidence=confidence,
                                classification_confidence=0.6 if nearby_text else 0.4,
                                owner_confidence=0.5,
                                evidence=f"Underline detected with nearby text: '{nearby_text}'" if nearby_text else "Underline detected (no label)",
                                label=nearby_text,
                                nearby_text=nearby_text,
                            ))

        # Also detect underscores in text
        if page_layout:
            for line in page_layout.get("lines", []):
                text = line.get("text", "")

                # Look for patterns like "Name: _________"
                underscore_match = re.search(r'_{3,}', text)
                if underscore_match:
                    bbox = line.get("bbox", {})
                    label_text = text[:underscore_match.start()].strip()

                    field_type, owner = self._classify_by_label(label_text)

                    candidates.append(DetectedField(
                        page_number=page_number,
                        bbox=BBox(
                            x=bbox.get("x", 0),
                            y=bbox.get("y", 0),
                            width=bbox.get("width", 100),
                            height=bbox.get("height", 20),
                        ),
                        field_type=field_type,
                        owner=owner,
                        detection_confidence=0.8,
                        classification_confidence=0.7 if label_text else 0.5,
                        owner_confidence=0.5,
                        evidence=f"Underscore blank with label: '{label_text}'" if label_text else "Underscore blank detected",
                        label=label_text or None,
                        nearby_text=label_text or None,
                    ))

        return candidates

    def _detect_checkboxes(
        self,
        page: fitz.Page,
        page_number: int,
    ) -> list[DetectedField]:
        """
        Detect checkboxes using vector graphics and form fields.

        Looks for:
        - Small square rectangles
        - Unicode checkbox characters
        - PDF form widgets
        """
        candidates = []

        # Check for existing form widgets
        widgets = page.widgets()
        if widgets:
            for widget in widgets:
                if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    rect = widget.rect
                    candidates.append(DetectedField(
                        page_number=page_number,
                        bbox=BBox(
                            x=rect.x0,
                            y=rect.y0,
                            width=rect.width,
                            height=rect.height,
                        ),
                        field_type=FieldType.CHECKBOX,
                        owner=FieldOwner.SIGNER_1,
                        detection_confidence=0.95,
                        classification_confidence=0.95,
                        owner_confidence=0.5,
                        evidence="PDF checkbox widget detected",
                    ))

        # Look for small square shapes in drawings
        drawings = page.get_drawings()
        for path in drawings:
            rect = path.get("rect")
            if rect:
                width = rect.width
                height = rect.height

                # Checkbox-like dimensions (small square)
                if 8 <= width <= 25 and 8 <= height <= 25 and abs(width - height) < 5:
                    candidates.append(DetectedField(
                        page_number=page_number,
                        bbox=BBox(x=rect.x0, y=rect.y0, width=width, height=height),
                        field_type=FieldType.CHECKBOX,
                        owner=FieldOwner.SIGNER_1,
                        detection_confidence=0.7,
                        classification_confidence=0.8,
                        owner_confidence=0.5,
                        evidence="Small square shape detected (potential checkbox)",
                    ))

        # Look for checkbox characters in text
        text = page.get_text("text")
        checkbox_chars = ["☐", "☑", "☒", "□", "▢", "▣"]

        for char in checkbox_chars:
            if char in text:
                # Find positions of checkbox characters
                text_instances = page.search_for(char)
                for inst in text_instances:
                    candidates.append(DetectedField(
                        page_number=page_number,
                        bbox=BBox(
                            x=inst.x0,
                            y=inst.y0,
                            width=inst.width + 5,
                            height=inst.height + 5,
                        ),
                        field_type=FieldType.CHECKBOX,
                        owner=FieldOwner.SIGNER_1,
                        detection_confidence=0.9,
                        classification_confidence=0.95,
                        owner_confidence=0.5,
                        evidence=f"Checkbox character '{char}' detected",
                    ))

        return candidates

    def _detect_signature_areas(
        self,
        page: fitz.Page,
        page_number: int,
        page_layout: dict | None,
    ) -> list[DetectedField]:
        """
        Detect signature and date areas based on keywords.
        """
        candidates = []

        if not page_layout:
            return candidates

        for line in page_layout.get("lines", []):
            text = line.get("text", "").lower()
            bbox = line.get("bbox", {})

            # Check for signature keywords
            for keyword in self.SIGNATURE_KEYWORDS:
                if keyword in text:
                    # Signature field is typically to the right of or below the label
                    sig_bbox = BBox(
                        x=bbox.get("x", 0) + bbox.get("width", 0) + 10,
                        y=bbox.get("y", 0),
                        width=150,
                        height=40,
                    )

                    role_key, role_confidence = self._infer_role_from_text(text)
                    owner = self._role_to_legacy_owner(role_key)

                    candidates.append(DetectedField(
                        page_number=page_number,
                        bbox=sig_bbox,
                        field_type=FieldType.SIGNATURE,
                        owner=owner,
                        assignee_type=AssigneeType.ROLE,
                        detected_role_key=role_key,
                        detection_confidence=0.8,
                        classification_confidence=0.9,
                        owner_confidence=role_confidence,
                        role_confidence=role_confidence,
                        evidence=f"Signature keyword '{keyword}' detected (inferred role: {role_key})",
                        label=text.strip(),
                        nearby_text=text.strip(),
                    ))
                    break

            # Check for date keywords
            for keyword in self.DATE_KEYWORDS:
                if keyword in text and "signature" not in text:
                    date_bbox = BBox(
                        x=bbox.get("x", 0) + bbox.get("width", 0) + 10,
                        y=bbox.get("y", 0),
                        width=100,
                        height=20,
                    )

                    role_key, role_confidence = self._infer_role_from_text(text)
                    owner = self._role_to_legacy_owner(role_key)

                    candidates.append(DetectedField(
                        page_number=page_number,
                        bbox=date_bbox,
                        field_type=FieldType.DATE_SIGNED,
                        owner=owner,
                        assignee_type=AssigneeType.ROLE,
                        detected_role_key=role_key,
                        detection_confidence=0.75,
                        classification_confidence=0.85,
                        owner_confidence=role_confidence,
                        role_confidence=role_confidence,
                        evidence=f"Date keyword '{keyword}' detected (inferred role: {role_key})",
                        label=text.strip(),
                        nearby_text=text.strip(),
                    ))
                    break

            # Check for initials keywords
            for keyword in self.INITIALS_KEYWORDS:
                if keyword in text:
                    init_bbox = BBox(
                        x=bbox.get("x", 0) + bbox.get("width", 0) + 10,
                        y=bbox.get("y", 0),
                        width=60,
                        height=30,
                    )

                    role_key, role_confidence = self._infer_role_from_text(text)
                    owner = self._role_to_legacy_owner(role_key)

                    candidates.append(DetectedField(
                        page_number=page_number,
                        bbox=init_bbox,
                        field_type=FieldType.INITIALS,
                        owner=owner,
                        assignee_type=AssigneeType.ROLE,
                        detected_role_key=role_key,
                        detection_confidence=0.8,
                        classification_confidence=0.85,
                        owner_confidence=role_confidence,
                        role_confidence=role_confidence,
                        evidence=f"Initials keyword '{keyword}' detected (inferred role: {role_key})",
                        label=text.strip(),
                        nearby_text=text.strip(),
                    ))
                    break

        return candidates

    def _detect_anchor_tags(
        self,
        page: fitz.Page,
        page_number: int,
    ) -> list[DetectedField]:
        """
        Detect anchor text tags in format [type|role] or {{variable}}.

        Supported formats:
        - [sig|role:client] -> Signature field for client role (NEW)
        - [date|role:landlord] -> Date field for landlord role (NEW)
        - [sig|signer1] -> Signature field for Signer 1 (LEGACY, backward compat)
        - [date|signer2] -> Date field for Signer 2 (LEGACY, backward compat)
        - {{effective_date}} -> Sender variable
        """
        candidates = []
        text = page.get_text("text")

        # Map field code to type
        type_map = {
            "sig": FieldType.SIGNATURE,
            "signature": FieldType.SIGNATURE,
            "init": FieldType.INITIALS,
            "initials": FieldType.INITIALS,
            "date": FieldType.DATE_SIGNED,
            "text": FieldType.TEXT,
            "name": FieldType.NAME,
            "email": FieldType.EMAIL,
            "check": FieldType.CHECKBOX,
            "checkbox": FieldType.CHECKBOX,
        }

        # Pattern for new format [type|role:key]
        new_anchor_pattern = r'\[(\w+)\|role:(\w+)\]'
        for match in re.finditer(new_anchor_pattern, text):
            field_code = match.group(1).lower()
            role_key = match.group(2).lower()

            # Find position
            instances = page.search_for(match.group(0))
            if not instances:
                continue

            rect = instances[0]
            field_type = type_map.get(field_code, FieldType.TEXT)

            # Calculate appropriate size based on field type
            width = 150 if field_type == FieldType.SIGNATURE else (100 if field_type == FieldType.NAME else 80)
            height = 40 if field_type in [FieldType.SIGNATURE, FieldType.INITIALS] else 20

            candidates.append(DetectedField(
                page_number=page_number,
                bbox=BBox(x=rect.x0, y=rect.y0, width=width, height=height),
                field_type=field_type,
                owner=self._role_to_legacy_owner(role_key),  # Legacy compatibility
                assignee_type=AssigneeType.ROLE,
                detected_role_key=role_key,
                detection_confidence=0.95,
                classification_confidence=0.95,
                owner_confidence=0.95,
                role_confidence=0.95,
                evidence=f"Anchor tag '{match.group(0)}' detected (role: {role_key})",
                label=match.group(0),
            ))

        # Pattern for legacy format [type|signerN] or [type|sender]
        legacy_anchor_pattern = r'\[(\w+)\|(\w+)\]'
        for match in re.finditer(legacy_anchor_pattern, text):
            # Skip if already matched by new pattern
            if ":role:" in match.group(0).lower() or "role:" in match.group(0).lower():
                continue

            field_code = match.group(1).lower()
            role_code = match.group(2).lower()

            # Find position
            instances = page.search_for(match.group(0))
            if not instances:
                continue

            rect = instances[0]
            field_type = type_map.get(field_code, FieldType.TEXT)

            # Map legacy role code to owner and role_key
            legacy_role_map = {
                "signer1": ("signer_1", FieldOwner.SIGNER_1),
                "signer_1": ("signer_1", FieldOwner.SIGNER_1),
                "s1": ("signer_1", FieldOwner.SIGNER_1),
                "signer2": ("signer_2", FieldOwner.SIGNER_2),
                "signer_2": ("signer_2", FieldOwner.SIGNER_2),
                "s2": ("signer_2", FieldOwner.SIGNER_2),
                "sender": (None, FieldOwner.SENDER),
            }

            role_key, owner = legacy_role_map.get(role_code, ("signer_1", FieldOwner.SIGNER_1))
            assignee_type = AssigneeType.SENDER if owner == FieldOwner.SENDER else AssigneeType.ROLE

            # Calculate appropriate size based on field type
            width = 150 if field_type == FieldType.SIGNATURE else (100 if field_type == FieldType.NAME else 80)
            height = 40 if field_type in [FieldType.SIGNATURE, FieldType.INITIALS] else 20

            candidates.append(DetectedField(
                page_number=page_number,
                bbox=BBox(x=rect.x0, y=rect.y0, width=width, height=height),
                field_type=field_type,
                owner=owner,
                assignee_type=assignee_type,
                detected_role_key=role_key,
                detection_confidence=0.95,
                classification_confidence=0.95,
                owner_confidence=0.95,
                role_confidence=0.95,
                evidence=f"Anchor tag '{match.group(0)}' detected",
                label=match.group(0),
            ))

        # Pattern for {{variable}} (sender variables)
        var_pattern = r'\{\{(\w+)\}\}'
        for match in re.finditer(var_pattern, text):
            var_name = match.group(1)

            instances = page.search_for(match.group(0))
            if not instances:
                continue

            rect = instances[0]

            candidates.append(DetectedField(
                page_number=page_number,
                bbox=BBox(x=rect.x0, y=rect.y0, width=100, height=20),
                field_type=FieldType.TEXT,
                owner=FieldOwner.SENDER,
                assignee_type=AssigneeType.SENDER,
                detected_role_key=None,
                detection_confidence=0.95,
                classification_confidence=0.9,
                owner_confidence=0.95,
                role_confidence=0.95,
                evidence=f"Sender variable tag '{{{{{var_name}}}}}' detected",
                label=var_name,
            ))

        return candidates

    def _find_nearby_label(
        self,
        page_layout: dict | None,
        x: float,
        y: float,
        width: float,
    ) -> tuple[str | None, FieldType, FieldOwner]:
        """Find text label near a detected field position."""
        if not page_layout:
            return None, FieldType.TEXT, FieldOwner.SIGNER_1

        best_label = None
        best_distance = float("inf")

        for word in page_layout.get("words", []):
            word_bbox = word.get("bbox", {})
            word_x = word_bbox.get("x", 0)
            word_y = word_bbox.get("y", 0)

            # Check if word is above or to the left of the field
            if word_y <= y and word_x <= x + width:
                distance = abs(y - word_y) + abs(x - word_x)
                if distance < best_distance and distance < 100:
                    best_distance = distance
                    best_label = word.get("text", "")

        if best_label:
            field_type, owner = self._classify_by_label(best_label)
            return best_label, field_type, owner

        return None, FieldType.TEXT, FieldOwner.SIGNER_1

    def _classify_by_label(self, label: str) -> tuple[FieldType, FieldOwner]:
        """Classify field type and owner based on label text."""
        label_lower = label.lower()

        # Determine field type
        field_type = FieldType.TEXT

        for keyword in self.SIGNATURE_KEYWORDS:
            if keyword in label_lower:
                field_type = FieldType.SIGNATURE
                break

        if field_type == FieldType.TEXT:
            for keyword in self.DATE_KEYWORDS:
                if keyword in label_lower:
                    field_type = FieldType.DATE_SIGNED
                    break

        if field_type == FieldType.TEXT:
            for keyword in self.NAME_KEYWORDS:
                if keyword in label_lower:
                    field_type = FieldType.NAME
                    break

        if field_type == FieldType.TEXT:
            for keyword in self.EMAIL_KEYWORDS:
                if keyword in label_lower:
                    field_type = FieldType.EMAIL
                    break

        if field_type == FieldType.TEXT:
            for keyword in self.INITIALS_KEYWORDS:
                if keyword in label_lower:
                    field_type = FieldType.INITIALS
                    break

        # Determine owner
        owner = self._infer_owner_from_text(label_lower)

        return field_type, owner

    def _infer_role_from_text(self, text: str) -> tuple[str, float]:
        """
        Infer role key based on surrounding text.

        Returns:
            Tuple of (role_key, confidence)
        """
        text_lower = text.lower()

        for role_key, keywords in self.ROLE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return role_key, 0.7

        # Default to "signer" if no specific role detected
        return "signer", 0.3

    def _role_to_legacy_owner(self, role_key: str) -> FieldOwner:
        """Convert role key to legacy FieldOwner for backward compatibility."""
        return self.LEGACY_ROLE_MAP.get(role_key, FieldOwner.SIGNER_1)

    def _infer_owner_from_text(self, text: str) -> FieldOwner:
        """DEPRECATED: Use _infer_role_from_text instead."""
        role_key, _ = self._infer_role_from_text(text)
        return self._role_to_legacy_owner(role_key)

    def _deduplicate_candidates(
        self,
        candidates: list[DetectedField],
    ) -> list[DetectedField]:
        """Remove overlapping field candidates, keeping higher confidence ones."""
        if not candidates:
            return []

        # Sort by confidence (descending)
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.detection_confidence,
            reverse=True,
        )

        kept = []
        for candidate in sorted_candidates:
            overlaps = False
            for existing in kept:
                if (
                    existing.page_number == candidate.page_number
                    and self._boxes_overlap(existing.bbox, candidate.bbox)
                ):
                    overlaps = True
                    break

            if not overlaps:
                kept.append(candidate)

        return kept

    def _boxes_overlap(self, box1: BBox, box2: BBox, threshold: float = 0.5) -> bool:
        """Check if two bounding boxes overlap significantly."""
        x1_min, x1_max = box1.x, box1.x + box1.width
        y1_min, y1_max = box1.y, box1.y + box1.height
        x2_min, x2_max = box2.x, box2.x + box2.width
        y2_min, y2_max = box2.y, box2.y + box2.height

        # Calculate intersection
        inter_x = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
        inter_y = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
        inter_area = inter_x * inter_y

        # Calculate areas
        area1 = box1.width * box1.height
        area2 = box2.width * box2.height

        if area1 == 0 or area2 == 0:
            return False

        # Check if intersection is significant relative to either box
        overlap1 = inter_area / area1
        overlap2 = inter_area / area2

        return overlap1 > threshold or overlap2 > threshold


# Singleton instance
field_detector = FieldDetector()
