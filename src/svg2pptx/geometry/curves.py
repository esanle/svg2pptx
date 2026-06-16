"""Bezier curve and arc approximation utilities."""

import math
from typing import Optional


def bezier_to_lines(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: Optional[tuple[float, float]] = None,
    tolerance: float = 1.0,
) -> list[tuple[float, float]]:
    """
    Approximate a Bezier curve with line segments.

    Supports both quadratic (3 points) and cubic (4 points) Bezier curves.
    Uses recursive subdivision based on flatness.

    Args:
        p0: Start point (x, y).
        p1: First control point (x, y).
        p2: Second control point or end point for quadratic (x, y).
        p3: End point for cubic curves (x, y), None for quadratic.
        tolerance: Maximum allowed deviation from the curve.
            Lower values = more segments = smoother curves.

    Returns:
        List of points (excluding start point p0).
    """
    if p3 is None:
        # Quadratic Bezier - convert to cubic
        # Cubic control points from quadratic: 
        # cp1 = p0 + 2/3 * (p1 - p0)
        # cp2 = p2 + 2/3 * (p1 - p2)
        cp1 = (
            p0[0] + 2 / 3 * (p1[0] - p0[0]),
            p0[1] + 2 / 3 * (p1[1] - p0[1]),
        )
        cp2 = (
            p2[0] + 2 / 3 * (p1[0] - p2[0]),
            p2[1] + 2 / 3 * (p1[1] - p2[1]),
        )
        return _cubic_bezier_to_lines(p0, cp1, cp2, p2, tolerance)
    else:
        return _cubic_bezier_to_lines(p0, p1, p2, p3, tolerance)


def _cubic_bezier_to_lines(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    tolerance: float,
) -> list[tuple[float, float]]:
    """
    Approximate a cubic Bezier curve using recursive subdivision.

    Uses the flatness test: if the control points are close enough to the
    line from start to end, treat it as a line segment.
    """
    # Flatness test: check if control points are within tolerance of the line p0-p3
    if _is_flat(p0, p1, p2, p3, tolerance):
        return [p3]

    # Subdivide using de Casteljau's algorithm at t=0.5
    p01 = _midpoint(p0, p1)
    p12 = _midpoint(p1, p2)
    p23 = _midpoint(p2, p3)
    p012 = _midpoint(p01, p12)
    p123 = _midpoint(p12, p23)
    p0123 = _midpoint(p012, p123)

    # Recursively subdivide both halves
    left = _cubic_bezier_to_lines(p0, p01, p012, p0123, tolerance)
    right = _cubic_bezier_to_lines(p0123, p123, p23, p3, tolerance)

    return left + right


def _is_flat(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    tolerance: float,
) -> bool:
    """Check if the curve is flat enough to be approximated by a line."""
    # Distance from control points to the line p0-p3
    ux = 3 * p1[0] - 2 * p0[0] - p3[0]
    uy = 3 * p1[1] - 2 * p0[1] - p3[1]
    vx = 3 * p2[0] - 2 * p3[0] - p0[0]
    vy = 3 * p2[1] - 2 * p3[1] - p0[1]

    max_dist_sq = max(ux * ux + uy * uy, vx * vx + vy * vy)
    return max_dist_sq <= 16 * tolerance * tolerance


def _midpoint(
    p1: tuple[float, float], p2: tuple[float, float]
) -> tuple[float, float]:
    """Calculate the midpoint between two points."""
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)


def arc_to_lines(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    start_angle: float,
    end_angle: float,
    tolerance: float = 1.0,
) -> list[tuple[float, float]]:
    """
    Approximate an elliptical arc with line segments.

    Args:
        cx: Center X coordinate.
        cy: Center Y coordinate.
        rx: Radius in X direction.
        ry: Radius in Y direction.
        start_angle: Start angle in radians.
        end_angle: End angle in radians.
        tolerance: Approximation tolerance.

    Returns:
        List of points along the arc (excluding start point).
    """
    # Calculate number of segments based on arc length and tolerance
    avg_radius = (abs(rx) + abs(ry)) / 2
    if avg_radius == 0:
        return []

    angle_span = abs(end_angle - start_angle)
    arc_length = avg_radius * angle_span

    # More segments for larger arcs and smaller tolerances
    num_segments = max(
        4, int(math.ceil(arc_length / tolerance))
    )
    num_segments = min(num_segments, 64)  # Cap to avoid freeform render issues

    points = []
    for i in range(1, num_segments + 1):
        t = i / num_segments
        angle = start_angle + t * (end_angle - start_angle)
        x = cx + rx * math.cos(angle)
        y = cy + ry * math.sin(angle)
        points.append((x, y))

    return points


