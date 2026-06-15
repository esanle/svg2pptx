"""Parse foreignObject elements from draw.io SVG exports.

Draw.io exports text in <foreignObject> elements containing HTML divs
with inline styles for positioning and formatting. This parser extracts
the text content, position, and styling to create TextElement objects.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional, List

from svg2pptx.parser.elements import TextElement
from svg2pptx.parser.styles import Style, parse_color
from svg2pptx.parser.transforms import Transform


# Namespace for HTML elements within foreignObject
HTML_NS = "http://www.w3.org/1999/xhtml"


def local_tag(tag: str) -> str:
    """Extract local tag name from potentially namespace-qualified tag."""
    if "}" in tag:
        return tag.split("}")[-1]
    return tag


@dataclass
class TextRun:
    """A single run of text with optional formatting."""
    text: str
    bold: bool = False
    color: Optional[str] = None  # hex color override


@dataclass
class ForeignTextContent:
    """Parsed content from a foreignObject element."""
    text_runs: List[TextRun] = field(default_factory=list)
    x: float = 0.0  # margin-left from div
    y: float = 0.0  # padding-top from div
    width: float = 100.0  # width from div
    height: float = 20.0  # estimated from font-size
    font_size: float = 12.0
    font_family: str = "Arial"
    color: str = "#000000"
    bold: bool = False
    text_align: str = "center"  # default for draw.io


def parse_style_dict(style_str: str) -> dict:
    """Parse inline CSS style string into a dictionary."""
    if not style_str:
        return {}
    result = {}
    for declaration in style_str.split(";"):
        if ":" in declaration:
            prop, value = declaration.split(":", 1)
            result[prop.strip().lower()] = value.strip()
    return result


def extract_float(style_dict: dict, prop: str, default: float = 0.0) -> float:
    """Extract a float value from a style property (removing 'px' suffix)."""
    val = style_dict.get(prop, "")
    if not val:
        return default
    # Remove px suffix and parse
    match = re.match(r"([\d.]+)", val)
    if match:
        return float(match.group(1))
    return default


def extract_color(style_dict: dict, prop: str = "color", default: str = "#000000") -> str:
    """Extract and normalize a color value from style."""
    val = style_dict.get(prop, "")
    if not val:
        return default
    parsed = parse_color(val)
    if parsed == "none":
        return default
    return parsed


def parse_foreign_object(
    element: ET.Element,
    parent_style: Style,
    parent_transform: Transform,
) -> Optional[TextElement]:
    """
    Parse a foreignObject element and return a TextElement.

    Args:
        element: The foreignObject XML element.
        parent_style: Parent element's style for inheritance.
        parent_transform: Accumulated transform from parent groups.

    Returns:
        TextElement with parsed text content, position, and styling.
    """
    content = _parse_foreign_content(element)
    if not content.text_runs:
        return None

    # Combine all text runs for the main text
    full_text = "\n".join(run.text for run in content.text_runs)

    # Build style from parsed content
    style = Style(
        fill=content.color,
        stroke="none",
        font_family=content.font_family,
        font_size=content.font_size,
        font_weight="bold" if content.bold else "normal",
        text_anchor="middle" if content.text_align == "center"
                    else "end" if content.text_align == "right"
                    else "start",
    )

    # Create TextElement with position from div styles
    # x and y come from margin-left and padding-top in the div
    text_elem = TextElement(
        text=full_text,
        x=content.x,
        y=content.y,
        style=style,
        transform=parent_transform,
        element_id=element.get("id"),
    )

    # Store additional info for the writer
    # width is needed for proper centering
    text_elem._foreign_width = content.width
    text_elem._foreign_height = content.height
    text_elem._text_runs = content.text_runs

    return text_elem


def _parse_foreign_content(element: ET.Element) -> ForeignTextContent:
    """Parse the HTML content inside a foreignObject."""
    content = ForeignTextContent()

    # Walk through nested divs to find positioning and text
    # The structure is typically:
    #   div[margin-left, padding-top, width] -> outer positioning
    #     div[font-size: 0, color] -> spacing trick
    #       div[font-size, font-family, color] -> actual styling (innermost)
    inner_styled_div = None

    for child in element.iter():
        tag = local_tag(child.tag)
        style_str = child.get("style", "")
        style_dict = parse_style_dict(style_str)

        if tag == "div":
            # Check if this div has positioning info (margin-left, padding-top)
            if "margin-left" in style_dict:
                content.x = extract_float(style_dict, "margin-left")
                content.y = extract_float(style_dict, "padding-top")
                content.width = extract_float(style_dict, "width", 100.0)
                # text-align on the inner color div
                if "text-align" in style_dict:
                    content.text_align = style_dict.get("text-align", "center")

            # Check if this div has actual font info (display: inline-block typically)
            # Skip the spacer div with "font-size: 0"
            font_size = style_dict.get("font-size", "")
            if font_size and not font_size.strip().startswith("0"):
                inner_styled_div = child
                content.font_size = extract_float(style_dict, "font-size", 12.0)
                content.font_family = style_dict.get(
                    "font-family", "Arial"
                ).strip("'\"")
                # Color - inner div color takes precedence
                inner_color = extract_color(style_dict, "color", None)
                if inner_color:
                    content.color = inner_color
                # text-align (inner can override)
                if "text-align" in style_dict:
                    content.text_align = style_dict.get("text-align", "center")
                content.bold = "bold" in style_dict.get(
                    "font-weight", ""
                ).lower()
            elif "color" in style_dict and not inner_styled_div:
                # Outer color div
                outer_color = extract_color(style_dict, "color", None)
                if outer_color and outer_color != "#000000":
                    content.color = outer_color
                if "text-align" in style_dict:
                    content.text_align = style_dict.get("text-align", "center")

    # Now parse text runs from the innermost styled div
    if inner_styled_div is not None:
        runs = _parse_text_runs(inner_styled_div)

        # Check for nested <font style="font-size: ..."> that overrides size
        # If found, use the larger size as the main font size
        max_font_size = content.font_size
        for font_elem in inner_styled_div.iter():
            if local_tag(font_elem.tag) == "font":
                font_style = parse_style_dict(font_elem.get("style", ""))
                if "font-size" in font_style:
                    nested_size = extract_float(font_style, "font-size", 0.0)
                    if nested_size > max_font_size:
                        max_font_size = nested_size
        content.font_size = max_font_size

        if runs:
            content.text_runs = runs

    # Estimate height from font size and number of lines
    num_lines = sum(r.text.count("\n") + 1 for r in content.text_runs) or 1
    content.height = content.font_size * 1.5 * num_lines

    return content


def _parse_text_runs(elem: ET.Element) -> List[TextRun]:
    """Parse text runs from an element, handling <b>, <br>, <font> tags."""
    runs = []

    # Direct text content
    if elem.text:
        runs.append(TextRun(text=elem.text))

    # Process children
    for child in elem:
        tag = local_tag(child.tag)

        if tag == "b":
            # Bold text - recurse to get nested content (e.g., <b><font>...</font></b>)
            inner_runs = _parse_text_runs(child)
            for r in inner_runs:
                # Mark all inner runs as bold
                r.bold = True
                runs.append(r)
            # Text after <b>
            if child.tail:
                runs.append(TextRun(text=child.tail))

        elif tag == "br":
            # Newline - append to previous run or create new one
            if runs:
                runs[-1].text += "\n"
            else:
                runs.append(TextRun(text="\n"))
            # Text after <br>
            if child.tail:
                runs.append(TextRun(text=child.tail))

        elif tag == "font":
            # Font tag with color and/or size attribute
            color = child.get("color")
            parsed_color = parse_color(color) if color else None
            # Recurse into font children to handle nested formatting
            inner_runs = _parse_text_runs(child)
            for r in inner_runs:
                if parsed_color and parsed_color != "none" and not r.color:
                    r.color = parsed_color
                runs.append(r)
            if child.tail:
                runs.append(TextRun(text=child.tail))

        elif tag == "span":
            # Span with style
            span_style = parse_style_dict(child.get("style", ""))
            span_bold = "bold" in span_style.get("font-weight", "").lower()
            span_color = extract_color(span_style, "color", None)
            inner_runs = _parse_text_runs(child)
            for r in inner_runs:
                if span_bold:
                    r.bold = True
                if span_color and not r.color:
                    r.color = span_color
                runs.append(r)
            if child.tail:
                runs.append(TextRun(text=child.tail))

        elif tag == "ul":
            # Bullet list - each li becomes a line with bullet
            for li in child:
                if local_tag(li.tag) == "li":
                    li_text = "".join(li.itertext()).strip()
                    if li_text:
                        runs.append(TextRun(text=f"• {li_text}"))

        elif tag in ("div", "p"):
            # Nested div/p - recurse and treat as a new line
            nested_runs = _parse_text_runs(child)
            # Add a newline before nested div content if there's prior text
            if runs and nested_runs and any(r.text.strip() for r in nested_runs):
                if not runs[-1].text.endswith("\n"):
                    runs[-1].text += "\n"
            runs.extend(nested_runs)

        else:
            # Unknown tag - just get text content
            text = "".join(child.itertext())
            if text.strip():
                runs.append(TextRun(text=text))
            if child.tail:
                runs.append(TextRun(text=child.tail))

    # Filter out empty/whitespace-only runs (but keep newlines)
    runs = [r for r in runs if r.text and (r.text.strip() or r.text == "\n")]

    # Merge adjacent plain runs (same formatting)
    merged = []
    for run in runs:
        if (merged and not run.bold and not run.color
                and not merged[-1].bold and not merged[-1].color):
            merged[-1].text += run.text
        else:
            merged.append(run)

    # Final cleanup: drop runs that are only whitespace/newlines
    merged = [r for r in merged if r.text.strip()]

    return merged