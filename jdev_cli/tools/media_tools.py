"""Media Tools - Image and PDF reading for Claude Code parity.

Claude Code parity: Implements multimodal file reading:
- Image files (PNG, JPG, GIF, WebP, SVG)
- PDF files (text extraction + page info)

Author: Juan CS
Date: 2025-11-26
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .base import Tool, ToolCategory, ToolResult

logger = logging.getLogger(__name__)


# =============================================================================
# IMAGE READING
# =============================================================================

@dataclass
class ImageInfo:
    """Information about an image file."""

    path: str
    format: str
    width: int
    height: int
    size_bytes: int
    mime_type: str
    base64_data: Optional[str] = None


class ImageReadTool(Tool):
    """Read image files and extract metadata.

    Claude Code parity: Read images for multimodal analysis.

    Supported formats:
    - PNG, JPG/JPEG, GIF, WebP, SVG
    - Returns dimensions, format, and optionally base64 data

    Note: For actual image understanding, the base64 data should be
    passed to a multimodal LLM (like Gemini Vision or Claude Vision).
    """

    # Supported image formats
    SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"}

    def __init__(self):
        super().__init__()
        self.name = "image_read"
        self.category = ToolCategory.FILE_READ
        self.description = "Read image files and extract metadata"
        self.parameters = {
            "file_path": {
                "type": "string",
                "description": "Path to the image file",
                "required": True
            },
            "include_base64": {
                "type": "boolean",
                "description": "Include base64-encoded image data (default: False)",
                "required": False
            },
            "max_size_mb": {
                "type": "number",
                "description": "Maximum file size in MB to process (default: 10)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Read image file."""
        file_path = kwargs.get("file_path", "")
        include_base64 = kwargs.get("include_base64", False)
        max_size_mb = kwargs.get("max_size_mb", 10)

        if not file_path:
            return ToolResult(success=False, error="file_path is required")

        path = Path(file_path)

        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")

        if not path.is_file():
            return ToolResult(success=False, error=f"Not a file: {file_path}")

        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            return ToolResult(
                success=False,
                error=f"Unsupported format: {suffix}. Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Check file size
        size_bytes = path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        if size_mb > max_size_mb:
            return ToolResult(
                success=False,
                error=f"File too large: {size_mb:.1f}MB > {max_size_mb}MB limit"
            )

        try:
            # Get image dimensions
            width, height = self._get_image_dimensions(path)

            # Get MIME type
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type:
                mime_type = f"image/{suffix[1:]}"

            # Optionally include base64 data
            base64_data = None
            if include_base64:
                with open(path, "rb") as f:
                    base64_data = base64.b64encode(f.read()).decode("utf-8")

            image_info = ImageInfo(
                path=str(path),
                format=suffix[1:].upper(),
                width=width,
                height=height,
                size_bytes=size_bytes,
                mime_type=mime_type,
                base64_data=base64_data
            )

            return ToolResult(
                success=True,
                data={
                    "path": image_info.path,
                    "format": image_info.format,
                    "dimensions": f"{width}x{height}",
                    "width": width,
                    "height": height,
                    "size_bytes": size_bytes,
                    "size_human": self._human_size(size_bytes),
                    "mime_type": mime_type,
                    "base64": base64_data[:100] + "..." if base64_data else None,
                    "base64_full": base64_data if include_base64 else None,
                },
                metadata={
                    "format": image_info.format,
                    "has_base64": base64_data is not None
                }
            )
        except Exception as e:
            logger.error(f"Error reading image: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_image_dimensions(self, path: Path) -> Tuple[int, int]:
        """Get image dimensions without external dependencies."""
        suffix = path.suffix.lower()

        with open(path, "rb") as f:
            data = f.read(32)

            if suffix == ".png":
                return self._png_dimensions(data)
            elif suffix in (".jpg", ".jpeg"):
                f.seek(0)
                return self._jpeg_dimensions(f)
            elif suffix == ".gif":
                return self._gif_dimensions(data)
            elif suffix == ".webp":
                f.seek(0)
                return self._webp_dimensions(f.read(30))
            elif suffix == ".bmp":
                return self._bmp_dimensions(data)
            elif suffix == ".svg":
                f.seek(0)
                return self._svg_dimensions(f.read().decode("utf-8", errors="ignore"))
            else:
                return (0, 0)

    def _png_dimensions(self, data: bytes) -> Tuple[int, int]:
        """Extract dimensions from PNG header."""
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            return (0, 0)
        width = struct.unpack(">I", data[16:20])[0]
        height = struct.unpack(">I", data[20:24])[0]
        return (width, height)

    def _jpeg_dimensions(self, f) -> Tuple[int, int]:
        """Extract dimensions from JPEG."""
        f.seek(0)
        data = f.read(2)
        if data != b'\xff\xd8':
            return (0, 0)

        while True:
            marker = f.read(2)
            if len(marker) < 2:
                break
            if marker[0] != 0xff:
                break

            marker_type = marker[1]

            # SOF markers contain dimensions
            if marker_type in (0xc0, 0xc1, 0xc2, 0xc3):
                f.read(3)  # Skip length and precision
                height = struct.unpack(">H", f.read(2))[0]
                width = struct.unpack(">H", f.read(2))[0]
                return (width, height)

            # Skip other segments
            if marker_type != 0xd8 and marker_type != 0xd9:
                length = struct.unpack(">H", f.read(2))[0]
                f.seek(length - 2, 1)

        return (0, 0)

    def _gif_dimensions(self, data: bytes) -> Tuple[int, int]:
        """Extract dimensions from GIF header."""
        if data[:6] not in (b'GIF87a', b'GIF89a'):
            return (0, 0)
        width = struct.unpack("<H", data[6:8])[0]
        height = struct.unpack("<H", data[8:10])[0]
        return (width, height)

    def _webp_dimensions(self, data: bytes) -> Tuple[int, int]:
        """Extract dimensions from WebP header."""
        if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
            return (0, 0)

        # VP8 format
        if data[12:16] == b'VP8 ':
            # Skip to dimensions
            width = struct.unpack("<H", data[26:28])[0] & 0x3fff
            height = struct.unpack("<H", data[28:30])[0] & 0x3fff
            return (width, height)

        # VP8L format
        if data[12:16] == b'VP8L':
            bits = struct.unpack("<I", data[21:25])[0]
            width = (bits & 0x3fff) + 1
            height = ((bits >> 14) & 0x3fff) + 1
            return (width, height)

        return (0, 0)

    def _bmp_dimensions(self, data: bytes) -> Tuple[int, int]:
        """Extract dimensions from BMP header."""
        if data[:2] != b'BM':
            return (0, 0)
        width = struct.unpack("<I", data[18:22])[0]
        height = abs(struct.unpack("<i", data[22:26])[0])
        return (width, height)

    def _svg_dimensions(self, content: str) -> Tuple[int, int]:
        """Extract dimensions from SVG."""
        import re

        # Try to find width/height attributes
        width_match = re.search(r'width=["\'](\d+)', content)
        height_match = re.search(r'height=["\'](\d+)', content)

        width = int(width_match.group(1)) if width_match else 0
        height = int(height_match.group(1)) if height_match else 0

        # Try viewBox if no explicit dimensions
        if width == 0 or height == 0:
            viewbox_match = re.search(r'viewBox=["\'][\d\s.]+\s+([\d.]+)\s+([\d.]+)', content)
            if viewbox_match:
                width = int(float(viewbox_match.group(1)))
                height = int(float(viewbox_match.group(2)))

        return (width, height)

    def _human_size(self, size_bytes: int) -> str:
        """Convert bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# =============================================================================
# PDF READING
# =============================================================================

@dataclass
class PDFInfo:
    """Information about a PDF file."""

    path: str
    pages: int
    size_bytes: int
    title: Optional[str] = None
    author: Optional[str] = None
    text_content: Optional[str] = None


class PDFReadTool(Tool):
    """Read PDF files and extract text content.

    Claude Code parity: Read PDFs for text analysis.

    Features:
    - Extract text content from PDF
    - Get page count and metadata
    - Works without external dependencies (basic extraction)

    For better PDF parsing, install pypdf: pip install pypdf
    """

    def __init__(self):
        super().__init__()
        self.name = "pdf_read"
        self.category = ToolCategory.FILE_READ
        self.description = "Read PDF files and extract text content"
        self.parameters = {
            "file_path": {
                "type": "string",
                "description": "Path to the PDF file",
                "required": True
            },
            "pages": {
                "type": "string",
                "description": "Page range to extract (e.g., '1-5', 'all'). Default: 'all'",
                "required": False
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to extract (default: 50000)",
                "required": False
            }
        }
        self._has_pypdf = self._check_pypdf()

    def _check_pypdf(self) -> bool:
        """Check if pypdf is available."""
        try:
            import pypdf
            return True
        except ImportError:
            return False

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Read PDF file."""
        file_path = kwargs.get("file_path", "")
        pages_spec = kwargs.get("pages", "all")
        max_chars = kwargs.get("max_chars", 50000)

        if not file_path:
            return ToolResult(success=False, error="file_path is required")

        path = Path(file_path)

        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")

        if path.suffix.lower() != ".pdf":
            return ToolResult(success=False, error="File must be a PDF")

        size_bytes = path.stat().st_size

        try:
            if self._has_pypdf:
                return await self._read_with_pypdf(path, pages_spec, max_chars, size_bytes)
            else:
                return await self._read_basic(path, pages_spec, max_chars, size_bytes)
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return ToolResult(success=False, error=str(e))

    async def _read_with_pypdf(
        self, path: Path, pages_spec: str, max_chars: int, size_bytes: int
    ) -> ToolResult:
        """Read PDF using pypdf library."""
        import pypdf

        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)

            total_pages = len(reader.pages)
            metadata = reader.metadata or {}

            # Parse page range
            page_indices = self._parse_page_range(pages_spec, total_pages)

            # Extract text
            text_parts = []
            chars_extracted = 0

            for idx in page_indices:
                if chars_extracted >= max_chars:
                    break

                page = reader.pages[idx]
                page_text = page.extract_text() or ""

                remaining = max_chars - chars_extracted
                if len(page_text) > remaining:
                    page_text = page_text[:remaining] + "..."

                text_parts.append(f"--- Page {idx + 1} ---\n{page_text}")
                chars_extracted += len(page_text)

            text_content = "\n\n".join(text_parts)

            return ToolResult(
                success=True,
                data={
                    "path": str(path),
                    "pages": total_pages,
                    "pages_extracted": len(page_indices),
                    "size_bytes": size_bytes,
                    "size_human": self._human_size(size_bytes),
                    "title": metadata.get("/Title", ""),
                    "author": metadata.get("/Author", ""),
                    "text_content": text_content,
                    "chars_extracted": chars_extracted,
                    "truncated": chars_extracted >= max_chars,
                },
                metadata={
                    "parser": "pypdf",
                    "total_pages": total_pages
                }
            )

    async def _read_basic(
        self, path: Path, pages_spec: str, max_chars: int, size_bytes: int
    ) -> ToolResult:
        """Basic PDF reading without external dependencies."""
        # Basic PDF text extraction using regex
        import re

        with open(path, "rb") as f:
            content = f.read()

        # Try to decode as text
        try:
            text = content.decode("latin-1")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="ignore")

        # Count pages (basic heuristic)
        page_count = len(re.findall(rb'/Type\s*/Page[^s]', content))

        # Extract text between stream markers (very basic)
        text_parts = []
        stream_pattern = re.compile(r'stream\s*(.*?)\s*endstream', re.DOTALL)

        for match in stream_pattern.finditer(text):
            stream_content = match.group(1)
            # Try to extract readable text
            readable = re.sub(r'[^\x20-\x7E\n]', '', stream_content)
            if len(readable) > 50:  # Only include meaningful content
                text_parts.append(readable[:1000])

        extracted_text = "\n".join(text_parts)[:max_chars]

        return ToolResult(
            success=True,
            data={
                "path": str(path),
                "pages": page_count or 1,
                "size_bytes": size_bytes,
                "size_human": self._human_size(size_bytes),
                "text_content": extracted_text or "(Could not extract text. Install pypdf for better results)",
                "chars_extracted": len(extracted_text),
                "warning": "Basic extraction. Install pypdf for better results: pip install pypdf"
            },
            metadata={
                "parser": "basic",
                "total_pages": page_count
            }
        )

    def _parse_page_range(self, spec: str, total: int) -> List[int]:
        """Parse page range specification."""
        if spec.lower() == "all":
            return list(range(total))

        indices = []
        for part in spec.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                start = int(start) - 1  # Convert to 0-indexed
                end = int(end)
                indices.extend(range(max(0, start), min(end, total)))
            else:
                idx = int(part) - 1
                if 0 <= idx < total:
                    indices.append(idx)

        return sorted(set(indices))

    def _human_size(self, size_bytes: int) -> str:
        """Convert bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# =============================================================================
# SCREENSHOT TOOL
# =============================================================================

class ScreenshotReadTool(Tool):
    """Read screenshot files for analysis.

    Claude Code parity: Handles screenshot paths from user input.
    Delegates to ImageReadTool for actual processing.
    """

    def __init__(self):
        super().__init__()
        self.name = "screenshot_read"
        self.category = ToolCategory.FILE_READ
        self.description = "Read screenshot files (delegates to image_read)"
        self.parameters = {
            "file_path": {
                "type": "string",
                "description": "Path to the screenshot file",
                "required": True
            },
            "include_base64": {
                "type": "boolean",
                "description": "Include base64-encoded data for LLM analysis",
                "required": False
            }
        }
        self._image_tool = ImageReadTool()

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Read screenshot file."""
        # Delegate to ImageReadTool
        result = await self._image_tool._execute_validated(**kwargs)

        if result.success:
            result.data["type"] = "screenshot"

        return result


# =============================================================================
# REGISTRY HELPER
# =============================================================================

def get_media_tools() -> List[Tool]:
    """Get all media tools."""
    return [
        ImageReadTool(),
        PDFReadTool(),
        ScreenshotReadTool(),
    ]