def svg_arc_to_center(
    x1: float,
    y1: float,
    rx: float,
    ry: float,
    phi: float,
    large_arc: bool,
    sweep: bool,
    x2: float,
    y2: float,
) -> tuple[float, float, float, float, float, float]:
    """
    Convert SVG arc parameters to center parameterization.

    SVG arcs are defined by endpoints, radii, and flags. This converts to
    center point, start angle, and sweep angle.

    Args:
        x1, y1: Start point.
        rx, ry: Radii.
        phi: X-axis rotation in radians.
        large_arc: Large arc flag.
        sweep: Sweep direction flag.
        x2, y2: End point.

    Returns:
        Tuple of (cx, cy, rx, ry, start_angle, delta_angle).
    """
    # Handle degenerate cases
    if rx == 0 or ry == 0:
        return (x1, y1, 0, 0, 0, 0)

    rx = abs(rx)
    ry = abs(ry)

    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)

    # Step 1: Compute (x1', y1')
    dx = (x1 - x2) / 2
    dy = (y1 - y2) / 2
    x1p = cos_phi * dx + sin_phi * dy
    y1p = -sin_phi * dx + cos_phi * dy

    # Correct out-of-range radii
    lambda_sq = (x1p ** 2) / (rx ** 2) + (y1p ** 2) / (ry ** 2)
    if lambda_sq > 1:
        lambda_val = math.sqrt(lambda_sq)
        rx *= lambda_val
        ry *= lambda_val

    # Step 2: Compute (cx', cy')
    sq = max(
        0,
        (rx ** 2 * ry ** 2 - rx ** 2 * y1p ** 2 - ry ** 2 * x1p ** 2)
        / (rx ** 2 * y1p ** 2 + ry ** 2 * x1p ** 2),
    )
    sq = math.sqrt(sq)
    if large_arc == sweep:
        sq = -sq

    cxp = sq * rx * y1p / ry
    cyp = -sq * ry * x1p / rx

    # Step 3: Compute (cx, cy)
    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2

    # Step 4: Compute start angle and delta angle
    def angle(ux: float, uy: float, vx: float, vy: float) -> float:
        n = math.sqrt(ux ** 2 + uy ** 2)
        c = math.sqrt(vx ** 2 + vy ** 2)
        if n == 0 or c == 0:
            return 0
        cos_angle = (ux * vx + uy * vy) / (n * c)
        cos_angle = max(-1, min(1, cos_angle))  # Clamp for numerical stability
        angle_rad = math.acos(cos_angle)
        if ux * vy - uy * vx < 0:
            angle_rad = -angle_rad
        return angle_rad

    theta1 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dtheta = angle(
        (x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry
    )

    if not sweep and dtheta > 0:
        dtheta -= 2 * math.pi
    elif sweep and dtheta < 0:
        dtheta += 2 * math.pi

    return (cx, cy, rx, ry, theta1, dtheta)


def svg_arc_to_lines(
    x1: float,
    y1: float,
    rx: float,
    ry: float,
    x_axis_rotation: float,
    large_arc_flag: bool,
    sweep_flag: bool,
    x2: float,
    y2: float,
    tolerance: float = 1.0,
) -> list[tuple[float, float]]:
    """
    Convert SVG arc command to line segments.

    Args:
        x1, y1: Start point.
        rx, ry: Radii.
        x_axis_rotation: X-axis rotation in degrees.
        large_arc_flag: Large arc flag (1 = large arc).
        sweep_flag: Sweep direction flag (1 = positive angle).
        x2, y2: End point.
        tolerance: Approximation tolerance.

    Returns:
        List of points (excluding start point, including end point).
    """
    if rx == 0 or ry == 0:
        # Treat as line
        return [(x2, y2)]

    phi = math.radians(x_axis_rotation)
    cx, cy, rx, ry, theta1, dtheta = svg_arc_to_center(
        x1, y1, rx, ry, phi, large_arc_flag, sweep_flag, x2, y2
    )

    # Generate points along the arc
    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)

    avg_radius = (rx + ry) / 2
    arc_length = avg_radius * abs(dtheta)
    # Use tolerance-based segmentation, but cap segments to avoid excessive
    # point counts that render poorly in PowerPoint/LibreOffice freeform shapes.
    num_segments = max(4, int(math.ceil(arc_length / tolerance)))
    num_segments = min(num_segments, 64)

    points = []
    for i in range(1, num_segments + 1):
        t = i / num_segments
        theta = theta1 + t * dtheta
        
        # Point on unit circle
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        
        # Scale by radii and rotate
        x = cx + cos_phi * rx * cos_theta - sin_phi * ry * sin_theta
        y = cy + sin_phi * rx * cos_theta + cos_phi * ry * sin_theta
        points.append((x, y))

    return points
