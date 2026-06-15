"""Configuration options for SVG to PowerPoint conversion."""

from dataclasses import dataclass
from pptx.util import Inches


@dataclass
class Config:
    """
    Configuration settings for SVG to PowerPoint conversion.

    Attributes:
        slide_width: Width of the slide in EMU. Defaults to 13.333 inches (16:9).
        slide_height: Height of the slide in EMU. Defaults to 7.5 inches (16:9).
        scale: Scale factor applied to SVG content. Defaults to 1.0.
        offset_x: Horizontal offset in EMU for placing SVG content.
        offset_y: Vertical offset in EMU for placing SVG content.
        curve_tolerance: Tolerance for Bezier curve approximation.
            Lower values = more line segments = smoother curves.
            Defaults to 1.0.
        preserve_groups: Whether to maintain SVG group structure in PowerPoint.
            Defaults to False (shapes are ungrouped).
        flatten_groups: Whether to flatten all groups into individual shapes.
            Defaults to True (shapes are ungrouped for easier editing).
        default_fill: Default fill color for shapes without fill specified.
            Use "none" for transparent, or a hex color like "#000000".
        default_stroke: Default stroke color when not specified.
        default_stroke_width: Default stroke width in pixels when not specified.
        disable_shadows: Whether to disable shadows on generated shapes.
            Defaults to True.
        convert_text: Whether to convert text elements. Defaults to True.
        convert_shapes: Whether to convert shape elements. Defaults to True.
        convert_images: Whether to convert image elements. Defaults to True.
    """

    slide_width: int = Inches(13.333)
    slide_height: int = Inches(7.5)
    scale: float = 1.0
    offset_x: int = 0
    offset_y: int = 0
    curve_tolerance: float = 1.0
    preserve_groups: bool = False
    flatten_groups: bool = True
    default_fill: str = "none"
    default_stroke: str = "none"
    default_stroke_width: float = 1.0
    disable_shadows: bool = True
    convert_text: bool = True
    convert_shapes: bool = True
    convert_images: bool = True

