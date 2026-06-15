"""Parse <image> elements from SVG, including embedded base64 data URIs.

Handles draw.io and general SVG image elements, extracting the binary
data and positioning information needed to create PPTX picture shapes.
"""

import base64
import re
import xml.etree.ElementTree as ET
from typing import Optional

from svg2pptx.parser.styles import Style, parse_style
from svg2pptx.parser.transforms import Transform, parse_transform
from svg2pptx.geometry.units import parse_length

# Namespace for xlink attributes
XLINK_NS = "http://www.w3.org/1999/xlink"


# Pattern for parsing data URIs: data:image/png;base64,<data>
DATA_URI_PATTERN = re.compile(
    r"data:image/([a-zA-Z+]+);base64,(.*)",
    re.DOTALL,
)


class ImageElement:
    """
    Parsed SVG <image> element.

    Attributes:
        image_bytes: Decoded binary image data (None if not a data URI).
        mime_type: MIME subtype (e.g., "png", "jpeg", "svg+xml").
        x: X position in pixels.
        y: Y position in pixels.
        width: Width in pixels.
        height: Height in pixels.
        style: Image style.
        transform: Accumulated transform.
        element_id: Optional element ID.
        href: Original href (for non-data-URI references).
    """

    def __init__(
        self,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "png",
        x: float = 0.0,
        y: float = 0.0,
        width: float = 0.0,
        height: float = 0.0,
        style: Optional[Style] = None,
        transform: Optional[Transform] = None,
        element_id: Optional[str] = None,
        href: Optional[str] = None,
    ):
        self.image_bytes = image_bytes
        self.mime_type = mime_type
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.style = style or Style()
        self.transform = transform or Transform.identity()
        self.element_id = element_id
        self.href = href

    def __repr__(self) -> str:
        size = len(self.image_bytes) if self.image_bytes else 0
        return (
            f"ImageElement(x={self.x}, y={self.y}, w={self.width}, "
            f"h={self.height}, mime={self.mime_type}, bytes={size})"
        )


def parse_image(
    element: ET.Element,
    parent_style: Optional[Style] = None,
    parent_transform: Optional[Transform] = None,
) -> Optional[ImageElement]:
    """
    Parse an SVG <image> element.

    Args:
        element: The <image> XML element.
        parent_style: Parent element's style for inheritance.
        parent_transform: Accumulated transform from parent groups.

    Returns:
        ImageElement object, or None if parsing fails.
    """
    style = parse_style(element, parent_style)
    local_transform = parse_transform(element.get("transform", ""))
    if parent_transform:
        transform = parent_transform.compose(local_transform)
    else:
        transform = local_transform

    element_id = element.get("id")

    # Get href - try both xlink:href and href
    href = (
        element.get(f"{{{XLINK_NS}}}href")
        or element.get("href")
        or ""
    )

    if not href:
        return None

    image_bytes = None
    mime_type = "png"

    # Parse data URI
    match = DATA_URI_PATTERN.match(href)
    if match:
        mime_type = match.group(1).lower()
        # Normalize common MIME subtypes
        if mime_type == "svg+xml":
            mime_type = "svg"
        elif mime_type == "jpeg":
            mime_type = "jpg"
        try:
            image_bytes = base64.b64decode(match.group(2))
        except Exception:
            return None
    else:
        # Non-data-URI reference (external file) - skip for now
        href = href  # keep reference but no bytes

    # Parse position and dimensions
    x = _safe_parse_length(element.get("x", "0"))
    y = _safe_parse_length(element.get("y", "0"))
    width = _safe_parse_length(element.get("width", "0"))
    height = _safe_parse_length(element.get("height", "0"))

    return ImageElement(
        image_bytes=image_bytes,
        mime_type=mime_type,
        x=x,
        y=y,
        width=width,
        height=height,
        style=style,
        transform=transform,
        element_id=element_id,
        href=href if not image_bytes else None,
    )


def _safe_parse_length(value: str) -> float:
    """Parse a length value, returning 0.0 on failure."""
    if not value:
        return 0.0
    try:
        return parse_length(value)
    except ValueError:
        return 0.0