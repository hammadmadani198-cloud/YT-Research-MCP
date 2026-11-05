"""Small public title parser; richer mechanisms and thumbnails require attributed review."""

import re

from youtube_niche_mcp.qualitative.models import PackagingReview


def parse_title(video_id: str, title: str) -> PackagingReview:
    if len(title) > 1000:
        raise ValueError("Bounded title review required")
    mechanisms = ["question" if "?" in title else "statement"]
    if re.search(r"\d", title):
        mechanisms.append("number")
    return PackagingReview(
        video_id=video_id, title_length=len(title), title_mechanisms=tuple(mechanisms)
    )
