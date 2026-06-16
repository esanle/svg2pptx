"""Render nested SVG icon elements to PNG for high-fidelity embedding.

Complex icons (from nested <svg> with viewBox scaling) convert poorly to
PowerPoint freeform shapes because the many Bezier points render
incompletely at small sizes. This module renders such icon subtrees
directly to PNG using rsvg-convert (falling back to cairosvg) so they
embed as crisp pictures instead.
"""

import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from typing import Optional


# Register SVG namespaces so serialized icons use clean default prefixes
# (rsvg-convert/cairosvg render blank when elements carry ns0: prefixes).
ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def render_svg_element_to_png(
    element,
    width: float,
    height: float,
    scale: int = 4,
) -> Optional[bytes]:
    """
    Render an SVG element (a nested <svg> icon subtree) to PNG bytes.

    Args:
        element: The nested <svg> ElementTree element.
        width: Icon width in SVG pixels.
        height: Icon height in SVG pixels.
        scale: Oversampling factor for higher resolution.

    Returns:
        PNG image bytes, or None if rendering fails.
    """
    if width <= 0 or height <= 0:
        return None

    # Serialize the nested svg element to a standalone SVG document.
    svg_bytes = ET.tostring(element, encoding="utf-8")

    tmp_dir = tempfile.mkdtemp(prefix="svg2pptx_icon_")
    svg_path = os.path.join(tmp_dir, "icon.svg")

    try:
        with open(svg_path, "wb") as f:
            f.write(svg_bytes)

        out_w = max(1, int(width * scale))
        out_h = max(1, int(height * scale))

        png_bytes = _try_rsvg_convert(svg_path, out_w, out_h)
        if png_bytes is None:
            png_bytes = _try_cairosvg(svg_path, out_w, out_h)

        return png_bytes
    except Exception:
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _try_rsvg_convert(svg_path: str, width: int, height: int) -> Optional[bytes]:
    """Render using rsvg-convert if available."""
    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        return None

    # Try output to stdout first (rsvg-convert writes PNG to stdout by default)
    for args in (
        [rsvg, "-w", str(width), "-h", str(height), "-f", "png", svg_path],
        [rsvg, "-w", str(width), "-h", str(height), "-f", "png",
         "-o", "-", svg_path],
    ):
        try:
            result = subprocess.run(args, capture_output=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except (subprocess.TimeoutExpired, OSError):
            continue
    return None


def _try_cairosvg(svg_path: str, width: int, height: int) -> Optional[bytes]:
    """Render using cairosvg if available."""
    try:
        import cairosvg
    except ImportError:
        return None

    try:
        with open(svg_path, "rb") as f:
            svg_data = f.read()
        return cairosvg.svg2png(
            bytestring=svg_data, output_width=width, output_height=height
        )
    except Exception:
        return None


def is_renderer_available() -> bool:
    """Check if at least one SVG-to-PNG renderer is available."""
    if shutil.which("rsvg-convert"):
        return True
    try:
        import cairosvg  # noqa: F401
        return True
    except ImportError:
        return False