"""Finite-frame missing-outcome bounds, without inferential statistics."""

from youtube_niche_mcp.analysis.numerics import ratio


def bounds(n: int, h: int, u: int, enumerated: bool):
    if any(type(v) is not int or v < 0 for v in (n, h, u)) or h + u > n:
        raise ValueError("Consistent nonnegative finite counts required")
    if not enumerated:
        return {
            "state": "finite_frame_not_established",
            "n": n,
            "h": h,
            "u": u,
            "lower": None,
            "upper": None,
        }
    return {
        "state": "available" if n else "insufficient_sample",
        "n": n,
        "h": h,
        "u": u,
        "lower": ratio(h, n),
        "upper": ratio(h + u, n),
    }
