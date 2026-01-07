"""Document processing service for PDF handling."""

import io
import json
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image

from app.services.storage import storage_service


class DocumentProcessingService:
    """Service for processing PDF documents."""

    def __init__(self):
        """Initialize document processing service."""
        self.dpi = 150  # Resolution for page image rendering

    async def process_document(
        self,
        document_id: str,
        file_path: Path,
    ) -> dict[str, Any]:
        """
        Process a PDF document: render pages, extract text and layout.

        Args:
            document_id: Document ID
            file_path: Path to the PDF file

        Returns:
            Dictionary with page_count, page_images, extracted_text, text_layout
        """
        doc = fitz.open(file_path)
        page_count = len(doc)

        page_images = []
        extracted_text = []
        text_layout = {"pages": []}

        for page_num in range(page_count):
            page = doc[page_num]

            # Render page to image
            image_path = await self._render_page(document_id, page_num + 1, page)
            page_images.append(storage_service.get_file_url(image_path))

            # Extract text
            page_text = page.get_text("text")
            extracted_text.append(page_text)

            # Extract text layout with positions
            page_layout = self._extract_text_layout(page, page_num + 1)
            text_layout["pages"].append(page_layout)

        doc.close()

        return {
            "page_count": page_count,
            "page_images": page_images,
            "extracted_text": "\n\n".join(extracted_text),
            "text_layout": text_layout,
        }

    async def _render_page(
        self,
        document_id: str,
        page_number: int,
        page: fitz.Page,
    ) -> Path:
        """Render a page to PNG image."""
        # Get the zoom factor for desired DPI
        zoom = self.dpi / 72  # PDF default is 72 DPI
        mat = fitz.Matrix(zoom, zoom)

        # Render page to pixmap
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Convert to PIL Image and save
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image_path = storage_service.get_page_image_path(document_id, page_number)
        image_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as PNG
        img.save(image_path, "PNG", optimize=True)

        return image_path

    def _extract_text_layout(
        self,
        page: fitz.Page,
        page_number: int,
    ) -> dict[str, Any]:
        """
        Extract text layout with bounding boxes.

        Returns structured data about text positions for field detection.
        """
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        page_width = page.rect.width
        page_height = page.rect.height

        layout = {
            "page_number": page_number,
            "width": page_width,
            "height": page_height,
            "blocks": [],
            "lines": [],
            "words": [],
        }

        for block in blocks.get("blocks", []):
            if block.get("type") == 0:  # Text block
                block_bbox = block.get("bbox", [])
                block_data = {
                    "bbox": {
                        "x": block_bbox[0] if len(block_bbox) > 0 else 0,
                        "y": block_bbox[1] if len(block_bbox) > 1 else 0,
                        "width": (block_bbox[2] - block_bbox[0])
                        if len(block_bbox) > 2
                        else 0,
                        "height": (block_bbox[3] - block_bbox[1])
                        if len(block_bbox) > 3
                        else 0,
                    },
                    "lines": [],
                }

                for line in block.get("lines", []):
                    line_bbox = line.get("bbox", [])
                    line_text = ""
                    line_words = []

                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        span_bbox = span.get("bbox", [])
                        line_text += span_text

                        if span_text.strip():
                            word_data = {
                                "text": span_text,
                                "bbox": {
                                    "x": span_bbox[0] if len(span_bbox) > 0 else 0,
                                    "y": span_bbox[1] if len(span_bbox) > 1 else 0,
                                    "width": (span_bbox[2] - span_bbox[0])
                                    if len(span_bbox) > 2
                                    else 0,
                                    "height": (span_bbox[3] - span_bbox[1])
                                    if len(span_bbox) > 3
                                    else 0,
                                },
                                "font_size": span.get("size", 12),
                                "font_name": span.get("font", ""),
                            }
                            line_words.append(word_data)
                            layout["words"].append(word_data)

                    line_data = {
                        "text": line_text,
                        "bbox": {
                            "x": line_bbox[0] if len(line_bbox) > 0 else 0,
                            "y": line_bbox[1] if len(line_bbox) > 1 else 0,
                            "width": (line_bbox[2] - line_bbox[0])
                            if len(line_bbox) > 2
                            else 0,
                            "height": (line_bbox[3] - line_bbox[1])
                            if len(line_bbox) > 3
                            else 0,
                        },
                        "words": line_words,
                    }
                    block_data["lines"].append(line_data)
                    layout["lines"].append(line_data)

                layout["blocks"].append(block_data)

        return layout

    def get_page_dimensions(self, file_path: Path) -> list[dict[str, float]]:
        """Get dimensions of all pages in a PDF."""
        doc = fitz.open(file_path)
        dimensions = []

        for page in doc:
            dimensions.append(
                {
                    "width": page.rect.width,
                    "height": page.rect.height,
                }
            )

        doc.close()
        return dimensions

    async def extract_drawings(
        self,
        file_path: Path,
        page_number: int,
    ) -> list[dict[str, Any]]:
        """
        Extract vector drawings from a page (lines, rectangles, etc.).

        This is useful for detecting underlines and checkboxes.
        """
        doc = fitz.open(file_path)
        page = doc[page_number - 1]

        drawings = []
        paths = page.get_drawings()

        for path in paths:
            items = path.get("items", [])
            rect = path.get("rect", fitz.Rect())

            for item in items:
                item_type = item[0]

                if item_type == "l":  # Line
                    # item format: ("l", start_point, end_point)
                    start = item[1]
                    end = item[2]
                    drawings.append(
                        {
                            "type": "line",
                            "start": {"x": start.x, "y": start.y},
                            "end": {"x": end.x, "y": end.y},
                            "width": abs(end.x - start.x),
                            "height": abs(end.y - start.y),
                        }
                    )
                elif item_type == "re":  # Rectangle
                    # item format: ("re", rect)
                    r = item[1]
                    drawings.append(
                        {
                            "type": "rectangle",
                            "bbox": {
                                "x": r.x0,
                                "y": r.y0,
                                "width": r.width,
                                "height": r.height,
                            },
                        }
                    )

        doc.close()
        return drawings


# Singleton instance
document_service = DocumentProcessingService()
