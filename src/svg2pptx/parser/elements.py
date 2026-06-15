"""Data classes for parsed SVG elements.

These classes represent the parsed content from SVG elements that
will be converted to PowerPoint shapes.
"""

from dataclasses import dataclass, field
from typing import Optional

from svg2pptx.parser.styles import Style
from svg2pptx.parser.transforms import Transform


@dataclass
class TextElement:
    """
    Parsed SVG text element.

    Attributes:
        text: Text content.
        x: X position.
        y: Y position.
        style: Text style.
        transform: Element transform.
        element_id: Optional element ID.
    """

    text: str
    x: float = 0.0
    y: float = 0.0
    style: Style = field(default_factory=Style)
    transform: Transform = field(default_factory=Transform.identity)
    element_id: Optional[str] = None

    # Additional attributes for foreignObject text (set by parser)
    _foreign_width: float = 0.0
    _foreign_height: float = 0.0
    _text_runs: list = field(default_factory=list)


@dataclass
class GroupElement:
    """
    Parsed SVG group element.

    Attributes:
        children: List of child elements.
        style: Group style.
        transform: Group transform.
        element_id: Optional element ID.
    """

    children: list = field(default_factory=list)
    style: Style = field(default_factory=Style)
    transform: Transform = field(default_factory=Transform.identity)
    element_id: Optional[str] = None